import pytest
from unittest.mock import MagicMock, AsyncMock
from htd_client.mca_client import HtdMcaClient
from htd_client.lync_client import HtdLyncClient
from htd_client.constants import HtdConstants, HtdDeviceKind, HtdMcaCommands, HtdLyncCommands, HtdLyncConstants
from htd_client.models import ZoneDetail
import asyncio

# --- Fixtures ---

@pytest.fixture
def mca_client():
    loop = MagicMock()
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
    client._zone_data = {
        i: ZoneDetail(i, enabled=True, power=True, volume=30, bass=0, treble=0) 
        for i in range(1, 7)
    }
    return client

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
    client._zone_data = {
        i: ZoneDetail(i, enabled=True, power=True, volume=30, bass=0, treble=0) 
        for i in range(1, 7)
    }
    return client

# --- MCA Tests ---

@pytest.mark.asyncio
async def test_mca_bass_up(mca_client):
    mca_client._async_send_and_validate = AsyncMock()
    mca_client._zone_data[1].bass = 0
    
    await mca_client.async_bass_up(1)
    
    args = mca_client._async_send_and_validate.call_args[0]
    # args: validate, zone, cmd, code
    assert args[1] == 1
    assert args[3] == HtdMcaCommands.BASS_UP_COMMAND

@pytest.mark.asyncio
async def test_mca_bass_down(mca_client):
    mca_client._async_send_and_validate = AsyncMock()
    mca_client._zone_data[1].bass = 0
    
    await mca_client.async_bass_down(1)
    
    args = mca_client._async_send_and_validate.call_args[0]
    assert args[1] == 1
    assert args[3] == HtdMcaCommands.BASS_DOWN_COMMAND

@pytest.mark.asyncio
async def test_mca_treble_up(mca_client):
    mca_client._async_send_and_validate = AsyncMock()
    mca_client._zone_data[1].treble = 0
    
    await mca_client.async_treble_up(1)
    
    args = mca_client._async_send_and_validate.call_args[0]
    assert args[1] == 1
    assert args[3] == HtdMcaCommands.TREBLE_UP_COMMAND

@pytest.mark.asyncio
async def test_mca_treble_down(mca_client):
    mca_client._async_send_and_validate = AsyncMock()
    mca_client._zone_data[1].treble = 0
    
    await mca_client.async_treble_down(1)
    
    args = mca_client._async_send_and_validate.call_args[0]
    assert args[1] == 1
    assert args[3] == HtdMcaCommands.TREBLE_DOWN_COMMAND

@pytest.mark.asyncio
async def test_mca_limits(mca_client):
    mca_client._async_send_and_validate = AsyncMock()
    
    # Bass Max
    mca_client._zone_data[1].bass = HtdConstants.MCA_MAX_BASS
    await mca_client.async_bass_up(1)
    mca_client._async_send_and_validate.assert_not_called()
    
    # Bass Min
    mca_client._zone_data[1].bass = HtdConstants.MCA_MIN_BASS
    await mca_client.async_bass_down(1)
    mca_client._async_send_and_validate.assert_not_called()

    # Treble Max
    mca_client._zone_data[1].treble = HtdConstants.MCA_MAX_TREBLE
    await mca_client.async_treble_up(1)
    mca_client._async_send_and_validate.assert_not_called()
    
    # Treble Min
    mca_client._zone_data[1].treble = HtdConstants.MCA_MIN_TREBLE
    await mca_client.async_treble_down(1)
    mca_client._async_send_and_validate.assert_not_called()

# --- Lync Tests ---

@pytest.mark.asyncio
async def test_lync_set_bass(lync_client):
    lync_client._send_cmd = AsyncMock() # Ensure this is mocked
    lync_client._async_send_and_validate = AsyncMock()
    
    target_bass = 5
    await lync_client.async_set_bass(1, target_bass)
    
    args_send = lync_client._send_cmd.call_args[0]
    # args: zone, command, data_code
    assert args_send[0] == 1
    assert args_send[1] == HtdLyncCommands.BASS_SETTING_CONTROL_COMMAND_CODE
    assert args_send[2] == target_bass & 0xFF

    args_validate = lync_client._async_send_and_validate.call_args[0]
    # args: validate, zone, command, data_code
    assert args_validate[1] == 1
    # Commit Command
    assert args_validate[2] == HtdLyncCommands.COMMON_COMMAND_CODE
    assert args_validate[3] == HtdLyncConstants.STATUS_REFRESH_CODE

@pytest.mark.asyncio
async def test_lync_set_treble(lync_client):
    lync_client._send_cmd = AsyncMock() # Mock _send_cmd as well
    lync_client._async_send_and_validate = AsyncMock()
    
    target_treble = -5
    await lync_client.async_set_treble(1, target_treble)
    
    args_send = lync_client._send_cmd.call_args[0]
    assert args_send[0] == 1
    assert args_send[1] == HtdLyncCommands.TREBLE_SETTING_CONTROL_COMMAND_CODE
    assert args_send[2] == target_treble & 0xFF

    args_validate = lync_client._async_send_and_validate.call_args[0]
    assert args_validate[1] == 1
    assert args_validate[2] == HtdLyncCommands.COMMON_COMMAND_CODE
    assert args_validate[3] == HtdLyncConstants.STATUS_REFRESH_CODE


@pytest.mark.asyncio
async def test_lync_bass_up(lync_client):
    lync_client.async_set_bass = AsyncMock()
    lync_client._zone_data[1].bass = 0
    
    await lync_client.async_bass_up(1)
    lync_client.async_set_bass.assert_awaited_with(1, 1)

@pytest.mark.asyncio
async def test_lync_bass_down(lync_client):
    lync_client.async_set_bass = AsyncMock()
    lync_client._zone_data[1].bass = 0
    
    await lync_client.async_bass_down(1)
    lync_client.async_set_bass.assert_awaited_with(1, -1)

@pytest.mark.asyncio
async def test_lync_treble_up(lync_client):
    lync_client.async_set_treble = AsyncMock()
    lync_client._zone_data[1].treble = 0
    
    await lync_client.async_treble_up(1)
    lync_client.async_set_treble.assert_awaited_with(1, 1)

@pytest.mark.asyncio
async def test_lync_treble_down(lync_client):
    lync_client.async_set_treble = AsyncMock()
    lync_client._zone_data[1].treble = 0
    
    await lync_client.async_treble_down(1)
    lync_client.async_set_treble.assert_awaited_with(1, -1)

@pytest.mark.asyncio
async def test_lync_limits(lync_client):
    lync_client.async_set_bass = AsyncMock()
    lync_client.async_set_treble = AsyncMock()
    
    # Bass Max
    lync_client._zone_data[1].bass = HtdConstants.LYNC_MAX_BASS
    await lync_client.async_bass_up(1)
    lync_client.async_set_bass.assert_not_called()
    
    # Bass Min
    lync_client._zone_data[1].bass = HtdConstants.LYNC_MIN_BASS
    await lync_client.async_bass_down(1)
    lync_client.async_set_bass.assert_not_called()
