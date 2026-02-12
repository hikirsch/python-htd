import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from htd_client.base_client import BaseClient
from htd_client.constants import HtdConstants, HtdModelInfo, HtdDeviceKind, HtdCommonCommands

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

@pytest.fixture
def mock_model_info():
    return {
        "zones": 6,
        "sources": 6,
        "friendly_name": "MCA66",
        "name": "MCA66",
        "kind": HtdDeviceKind.mca,
        "identifier": b'Wangine_MCA66'
    }

@pytest.fixture
def client(mock_model_info):
    loop = MagicMock()
    # Mock create_task to return a mock task
    mock_task = MagicMock()
    mock_task.cancel = MagicMock()
    # Mock call_soon and call_later? Not strictly needed unless used.
    loop.create_task.return_value = mock_task
    
    return ConcreteClient(loop, mock_model_info, network_address=("1.2.3.4", 10006))

@pytest.mark.asyncio
async def test_connect_network(client):
    # client._loop is a MagicMock. create_connection on it needs to be awaitable.
    # We can patch client._loop.create_connection.
    client._loop.create_connection = AsyncMock()
    # It returns (transport, protocol)
    client._loop.create_connection.return_value = (MagicMock(), MagicMock())
    
    await client.async_connect()
    client._loop.create_connection.assert_called_once()

@pytest.mark.asyncio
async def test_connect_serial(mock_model_info):
    loop = MagicMock()
    client = ConcreteClient(loop, mock_model_info, serial_address="/dev/ttyUSB0")
    
    with patch("htd_client.base_client.create_serial_connection", new_callable=AsyncMock) as mock_create_serial:
        await client.async_connect()
        mock_create_serial.assert_called_once()

@pytest.mark.asyncio
async def test_connection_lifecycle(client):
    transport = MagicMock()
    # Connection made
    with patch("asyncio.create_task") as mock_create_task:
        client.connection_made(transport)
        assert client.connected
        assert client._connection == transport
        mock_create_task.assert_called() # Heartbeat task

    # Disconnect
    client.disconnect()
    assert client._disconnected
    transport.close.assert_called_once()
    
    # Connection lost
    client.connection_lost(None)
    assert not client.connected

@pytest.mark.asyncio
async def test_reconnect_logic(client):
    # Setup initial state
    client._connected = False
    client._disconnected = False
    
    # Mock async_connect to fail once then succeed?
    # Actually checking internal logic of _async_reconnect handles exceptions and retries
    
    # Rerunning logic:
    # await client._async_reconnect() -> calls connect() -> raises Exception.
    # catches exception -> updates delay -> creates task.
    # func returns.
    
    # Check that new task was created
    # We need to check if asyncio.create_task was called. 
    # But we didn't patch it inside the test function scope valid for the 'await client._async_reconnect()'.
    # We need to wrap the call.
    
    with patch.object(client, 'async_connect', new_callable=AsyncMock) as mock_connect:
        mock_connect.side_effect = [Exception("Fail"), None]
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("asyncio.create_task") as mock_create_task:
                 await client._async_reconnect()
                 assert mock_connect.call_count == 1
                 mock_create_task.assert_called()

def test_data_received(client):
    # Mock _process_next_command to consume data
    client._process_next_command = MagicMock(return_value=(1, 5)) # zone 1, 5 bytes consumed
    client._broadcast = MagicMock() # Needs to be async? create_task handles it.
    client._loop.create_task = MagicMock()
    
    client.data_received(b"12345")
    
    client._process_next_command.assert_called()
    assert len(client._buffer) == 0
    client._loop.create_task.assert_called() # Broadcast

def test_data_received_partial(client):
    # Mock processing that consumes nothing (waiting for more data)
    client._process_next_command = MagicMock(return_value=(None, 0))
    
    client.data_received(b"123")
    assert client._buffer == b"123"
    
    # Send more
    # Mock processing consuming everything now
    client._process_next_command.side_effect = [(1, 6)]
    client.data_received(b"456")
    # buffer was 123, now 123456. consumed 6. empty.
    assert len(client._buffer) == 0

def test_process_next_command_parsing(client):
    from htd_client.utils import calculate_checksum
    
    # Construct a valid ZONE_STATUS packet
    # Header: 0x02 0x00
    # Zone: 0x01
    # Cmd: 0x05 (ZONE_STATUS)
    # Len: 9 (from map)
    # Data: 9 bytes
    # Checksum: 1 byte
    
    header = bytes([HtdConstants.HEADER_BYTE, HtdConstants.RESERVED_BYTE])
    zone = 1
    cmd = HtdCommonCommands.ZONE_STATUS_RECEIVE_COMMAND
    # Data length for ZONE_STATUS is 9.
    # 0: toggles, 1: ?, 2: ?, 3: ?, 4: source, 5: vol, 6: treb, 7: bass, 8: bal
    data_content = bytes([0] * 9) 
    
    frame_to_sum = header + bytes([zone, cmd]) + data_content
    checksum = calculate_checksum(frame_to_sum)
    
    full_packet = frame_to_sum + bytes([checksum])
    
    # Setup client state
    client._subscribers = set()
    client._model_info["kind"] = HtdDeviceKind.mca
    client._zone_data = {}
    
    client._parse_zone = MagicMock()
    mock_zone_detail = MagicMock()
    client._parse_zone.return_value = mock_zone_detail
    
    zone_ret, length_ret = client._process_next_command(full_packet)
    
    assert zone_ret == 1
    assert length_ret == len(full_packet)
    client._parse_zone.assert_called_once()
    assert client._zone_data[1] == mock_zone_detail

@pytest.mark.asyncio
async def test_send_and_validate_success(client):
    client._connection = MagicMock()
    client._connection.write = MagicMock()
    client._socket_lock = asyncio.Lock()
    
    validate_func = MagicMock(side_effect=[False, True]) # Fail first check, succeed second
    # get_zone calls validate. 
    # Logic: while not validate(get_zone(zone)):
    
    client.get_zone = MagicMock()
    
    await client._async_send_and_validate(validate_func, 1, 0x01, 0x02)
    
    assert client._connection.write.call_count >= 1

@pytest.mark.asyncio
async def test_send_and_validate_timeout(client):
    client._connection = MagicMock()
    client._socket_lock = asyncio.Lock()
    client._retry_attempts = 1
    client._command_retry_timeout = 0 # Immediate retry
    
    validate_func = MagicMock(return_value=False) # Always fail
    client.get_zone = MagicMock()
    client.refresh = AsyncMock()
    
    with pytest.raises(Exception, match="Failed to execute command"):
         await client._async_send_and_validate(validate_func, 1, 0x01, 0x02)
