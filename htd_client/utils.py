import logging
import socket
from typing import Literal

from .constants import HtdConstants, MAX_BYTES_TO_RECEIVE

_LOGGER = logging.getLogger(__name__)


def build_command(zone: int, command: int, data_code: int, extra_data: bytearray = None) -> bytearray:
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
        zone,
        command,
        data_code
    ]

    if extra_data is not None:
        cmd += extra_data

    checksum = calculate_checksum(cmd)
    cmd.append(checksum)

    return bytearray(cmd)


def stringify_bytes_raw(data: bytes, fmt: Literal["hex", "dec"] = "hex") -> str:
    if fmt == "hex":
        prefix = "0x"
        f = "02x"

    elif fmt == "dec":
        prefix = ""
        f = "4d"

    else:
        raise ValueError("format must be 'hex' or 'dec'")

    return " ".join(f"{prefix}{byte:{f}}" for byte in data)


def stringify_bytes(data: bytes) -> str:
    position = 0
    chunk_num = 0
    ret_val = "\n"

    while position < len(data):
        # each chunk represents a different zone that should be 14 bytes long,
        chunk = data[position: position + HtdConstants.MESSAGE_CHUNK_SIZE]
        position += HtdConstants.MESSAGE_CHUNK_SIZE
        chunk_num += 1
        line = f'[{chunk_num:2}] ' + stringify_bytes_raw(chunk) + '\n'
        line += f'[{chunk_num:2}] ' + stringify_bytes_raw(chunk, "dec") + '\n'
        # line += f'[{chunk_num:2}] ' + decode_response(chunk) + '\n'
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


def convert_value(value: int):
    return value - 0x100 if value > 0x7F else value


def convert_volume(raw_volume: int) -> (int, int):
    """
    Convert the volume into a usable value. the device will transmit a number between 196 - 255. if it's at max volume, the raw volume will come as 0. this is probably because the gateway only transmits 8 bits per byte. 255 is 0b11111111. since there's no volume = 0 (use mute I guess), if the volume hits 0, it's because it's at max volume, so we make it 256. credit for this goes to lounsbrough

    Args:
        raw_volume (int): the raw volume amount, a number usually ranges from 196 to 255

    Returns:
        (int, int): A tuple where the first number is a percentage, and the second is the raw volume from 0 to 60
    """
    if raw_volume == 0:
        return HtdConstants.MAX_VOLUME

    htd_volume = raw_volume - HtdConstants.VOLUME_OFFSET

    return htd_volume


def convert_volume_to_raw(volume: int) -> int:
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
    return sum(message) & 0xff


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
    return response.decode(errors="replace")
