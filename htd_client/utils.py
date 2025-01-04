import socket
from encodings import utf_8

from .constants import HtdConstants, HtdMcaConstants, HtdDeviceKind, MAX_BYTES_TO_RECEIVE, HtdLyncConstants
from .models import ZoneDetail

import logging

_LOGGER = logging.getLogger(__name__)

def build_command(zone: int, command: int, data_code: int, extra_data: bytes = None) -> bytearray:
    """
    The command sequence we use to send to the device, the header and reserved bytes are always first, the zone is third, followed by the command and code.

    Args:
        zone (int): the zone this command is for
        command (int): the command itself
        data_code (int): a value associated to the command, can be a source value, or an action to perform for set.
        extra_data (int, optional): additional data to send with the command, if any. Defaults to None.

    Returns:
        bytes: a bytes sequence representing the instruction for the action requested
    """
    cmd = [
        HtdConstants.HEADER_BYTE,
        HtdConstants.RESERVED_BYTE,
        zone
    ]

    if isinstance(command, bytes):
        cmd += command
    else:
        cmd.append(command)

    if isinstance(data_code, bytes):
        cmd += data_code
    else:
        cmd.append(data_code)

    if extra_data is not None:
        cmd += extra_data

    checksum = calculate_checksum(cmd)
    cmd.append(checksum)

    return bytearray(cmd)

def stringify_bytes(data: bytes) -> str:
    position = 0
    chunk_num = 0
    ret_val = "\n"
    while position < len(data):
        # each chunk represents a different zone that should be 14 bytes long,
        chunk = data[position: position + HtdConstants.MESSAGE_CHUNK_SIZE]
        position += HtdConstants.MESSAGE_CHUNK_SIZE
        chunk_num += 1
        line = f'[{chunk_num:2}] ' + ' '.join(f'0x{byte:02x}' for byte in chunk) + '\n'
        line += f'[{chunk_num:2}] ' + ' '.join(f'{byte:4}' for byte in chunk) + '\n'
        ret_val += line

    return ret_val


def send_command(
    cmd: bytes,
    ip_address: str,
    port: int,
) -> bytes | None:
    connection = socket.create_connection(address=(ip_address, port))
    connection.send(cmd)
    data = connection.recv(MAX_BYTES_TO_RECEIVE)
    connection.close()
    return data


def convert_balance_value_mca(value: int):
    signed_val = (value - 0x100) if value > 0x7F else value
    return signed_val


def convert_volume(raw_volume: int) -> (int, int):
    """
    Convert the volume into a usable value. the device will transmit a number between 196 - 255. if it's at max volume, the raw volume will come as 0. this is probably because the gateway only transmits 8 bits per byte. 255 is 0b11111111. since there's no volume = 0 (use mute I guess), if the volume hits 0, it's because it's at max volume, so we make it 256. credit for this goes to lounsbrough

    Args:
        raw_volume (int): the raw volume amount, a number usually ranges from 196 to 255

    Returns:
        (int, int): A tuple where the first number is a percentage, and the second is the raw volume from 0 to 60
    """
    if raw_volume == 0:
        return 100, HtdConstants.MAX_VOLUME

    htd_volume = raw_volume - HtdConstants.VOLUME_OFFSET
    percent_volume = round(htd_volume / HtdConstants.MAX_VOLUME * 100)
    fixed = max(0, min(100, percent_volume))
    return fixed, htd_volume


def convert_htd_volume_to_raw(volume: int) -> int:
    if volume == 0:
        return 0

    return HtdConstants.MAX_RAW_VOLUME - (HtdConstants.MAX_VOLUME - volume)


def calculate_checksum(message: [int]) -> int:
    """
    A helper method to calculate the checksum bit, it is the last digit on the entire command. The value is the sum of all the bytes in the message.

    Args:
        message (int): an array of ints, to calculate a checksum for

    Returns:
        int: the sum of the message ints
    """
    cs = 0
    for b in message:
        cs += b
    cs &= 0xff
    return cs


def is_bit_on(toggles: str, index: int) -> bool:
    """
    A helper method to check the state toggle index is on.

    Args:
        toggles (str): the binary string to check if enabled
        index (index): the position to check if on

    Returns:
        bool: if the bit is on
    """
    return toggles[index] == "1"


def validate_source(source: int):
    """
    A helper method to validate the source is not outside the range. If it's invalid, an Exception is raised, otherwise nothing will happen.

    Args:
        source (int): the source number to validate

    Raises:
        Exception: source X is invalid
    """
    # if source not in range(1, HtdConstants.MAX_HTD_SOURCES + 1):
    #     raise Exception("source %s is invalid" % source)
    pass


def validate_zone(zone: int):
    """
    A helper method to validate the zone is not outside the range. If it's invalid, an Exception is raised, otherwise nothing will happen.

    Args:
        zone (int): the zone to validate

    Raises:
        Exception - zone X is invalid
    """
    # if zone not in range(1, HtdConstants.MAX_HTD_ZONES + 1):
    #     raise Exception("zone %s is invalid" % zone)
    pass


def validate_zone_response(zone_data: bytes) -> bool:
    return (
        zone_data[HtdConstants.HEADER_BYTE_RESPONSE_INDEX] == HtdConstants.HEADER_BYTE and
        zone_data[HtdConstants.RESERVED_BYTE_RESPONSE_INDEX] == HtdConstants.RESERVED_BYTE
        # and zone_data[HtdConstants.COMMAND_RESPONSE_BYTE_RESPONSE_INDEX] == command
    )

def validate_zone_response_2(zone_data: bytes) -> bool:
    return (
        zone_data[HtdConstants.HEADER_BYTE_RESPONSE_INDEX] == HtdConstants.HEADER_BYTE or zone_data[HtdConstants.HEADER_BYTE_RESPONSE_INDEX] == 20 and
        zone_data[HtdConstants.RESERVED_BYTE_RESPONSE_INDEX] == HtdConstants.RESERVED_BYTE
    )


# credit for this new parser goes to lounsbrough
def parse_zone_mca(zone_data: bytes) -> ZoneDetail | None:
    """
    This will take a single message chunk of 14 bytes and parse this into a usable `ZoneDetail` model to read the state.

    Parameters:
        zone_data (bytes): an array of bytes representing a zone

    Returns:
        ZoneDetail - a parsed instance of zone_data normalized or None if invalid
    """
    zone_number = zone_data[HtdConstants.ZONE_NUMBER_ZONE_DATA_INDEX]

    if zone_number == 0:
        return None

    # the 4th position represent the toggles for power, mute, mode and party,
    state_toggles = to_binary_string(
        zone_data[HtdConstants.STATE_TOGGLES_ZONE_DATA_INDEX]
    )

    volume, htd_volume = convert_volume(
        zone_data[HtdMcaConstants.VOLUME_ZONE_DATA_INDEX]
    )

    zone = ZoneDetail(zone_number)

    zone.number = zone_number
    zone.power = is_bit_on(
        state_toggles,
        HtdMcaConstants.POWER_STATE_TOGGLE_INDEX
    )
    zone.mute = is_bit_on(state_toggles, HtdMcaConstants.MUTE_STATE_TOGGLE_INDEX)
    zone.mode = is_bit_on(state_toggles, HtdMcaConstants.MODE_STATE_TOGGLE_INDEX)

    zone.source = zone_data[HtdMcaConstants.SOURCE_ZONE_DATA_INDEX] + HtdConstants.SOURCE_QUERY_OFFSET
    zone.volume = volume
    zone.htd_volume = htd_volume
    zone.treble = convert_balance_value_mca(zone_data[HtdMcaConstants.TREBLE_ZONE_DATA_INDEX])
    zone.bass = convert_balance_value_mca(zone_data[HtdMcaConstants.BASS_ZONE_DATA_INDEX])
    zone.balance = convert_balance_value_mca(zone_data[HtdMcaConstants.BALANCE_ZONE_DATA_INDEX])

    return zone


def parse_zone_lync(zone_number: int, zone_data: bytes) -> ZoneDetail | None:
    """
    This will take a single message chunk of 14 bytes and parse this into a usable `ZoneDetail` model to read the state.

    Parameters:
        zone_data (bytes): an array of bytes representing a zone

    Returns:
        ZoneDetail - a parsed instance of zone_data normalized or None if invalid
    """

    # zone_number = zone_data[HtdConstants.ZONE_NUMBER_ZONE_DATA_INDEX]
    #
    # if zone_number == 0:
    #     return None

    # the 4th position represent the toggles for power, mute, mode and party,
    state_toggles = to_binary_string(
        zone_data[HtdConstants.STATE_TOGGLES_ZONE_DATA_INDEX]
    )

    # for lync, the toggles are read backwards
    state_toggles = state_toggles[::-1]

    volume, htd_volume = convert_volume(
        zone_data[HtdLyncConstants.VOLUME_ZONE_DATA_INDEX]
    )

    zone = ZoneDetail(zone_number)

    zone.power = is_bit_on(
        state_toggles,
        HtdMcaConstants.POWER_STATE_TOGGLE_INDEX
    )
    zone.mute = is_bit_on(state_toggles, HtdLyncConstants.MUTE_STATE_TOGGLE_INDEX)
    zone.mode = is_bit_on(state_toggles, HtdLyncConstants.MODE_STATE_TOGGLE_INDEX)

    zone.source = zone_data[HtdLyncConstants.SOURCE_ZONE_DATA_INDEX] + HtdConstants.SOURCE_QUERY_OFFSET
    zone.volume = volume
    zone.htd_volume = htd_volume
    zone.treble = zone_data[HtdLyncConstants.TREBLE_ZONE_DATA_INDEX]
    zone.bass = zone_data[HtdLyncConstants.BASS_ZONE_DATA_INDEX]
    zone.balance = zone_data[HtdLyncConstants.BALANCE_ZONE_DATA_INDEX]

    return zone


def parse_all_zones(data: bytes, kind: HtdDeviceKind) -> dict[int, ZoneDetail]:
    """
    The handler method to take the entire response from the controller and parses each zone.

    Args:
        data (bytes): the full response from the device, represents all the zones to be parsed
        kind (HtdDeviceKind): which htd device is the message from, so we know how to parse it.

    Returns:
        dict[int, ZoneDetail]: a dict where the key represents the zone number, and the value are the details of the zone
    """
    position = 0
    zones = {}

    while position < len(data):
        # each chunk represents a different zone that should be 14 bytes long,
        zone_data = data[position: position + HtdConstants.MESSAGE_CHUNK_SIZE]
        position += HtdConstants.MESSAGE_CHUNK_SIZE

        # if the zone data we got is less than the exp
        if len(zone_data) < HtdConstants.MESSAGE_CHUNK_SIZE:
            break

        parse_zone = parse_zone_lync if kind == HtdDeviceKind.lync else parse_zone_mca

        zone_info = parse_zone(zone_data)

        # if a valid zone was found, we're done
        if zone_info is not None:
            zones[zone_info.number] = zone_info

    return zones


def to_binary_string(raw_value: int) -> str:
    """
    A helper method to convert the integer number for the state values into a binary string, so we can check the state of each individual toggle.

    Parameters:
        raw_value (int): a number to convert to a binary string

    Returns:
        str: a binary string of the int
    """

    # the state toggles value needs to be interpreted in binary,
    # each bit represents a new flag.
    state_toggles = bin(raw_value)

    # when converting to binary, python will prepend '0b',
    # so substring starting at 2
    state_toggles = state_toggles[2:]

    # each of the 8 bits as 1 represent that the toggle is set to on,
    # if it's less than 8 digits, we fill with zeros
    state_toggles = state_toggles.zfill(8)

    return state_toggles


def parse_zone_name(data: bytes):
    start = HtdConstants.NAME_START_INDEX
    end = start + HtdConstants.ZONE_NAME_MAX_LENGTH
    zone_name = data[start:end]
    stripped = zone_name.strip(b"\x00")
    decoded = decode_response(stripped)
    return decoded


def decode_response(response: bytes):
    return response.decode(utf_8.getregentry().name, errors="replace")


def int_to_bytes(number: int) -> bytearray:
    # return number.to_bytes(1, byteorder="little")
    return bytearray([number])

def str_to_bytes(string: str) -> bytes:
    return string.encode()
