import pytest
import htd_client.utils
from htd_client.constants import HtdConstants
from unittest.mock import AsyncMock, patch

def test_build_command_with_extra_data():
    # Test build_command with extra_data (line 34)
    zone = 1
    command = 2
    data = 3
    extra = bytearray([4, 5])
    
    cmd = htd_client.utils.build_command(zone, command, data, extra)
    
    # Header (2) + Zone (1) + Command (1) + Data (1) + Extra (2) + Checksum (1) = 8 bytes
    assert len(cmd) == 8
    assert cmd[0] == HtdConstants.HEADER_BYTE
    assert cmd[4] == data
    assert cmd[5] == 4
    assert cmd[6] == 5

@pytest.mark.asyncio
async def test_async_send_command_no_header():
    # Test async_send_command when response has no header (line 104)
    loop = AsyncMock()
    # Mock open_connection
    reader = AsyncMock()
    writer = AsyncMock()
    
    # Return data without header
    reader.read.return_value = b'\x00\x00\x00\x00' 
    
    with patch('asyncio.open_connection', return_value=(reader, writer)):
        response = await htd_client.utils.async_send_command(
            loop,
            b'cmd',
            network_address=('localhost', 1234)
        )
        
        assert response == b'\x00\x00\x00\x00'
