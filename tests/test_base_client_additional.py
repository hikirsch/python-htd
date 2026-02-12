import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from htd_client.base_client import BaseClient
from htd_client.constants import HtdConstants, HtdCommonCommands, HtdDeviceKind

@pytest.fixture
def client():
    mock_model_info = {
        "zones": 16, # Use 16 for keypad test
        "sources": 6,
        "friendly_name": "MCA66",
        "name": "MCA66",
        "kind": HtdDeviceKind.mca,
        "identifier": b'Wangine_MCA66'
    }
    loop = MagicMock()
    mock_task = MagicMock()
    mock_task.cancel = MagicMock()
    loop.create_task.return_value = mock_task
    
    c = ConcreteClient(loop, mock_model_info, network_address=("1.2.3.4", 10006))
    c._connection = MagicMock()
    c._subscribers = set()
    c._zone_data = {}
    c._socket_lock = asyncio.Lock()
    c._callback_lock = asyncio.Lock()
    c._connected = True
    return c

class ConcreteClient(BaseClient):
    async def refresh(self, zone: int = None): pass
    async def power_on_all_zones(self): pass
    async def power_off_all_zones(self): pass
    async def async_set_source(self, zone: int, source: int): pass
    async def async_volume_up(self, zone: int): pass
    async def async_set_volume(self, zone: int, volume: int): pass
    async def async_volume_down(self, zone: int): pass
    async def async_mute(self, zone: int): pass
    async def async_unmute(self, zone: int): pass
    async def async_power_on(self, zone: int): pass
    async def async_power_off(self, zone: int): pass
    async def async_bass_up(self, zone: int): pass
    async def async_bass_down(self, zone: int): pass
    async def async_treble_up(self, zone: int): pass
    async def async_treble_down(self, zone: int): pass
    async def async_balance_left(self, zone: int): pass
    async def async_balance_right(self, zone: int): pass

@pytest.mark.asyncio
async def test_heartbeat_task(client):
    client.refresh = AsyncMock()
    # Mock sleep to yield control but not wait.
    
    # We can mock refresh to set connected=False?
    client.refresh.side_effect = lambda: setattr(client, "_connected", False)
    client._connected = True
    
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # Run heartbeat
        await client._heartbeat()
        mock_sleep.assert_called_with(60)
    
    client.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_broadcast_subscribers(client):
    client._zones_loaded = 6
    client._subscribers = set()
    
    # Mock callback
    callback = MagicMock()
   
    await client.async_subscribe(callback)
    assert callback in client._subscribers
    
    await client._broadcast(1)
    callback.assert_called_with(1)

@pytest.mark.asyncio
async def test_toggle_mute(client):
    client.async_mute = AsyncMock()
    client.async_unmute = AsyncMock()
    client._zone_data = {
        1: MagicMock(mute=True),
        2: MagicMock(mute=False)
    }
    
    await client.async_toggle_mute(1)
    client.async_unmute.assert_called_with(1)
    
    await client.async_toggle_mute(2)
    client.async_mute.assert_called_with(2)

def test_parse_keypad_exists(client):
    client._zone_data = {}
    cmd = HtdCommonCommands.KEYPAD_EXISTS_RECEIVE_COMMAND
    
    # Zones 1-8: 0xFF -> all enabled.
    # Zones 9-16: 0x01 -> 9 enabled.
    data = bytes([0, 0xFF, 0, 0x01, 0])
    
    client._parse_command(0, cmd, data)
    
    assert client._zone_data[1].enabled
    assert client._zone_data[2].enabled
    assert client._zone_data[8].enabled
    assert client._zone_data[9].enabled
    assert not client._zone_data[10].enabled

def test_parse_source_name(client):
    cmd = HtdCommonCommands.SOURCE_NAME_RECEIVE_COMMAND
    # data[11] = source index
    # data[0:10] = name
    name = b"ChromeCast"
    source_idx = 3
    data = name + b"\x00" * (11 - len(name)) + bytes([source_idx])
    
    # The method updates something?
    # Code is commented out in base_client.py lines 338-339?
    # But it does: source = data[11], name = ...
    # So it runs lines of code.
    client._parse_command(0, cmd, data)

def test_parse_error(client):
    cmd = HtdCommonCommands.ERROR_RECEIVE_COMMAND
    data = bytes([0x01])
    # Just logs warning
    client._parse_command(0, cmd, data)

def test_parse_unknown(client):
    cmd = 0xFE
    data = bytes([0])
    client._parse_command(0, cmd, data)
