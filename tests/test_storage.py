import pytest
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
