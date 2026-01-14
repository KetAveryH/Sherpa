import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import anthropic

from src.storage import InventoryStorage


class ActionType(Enum):
    UPDATE = "UPDATE"
    QUERY = "QUERY"
    LEARN = "LEARN"
    MISSION = "MISSION"
    UNKNOWN = "UNKNOWN"


@dataclass
class SherpaResponse:
    action: ActionType
    changes: dict
    response: str
    is_short: bool
    location: Optional[dict[str, str]] = None
    tip: Optional[str] = None
    mission: Optional[str] = None

    @classmethod
    def from_json(cls, data: dict) -> "SherpaResponse":
        try:
            action = ActionType[data.get("action", "UNKNOWN")]
        except KeyError:
            action = ActionType.UNKNOWN
        return cls(
            action=action,
            changes=data.get("changes", {}),
            response=data.get("response", ""),
            is_short=data.get("response_type", "short") == "short",
            location=data.get("location"),
            tip=data.get("tip"),
            mission=data.get("mission"),
        )

    @classmethod
    def error(cls, message: str) -> "SherpaResponse":
        return cls(
            action=ActionType.UNKNOWN,
            changes={},
            response=message,
            is_short=True,
        )


SYSTEM_PROMPT = """You are Sherpa, a voice inventory assistant for Arc Raiders.

Given the user's command, determine the action and respond with JSON only:

Actions:
- UPDATE: Add/remove/set item counts. Use changes field with item names and values.
  - "+15" means add 15 to current count
  - "-5" means subtract 5 from current count
  - "50" means set to exactly 50
- QUERY: Answer a question about inventory or knowledge
- LEARN: Store new knowledge. Include "location" field for item locations, "tip" field for tips
- MISSION: Set or check mission goals. Include "mission" field to set new mission

Response format:
{{
  "action": "UPDATE|QUERY|LEARN|MISSION",
  "changes": {{"item_name": "+15"}},
  "response": "Natural language response to speak",
  "response_type": "short|long",
  "location": {{"item": "location description"}},
  "tip": "tip text if learning a tip",
  "mission": "mission text if setting mission"
}}

Rules:
- Keep responses concise for voice (under 20 words for short)
- Use "long" response_type only for full inventory lists or detailed info
- If user says "quick answer", always use "short" response_type
- Prioritize newer information over older when conflicts arise
- Item names should be lowercase
- Be helpful and conversational

Current inventory:
{inventory}

Current mission: {mission}

Known locations:
{locations}

Tips:
{tips}"""


class SherpaBrain:
    def __init__(self, storage: InventoryStorage, api_key: str, max_history: int = 20):
        self.storage = storage
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.conversation_history: list[dict] = []
        self.max_history = max_history  # Keep last N messages

    def _build_context(self) -> str:
        items = self.storage.get_all_items()
        inv_str = json.dumps(items, indent=2) if items else "Empty"

        mission = self.storage.get_mission() or "None set"

        locations = {}
        for item in items:
            loc = self.storage.get_location(item)
            if loc:
                locations[item] = loc
        loc_str = json.dumps(locations, indent=2) if locations else "None known"

        tips = self.storage.get_tips()
        tips_str = "\n".join(f"- {t}" for t in tips) if tips else "None"

        return SYSTEM_PROMPT.format(
            inventory=inv_str,
            mission=mission,
            locations=loc_str,
            tips=tips_str,
        )

    async def process_command(self, command: str) -> SherpaResponse:
        try:
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": command})

            # Trim history if too long
            if len(self.conversation_history) > self.max_history:
                self.conversation_history = self.conversation_history[-self.max_history:]

            message = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=self._build_context(),
                messages=self.conversation_history,
            )

            response_text = message.content[0].text

            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                return SherpaResponse.error("I couldn't understand that, try again")

            data = json.loads(json_match.group())
            response = SherpaResponse.from_json(data)

            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": response_text})

            self._apply_changes(response.changes)
            self._apply_knowledge(response)

            return response

        except anthropic.APIError as e:
            return SherpaResponse.error("I'm having trouble thinking, try again")
        except json.JSONDecodeError:
            return SherpaResponse.error("I got confused, could you rephrase that?")

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def _apply_changes(self, changes: dict):
        for item, value in changes.items():
            value_str = str(value)
            try:
                if value_str.startswith("+"):
                    self.storage.update_item(item, int(value_str[1:]), relative=True)
                elif value_str.startswith("-"):
                    self.storage.update_item(item, int(value_str), relative=True)
                else:
                    self.storage.update_item(item, int(value_str), relative=False)
            except ValueError:
                continue  # Skip invalid non-numeric values

    def _apply_knowledge(self, response: SherpaResponse):
        if response.location:
            if isinstance(response.location, dict):
                for item, loc in response.location.items():
                    self.storage.add_location(item, loc)
            # Skip non-dict locations - the LLM occasionally returns string
            # locations which don't match our expected {item: location} format

        if response.tip:
            self.storage.add_tip(response.tip)

        if response.mission:
            self.storage.set_mission(response.mission)
