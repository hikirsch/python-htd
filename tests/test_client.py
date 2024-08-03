from encodings import utf_8
from unittest.mock import MagicMock, patch

import pytest

from htd_client import HtdClient
from htd_client.constants import HtdConstants

# Mock constants
MOCK_IP_ADDRESS = "10.0.0.1"
MOCK_PORT = 12345

MOCK_RETRY_ATTEMPTS = 2
MOCK_SOCKET_TIMEOUT = 500
MOCK_COMMAND_DELAY = 250


@pytest.fixture
def htd_instance():
    return HtdClient(
        ip_address=MOCK_IP_ADDRESS,
        port=MOCK_PORT,
        retry_attempts=MOCK_RETRY_ATTEMPTS,
        command_delay=MOCK_COMMAND_DELAY,
        socket_timeout=MOCK_SOCKET_TIMEOUT,
    )


def test_constructor(htd_instance):
    assert htd_instance._ip_address == MOCK_IP_ADDRESS
    assert htd_instance._port == MOCK_PORT
    assert htd_instance._retry_attempts == MOCK_RETRY_ATTEMPTS
    assert htd_instance._socket_timeout_sec == MOCK_SOCKET_TIMEOUT / 1_000
    assert htd_instance._command_delay_sec == MOCK_COMMAND_DELAY / 1_000


@pytest.mark.parametrize(
    'method,code', [
        ("volume_up", HtdConstants.VOLUME_UP_COMMAND),
        ("volume_down", HtdConstants.VOLUME_DOWN_COMMAND),
        ("toggle_mute", HtdConstants.TOGGLE_MUTE_COMMAND),
        ("power_on", HtdConstants.POWER_ON_ZONE_COMMAND),
        ("power_off", HtdConstants.POWER_OFF_ZONE_COMMAND),
        ("bass_up", HtdConstants.BASS_UP_COMMAND),
        ("bass_down", HtdConstants.BASS_DOWN_COMMAND),
        ("treble_up", HtdConstants.TREBLE_UP_COMMAND),
        ("treble_down", HtdConstants.TREBLE_DOWN_COMMAND),
        ("balance_left", HtdConstants.BALANCE_LEFT_COMMAND),
        ("balance_right", HtdConstants.BALANCE_RIGHT_COMMAND),
    ]
)
@patch('htd_client.utils.validate_zone')
@patch('htd_client.HtdClient._send_and_parse', return_value="return_value")
def test_zone_set_commands(mock__send_and_parse, mock_validate_zone, method, code, htd_instance):
    zone_number = 100
    response = getattr(htd_instance, method)(zone_number)
    mock_validate_zone.assert_called_with(zone_number)
    mock__send_and_parse.assert_called_with(zone_number, HtdConstants.SET_COMMAND_CODE, code)
    assert response == "return_value"


@patch('htd_client.utils.validate_zone')
@patch('htd_client.utils.validate_source')
@patch('htd_client.HtdClient._send_and_parse', return_value="return_value")
def test_zone_set_source_command(mock__send_and_parse, mock_validate_source, mock_validate_zone, htd_instance):
    zone_number = 20
    source_number = 30
    response = htd_instance.set_source(zone_number, source_number)

    mock_validate_zone.assert_called_with(zone_number)
    mock_validate_source.assert_called_with(source_number)

    mock__send_and_parse.assert_called_with(
        zone_number,
        HtdConstants.SET_COMMAND_CODE,
        HtdConstants.SOURCE_COMMAND_OFFSET + source_number
    )

    assert response == "return_value"


@pytest.mark.parametrize(
    'method,code', [
        ("power_off_all_zones", HtdConstants.POWER_OFF_ALL_ZONES_COMMAND),
        ("power_on_all_zones", HtdConstants.POWER_ON_ALL_ZONES_COMMAND),
    ]
)
@patch('htd_client.HtdClient._send_and_parse_all')
def test_all_zones_set_commands(mock__send_and_parse_all, method, code, htd_instance):
    callable = getattr(htd_instance, method)
    callable()
    mock__send_and_parse_all.assert_called_with(1, HtdConstants.SET_COMMAND_CODE, code)


@patch('htd_client.HtdClient._send_and_parse_all', return_value="return_value")
def test_all_zones_query_command(mock__send_and_parse_all, htd_instance):
    response = htd_instance.query_all_zones()
    mock__send_and_parse_all.assert_called_with(0, HtdConstants.QUERY_COMMAND_CODE, 0)
    assert response == "return_value"


@patch('htd_client.utils.get_friendly_name')
@patch('htd_client.HtdClient._send')
def test_model_info_query(mock__send, mock_get_friendly_name, htd_instance):
    expected = "return_value"
    expected_friendly_name = "friendly_name"
    mock__send.return_value = expected.encode(utf_8.getregentry().name)
    mock_get_friendly_name.return_value = expected_friendly_name
    (model_info, friendly_name) = htd_instance.get_model_info()
    mock__send.assert_called_with(1, HtdConstants.MODEL_QUERY_COMMAND_CODE, 0)
    assert friendly_name == expected_friendly_name
    assert model_info == expected


@patch('htd_client.HtdClient._send_and_parse', return_value="return_value")
def test_query_zone(mock__send_and_parse, htd_instance):
    zone_number = 1
    response = htd_instance.query_zone(zone_number)
    mock__send_and_parse.assert_called_with(zone_number, HtdConstants.QUERY_COMMAND_CODE, 0)
    assert response == "return_value"


@patch('htd_client.HtdClient._send_and_parse', return_value="return_value")
def test_send_and_parse_all(mock__send_and_parse, htd_instance):
    arg1 = 1
    arg2 = bytearray([0])
    arg3 = 2

    response = htd_instance._send_and_parse_all(arg1, arg2, arg3)
    mock__send_and_parse.assert_called_with(arg1, arg2, arg3, True)

    assert response == "return_value"


@patch('htd_client.utils.get_command')
@patch('socket.create_connection')
def test_send(mock_create_connection, mock_get_command, htd_instance):
    mock_socket_instance = MagicMock()
    mock_create_connection.return_value = mock_socket_instance
    mock_socket_instance.recv.return_value = "return_value"

    mock_get_command.return_value = 'fake_command'

    response = htd_instance._send(1, HtdConstants.SET_COMMAND_CODE, 1)

    mock_create_connection.assert_called_once_with(
        address=(MOCK_IP_ADDRESS, MOCK_PORT),
        timeout=MOCK_SOCKET_TIMEOUT / 1_000
    )

    mock_socket_instance.send.assert_called_with('fake_command')
    mock_get_command.assert_called_with(1, HtdConstants.SET_COMMAND_CODE, 1)

    mock_socket_instance.recv.assert_called_with(1024)
    mock_socket_instance.close.assert_called_once()

    assert response == "return_value"


@patch('htd_client.HtdClient._send')
@patch('htd_client.utils.parse_single_zone')
def test_send_and_parse_single(mock_parse_single_zone, mock__send, htd_instance):
    mock_response = "raw_return_value"
    mock_parsed_response = "return_value"
    mock__send.return_value = mock_response
    mock_parse_single_zone.return_value = mock_parsed_response
    mock_zone = 10
    mock_command = bytearray([0x01, 0x02, 0x03, 0x04, 0x05])
    mock_data_code = 5
    response = htd_instance._send_and_parse(mock_zone, mock_command, mock_data_code)

    assert response == mock_parsed_response


@patch('htd_client.HtdClient._send')
@patch('htd_client.utils.parse_all_zones')
def test_send_and_parse_multiple(mock_parse_all_zones, mock__send, htd_instance):
    mock_response = "raw_return_value"
    mock_parsed_response = "return_value"
    mock__send.return_value = mock_response
    mock_parse_all_zones.return_value = mock_parsed_response
    mock_zone = 10
    mock_command = bytearray([0x01, 0x02, 0x03, 0x04, 0x05])
    mock_data_code = 5
    response = htd_instance._send_and_parse(mock_zone, mock_command, mock_data_code, is_multiple=True)

    assert response == mock_parsed_response


@patch('htd_client.HtdClient._send')
@patch('htd_client.utils.parse_single_zone')
def test_send_and_parse_single_invalid_no_retry(mock_parse_single_zone, mock__send, htd_instance):
    mock_response = "raw_return_value"
    mock_parsed_response = None
    mock__send.return_value = mock_response
    mock_parse_single_zone.return_value = mock_parsed_response
    mock_zone = 10
    mock_command = bytearray([0x01, 0x02, 0x03, 0x04, 0x05])
    mock_data_code = 5
    response = htd_instance._send_and_parse(mock_zone, mock_command, mock_data_code, enable_retry=False)

    assert response is None
    assert mock__send.call_count == 1


@patch('time.sleep')
@patch('htd_client.HtdClient._send')
@patch('htd_client.utils.parse_single_zone')
def test_send_and_parse_single_invalid_with_retry(mock_parse_single_zone, mock__send, mock_sleep, htd_instance):
    mock_response = "raw_return_value"
    mock_parsed_response = None
    mock__send.return_value = mock_response
    mock_parse_single_zone.return_value = mock_parsed_response
    mock_zone = 10
    mock_command = bytearray([0x01, 0x02, 0x03, 0x04, 0x05])
    mock_data_code = 5
    response = htd_instance._send_and_parse(mock_zone, mock_command, mock_data_code, enable_retry=True)

    assert response is None
    assert mock__send.call_count == 3

    for i in range(0, MOCK_RETRY_ATTEMPTS):
        assert mock_sleep.call_args_list[i].args[0] == (i + 1) * MOCK_COMMAND_DELAY / 1_000


@patch('htd_client.HtdClient.query_zone')
def test_set_volume_query_zone_volume_ok(mock_query_zone, htd_instance):
    mock_zone = 10
    mock_volume = 30
    mock_zone_info = MagicMock()
    mock_zone_info.volume = 30
    mock_query_zone.return_value = mock_zone_info

    response = htd_instance.set_volume(mock_zone, mock_volume)
    assert mock_query_zone.call_count == 1
    assert response == mock_zone_info


@patch('htd_client.HtdClient.query_zone')
@patch('htd_client.HtdClient._send_and_parse')
def test_set_volume_query_zone_volume_down(mock_send_and_parse, mock_query_zone, htd_instance):
    mock_zone = 10
    mock_volume = 30

    mock_zone_info = MagicMock()
    mock_zone_info.volume = 40

    call_counter = {'count': 0}

    def mock_zone_info_response(
        zone: int,
        command: bytes,
        data_code: int,
        enable_retry: bool = False
    ):
        call_counter['count'] += 1

        mock = MagicMock()

        if call_counter['count'] == 1:
            mock.volume = 38
            return mock

        return None

    def on_increment(volume, zone_info):
        if call_counter['count'] == 1:
            return 40

        return None

    mock_send_and_parse.side_effect = mock_zone_info_response

    mock = MagicMock()
    mock.volume = 40
    mock_query_zone.return_value = mock

    response = htd_instance.set_volume(mock_zone, mock_volume, on_increment, mock_zone_info)

    assert mock_send_and_parse.call_args_list[0].args[0] == mock_zone
    assert mock_send_and_parse.call_args_list[0].args[1] == HtdConstants.SET_COMMAND_CODE
    assert mock_send_and_parse.call_args_list[0].args[2] == HtdConstants.VOLUME_DOWN_COMMAND
    assert mock_send_and_parse.call_args_list[0].kwargs['enable_retry'] == False

    assert mock_send_and_parse.call_args_list[1].args[0] == mock_zone
    assert mock_send_and_parse.call_args_list[1].args[1] == HtdConstants.SET_COMMAND_CODE
    assert mock_send_and_parse.call_args_list[1].args[2] == HtdConstants.VOLUME_UP_COMMAND
    assert mock_send_and_parse.call_args_list[1].kwargs['enable_retry'] == False

    # assert response == mock_zone_info_response

    # response = htd_instance.set_volume(mock_zone, mock_volume, None, mock_zone_info)
    # assert mock_query_zone.call_count == 1
    # assert response == mock_zone_info

    # response = htd_instance.set_volume(mock_zone, mock_volume, on_increment, None)
    # assert mock_query_zone.call_count == 1
    # assert response == mock_zone_info

    # response = htd_instance.set_volume(mock_zone, mock_volume, None, None)
    # assert mock_query_zone.call_count == 1
    # assert response == mock_zone_info

# @patch('htd_client.socket.create_connection')
# def _test_my_client(mock_create_connection, htd_instance):
#     # Create a mock socket instance
#     mock_socket_instance = MagicMock()
#     mock_create_connection.return_value = mock_socket_instance
#
#     mock_zone = 1
#     mock_power = True
#     mock_mode = False
#     mock_mute = True
#     mock_party_mode = False
#     mock_volume = 11
#     mock_source = 3
#     mock_treble = 25
#     mock_bass = 15
#     mock_balance = 18
#
#     mock_response = create_mock_response(
#         zone=mock_zone,
#         state_toggles={
#             "power": True,
#             "mode": False,
#             "mute": True,
#             "party_mode": False,
#         },
#         volume=mock_volume,
#         source=mock_source,
#         treble=mock_treble,
#         bass=mock_bass,
#         balance=mock_balance,
#     )
#
#     mock_socket_instance.recv.return_value = mock_response
#     zone_info = htd_instance.query_zone(mock_zone)
#
#     mock_create_connection.assert_called_once_with(
#         address=(MOCK_IP_ADDRESS, MOCK_PORT),
#         timeout=MOCK_SOCKET_TIMEOUT / 1_000,
#     )
#
#     assert zone_info.power == mock_power
#     assert zone_info.mode == mock_mode
#     assert zone_info.mute == mock_mute
#     assert zone_info.party == mock_party_mode
#
#     assert zone_info.htd_volume == mock_volume
#     assert zone_info.source == mock_source
#     assert zone_info.treble == mock_treble
#     assert zone_info.bass == mock_bass
#     assert zone_info.balance == mock_balance
