# Sherpa Bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Discord voice bot that tracks Arc Raiders inventory via voice commands with "Hey Sherpa" wake word.

**Architecture:** Local Python Discord bot captures voice audio, transcribes with mlx-whisper, detects wake word, sends commands to Claude API for processing, and responds via Piper TTS or text channel.

**Tech Stack:** Python 3.11+, discord.py[voice], mlx-whisper, piper-tts, anthropic, ffmpeg

---

## Task 0: System Dependencies

**Step 1: Install Homebrew dependencies**

Run:
```bash
brew install ffmpeg opus
```

**Step 2: Download Piper TTS voice model**

Run:
```bash
mkdir -p ~/.local/share/piper
curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" -o ~/.local/share/piper/en_US-lessac-medium.onnx
curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" -o ~/.local/share/piper/en_US-lessac-medium.onnx.json
```

**Step 3: Verify ffmpeg**

Run: `ffmpeg -version`
Expected: Version info displayed

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `data/inventory.json`
- Create: `data/knowledge.json`

**Step 1: Create requirements.txt**

```txt
discord.py[voice]>=2.3.0
anthropic>=0.40.0
mlx-whisper>=0.4.0
piper-tts>=1.2.0
numpy>=1.24.0
python-dotenv>=1.0.0
```

**Step 2: Create virtual environment and install**

Run:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Step 3: Create directory structure**

Run:
```bash
mkdir -p src data logs
touch src/__init__.py
```

**Step 4: Create initial data files**

`data/inventory.json`:
```json
{
  "items": {},
  "last_updated": null
}
```

`data/knowledge.json`:
```json
{
  "locations": {},
  "tips": [],
  "missions": {
    "current": null
  }
}
```

**Step 5: Commit**

```bash
git add requirements.txt src/ data/
git commit -m "feat: project setup with dependencies and data structure"
```

---

## Task 2: Storage Module

**Files:**
- Create: `src/storage.py`
- Create: `tests/test_storage.py`

**Step 1: Write failing tests**

`tests/test_storage.py`:
```python
import pytest
import json
import tempfile
from pathlib import Path

from src.storage import InventoryStorage


@pytest.fixture
def storage(tmp_path):
    inv_file = tmp_path / "inventory.json"
    know_file = tmp_path / "knowledge.json"
    inv_file.write_text('{"items": {}, "last_updated": null}')
    know_file.write_text('{"locations": {}, "tips": [], "missions": {"current": null}}')
    return InventoryStorage(inv_file, know_file)


def test_get_item_count_empty(storage):
    assert storage.get_item_count("titanium") == 0


def test_update_item_add(storage):
    storage.update_item("titanium", 15)
    assert storage.get_item_count("titanium") == 15


def test_update_item_increment(storage):
    storage.update_item("titanium", 10)
    storage.update_item("titanium", 5, relative=True)
    assert storage.get_item_count("titanium") == 15


def test_update_item_decrement(storage):
    storage.update_item("titanium", 20)
    storage.update_item("titanium", -5, relative=True)
    assert storage.get_item_count("titanium") == 15


def test_get_all_items(storage):
    storage.update_item("titanium", 10)
    storage.update_item("copper", 5)
    items = storage.get_all_items()
    assert items == {"titanium": 10, "copper": 5}


def test_add_location(storage):
    storage.add_location("titanium", "industrial areas")
    assert storage.get_location("titanium") == "industrial areas"


def test_add_tip(storage):
    storage.add_tip("Medkits need herbs")
    tips = storage.get_tips()
    assert "Medkits need herbs" in tips


def test_set_mission(storage):
    storage.set_mission("Collect 50 titanium")
    assert storage.get_mission() == "Collect 50 titanium"


def test_persistence(tmp_path):
    inv_file = tmp_path / "inventory.json"
    know_file = tmp_path / "knowledge.json"
    inv_file.write_text('{"items": {}, "last_updated": null}')
    know_file.write_text('{"locations": {}, "tips": [], "missions": {"current": null}}')

    storage1 = InventoryStorage(inv_file, know_file)
    storage1.update_item("titanium", 42)

    storage2 = InventoryStorage(inv_file, know_file)
    assert storage2.get_item_count("titanium") == 42
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL (module not found)

**Step 3: Implement storage module**

`src/storage.py`:
```python
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class InventoryStorage:
    def __init__(self, inventory_path: Path, knowledge_path: Path):
        self.inventory_path = Path(inventory_path)
        self.knowledge_path = Path(knowledge_path)
        self._load()

    def _load(self):
        with open(self.inventory_path) as f:
            self._inventory = json.load(f)
        with open(self.knowledge_path) as f:
            self._knowledge = json.load(f)

    def _save_inventory(self):
        self._inventory["last_updated"] = datetime.now().isoformat()
        with open(self.inventory_path, "w") as f:
            json.dump(self._inventory, f, indent=2)

    def _save_knowledge(self):
        with open(self.knowledge_path, "w") as f:
            json.dump(self._knowledge, f, indent=2)

    def get_item_count(self, item: str) -> int:
        return self._inventory["items"].get(item.lower(), 0)

    def update_item(self, item: str, count: int, relative: bool = False):
        item = item.lower()
        if relative:
            current = self.get_item_count(item)
            self._inventory["items"][item] = max(0, current + count)
        else:
            self._inventory["items"][item] = max(0, count)
        self._save_inventory()

    def get_all_items(self) -> dict[str, int]:
        return dict(self._inventory["items"])

    def add_location(self, item: str, location: str):
        self._knowledge["locations"][item.lower()] = location
        self._save_knowledge()

    def get_location(self, item: str) -> Optional[str]:
        return self._knowledge["locations"].get(item.lower())

    def add_tip(self, tip: str):
        if tip not in self._knowledge["tips"]:
            self._knowledge["tips"].append(tip)
            self._save_knowledge()

    def get_tips(self) -> list[str]:
        return list(self._knowledge["tips"])

    def set_mission(self, mission: str):
        self._knowledge["missions"]["current"] = mission
        self._save_knowledge()

    def get_mission(self) -> Optional[str]:
        return self._knowledge["missions"]["current"]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_storage.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/storage.py tests/
git commit -m "feat: add storage module for inventory and knowledge"
```

---

## Task 3: Sherpa Brain (Claude Integration)

**Files:**
- Create: `src/sherpa.py`
- Create: `tests/test_sherpa.py`

**Step 1: Write failing tests**

`tests/test_sherpa.py`:
```python
import pytest
from unittest.mock import Mock, patch

from src.sherpa import SherpaBrain, SherpaResponse, ActionType


@pytest.fixture
def mock_storage():
    storage = Mock()
    storage.get_all_items.return_value = {"titanium": 10}
    storage.get_item_count.return_value = 10
    storage.get_location.return_value = None
    storage.get_mission.return_value = None
    storage.get_tips.return_value = []
    return storage


def test_parse_response_update():
    response = SherpaResponse.from_json({
        "action": "UPDATE",
        "changes": {"titanium": "+15"},
        "response": "Added 15 titanium",
        "response_type": "short"
    })
    assert response.action == ActionType.UPDATE
    assert response.changes == {"titanium": "+15"}
    assert response.response == "Added 15 titanium"
    assert response.is_short


def test_parse_response_query():
    response = SherpaResponse.from_json({
        "action": "QUERY",
        "changes": {},
        "response": "You have 25 titanium",
        "response_type": "short"
    })
    assert response.action == ActionType.QUERY
    assert response.is_short


def test_parse_response_long():
    response = SherpaResponse.from_json({
        "action": "QUERY",
        "changes": {},
        "response": "Here is your full inventory...",
        "response_type": "long"
    })
    assert not response.is_short


def test_apply_changes_absolute(mock_storage):
    brain = SherpaBrain.__new__(SherpaBrain)
    brain.storage = mock_storage

    brain._apply_changes({"titanium": "50"})
    mock_storage.update_item.assert_called_with("titanium", 50, relative=False)


def test_apply_changes_relative_add(mock_storage):
    brain = SherpaBrain.__new__(SherpaBrain)
    brain.storage = mock_storage

    brain._apply_changes({"titanium": "+15"})
    mock_storage.update_item.assert_called_with("titanium", 15, relative=True)


def test_apply_changes_relative_subtract(mock_storage):
    brain = SherpaBrain.__new__(SherpaBrain)
    brain.storage = mock_storage

    brain._apply_changes({"titanium": "-5"})
    mock_storage.update_item.assert_called_with("titanium", -5, relative=True)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sherpa.py -v`
Expected: FAIL (module not found)

**Step 3: Implement Sherpa brain**

`src/sherpa.py`:
```python
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
    location: Optional[str] = None
    tip: Optional[str] = None
    mission: Optional[str] = None

    @classmethod
    def from_json(cls, data: dict) -> "SherpaResponse":
        action = ActionType[data.get("action", "UNKNOWN")]
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
{
  "action": "UPDATE|QUERY|LEARN|MISSION",
  "changes": {"item_name": "+15"},
  "response": "Natural language response to speak",
  "response_type": "short|long",
  "location": {"item": "location description"},
  "tip": "tip text if learning a tip",
  "mission": "mission text if setting mission"
}

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
    def __init__(self, storage: InventoryStorage, api_key: str):
        self.storage = storage
        self.client = anthropic.Anthropic(api_key=api_key)

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
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=self._build_context(),
                messages=[{"role": "user", "content": command}],
            )

            response_text = message.content[0].text

            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                return SherpaResponse.error("I couldn't understand that, try again")

            data = json.loads(json_match.group())
            response = SherpaResponse.from_json(data)

            self._apply_changes(response.changes)
            self._apply_knowledge(response)

            return response

        except anthropic.APIError as e:
            return SherpaResponse.error("I'm having trouble thinking, try again")
        except json.JSONDecodeError:
            return SherpaResponse.error("I got confused, could you rephrase that?")

    def _apply_changes(self, changes: dict):
        for item, value in changes.items():
            value_str = str(value)
            if value_str.startswith("+"):
                self.storage.update_item(item, int(value_str[1:]), relative=True)
            elif value_str.startswith("-"):
                self.storage.update_item(item, int(value_str), relative=True)
            else:
                self.storage.update_item(item, int(value_str), relative=False)

    def _apply_knowledge(self, response: SherpaResponse):
        if response.location:
            if isinstance(response.location, dict):
                for item, loc in response.location.items():
                    self.storage.add_location(item, loc)
            else:
                pass

        if response.tip:
            self.storage.add_tip(response.tip)

        if response.mission:
            self.storage.set_mission(response.mission)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sherpa.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/sherpa.py tests/test_sherpa.py
git commit -m "feat: add Sherpa brain with Claude integration"
```

---

## Task 4: TTS Module

**Files:**
- Create: `src/tts.py`
- Create: `tests/test_tts.py`

**Step 1: Write failing test**

`tests/test_tts.py`:
```python
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from src.tts import TextToSpeech


def test_tts_generates_audio_file(tmp_path):
    tts = TextToSpeech(output_dir=tmp_path)
    audio_path = tts.speak("Hello world")
    assert audio_path.exists()
    assert audio_path.suffix == ".wav"


def test_tts_different_texts_different_files(tmp_path):
    tts = TextToSpeech(output_dir=tmp_path)
    path1 = tts.speak("Hello")
    path2 = tts.speak("Goodbye")
    assert path1 != path2
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tts.py -v`
Expected: FAIL (module not found)

**Step 3: Implement TTS module (with macOS fallback)**

`src/tts.py`:
```python
import subprocess
import hashlib
from pathlib import Path
from typing import Optional

try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False


class TextToSpeech:
    def __init__(
        self,
        output_dir: Path = Path("./audio_cache"),
        model_path: Optional[Path] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.use_piper = PIPER_AVAILABLE and model_path and model_path.exists()

        if self.use_piper:
            self.voice = PiperVoice.load(str(model_path))
        else:
            self.voice = None

    def speak(self, text: str) -> Path:
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        output_path = self.output_dir / f"speech_{text_hash}.wav"

        if output_path.exists():
            return output_path

        if self.use_piper:
            self._speak_piper(text, output_path)
        else:
            self._speak_macos(text, output_path)

        return output_path

    def _speak_piper(self, text: str, output_path: Path):
        audio_data = self.voice.synthesize(text)
        with open(output_path, "wb") as f:
            f.write(audio_data)

    def _speak_macos(self, text: str, output_path: Path):
        aiff_path = output_path.with_suffix(".aiff")
        subprocess.run(
            ["say", "-o", str(aiff_path), text],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-i", str(aiff_path), "-y", str(output_path)],
            check=True,
            capture_output=True,
        )
        aiff_path.unlink()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tts.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/tts.py tests/test_tts.py
git commit -m "feat: add TTS module with Piper and macOS fallback"
```

---

## Task 5: Transcriber Module

**Files:**
- Create: `src/transcriber.py`
- Create: `tests/test_transcriber.py`

**Step 1: Write failing tests**

`tests/test_transcriber.py`:
```python
import pytest
from src.transcriber import WakeWordDetector


def test_detect_wake_word_present():
    detector = WakeWordDetector("hey sherpa")
    result = detector.check("hey sherpa what is my titanium count")
    assert result is not None
    assert result == "what is my titanium count"


def test_detect_wake_word_missing():
    detector = WakeWordDetector("hey sherpa")
    result = detector.check("what is my titanium count")
    assert result is None


def test_detect_wake_word_case_insensitive():
    detector = WakeWordDetector("hey sherpa")
    result = detector.check("Hey Sherpa add 10 copper")
    assert result == "add 10 copper"


def test_detect_wake_word_with_filler():
    detector = WakeWordDetector("hey sherpa")
    result = detector.check("um hey sherpa uh add 5 titanium")
    assert result is not None
    assert "add 5 titanium" in result.lower()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_transcriber.py -v`
Expected: FAIL (module not found)

**Step 3: Implement transcriber module**

`src/transcriber.py`:
```python
import re
import asyncio
import numpy as np
from pathlib import Path
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass

import mlx_whisper


@dataclass
class TranscriptionResult:
    text: str
    command: Optional[str]


class WakeWordDetector:
    def __init__(self, wake_word: str = "hey sherpa"):
        self.wake_word = wake_word.lower()
        self.pattern = re.compile(
            rf"(?:um|uh|like|so|)?\s*{re.escape(self.wake_word)}\s*(?:um|uh|)?\s*(.*)",
            re.IGNORECASE,
        )

    def check(self, text: str) -> Optional[str]:
        match = self.pattern.search(text)
        if match:
            command = match.group(1).strip()
            return command if command else None
        return None


class Transcriber:
    def __init__(
        self,
        wake_word: str = "hey sherpa",
        model_name: str = "mlx-community/whisper-base-mlx",
        silence_threshold: float = 1.5,
    ):
        self.detector = WakeWordDetector(wake_word)
        self.model_name = model_name
        self.silence_threshold = silence_threshold
        self._model_loaded = False

    def _ensure_model(self):
        if not self._model_loaded:
            self._model_loaded = True

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscriptionResult:
        self._ensure_model()

        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self.model_name,
        )

        text = result.get("text", "").strip()
        command = self.detector.check(text)

        return TranscriptionResult(text=text, command=command)

    async def transcribe_async(
        self, audio: np.ndarray, sample_rate: int = 16000
    ) -> TranscriptionResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.transcribe, audio, sample_rate)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_transcriber.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/transcriber.py tests/test_transcriber.py
git commit -m "feat: add transcriber with wake word detection"
```

---

## Task 6: Discord Bot

**Files:**
- Create: `src/bot.py`
- Create: `src/audio_sink.py`

**Step 1: Implement audio sink for Discord voice**

`src/audio_sink.py`:
```python
import asyncio
import numpy as np
from collections import deque
from typing import Optional, Callable, Awaitable

import discord


class AudioBuffer:
    def __init__(
        self,
        sample_rate: int = 48000,
        target_rate: int = 16000,
        silence_duration: float = 1.5,
        min_audio_duration: float = 0.5,
    ):
        self.sample_rate = sample_rate
        self.target_rate = target_rate
        self.silence_duration = silence_duration
        self.min_audio_duration = min_audio_duration

        self.buffer: list[bytes] = []
        self.silence_samples = 0
        self.silence_threshold = int(silence_duration * sample_rate)
        self.min_samples = int(min_audio_duration * sample_rate)

        self.is_speaking = False

    def add_audio(self, pcm_data: bytes) -> Optional[np.ndarray]:
        audio = np.frombuffer(pcm_data, dtype=np.int16)

        rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
        is_voice = rms > 500

        if is_voice:
            self.is_speaking = True
            self.silence_samples = 0
            self.buffer.append(pcm_data)
        elif self.is_speaking:
            self.silence_samples += len(audio)
            self.buffer.append(pcm_data)

            if self.silence_samples >= self.silence_threshold:
                return self._flush_buffer()

        return None

    def _flush_buffer(self) -> Optional[np.ndarray]:
        if not self.buffer:
            return None

        self.is_speaking = False
        self.silence_samples = 0

        all_audio = b"".join(self.buffer)
        self.buffer = []

        audio = np.frombuffer(all_audio, dtype=np.int16).astype(np.float32) / 32768.0

        if len(audio) < self.min_samples:
            return None

        ratio = self.target_rate / self.sample_rate
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length).astype(int)
        resampled = audio[indices]

        return resampled

    def reset(self):
        self.buffer = []
        self.silence_samples = 0
        self.is_speaking = False


class SherpaAudioSink(discord.AudioSink):
    def __init__(self, callback: Callable[[np.ndarray], Awaitable[None]]):
        super().__init__()
        self.callback = callback
        self.buffers: dict[int, AudioBuffer] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def write(self, user: discord.User, data: discord.VoiceData):
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        if user.id not in self.buffers:
            self.buffers[user.id] = AudioBuffer()

        buffer = self.buffers[user.id]
        audio = buffer.add_audio(data.pcm)

        if audio is not None:
            asyncio.run_coroutine_threadsafe(
                self.callback(audio), self._loop
            )

    def cleanup(self):
        self.buffers.clear()
```

**Step 2: Implement main bot**

`src/bot.py`:
```python
import os
import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from src.storage import InventoryStorage
from src.sherpa import SherpaBrain
from src.transcriber import Transcriber
from src.tts import TextToSpeech
from src.audio_sink import SherpaAudioSink

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/sherpa.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("sherpa")


class SherpaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(command_prefix="!", intents=intents)

        data_dir = Path("data")
        self.storage = InventoryStorage(
            data_dir / "inventory.json",
            data_dir / "knowledge.json",
        )

        self.brain = SherpaBrain(
            storage=self.storage,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

        self.transcriber = Transcriber(wake_word="hey sherpa")

        self.tts = TextToSpeech(output_dir=Path("audio_cache"))

        self.voice_client: discord.VoiceClient | None = None
        self.text_channel: discord.TextChannel | None = None

    async def setup_hook(self):
        await self.add_cog(VoiceCommands(self))

    async def on_ready(self):
        logger.info(f"Sherpa is ready! Logged in as {self.user}")

    async def handle_audio(self, audio):
        result = await self.transcriber.transcribe_async(audio)

        logger.info(f"Transcribed: {result.text}")

        if result.command:
            logger.info(f"Command detected: {result.command}")
            await self.process_command(result.command)

    async def process_command(self, command: str):
        response = await self.brain.process_command(command)

        logger.info(f"Sherpa response: {response.response}")

        if response.is_short and self.voice_client and self.voice_client.is_connected():
            audio_path = self.tts.speak(response.response)
            source = discord.FFmpegPCMAudio(str(audio_path))

            if self.voice_client.is_playing():
                self.voice_client.stop()

            self.voice_client.play(source)
        elif self.text_channel:
            await self.text_channel.send(f"**Sherpa:** {response.response}")


class VoiceCommands(commands.Cog):
    def __init__(self, bot: SherpaBot):
        self.bot = bot

    @commands.command(name="join")
    async def join(self, ctx: commands.Context):
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel!")
            return

        channel = ctx.author.voice.channel

        if self.bot.voice_client:
            await self.bot.voice_client.move_to(channel)
        else:
            self.bot.voice_client = await channel.connect()

        self.bot.text_channel = ctx.channel

        sink = SherpaAudioSink(self.bot.handle_audio)
        self.bot.voice_client.start_recording(sink, self.on_recording_stopped)

        await ctx.send(f"Sherpa joined {channel.name}! Say 'Hey Sherpa' to interact.")
        logger.info(f"Joined voice channel: {channel.name}")

    async def on_recording_stopped(self, sink: SherpaAudioSink, *args):
        sink.cleanup()

    @commands.command(name="leave")
    async def leave(self, ctx: commands.Context):
        if self.bot.voice_client:
            self.bot.voice_client.stop_recording()
            await self.bot.voice_client.disconnect()
            self.bot.voice_client = None
            await ctx.send("Sherpa left the voice channel.")
            logger.info("Left voice channel")
        else:
            await ctx.send("I'm not in a voice channel!")

    @commands.command(name="inventory")
    async def inventory(self, ctx: commands.Context):
        items = self.bot.storage.get_all_items()
        if items:
            lines = [f"- {item}: {count}" for item, count in items.items()]
            await ctx.send("**Current Inventory:**\n" + "\n".join(lines))
        else:
            await ctx.send("Inventory is empty!")


def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN not set in .env")
        return

    bot = SherpaBot()
    bot.run(token)


if __name__ == "__main__":
    main()
```

**Step 3: Create logs directory**

Run: `mkdir -p logs`

**Step 4: Commit**

```bash
git add src/bot.py src/audio_sink.py
git commit -m "feat: add Discord bot with voice integration"
```

---

## Task 7: Integration Test

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

`tests/test_integration.py`:
```python
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import tempfile

from src.storage import InventoryStorage
from src.sherpa import SherpaBrain, SherpaResponse, ActionType


@pytest.fixture
def temp_storage(tmp_path):
    inv_file = tmp_path / "inventory.json"
    know_file = tmp_path / "knowledge.json"
    inv_file.write_text('{"items": {}, "last_updated": null}')
    know_file.write_text('{"locations": {}, "tips": [], "missions": {"current": null}}')
    return InventoryStorage(inv_file, know_file)


@pytest.mark.asyncio
async def test_full_add_query_flow(temp_storage):
    with patch("src.sherpa.anthropic.Anthropic") as mock_anthropic:
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        mock_client.messages.create.return_value = Mock(
            content=[Mock(text='{"action": "UPDATE", "changes": {"titanium": "+15"}, "response": "Added 15 titanium. You now have 15.", "response_type": "short"}')]
        )

        brain = SherpaBrain(temp_storage, "fake-key")
        response = await brain.process_command("I picked up 15 titanium")

        assert response.action == ActionType.UPDATE
        assert temp_storage.get_item_count("titanium") == 15
        assert "15" in response.response

        mock_client.messages.create.return_value = Mock(
            content=[Mock(text='{"action": "QUERY", "changes": {}, "response": "You have 15 titanium.", "response_type": "short"}')]
        )

        response = await brain.process_command("how much titanium do I have")
        assert response.action == ActionType.QUERY
        assert "15" in response.response


@pytest.mark.asyncio
async def test_learn_location_flow(temp_storage):
    with patch("src.sherpa.anthropic.Anthropic") as mock_anthropic:
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        mock_client.messages.create.return_value = Mock(
            content=[Mock(text='{"action": "LEARN", "changes": {}, "response": "Got it, titanium is in industrial areas.", "response_type": "short", "location": {"titanium": "industrial areas"}}')]
        )

        brain = SherpaBrain(temp_storage, "fake-key")
        response = await brain.process_command("titanium is found in industrial areas")

        assert response.action == ActionType.LEARN
        assert temp_storage.get_location("titanium") == "industrial areas"
```

**Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full command flow"
```

---

## Task 8: Final Setup and Run

**Step 1: Add Discord bot token to .env**

Edit `.env` and replace `your_discord_bot_token_here` with your actual bot token.

**Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 3: Start the bot**

Run: `python -m src.bot`

**Step 4: Test in Discord**
1. Invite bot to your server using OAuth URL
2. Join a voice channel
3. Type `!join` in a text channel
4. Say "Hey Sherpa, add 10 titanium"
5. Sherpa should respond with voice confirmation

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete Sherpa v1 implementation"
```

---

## Summary

Tasks completed:
1. System dependencies (ffmpeg, opus, Piper voice)
2. Project setup (requirements, directories)
3. Storage module (inventory + knowledge JSON)
4. Sherpa brain (Claude integration)
5. TTS module (Piper with macOS fallback)
6. Transcriber (Whisper + wake word)
7. Discord bot (voice capture + response)
8. Integration tests + final run

Run `python -m src.bot` to start Sherpa!
