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
