from htd_client.constants import HtdConstants
from htd_client.models import ZoneDetail

def get_command(zone: int, command: bytes, data_code: int) -> bytes:
    """
    The command sequence we use to send to the device, the header and reserved bytes are always first, the zone is third, followed by the command and code.

    Args:
        zone (int): the zone this command is for
        command (bytes): the command itself
        data_code (int): a value associated to the command, can be a source value, or an action to perform for set.

    Returns:
        bytes: a bytes sequence representing the instruction for the action requested
    """
    cmd = [
        HtdConstants.HEADER_BYTE,
        HtdConstants.RESERVED_BYTE,
        zone,
        command,
        data_code,
    ]
    checksum = calculate_checksum(cmd)
    cmd.append(checksum)

    return bytes(cmd)


def convert_volume(raw_volume: int) -> (int, int):
    """
    Convert the volume into a usable value. the device will transmit a number between 196 - 255. if it's at max volume, the raw volume will come as 0. this is probably because the gateway only transmits 8 bits per byte. 255 is 0b11111111. since there's no volume = 0 (use mute I guess), if the volume hits 0, it's because it's at max volume, so we make it 256. credit for this goes to lounsbrough

    Args:
        raw_volume (int): the raw volume amount, a number usually ranges from 196 to 255

    Returns:
        (int, int): A tuple where the first number is a percentage, and the second is the raw volume from 0 to 60
    """
    if raw_volume == 0:
        return 100, HtdConstants.MAX_HTD_VOLUME

    htd_volume = raw_volume - HtdConstants.VOLUME_OFFSET
    percent_volume = round(htd_volume / HtdConstants.MAX_HTD_VOLUME * 100)
    fixed = max(0, min(100, percent_volume))
    return fixed, htd_volume


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
    if source not in range(1, HtdConstants.MAX_HTD_SOURCES + 1):
        raise Exception("source %s is invalid" % source)


def validate_zone(zone: int):
    """
    A helper method to validate the zone is not outside the range. If it's invalid, an Exception is raised, otherwise nothing will happen.

    Args:
        zone (int): the zone to validate

    Raises:
        Exception - zone X is invalid
    """
    if zone not in range(1, HtdConstants.MAX_HTD_ZONES + 1):
        raise Exception("zone %s is invalid" % zone)


# credit for this new parser goes to lounsbrough
def parse_zone(zone_data: bytes) -> ZoneDetail | None:
    """
    This will take a single message chunk of 14 bytes and parse this into a usable `ZoneDetail` model to read the state.

    Parameters:
        zone_data (bytes): an array of bytes representing a zone

    Returns:
        ZoneDetail - a parsed instance of zone_data normalized or None if invalid
    """
    if (
        zone_data[HtdConstants.HEADER_BYTE_ZONE_DATA_INDEX] != HtdConstants.HEADER_BYTE or
        zone_data[HtdConstants.RESERVED_BYTE_ZONE_DATA_INDEX] != HtdConstants.RESERVED_BYTE
    ):
        return None

    # I think this is some kind of verification, it has been right so far.
    if zone_data[HtdConstants.VERIFICATION_BYTE_ZONE_DATA_INDEX] != HtdConstants.VERIFICATION_BYTE:
        return None

    # the 4th position represent the toggles for power, mute, mode and party,
    state_toggles = to_binary_string(
        zone_data[HtdConstants.STATE_TOGGLES_ZONE_DATA_INDEX]
    )

    volume, htd_volume = convert_volume(
        zone_data[HtdConstants.VOLUME_ZONE_DATA_INDEX]
    )

    zone_number = zone_data[HtdConstants.ZONE_NUMBER_ZONE_DATA_INDEX]

    zone = ZoneDetail(zone_number)

    zone.number = zone_number
    zone.power = is_bit_on(
        state_toggles,
        HtdConstants.POWER_STATE_TOGGLE_INDEX
    )
    zone.mute = is_bit_on(state_toggles, HtdConstants.MUTE_STATE_TOGGLE_INDEX)
    zone.mode = is_bit_on(state_toggles, HtdConstants.MODE_STATE_TOGGLE_INDEX)
    zone.party = is_bit_on(
        state_toggles,
        HtdConstants.PARTY_MODE_STATE_TOGGLE_INDEX
    )

    zone.source = zone_data[HtdConstants.SOURCE_ZONE_DATA_INDEX] + HtdConstants.SOURCE_QUERY_OFFSET
    zone.volume = volume
    zone.htd_volume = htd_volume
    zone.treble = zone_data[HtdConstants.TREBLE_ZONE_DATA_INDEX]
    zone.bass = zone_data[HtdConstants.BASS_ZONE_DATA_INDEX]
    zone.balance = zone_data[HtdConstants.BALANCE_ZONE_DATA_INDEX]

    return zone


def parse_all_zones(data: bytes) -> dict[int, ZoneDetail]:
    """
    The handler method to take the entire response from the controller and parses each zone.

    Args:
        data (bytes): the full response from the device, represents all the zones to be parsed

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

    # each of the 4 bits as 1 represent that the toggle is set to on,
    # if it's less than 4 digits, we fill with zeros
    state_toggles = state_toggles.zfill(4)

    return state_toggles

def get_friendly_name(model: str):
    """
    This will return a friendlier name for the model gateway based on the name from the device.

    Args:
        model (str):

    Returns:
        str: a friendlier name of the model
    """
    match model:
        case HtdConstants.MCA66_MODEL_NAME:
            return HtdConstants.MCA66_FRIENDLY_MODEL_NAME
        case _:
            return f"Unknown ({model})"
