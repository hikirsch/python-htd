from typing import TypedDict
from unittest.mock import Mock, patch

import pytest

from htd_client import HtdConstants, ZoneDetail


class StateTogglesDict(TypedDict):
    power: bool
    mute: bool
    mode: bool
    party_mode: bool


def mock_convert_volume(volume: int):
    if volume == HtdConstants.MAX_HTD_VOLUME:
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

    zone_data[HtdConstants.HEADER_BYTE_ZONE_DATA_INDEX] = HtdConstants.HEADER_BYTE
    zone_data[HtdConstants.RESERVED_BYTE_ZONE_DATA_INDEX] = HtdConstants.RESERVED_BYTE
    zone_data[HtdConstants.ZONE_NUMBER_ZONE_DATA_INDEX] = zone
    zone_data[HtdConstants.VERIFICATION_BYTE_ZONE_DATA_INDEX] = HtdConstants.VERIFICATION_BYTE

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
    command = HtdConstants.VOLUME_UP_COMMAND

    mock_calculate_checksum.return_value = mock_checksum

    from htd_client.utils import get_command
    instruction = get_command(zone_number, command, data_code)

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


def test_get_friendly_name():
    from htd_client.utils import get_friendly_name
    assert get_friendly_name(HtdConstants.MCA66_MODEL_NAME) == HtdConstants.MCA66_FRIENDLY_MODEL_NAME
    assert get_friendly_name("foo") == f"Unknown (foo)"


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
    from htd_client.utils import convert_volume

    raw = mock_convert_volume(expected_htd)
    (actual_percent, actual_htd) = convert_volume(raw)

    assert expected_percent == actual_percent
    assert expected_htd == actual_htd


@pytest.mark.parametrize(
    "number, binary",
    [
        (1, "0001"),
        (2, "0010"),
        (3, "0011"),
        (4, "0100"),
        (5, "0101"),
        (6, "0110"),
        (7, "0111"),
        (8, "1000"),
        (9, "1001"),
        (10, "1010"),
        (11, "1011"),
        (12, "1100"),
        (13, "1101"),
        (14, "1110"),
        (15, "1111"),
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


@pytest.mark.parametrize(
    "is_valid, number",
    [
        (True, 1),
        (True, 2),
        (True, 3),
        (True, 4),
        (True, 5),
        (True, 6),
        (False, 7),
        (False, 0),
        (False, 10),
    ]
)
def test_validate_zone_source(is_valid, number):
    from htd_client.utils import validate_source, validate_zone
    if is_valid:
        validate_source(number)
        validate_zone(number)

    else:
        with pytest.raises(Exception, match="source %s is invalid" % number):
            validate_source(number)

        with pytest.raises(Exception, match="zone %s is invalid" % number):
            validate_zone(number)


def custom_side_effect(x):
    result = ZoneDetail(x[0])
    return result


@patch('htd_client.utils.parse_zone', side_effect=custom_side_effect)
def test_parse_all_zones(mock_parse_zone):
    from htd_client.utils import parse_all_zones

    full_message = []
    chunks = []

    for zone in range(0, 6):
        message = [zone + 1]

        for _ in range(1, HtdConstants.MESSAGE_CHUNK_SIZE):
            message.append(0)

        full_message += message
        chunks.append(bytearray(message))

    # add an invalid zone to the response to make sure it gets dropped
    full_message += [7, 0, 0, 0, 0]

    response = parse_all_zones(bytearray(full_message))

    for index in range(0, 6):
        assert mock_parse_zone.call_args_list[index].args[0] == chunks[index]

    assert 6 == len(response.keys())

@patch('htd_client.utils.parse_all_zones')
def test_parse_single_zone(mock_parse_all_zones):
    fake_data = bytearray([0, 1, 2, 3, 4, 5])
    fake_value = {"some": "fake"}
    fake_dict = {
        64: fake_value
    }
    mock_parse_all_zones.return_value = fake_dict
    from htd_client.utils import parse_single_zone
    response = parse_single_zone(fake_data, 64)

    mock_parse_all_zones.assert_called_with(fake_data)
    assert response == fake_value

    response = parse_single_zone(fake_data, 1)

    assert response is None



def test_test_parse_zone():
    from htd_client.utils import parse_zone, convert_volume

    mock_zone = 1
    mock_power = True
    mock_mode = False
    mock_mute = True
    mock_party_mode = False
    mock_htd_volume = 30
    mock_source = 3
    mock_treble = 25
    mock_bass = 15
    mock_balance = 18

    mock_response = create_mock_response(
        zone=mock_zone,
        state_toggles={
            "power": True,
            "mode": False,
            "mute": True,
            "party_mode": False,
        },
        volume=mock_htd_volume,
        source=mock_source,
        treble=mock_treble,
        bass=mock_bass,
        balance=mock_balance,
    )

    (mock_percent_volume, _) = convert_volume(mock_convert_volume(mock_htd_volume))

    zone_info = parse_zone(mock_response)

    assert zone_info.number == mock_zone
    assert zone_info.power == mock_power
    assert zone_info.mute == mock_mute
    assert zone_info.mode == mock_mode
    assert zone_info.party == mock_party_mode

    assert zone_info.source == mock_source
    assert zone_info.volume == mock_percent_volume
    assert zone_info.htd_volume == mock_htd_volume
    assert zone_info.treble == mock_treble
    assert zone_info.bass == mock_bass
    assert zone_info.balance == mock_balance

@pytest.mark.parametrize(
    "zone_data",
    [
        [HtdConstants.HEADER_BYTE, HtdConstants.RESERVED_BYTE, 0, 0],
        [0, HtdConstants.RESERVED_BYTE],
        [HtdConstants.HEADER_BYTE, 1],
    ]
)
def test_invalid_parse_zone(zone_data):
    from htd_client.utils import parse_zone
    result = parse_zone(bytearray(zone_data))

    assert result is None