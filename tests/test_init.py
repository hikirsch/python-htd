import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from htd_client import async_get_client, async_get_model_info, HtdMcaClient, HtdLyncClient
from htd_client.constants import HtdConstants, HtdDeviceKind

@pytest.mark.asyncio
async def test_async_get_model_info_success():
    mock_loop = MagicMock()
    mock_response = b"MCA-66" 
    
    # MCA-66 identifier is "MCA-66" in constants? Let's check constants.py content implicitly or mock it.
    # Actually, let's look at what async_get_model_info does.
    # It sends MODEL_QUERY_COMMAND_CODE.
    # It iterates HtdConstants.SUPPORTED_MODELS and checks if model["identifier"] is in response.
    
    with patch("htd_client.utils.async_send_command", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = b"Wangine_MCA66"
        
        model = await async_get_model_info(loop=mock_loop, network_address=("1.2.3.4", 10006))
        
        assert model == HtdConstants.SUPPORTED_MODELS["mca66"]
        mock_send.assert_called_once()

@pytest.mark.asyncio
async def test_async_get_model_info_failure():
    mock_loop = MagicMock()
    
    with patch("htd_client.utils.async_send_command", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = b"Unknown Device"
        
        model = await async_get_model_info(loop=mock_loop, network_address=("1.2.3.4", 10006))
        
        assert model is None

@pytest.mark.asyncio
async def test_async_get_client_mca():
    mock_loop = MagicMock()
    
    with patch("htd_client.async_get_model_info", new_callable=AsyncMock) as mock_get_info:
        model_info = HtdConstants.SUPPORTED_MODELS["mca66"]
        mock_get_info.return_value = model_info
        
        with patch("htd_client.mca_client.HtdMcaClient.async_connect", new_callable=AsyncMock) as mock_connect:
            client = await async_get_client(loop=mock_loop, network_address=("1.2.3.4", 10006))
            
            assert isinstance(client, HtdMcaClient)
            mock_connect.assert_called_once()

@pytest.mark.asyncio
async def test_async_get_client_lync():
    mock_loop = MagicMock()
    
    with patch("htd_client.async_get_model_info", new_callable=AsyncMock) as mock_get_info:
        model_info = HtdConstants.SUPPORTED_MODELS["lync6"]
        mock_get_info.return_value = model_info
        
        with patch("htd_client.lync_client.HtdLyncClient.async_connect", new_callable=AsyncMock) as mock_connect:
            client = await async_get_client(loop=mock_loop, network_address=("1.2.3.4", 10006))
            
            assert isinstance(client, HtdLyncClient)
            mock_connect.assert_called_once()

@pytest.mark.asyncio
async def test_async_get_client_unknown():
    mock_loop = MagicMock()
    
    with patch("htd_client.async_get_model_info", new_callable=AsyncMock) as mock_get_info:
        mock_get_info.return_value = {"kind": "unknown_kind"}
        
        with pytest.raises(ValueError, match="Unknown Device Kind"):
            await async_get_client(loop=mock_loop, network_address=("1.2.3.4", 10006))
