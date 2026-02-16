import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from htd_client.base_client import BaseClient
from htd_client.constants import HtdModelInfo

class ConcreteClient(BaseClient):
    pass

@pytest.fixture
def base_client():
    mock_loop = MagicMock()
    model_info = {"zones": 6, "sources": 6, "kind": "lync", "name": "Lync6"}
    client = ConcreteClient(mock_loop, model_info)
    return client

@pytest.mark.asyncio
async def test_wait_until_ready_success(base_client):
    base_client._ready = False
    
    # Simulate ready becoming true after delay
    async def make_ready():
        await asyncio.sleep(0.05)
        base_client._ready = True
        
    asyncio.create_task(make_ready())
    
    await base_client.async_wait_until_ready()
    assert base_client._ready is True

@pytest.mark.asyncio
async def test_wait_until_ready_timeout(base_client):
    base_client._ready = False
    base_client._socket_timeout_sec = 0.1
    
    with pytest.raises(Exception, match="Timed out waiting for device to be ready"):
        await base_client.async_wait_until_ready()

@pytest.mark.asyncio
async def test_connect_already_connected(base_client):
    base_client._connected = True
    result = await base_client.async_connect()
    assert result is None

@pytest.mark.asyncio
async def test_connect_no_address(base_client):
    base_client._connected = False
    base_client._serial_address = None
    base_client._network_address = None
    
    with pytest.raises(ValueError, match="No address provided"):
        await base_client.async_connect()

def test_ready_property(base_client):
    base_client._ready = True
    assert base_client.ready is True
    base_client._ready = False
    assert base_client.ready is False
