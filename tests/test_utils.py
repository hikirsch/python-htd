from typing import TypedDict
from unittest.mock import Mock, patch

import pytest

from htd_client.constants import HtdConstants
from htd_client.models import ZoneDetail


class StateTogglesDict(TypedDict):
    power: bool
    mute: bool
    mode: bool
    party_mode: bool


def mock_convert_volume(volume: int):
    if volume == HtdConstants.MAX_VOLUME:
        return 0

    return volume + HtdConstants.VOLUME_OFFSET


def create_mock_response(
    zone: int,
    state_toggles: StateTogglesDict = None,
    volume: int = 0,
    source: int = 1,
    treble: int = 0,
    bass: int = 0,
    balance: int = 0,
):
    zone_data = [0] * HtdConstants.MESSAGE_CHUNK_SIZE

    zone_data[HtdConstants.HEADER_BYTE_RESPONSE_INDEX] = HtdConstants.HEADER_BYTE
    zone_data[HtdConstants.RESERVED_BYTE_RESPONSE_INDEX] = HtdConstants.RESERVED_BYTE
    zone_data[HtdConstants.ZONE_NUMBER_ZONE_DATA_INDEX] = zone
    zone_data[HtdConstants.COMMAND_RESPONSE_BYTE_RESPONSE_INDEX] = HtdConstants.QUERY_COMMAND_CODE

    zone_data[HtdConstants.STATE_TOGGLES_ZONE_DATA_INDEX] = create_mock_state_toggles(state_toggles)
    zone_data[HtdConstants.SOURCE_ZONE_DATA_INDEX] = source - HtdConstants.SOURCE_QUERY_OFFSET
    zone_data[HtdConstants.VOLUME_ZONE_DATA_INDEX] = mock_convert_volume(volume)
    zone_data[HtdConstants.TREBLE_ZONE_DATA_INDEX] = treble
    zone_data[HtdConstants.BASS_ZONE_DATA_INDEX] = bass
    zone_data[HtdConstants.BALANCE_ZONE_DATA_INDEX] = balance

    return bytearray(zone_data)


def create_mock_state_toggles(state_toggles: StateTogglesDict):
    mock_state = ''

    toggles = StateTogglesDict.__annotations__.keys()
    for toggle in toggles:
        mock_state += '1' if state_toggles.get(toggle) else '0'

    return int(mock_state, 2)


@patch('htd_client.utils.calculate_checksum')
def test_get_command(mock_calculate_checksum: Mock):
    mock_checksum = 100
    zone_number = 5
    data_code = 10
    from htd_client.constants import HtdMcaCommands
    command = HtdMcaCommands.VOLUME_UP_COMMAND

    mock_calculate_checksum.return_value = mock_checksum

    from htd_client.utils import build_command
    instruction = build_command(zone_number, command, data_code)

    assert instruction[0] == HtdConstants.HEADER_BYTE
    assert instruction[1] == HtdConstants.RESERVED_BYTE
    assert instruction[2] == zone_number
    assert instruction[3] == command
    assert instruction[4] == data_code
    assert instruction[5] == mock_checksum


def test_calculate_checksum():
    from htd_client.utils import calculate_checksum
    assert 10 == calculate_checksum([1, 2, 3, 4])
    assert 0 == calculate_checksum([1, 2, 3, 4, -10])





@pytest.mark.parametrize(
    "expected_htd, expected_percent",
    [
        (0, 0),
        (15, 25),
        (30, 50),
        (45, 75),
        (60, 100),
    ]
)
def test_convert_volume(expected_htd, expected_percent):
    from htd_client.constants import HtdDeviceKind
    from htd_client.utils import convert_volume

    raw = mock_convert_volume(expected_htd)
    actual_volume = convert_volume(HtdDeviceKind.mca, raw)
    
    # convert_volume returns the HTD volume (0-60)
    assert expected_htd == actual_volume
    # assert expected_htd == actual_htd


@pytest.mark.parametrize(
    "number, binary",
    [
        (1, "00000001"),
        (2, "00000010"),
        (3, "00000011"),
        (4, "00000100"),
        (5, "00000101"),
        (6, "00000110"),
        (7, "00000111"),
        (8, "00001000"),
        (9, "00001001"),
        (10, "00001010"),
        (11, "00001011"),
        (12, "00001100"),
        (13, "00001101"),
        (14, "00001110"),
        (15, "00001111"),
    ]
)
def test_to_binary_string(number, binary):
    from htd_client.utils import to_binary_string
    actual = to_binary_string(number)

    assert actual == binary


@pytest.mark.parametrize(
    "actual, string, index",
    [
        (True, "abc1adf", 3),
        (False, "abc0adf", 3),
        (True, "10", 0),
        (False, "10", 1),
    ]
)
def test_is_bit_on(actual, string, index):
    from htd_client.utils import is_bit_on
    assert actual == is_bit_on(string, index)

