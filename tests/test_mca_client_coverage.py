import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from htd_client.mca_client import HtdMcaClient
from htd_client.constants import HtdConstants, HtdDeviceKind, HtdMcaCommands
from htd_client.models import ZoneDetail

@pytest.fixture
def mca_client():
    loop = MagicMock()
    loop.create_task = MagicMock()
    model_info = {
        "zones": 6,
        "sources": 6,
        "friendly_name": "MCA66",
        "name": "MCA66",
        "kind": HtdDeviceKind.mca,
        "identifier": b'Wangine_MCA66'
    }
    client = HtdMcaClient(loop, model_info)
    client._connection = MagicMock()
    client._socket_lock = asyncio.Lock()
    # Mock _zone_data for all zones
    client._zone_data = {
        i: ZoneDetail(i, enabled=True, power=True, volume=30) 
        for i in range(1, 7)
    }
    return client

@pytest.mark.asyncio
async def test_connect_subscribes(mca_client):
    with patch("htd_client.base_client.create_serial_connection", new_callable=AsyncMock):
        mca_client._serial_address = "/dev/ttyUSB0"
        mca_client.async_subscribe = AsyncMock()
        await mca_client.async_connect()
        mca_client.async_subscribe.assert_called_with(mca_client._on_zone_update)
        assert mca_client._subscribed

def test_on_zone_update_no_target(mca_client):
    # No target set
    mca_client._target_volumes[1] = None
    mca_client._async_set_volume = MagicMock()
    
    mca_client._on_zone_update(1)
    
    mca_client._async_set_volume.assert_not_called()

def test_on_zone_update_reached_target(mca_client):
    mca_client._target_volumes[1] = 30
    mca_client._zone_data[1].volume = 30
    
    mca_client._on_zone_update(1)
    
    assert mca_client._target_volumes[1] is None

def test_on_zone_update_needs_adjustment(mca_client):
    mca_client._target_volumes[1] = 40
    mca_client._zone_data[1].volume = 30
    
    # Needs to run async_set_volume. run_coroutine_threadsafe is used.
    # We should mock asyncio.run_coroutine_threadsafe
    with patch("asyncio.run_coroutine_threadsafe") as mock_run:
        mca_client._on_zone_update(1)
        mock_run.assert_called()

@pytest.mark.asyncio
async def test_async_set_volume_start(mca_client):
    # Set target, power is on
    mca_client._async_set_volume = AsyncMock()
    
    await mca_client.async_set_volume(1, 40)
    
    assert mca_client._target_volumes[1] == 40
    mca_client._async_set_volume.assert_awaited_with(1)

@pytest.mark.asyncio
async def test_async_set_volume_power_off(mca_client):
    mca_client._zone_data[1].power = False
    mca_client.async_power_on = AsyncMock()
    mca_client._async_set_volume = AsyncMock()
    
    await mca_client.async_set_volume(1, 40)
    
    mca_client.async_power_on.assert_awaited_with(1)
    mca_client._async_set_volume.assert_awaited_with(1)

@pytest.mark.asyncio
async def test_internal_async_set_volume_up(mca_client):
    mca_client._target_volumes[1] = 40
    mca_client._zone_data[1].volume = 30
    mca_client._async_send_and_validate = AsyncMock()
    
    await mca_client._async_set_volume(1)
    
    mca_client._async_send_and_validate.assert_called()
    # Check command is VOL_UP
    args = mca_client._async_send_and_validate.call_args[0]
    # args: validate, zone, cmd, data
    assert args[1] == 1
    assert args[3] == HtdMcaCommands.VOLUME_UP_COMMAND

@pytest.mark.asyncio
async def test_simple_commands(mca_client):
    mca_client._send_cmd = AsyncMock()
    
    await mca_client.refresh(1)
    mca_client._send_cmd.assert_called()
    
    await mca_client.power_on_all_zones()
    mca_client._send_cmd.assert_called()

@pytest.mark.asyncio
async def test_wrappers(mca_client):
    mca_client._async_send_and_validate = AsyncMock()
    
    # Case 1: Mute is False. async_mute should call toggle.
    mca_client._zone_data[1].mute = False
    await mca_client.async_mute(1) 
    mca_client._async_send_and_validate.assert_called()
    
    mca_client._async_send_and_validate.reset_mock()
    
    # Case 2: Mute is True. async_mute should do nothing.
    mca_client._zone_data[1].mute = True
    await mca_client.async_mute(1)
    mca_client._async_send_and_validate.assert_not_called()


    
    # Case 3: Unmute when muted.
    await mca_client.async_unmute(1)
    mca_client._async_send_and_validate.assert_called()

@pytest.mark.asyncio
async def test_bass_up_limits(mca_client):
    mca_client._async_send_and_validate = AsyncMock()
    
    # Bass max is 10
    mca_client._zone_data[1].bass = 10
    await mca_client.async_bass_up(1)
    mca_client._async_send_and_validate.assert_not_called()
    
    mca_client._zone_data[1].bass = 0
    await mca_client.async_bass_up(1)
    mca_client._async_send_and_validate.assert_called()

@pytest.mark.asyncio
async def test_audio_limits_mca(mca_client):
    mca_client._async_send_and_validate = AsyncMock()
    
    # Bass Down limit
    mca_client._zone_data[1].bass = HtdConstants.MCA_MIN_BASS
    await mca_client.async_bass_down(1)
    mca_client._async_send_and_validate.assert_not_called()
    
    # Treble limits
    mca_client._zone_data[1].treble = HtdConstants.MCA_MAX_TREBLE
    await mca_client.async_treble_up(1)
    mca_client._async_send_and_validate.assert_not_called()
    
    mca_client._zone_data[1].treble = HtdConstants.MCA_MIN_TREBLE
    await mca_client.async_treble_down(1)
    mca_client._async_send_and_validate.assert_not_called()

    # Balance limits
    mca_client._zone_data[1].balance = HtdConstants.MCA_MAX_BALANCE
    await mca_client.async_balance_right(1)
    mca_client._async_send_and_validate.assert_not_called()
    
    mca_client._zone_data[1].balance = HtdConstants.MCA_MIN_BALANCE
    await mca_client.async_balance_left(1)
    mca_client._async_send_and_validate.assert_not_called()

@pytest.mark.asyncio
async def test_set_source(mca_client):
    mca_client._async_send_and_validate = AsyncMock()
    await mca_client.async_set_source(1, 2)
    # Check offset
    args = mca_client._async_send_and_validate.call_args[0]
    # Source 2 + offset
    from htd_client.constants import HtdMcaConstants
    assert args[3] == 2 + HtdMcaConstants.SOURCE_COMMAND_OFFSET

@pytest.mark.asyncio
async def test_volume_limits_mca(mca_client):
    mca_client._async_send_and_validate = AsyncMock()
     
    # Max volume
    mca_client._zone_data[1].volume = HtdConstants.MAX_VOLUME
    await mca_client.async_volume_up(1)
    mca_client._async_send_and_validate.assert_not_called()
     
    # Treble/Bass limits?
    mca_client._zone_data[1].treble = HtdConstants.MCA_MAX_TREBLE
    await mca_client.async_treble_up(1)
    mca_client._async_send_and_validate.assert_not_called()
     
    mca_client._zone_data[1].treble = HtdConstants.MCA_MIN_TREBLE
    await mca_client.async_treble_down(1)
    mca_client._async_send_and_validate.assert_not_called()


def test_on_zone_update(mca_client):
    mca_client._target_volumes = {1: 50, 2: None}
    mca_client._zone_data[1].volume = 40
    mca_client._loop = MagicMock()
    
    # Case 1: Volume mismatch, target exists
    mca_client._on_zone_update(1)
    mca_client._loop.call_soon_threadsafe.assert_called() 
    
    # Case 2: Volume match
    mca_client._zone_data[1].volume = 50
    mca_client._on_zone_update(1)
    assert mca_client._target_volumes[1] is None
    
    # Case 3: No target
    mca_client._on_zone_update(2)
    # nothing happens
