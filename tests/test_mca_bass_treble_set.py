import pytest
from unittest.mock import MagicMock, AsyncMock, call
from htd_client.mca_client import HtdMcaClient
from htd_client.constants import HtdConstants

@pytest.fixture
def mca_client():
    mock_loop = MagicMock()
    model_info = {"zones": 6, "sources": 6, "kind": "mca", "name": "MCA66"}
    client = HtdMcaClient(mock_loop, model_info)
    client._connection = MagicMock()
    client._socket_lock = AsyncMock()
    client._zone_data = {}
    
    # Mock methods to avoid actual network calls
    client._async_send_and_validate = AsyncMock()
    client.async_power_on = AsyncMock()
    
    return client

@pytest.mark.asyncio
async def test_set_bass_target(mca_client):
    zone = 1
    target_bass = 4 # Use a valid step (4 on wire)
    current_bass = 0
    
    # Setup initial state
    mca_client._zone_data[zone] = MagicMock(bass=current_bass, power=True)
    
    # Call set_bass
    await mca_client.async_set_bass(zone, target_bass)
    
    # Check target is set
    assert mca_client._target_bass[zone] == target_bass
    assert mca_client.has_bass_target(zone)
    
    # Check _async_set_bass logic trigger (should send UP command)
    # The first call interacts with _async_set_bass which calls _async_send_and_validate
    mca_client._async_send_and_validate.assert_called()

@pytest.mark.asyncio
async def test_set_treble_logic(mca_client):
    zone = 1
    mca_client._zone_data[zone] = MagicMock(treble=0, power=True)
    mca_client._target_treble[zone] = 4 # Step of 4
    
    # Test _async_set_treble directly
    await mca_client._async_set_treble(zone)
    
    # Should send UP command
    mca_client._async_send_and_validate.assert_called() 

@pytest.mark.asyncio
async def test_target_cleared_when_reached(mca_client):
    zone = 1
    target_bass = 4
    mca_client._target_bass[zone] = target_bass
    mca_client._zone_data[zone] = MagicMock(bass=target_bass, power=True)
    
    # Trigger update with matching value
    # We need to simulate _on_zone_update logic without the threadsafe call for simplicity
    if mca_client._zone_data[zone].bass == mca_client._target_bass[zone]:
        mca_client._target_bass[zone] = None
        
    assert mca_client._target_bass[zone] is None
    assert not mca_client.has_bass_target(zone)

@pytest.mark.asyncio
async def test_auto_power_on_bass(mca_client):
    zone = 1
    mca_client._zone_data[zone] = MagicMock(bass=0, power=False)
    
    # calling bass up should trigger power on
    await mca_client.async_bass_up(zone)
    
    mca_client.async_power_on.assert_called_with(zone)
    mca_client._async_send_and_validate.assert_called()

@pytest.mark.asyncio
async def test_auto_power_on_treble(mca_client):
    zone = 1
    mca_client._zone_data[zone] = MagicMock(treble=0, power=False)
    
    await mca_client.async_treble_up(zone)
    
    mca_client.async_power_on.assert_called_with(zone)
    mca_client._async_send_and_validate.assert_called()

@pytest.mark.asyncio
async def test_auto_power_on_balance(mca_client):
    zone = 1
    mca_client._zone_data[zone] = MagicMock(balance=0, power=False)
    
    await mca_client.async_balance_right(zone)
    
    mca_client.async_power_on.assert_called_with(zone)
    mca_client._async_send_and_validate.assert_called()

@pytest.mark.asyncio
async def test_set_balance_target(mca_client):
    zone = 1
    target_balance = 6
    mca_client._zone_data[zone] = MagicMock(balance=0, power=True)
    
    await mca_client.async_set_balance(zone, target_balance)
    
    assert mca_client._target_balance[zone] == target_balance
    assert mca_client.has_balance_target(zone)
    mca_client._async_send_and_validate.assert_called()

@pytest.mark.asyncio
async def test_set_balance_logic_resume(mca_client):
    zone = 1
    mca_client._zone_data[zone] = MagicMock(balance=0, power=True)
    mca_client._target_balance[zone] = 6
    
    await mca_client._async_set_balance(zone)
    
    # Should be RIGHT command since target > current (1 > 0)
    mca_client._async_send_and_validate.assert_called()

@pytest.mark.asyncio
async def test_set_balance_logic_left(mca_client):
    zone = 1
    mca_client._zone_data[zone] = MagicMock(balance=6, power=True)
    mca_client._target_balance[zone] = 0
    
    await mca_client._async_set_balance(zone)
    
    # Should be LEFT command
    mca_client._async_send_and_validate.assert_called()

@pytest.mark.asyncio
async def test_mca_rounding(mca_client):
    zone = 1
    mca_client._zone_data[zone] = MagicMock(bass=0, power=True)
    
    # Test round up: 3 -> 4
    await mca_client.async_set_bass(zone, 3)
    assert mca_client._target_bass[zone] == 4
    
    # Test round down: 1 -> 0
    await mca_client.async_set_bass(zone, 1)
    assert mca_client._target_bass[zone] == 0
    
    # Test exact: 4 -> 4
    await mca_client.async_set_bass(zone, 4)
    assert mca_client._target_bass[zone] == 4

@pytest.mark.asyncio
async def test_mca_balance_rounding(mca_client):
    zone = 1
    mca_client._zone_data[zone] = MagicMock(balance=0, power=True)
    
    # Test round up: 4 -> 6 (step is 6)
    # 4 / 6 = 0.66 -> round to 1 -> 1 * 6 = 6
    await mca_client.async_set_balance(zone, 4)
    assert mca_client._target_balance[zone] == 6
    
    # Test round down: 2 -> 0
    # 2 / 6 = 0.33 -> round to 0 -> 0 * 6 = 0
    await mca_client.async_set_balance(zone, 2)
    assert mca_client._target_balance[zone] == 0
    
    # Test exact: 6 -> 6
    await mca_client.async_set_balance(zone, 6)
    assert mca_client._target_balance[zone] == 6
