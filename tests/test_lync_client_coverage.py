import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from htd_client.lync_client import HtdLyncClient
from htd_client.constants import HtdConstants, HtdDeviceKind, HtdLyncCommands, HtdLyncConstants
from htd_client.models import ZoneDetail

@pytest.fixture
def lync_client():
    loop = MagicMock()
    model_info = {
        "zones": 6,
        "sources": 6,
        "friendly_name": "Lync6",
        "name": "Lync6",
        "kind": HtdDeviceKind.lync,
        "identifier": b'Wangine_Lync6'
    }
    client = HtdLyncClient(loop, model_info)
    client._connection = MagicMock()
    client._socket_lock = asyncio.Lock()
    # Mock _zone_data
    client._zone_data = {
        i: ZoneDetail(i, enabled=True, power=True, volume=30) 
        for i in range(1, 7)
    }
    return client

@pytest.mark.asyncio
async def test_set_volume(lync_client):
    lync_client._async_send_and_validate = AsyncMock()
    
    await lync_client.async_set_volume(1, 40)
    
    lync_client._async_send_and_validate.assert_called()
    args = lync_client._async_send_and_validate.call_args[0]
    kwargs = lync_client._async_send_and_validate.call_args[1]
    # args: validate, zone, cmd, code
    assert args[1] == 1
    assert args[2] == HtdLyncCommands.VOLUME_SETTING_CONTROL_COMMAND_CODE
    # Follow up with mute off
    assert kwargs['follow_up'] == (HtdLyncCommands.COMMON_COMMAND_CODE, HtdLyncCommands.MUTE_OFF_COMMAND_CODE)

@pytest.mark.asyncio
async def test_set_source_intercom(lync_client):
    lync_client._async_send_and_validate = AsyncMock()
    
    # Source = 6 (last source? model has 6 sources)
    await lync_client.async_set_source(1, 6)
    
    # Logic: if source == model["sources"]: use INTERCOM_SOURCE_DATA
    # My mock has 6 sources. So source 6 == 6.
    args = lync_client._async_send_and_validate.call_args[0]
    assert args[3] == HtdLyncConstants.INTERCOM_SOURCE_DATA

@pytest.mark.asyncio
async def test_set_source_normal(lync_client):
    lync_client._async_send_and_validate = AsyncMock()
    
    await lync_client.async_set_source(1, 1)
    args = lync_client._async_send_and_validate.call_args[0]
    # source_offset = SOURCE_COMMAND_OFFSET
    assert args[3] == 1 + HtdLyncConstants.SOURCE_COMMAND_OFFSET

@pytest.mark.asyncio
async def test_volume_limits(lync_client):
    lync_client.async_set_volume = AsyncMock()
    
    # Max volume
    lync_client._zone_data[1].volume = HtdConstants.MAX_VOLUME
    await lync_client.async_volume_up(1)
    lync_client.async_set_volume.assert_not_called()
    
    # Min volume
    lync_client._zone_data[1].volume = 0
    await lync_client.async_volume_down(1)
    lync_client.async_set_volume.assert_not_called()
    
    # Valid up
    lync_client._zone_data[1].volume = 30
    await lync_client.async_volume_up(1)
    lync_client.async_set_volume.assert_awaited_with(1, 31)

@pytest.mark.asyncio
async def test_bass_treble_balance_limits(lync_client):
    lync_client.async_set_bass = AsyncMock()
    lync_client.async_set_treble = AsyncMock()
    lync_client.async_set_balance = AsyncMock()
    
    # Bass limit
    lync_client._zone_data[1].bass = HtdConstants.LYNC_MAX_BASS
    await lync_client.async_bass_up(1)
    lync_client.async_set_bass.assert_not_called()
    
    # Treble limit
    lync_client._zone_data[1].treble = HtdConstants.LYNC_MAX_TREBLE
    await lync_client.async_treble_up(1)
    lync_client.async_set_treble.assert_not_called()
    
    # Balance limit
    lync_client._zone_data[1].balance = HtdConstants.LYNC_MAX_BALANCE
    await lync_client.async_balance_right(1)
    lync_client.async_set_balance.assert_not_called()

@pytest.mark.asyncio
async def test_basic_commands(lync_client):
    lync_client._send_cmd = AsyncMock()
    
    await lync_client.refresh(1)
    lync_client._send_cmd.assert_called()
    
    await lync_client.power_on_all_zones()
    lync_client._send_cmd.assert_called()
    
    await lync_client.power_off_all_zones()
    lync_client._send_cmd.assert_called()

@pytest.mark.asyncio
async def test_audio_controls_success(lync_client):
    lync_client._send_cmd = AsyncMock() # send_and_validate calls send_cmd? No it calls send_cmd. Wait. 
    # send_and_validate calls send_cmd.
    # We should mock _async_send_and_validate if we want to check args easily.
    lync_client._async_send_and_validate = AsyncMock()
    
    # We should also mock wrapper methods if we test wrappers?
    # No, we want to test wrappers call helpers.
    # async_bass_up calls async_set_bass.
    lync_client.async_set_bass = AsyncMock()
    lync_client.async_set_treble = AsyncMock()
    lync_client.async_set_balance = AsyncMock()

    # Mute/Unmute - calls send_and_validate directly
    await lync_client.async_mute(1)
    # Check CMD ID
    args = lync_client._async_send_and_validate.call_args[0]
    # args: validate, zone, cmd, code
    assert args[3] == HtdLyncCommands.MUTE_ON_COMMAND_CODE
    
    await lync_client.async_unmute(1)
    args = lync_client._async_send_and_validate.call_args[0]
    assert args[3] == HtdLyncCommands.MUTE_OFF_COMMAND_CODE
    
    # Power - calls send_and_validate directly
    await lync_client.async_power_on(1)
    args = lync_client._async_send_and_validate.call_args[0]
    assert args[3] == HtdLyncCommands.POWER_ON_ZONE_COMMAND_CODE
    
    await lync_client.async_power_off(1)
    # Use call_args_list if needed, but here sequential
    args = lync_client._async_send_and_validate.call_args[0]
    assert args[3] == HtdLyncCommands.POWER_OFF_ZONE_COMMAND_CODE

    # Reset calls
    lync_client.async_set_bass.reset_mock()
    
    # Bass success
    lync_client._zone_data[1].bass = 0 # Within limits
    await lync_client.async_bass_up(1)
    # calls async_set_bass(1, 1)
    lync_client.async_set_bass.assert_awaited_with(1, 1)
    
    await lync_client.async_bass_down(1)
    lync_client.async_set_bass.assert_awaited_with(1, -1)
    
    # Treble success
    lync_client._zone_data[1].treble = 0
    await lync_client.async_treble_up(1)
    lync_client.async_set_treble.assert_awaited_with(1, 1)
    
    await lync_client.async_treble_down(1)
    lync_client.async_set_treble.assert_awaited_with(1, -1)
    
    # Balance success
    lync_client._zone_data[1].balance = 0
    await lync_client.async_balance_right(1) # +1
    lync_client.async_set_balance.assert_awaited_with(1, 1)
    
    await lync_client.async_balance_left(1) # -1
    lync_client.async_set_balance.assert_awaited_with(1, -1)

@pytest.mark.asyncio
async def test_set_audio_values(lync_client):
    lync_client._send_cmd = AsyncMock() 
    lync_client._async_send_and_validate = AsyncMock()
    
    # Set bass
    await lync_client.async_set_bass(1, 5)
    
    # Check 0x18 sent
    args_send = lync_client._send_cmd.call_args[0]
    assert args_send[1] == HtdLyncCommands.BASS_SETTING_CONTROL_COMMAND_CODE
    assert args_send[2] == 5
    
    # Check Commit
    args_val = lync_client._async_send_and_validate.call_args[0]
    assert args_val[2] == HtdLyncCommands.COMMON_COMMAND_CODE
    assert args_val[3] == HtdLyncConstants.STATUS_REFRESH_CODE
    
    # Set treble
    await lync_client.async_set_treble(1, 5)
    args_send = lync_client._send_cmd.call_args[0]
    assert args_send[1] == HtdLyncCommands.TREBLE_SETTING_CONTROL_COMMAND_CODE
    assert args_send[2] == 5
    
    args_val = lync_client._async_send_and_validate.call_args[0]
    assert args_val[2] == HtdLyncCommands.COMMON_COMMAND_CODE
    assert args_val[3] == HtdLyncConstants.STATUS_REFRESH_CODE
    
    # Set balance
    await lync_client.async_set_balance(1, 5)
    
    args_send = lync_client._send_cmd.call_args[0]
    assert args_send[1] == HtdLyncCommands.BALANCE_SETTING_CONTROL_COMMAND_CODE
    assert args_send[2] == 5
    
    args_val = lync_client._async_send_and_validate.call_args[0]
    assert args_val[2] == HtdLyncCommands.COMMON_COMMAND_CODE
    assert args_val[3] == HtdLyncConstants.STATUS_REFRESH_CODE

@pytest.mark.asyncio
async def test_set_source_high(lync_client):
    lync_client._async_send_and_validate = AsyncMock()
    # Source > 12
    await lync_client.async_set_source(1, 13)
    args = lync_client._async_send_and_validate.call_args[0]
    # Check offset usage
    assert args[3] == 13 + HtdLyncConstants.SOURCE_13_HIGHER_COMMAND_OFFSET
