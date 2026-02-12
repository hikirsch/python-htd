import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from htd_client.constants import HtdConstants, HtdDeviceKind
from htd_client.utils import (
    convert_value, 
    stringify_bytes_raw, 
    stringify_bytes, 
    convert_volume_to_raw, 
    decode_response, 
    parse_zone_name, 
    async_send_command
)

def test_convert_value():
    assert convert_value(0x10) == 0x10
    # convert_value returns value - 0x100 if value > 0x7F
    assert convert_value(0x80) == -128 
    assert convert_value(0xFF) == -1

def test_stringify_bytes_raw():
    b = bytes([0x01, 0x02, 0xFF])
    assert stringify_bytes_raw(b, "hex") == "0x01 0x02 0xff"
    
    with pytest.raises(ValueError):
        stringify_bytes_raw(b, "unknown")

def test_stringify_bytes():
    # Chunk size is 14.
    data = bytes(range(14))
    output = stringify_bytes(data)
    assert "[ 1]" in output

def test_convert_volume_to_raw():
    # MAX_RAW_VOLUME = 256, MAX_VOLUME = 60
    assert convert_volume_to_raw(0) == 0
    # MAX_RAW_VOLUME - (MAX_VOLUME - volume)
    # 60 -> 256 - (60 - 60) = 256
    assert convert_volume_to_raw(60) == 256
    # 30 -> 256 - (60 - 30) = 226
    assert convert_volume_to_raw(30) == 226

def test_decode_response():
    assert decode_response(b"hello") == "hello"

def test_parse_zone_name():
    # NAME_START_INDEX = 4. LENGTH = 10.
    # 0,1,2,3, NAME...
    prefix = b"\x00\x00\x00\x00"
    name = b"Zone1"
    padding = b"\x00" * (10 - len(name))
    data = prefix + name + padding + b"EXTRA"
    
    assert parse_zone_name(data) == "Zone1"

@pytest.mark.asyncio
async def test_async_send_command_network():
    mock_loop = MagicMock()
    mock_reader = AsyncMock()
    mock_writer = MagicMock()
    mock_writer.drain = AsyncMock()
    mock_writer.wait_closed = AsyncMock()
    
    # Setup mock reader to return data with header. Header is 0x02 0x00.
    # We should return header first then data? Or is it finding header in response?
    # data.find(HEADER). If found, returns data[0:header_index].
    # So if we return b"RESPONSE" + HEADER, it returns "RESPONSE".
    mock_reader.read.return_value = b"response" + HtdConstants.MESSAGE_HEADER
    
    with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_open:
        mock_open.return_value = (mock_reader, mock_writer)
        
        response = await async_send_command(mock_loop, b"cmd", network_address=("1.2.3.4", 1234))
        
        mock_open.assert_called_with("1.2.3.4", 1234)
        mock_writer.write.assert_called_with(b"cmd")
        mock_writer.drain.assert_called()
        mock_writer.close.assert_called()
        assert response == b"response"

@pytest.mark.asyncio
async def test_async_send_command_serial():
    mock_loop = MagicMock()
    mock_reader = AsyncMock()
    mock_writer = MagicMock()
    mock_writer.drain = AsyncMock()
    mock_writer.wait_closed = AsyncMock()
    
    mock_reader.read.return_value = b"response" + HtdConstants.MESSAGE_HEADER
    
    with patch("htd_client.utils.open_serial_connection", new_callable=AsyncMock) as mock_open:
        mock_open.return_value = (mock_reader, mock_writer)
        
        response = await async_send_command(mock_loop, b"cmd", serial_address="/dev/ttyUSB0")
        
        mock_open.assert_called()
        assert response == b"response"

@pytest.mark.asyncio
async def test_async_send_command_no_address():
    mock_loop = MagicMock()
    
    with pytest.raises(ValueError, match="unable to connect"):
        await async_send_command(mock_loop, b"cmd")
