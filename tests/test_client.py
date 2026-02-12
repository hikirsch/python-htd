from encodings import utf_8
from unittest.mock import MagicMock, patch

import pytest

from htd_client.mca_client import HtdMcaClient
from htd_client.constants import HtdConstants, HtdMcaCommands, HtdMcaConstants

# Mock constants
MOCK_IP_ADDRESS = "10.0.0.1"
MOCK_PORT = 12345

MOCK_RETRY_ATTEMPTS = 2
MOCK_SOCKET_TIMEOUT = 500
MOCK_COMMAND_DELAY = 250


@pytest.fixture
def htd_instance():
    loop = MagicMock()
    model_info = HtdConstants.SUPPORTED_MODELS["mca66"]
    client = HtdMcaClient(
        loop=loop,
        model_info=model_info,
        network_address=(MOCK_IP_ADDRESS, MOCK_PORT),
        retry_attempts=MOCK_RETRY_ATTEMPTS,
        socket_timeout=MOCK_SOCKET_TIMEOUT,
    )
    client._zone_data = {}
    return client


def test_constructor(htd_instance):
    assert htd_instance._network_address == (MOCK_IP_ADDRESS, MOCK_PORT)
    assert htd_instance._retry_attempts == MOCK_RETRY_ATTEMPTS
    assert htd_instance._socket_timeout_sec == MOCK_SOCKET_TIMEOUT / 1_000


@pytest.mark.parametrize(
    'method,code', [
        ("async_volume_up", HtdMcaCommands.VOLUME_UP_COMMAND),
        ("async_volume_down", HtdMcaCommands.VOLUME_DOWN_COMMAND),
        ("async_toggle_mute", HtdMcaCommands.TOGGLE_MUTE_COMMAND),
        ("async_power_on", HtdMcaCommands.POWER_ON_ZONE_COMMAND_CODE),
        ("async_power_off", HtdMcaCommands.POWER_OFF_ZONE_COMMAND_CODE),
        ("async_bass_up", HtdMcaCommands.BASS_UP_COMMAND),
        ("async_bass_down", HtdMcaCommands.BASS_DOWN_COMMAND),
        ("async_treble_up", HtdMcaCommands.TREBLE_UP_COMMAND),
        ("async_treble_down", HtdMcaCommands.TREBLE_DOWN_COMMAND),
        ("async_balance_left", HtdMcaCommands.BALANCE_LEFT_COMMAND),
        ("async_balance_right", HtdMcaCommands.BALANCE_RIGHT_COMMAND),
    ]
)
@patch('htd_client.base_client.BaseClient._async_send_and_validate', return_value="return_value")
@patch('htd_client.mca_client.HtdMcaClient.get_zone')
def test_zone_set_commands(mock_get_zone, mock__send_and_validate, method, code, htd_instance):
    zone_number = 4 # Changed to a valid zone number for mca66 (1-6)
    
    # Mock zone info to avoid logic errors in adjustments
    mock_zone_info = MagicMock()
    mock_zone_info.volume = 30
    mock_zone_info.bass = 0
    mock_zone_info.treble = 0
    mock_zone_info.balance = 0
    mock_zone_info.mute = False
    mock_zone_info.power = True
    
    # Configure get_zone to return our mock
    # We need to populate _zone_data as get_zone reads from it
    htd_instance._zone_data[zone_number] = mock_zone_info
    mock_get_zone.return_value = mock_zone_info
    
    # Since methods are async, we need to await them or mock them properly.
    # But since we are mocking the underlying _async_send_and_validate, we can just call the coroutine.
    # However, running the coroutine requires a loop.
    import asyncio
    
    coro = getattr(htd_instance, method)(zone_number)
    asyncio.run(coro)

    # Check that _async_send_and_validate was called with expected args
    # Note: Validate lambda is the first arg, we skip checking it precisely for now, check rest
    call_args = mock__send_and_validate.call_args
    assert call_args[0][1] == zone_number
    assert call_args[0][2] == HtdMcaCommands.COMMON_COMMAND_CODE
    assert call_args[0][3] == code


@patch('htd_client.base_client.BaseClient._async_send_and_validate', return_value="return_value")
def test_zone_set_source_command(mock__send_and_validate, htd_instance):
    zone_number = 2
    source_number = 3
    
    import asyncio
    asyncio.run(htd_instance.async_set_source(zone_number, source_number))

    call_args = mock__send_and_validate.call_args
    assert call_args[0][1] == zone_number
    assert call_args[0][2] == HtdMcaCommands.COMMON_COMMAND_CODE
    assert call_args[0][3] == HtdMcaConstants.SOURCE_COMMAND_OFFSET + source_number


@pytest.mark.parametrize(
    'method,code', [
        ("power_off_all_zones", HtdMcaCommands.POWER_OFF_ALL_ZONES_COMMAND_CODE),
        ("power_on_all_zones", HtdMcaCommands.POWER_ON_ALL_ZONES_COMMAND_CODE),
    ]
)
@patch('htd_client.mca_client.HtdMcaClient._send_cmd')
def test_all_zones_set_commands(mock__send_cmd, method, code, htd_instance):
    import asyncio
    # These methods call _send_cmd which is async
    asyncio.run(getattr(htd_instance, method)())
    mock__send_cmd.assert_called_with(1, HtdMcaCommands.COMMON_COMMAND_CODE, code)


@patch('htd_client.mca_client.HtdMcaClient._send_cmd', return_value="return_value")
def test_all_zones_query_command(mock__send_cmd, htd_instance):
    import asyncio
    asyncio.run(htd_instance.refresh())
    mock__send_cmd.assert_called_with(0, HtdMcaCommands.QUERY_COMMAND_CODE, 0)


# @patch('htd_client.utils.get_friendly_name')
# @patch('htd_client.HtdClient._send')
# def test_model_info_query(mock__send, mock_get_friendly_name, htd_instance):
#     expected = "return_value"
#     expected_friendly_name = "friendly_name"
#     mock__send.return_value = expected.encode(utf_8.getregentry().name)
#     mock_get_friendly_name.return_value = expected_friendly_name
#     (model_info, friendly_name) = htd_instance.get_model_info()
#     mock__send.assert_called_with(1, HtdConstants.MODEL_QUERY_COMMAND_CODE, 0)
#     assert friendly_name == expected_friendly_name
#     assert model_info == expected


@patch('htd_client.mca_client.HtdMcaClient._send_cmd', return_value="return_value")
def test_query_zone(mock__send_cmd, htd_instance):
    zone_number = 1
    import asyncio
    asyncio.run(htd_instance.refresh_zone(zone_number))
    mock__send_cmd.assert_called_with(zone_number, HtdMcaCommands.QUERY_COMMAND_CODE, 0)



