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
    with patch("src.sherpa.anthropic.AsyncAnthropic") as mock_anthropic:
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        mock_client.messages.create = AsyncMock(return_value=Mock(
            content=[Mock(text='{"action": "UPDATE", "changes": {"titanium": "+15"}, "response": "Added 15 titanium. You now have 15.", "response_type": "short"}')]
        ))

        brain = SherpaBrain(temp_storage, "fake-key")
        response = await brain.process_command("I picked up 15 titanium")

        assert response.action == ActionType.UPDATE
        assert temp_storage.get_item_count("titanium") == 15
        assert "15" in response.response

        mock_client.messages.create = AsyncMock(return_value=Mock(
            content=[Mock(text='{"action": "QUERY", "changes": {}, "response": "You have 15 titanium.", "response_type": "short"}')]
        ))

        response = await brain.process_command("how much titanium do I have")
        assert response.action == ActionType.QUERY
        assert "15" in response.response


@pytest.mark.asyncio
async def test_learn_location_flow(temp_storage):
    with patch("src.sherpa.anthropic.AsyncAnthropic") as mock_anthropic:
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        mock_client.messages.create = AsyncMock(return_value=Mock(
            content=[Mock(text='{"action": "LEARN", "changes": {}, "response": "Got it, titanium is in industrial areas.", "response_type": "short", "location": {"titanium": "industrial areas"}}')]
        ))

        brain = SherpaBrain(temp_storage, "fake-key")
        response = await brain.process_command("titanium is found in industrial areas")

        assert response.action == ActionType.LEARN
        assert temp_storage.get_location("titanium") == "industrial areas"
