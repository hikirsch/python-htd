import pytest
from unittest.mock import MagicMock, AsyncMock
from htd_client.lync_client import HtdLyncClient
from htd_client.constants import HtdConstants

@pytest.fixture
def lync_client():
    mock_loop = MagicMock()
    model_info = {"zones": 6, "sources": 6, "kind": "lync", "name": "Lync6"}
    client = HtdLyncClient(mock_loop, model_info)
    client._connection = MagicMock()
    client._socket_lock = AsyncMock()
    client._zone_data = {}
    return client

@pytest.mark.asyncio
async def test_lync_volume_down_boundary(lync_client):
    # Test volume down when already 0
    lync_client._zone_data[1] = MagicMock(volume=0)
    lync_client.async_set_volume = AsyncMock()
    
    await lync_client.async_volume_down(1)
    
    # Should not call set_volume
    lync_client.async_set_volume.assert_not_called()

@pytest.mark.asyncio
async def test_lync_set_bass_no_change(lync_client):
    # Test setting bass to same value
    lync_client._zone_data[1] = MagicMock(bass=0)
    lync_client._async_send_and_validate = AsyncMock()
    
    await lync_client.async_set_bass(1, 0)
    
    # Should not send command
    lync_client._async_send_and_validate.assert_not_called()

@pytest.mark.asyncio
async def test_lync_set_treble_no_change(lync_client):
    # Test setting treble to same value
    lync_client._zone_data[1] = MagicMock(treble=0)
    lync_client._async_send_and_validate = AsyncMock()
    
    await lync_client.async_set_treble(1, 0)
    
    # Should not send command
    lync_client._async_send_and_validate.assert_not_called()

@pytest.mark.asyncio
async def test_lync_set_balance_no_change(lync_client):
    # Test setting balance to same value
    lync_client._zone_data[1] = MagicMock(balance=0)
    lync_client._async_send_and_validate = AsyncMock()
    
    await lync_client.async_set_balance(1, 0)
    
    # Should not send command
    lync_client._async_send_and_validate.assert_not_called()

@pytest.mark.asyncio
async def test_lync_bass_up_boundary(lync_client):
    # Test bass up when already max
    lync_client._zone_data[1] = MagicMock(bass=HtdConstants.LYNC_MAX_BASS)
    lync_client.async_set_bass = AsyncMock()
    
    await lync_client.async_bass_up(1)
    
    # Should not call set_bass
    lync_client.async_set_bass.assert_not_called()

@pytest.mark.asyncio
async def test_lync_bass_down_boundary(lync_client):
    # Test bass down when already min
    lync_client._zone_data[1] = MagicMock(bass=HtdConstants.LYNC_MIN_BASS)
    lync_client.async_set_bass = AsyncMock()
    
    await lync_client.async_bass_down(1)
    
    # Should not call set_bass
    lync_client.async_set_bass.assert_not_called()

@pytest.mark.asyncio
async def test_lync_treble_up_boundary(lync_client):
    # Test treble up when already max
    lync_client._zone_data[1] = MagicMock(treble=HtdConstants.LYNC_MAX_TREBLE)
    lync_client.async_set_treble = AsyncMock()
    
    await lync_client.async_treble_up(1)
    
    # Should not call set_treble
    lync_client.async_set_treble.assert_not_called()

@pytest.mark.asyncio
async def test_lync_treble_down_boundary(lync_client):
    # Test treble down when already min
    lync_client._zone_data[1] = MagicMock(treble=HtdConstants.LYNC_MIN_TREBLE)
    lync_client.async_set_treble = AsyncMock()
    
    await lync_client.async_treble_down(1)
    
    # Should not call set_treble
    lync_client.async_set_treble.assert_not_called()

@pytest.mark.asyncio
async def test_lync_balance_left_boundary(lync_client):
    # Test balance left when already min
    lync_client._zone_data[1] = MagicMock(balance=HtdConstants.LYNC_MIN_BALANCE)
    lync_client.async_set_balance = AsyncMock()
    
    await lync_client.async_balance_left(1)
    
    # Should not call set_balance
    lync_client.async_set_balance.assert_not_called()

@pytest.mark.asyncio
async def test_lync_balance_right_boundary(lync_client):
    # Test balance right when already max
    lync_client._zone_data[1] = MagicMock(balance=HtdConstants.LYNC_MAX_BALANCE)
    lync_client.async_set_balance = AsyncMock()
    
    await lync_client.async_balance_right(1)
    
    # Should not call set_balance
    lync_client.async_set_balance.assert_not_called()

@pytest.mark.asyncio
async def test_lync_volume_down_success(lync_client):
    # Test volume down when > 0
    lync_client._zone_data[1] = MagicMock(volume=10)
    lync_client.async_set_volume = AsyncMock()
    
    await lync_client.async_volume_down(1)
    
    # Should call set_volume with 9
    lync_client.async_set_volume.assert_called_once_with(1, 9)
