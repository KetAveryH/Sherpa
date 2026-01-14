import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class InventoryStorage:
    DEFAULT_INVENTORY = {"items": {}, "last_updated": None}
    DEFAULT_KNOWLEDGE = {"locations": {}, "tips": [], "missions": {"current": None}}

    def __init__(self, inventory_path: Path, knowledge_path: Path):
        self.inventory_path = Path(inventory_path)
        self.knowledge_path = Path(knowledge_path)
        self._init_files()
        self._load()

    def _init_files(self):
        """Create default files if they don't exist."""
        if not self.inventory_path.exists():
            self._atomic_write(self.inventory_path, self.DEFAULT_INVENTORY)
        if not self.knowledge_path.exists():
            self._atomic_write(self.knowledge_path, self.DEFAULT_KNOWLEDGE)

    def _load(self):
        """Load data from files, falling back to defaults on errors."""
        try:
            with open(self.inventory_path) as f:
                self._inventory = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._inventory = dict(self.DEFAULT_INVENTORY)
            self._atomic_write(self.inventory_path, self._inventory)

        try:
            with open(self.knowledge_path) as f:
                self._knowledge = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._knowledge = dict(self.DEFAULT_KNOWLEDGE)
            self._atomic_write(self.knowledge_path, self._knowledge)

    def _atomic_write(self, path: Path, data: dict):
        """Write data to file atomically using temp file and rename."""
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)

    def _save_inventory(self):
        self._inventory["last_updated"] = datetime.now().isoformat()
        self._atomic_write(self.inventory_path, self._inventory)

    def _save_knowledge(self):
        self._atomic_write(self.knowledge_path, self._knowledge)

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
