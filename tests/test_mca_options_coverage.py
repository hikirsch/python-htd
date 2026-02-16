import pytest
from unittest.mock import MagicMock, AsyncMock
from htd_client.mca_client import HtdMcaClient
from htd_client.constants import HtdConstants, HtdMcaCommands

@pytest.fixture
def mca_client():
    mock_loop = MagicMock()
    model_info = {"zones": 6, "sources": 6, "kind": "mca", "name": "MCA66"}
    client = HtdMcaClient(mock_loop, model_info)
    client._connection = MagicMock()
    client._socket_lock = AsyncMock()
    # Initialize zone data
    client._zone_data = {1: MagicMock(volume=30, mute=False, power=True)}
    client._target_volumes = {key: None for key in range(1, 7)}
    return client

@pytest.mark.asyncio
async def test_mca_on_zone_update_none(mca_client):
    # Test _on_zone_update with None or 0
    mca_client._on_zone_update(None)
    mca_client._on_zone_update(0)
    # Should not crash

@pytest.mark.asyncio
async def test_mca_unmute_already_unmuted(mca_client):
    # Test unmute when already unmuted
    mca_client._zone_data[1].mute = False
    mca_client._async_toggle_mute = AsyncMock()
    
    await mca_client.async_unmute(1)
    
    mca_client._async_toggle_mute.assert_not_called()

@pytest.mark.asyncio
async def test_mca_has_volume_target(mca_client):
    mca_client._target_volumes[1] = 50
    assert mca_client.has_volume_target(1) is True
    
    mca_client._target_volumes[1] = None
    assert mca_client.has_volume_target(1) is False

@pytest.mark.asyncio
async def test_mca_set_volume_existing_target(mca_client):
    # Test setting volume when a target already exists
    mca_client._target_volumes[1] = 40
    mca_client._async_set_volume = AsyncMock()
    
    await mca_client.async_set_volume(1, 50)
    
    # Target should be updated, but _async_set_volume should not be called again immediately?
    # Actually logic says: if existing: return. So _async_set_volume NOT called.
    assert mca_client._target_volumes[1] == 50
    mca_client._async_set_volume.assert_not_called()

@pytest.mark.asyncio
async def test_mca_async_set_volume_power_off(mca_client):
    # Test _async_set_volume when power is off
    mca_client._zone_data[1].power = False
    mca_client._target_volumes[1] = 50
    
    await mca_client._async_set_volume(1)
    
    assert mca_client._target_volumes[1] is None

@pytest.mark.asyncio
async def test_mca_async_set_volume_no_diff(mca_client):
    # Test _async_set_volume when current volume equals target
    mca_client._target_volumes[1] = 30
    mca_client._zone_data[1].volume = 30
    mca_client._async_send_and_validate = AsyncMock()
    
    await mca_client._async_set_volume(1)
    
    mca_client._async_send_and_validate.assert_not_called()

@pytest.mark.asyncio
async def test_mca_async_set_volume_down(mca_client):
    # Test _async_set_volume when target is lower (diff < 0)
    mca_client._target_volumes[1] = 20
    mca_client._zone_data[1].volume = 30
    mca_client._async_send_and_validate = AsyncMock()
    
    await mca_client._async_set_volume(1)
    
    mca_client._async_send_and_validate.assert_called_once()
    # Check command arg
    args, _ = mca_client._async_send_and_validate.call_args
    assert args[3] == HtdMcaCommands.VOLUME_DOWN_COMMAND

@pytest.mark.asyncio
async def test_mca_volume_down_boundary(mca_client):
    # Test volume down when at 0
    mca_client._zone_data[1].volume = 0
    mca_client._async_send_and_validate = AsyncMock()
    
    await mca_client.async_volume_down(1)
    
    mca_client._async_send_and_validate.assert_not_called()
