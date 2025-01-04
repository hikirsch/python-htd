from enum import Enum
from typing import TypedDict, Dict

MAX_BYTES_TO_RECEIVE = 2 ** 10  # receive 1024 bytes
ONE_SECOND = 1_000


class HtdDeviceKind(Enum):
    mca = "mca"
    lync = "lync"


class HtdModelInfo(TypedDict):
    zones: int
    sources: int
    friendly_name: str
    name: str
    kind: HtdDeviceKind


class HtdConstants:
    """
    A constants class representing values used.
    """
    # MCA66_MODEL_NAME =
    # LYNC6_MODEL_NAME =
    # LYNC12_MODEL_NAME = 'Lync12'

    SUPPORTED_MODELS: Dict[str, HtdModelInfo] = {
        b'Wangine_MCA66': {
            'zones': 6,
            'sources': 6,
            'friendly_name': 'MCA66',
            'name': 'MCA66',
            'kind': HtdDeviceKind.mca,
        },
        b'Lync 6': {
            'zones': 6,
            'sources': 6,
            'friendly_name': 'Lync 6',
            'name': 'Lync 6',
            'kind': HtdDeviceKind.lync,
        },
        b'Lync12': {
            'zones': 12,
            'sources': 18,
            'friendly_name': 'Lync 12',
            'name': 'Lync12',
            'kind': HtdDeviceKind.lync,
        }
    }

    HEADER_BYTE = 0x02

    RESERVED_BYTE = 0x00

    VERIFICATION_BYTE = 0x05

    # in order to not flood the device with commands, we have a delay
    # inbetween commands, in milliseconds
    DEFAULT_COMMAND_DELAY = 100

    # the device is flakey, let's retry a bunch of times
    DEFAULT_RETRY_ATTEMPTS = 5

    # the port of the device, default is 10006
    DEFAULT_PORT = 10006

    # the number of seconds before we give up trying to read from the device
    DEFAULT_SOCKET_TIMEOUT = 1000 * 60

    # 255 is the max value you can have with 1 byte. the volume max is 60.
    # so, we use 256 to represent a real 100% when computing the volume
    MAX_RAW_VOLUME = 256
    MAX_VOLUME = 60

    VOLUME_OFFSET = MAX_RAW_VOLUME - MAX_VOLUME

    # each message we get is chunked at 14 bytes
    MESSAGE_CHUNK_SIZE = 14

    NAME_START_INDEX = 4
    ZONE_NAME_MAX_LENGTH = 10
    SOURCE_NAME_MAX_LENGTH = 10

    # the byte index for where to locate the corresponding setting
    HEADER_BYTE_RESPONSE_INDEX = 0
    RESERVED_BYTE_RESPONSE_INDEX = 1
    ZONE_NUMBER_ZONE_DATA_INDEX = 2
    COMMAND_RESPONSE_BYTE_RESPONSE_INDEX = 3
    STATE_TOGGLES_ZONE_DATA_INDEX = 4 - 4

    # when reading the source, we add this, so if unit says 0x04 it's Source 5 since + 1
    SOURCE_QUERY_OFFSET = 1


# command codes instruct the device what mode to do,
# it's followed with a command as well listed below

class HtdCommonCommands:
    MODEL_QUERY_COMMAND_CODE = 0x08


class HtdLyncCommands:
    COMMON_COMMAND_CODE = 0x04
    QUERY_COMMAND_CODE = 0x05
    SAVE_FILE_COMMAND_CODE = 0x0b
    QUERY_ALL_ZONE_STATUS_COMMAND_CODE = 0x0c
    QUERY_ZONE_NAME_COMMAND_CODE = 0x0d
    QUERY_SOURCE_NAME_COMMAND_CODE = 0x0e
    MP3_COMMAND_CODE = 0x01
    FIRMWARE_VERSION_COMMAND_CODE = 0x0f
    VOLUME_SETTING_CONTROL_COMMAND_CODE = 0x15
    BALANCE_SETTING_CONTROL_COMMAND_CODE = 0x16
    TREBLE_SETTING_CONTROL_COMMAND_CODE = 0x17
    BASS_SETTING_CONTROL_COMMAND_CODE = 0x18
    SET_AUDIO_TO_DEFAULT_COMMAND_CODE = 0x1c
    SET_NAME_TO_DEFAULT_COMMAND_CODE = 0x1e

    MP3_FAST_FORWARD_COMMAND_CODE = 0x0a
    MP3_PLAY_PAUSE_COMMAND_CODE = 0x0b
    MP3_FAST_BACKWARDS_COMMAND_CODE = 0x0c
    MP3_STOP_COMMAND_CODE = 0x0d

    POWER_ON_ALL_ZONES_COMMAND_CODE = 0x55
    POWER_OFF_ALL_ZONES_COMMAND_CODE = 0x56

    POWER_ON_ZONE_COMMAND_CODE = 0x57
    POWER_OFF_ZONE_COMMAND_CODE = 0x58

    MUTE_ON_COMMAND_CODE = 0x1e
    MUTE_OFF_COMMAND_CODE = 0x1f

    DND_ON_COMMAND_CODE = 0x59
    DND_OFF_COMMAND_CODE = 0x5a

    MP3_REPEAT_OFF = 0x00
    MP3_REPEAT_ON = 0xff

    SET_ZONE_NAME_COMMAND_CODE = 0x06
    SET_SOURCE_NAME_COMMAND_CODE = 0x07

    UNDEFINED_RECEIVE_COMMAND = 0x02
    ZONE_STATUS_RECEIVE_COMMAND = 0x05
    KEYPAD_EXISTS_RECEIVE_COMMAND = 0x06
    MP3_PLAY_END_RECEIVE_COMMAND = 0x09
    ZONE_SOURCE_NAME_RECEIVE_COMMAND = 0x0C
    ZONE_NAME_RECEIVE_COMMAND = 0x0D
    SOURCE_NAME_RECEIVE_COMMAND = 0x0E
    MP3_FILE_NAME_RECEIVE_COMMAND = 0x11
    MP3_ARTIST_NAME_RECEIVE_COMMAND = 0x12
    MP3_ON_RECEIVE_COMMAND = 0x13
    MP3_OFF_RECEIVE_COMMAND = 0x14
    ERROR_RECEIVE_COMMAND = 0x1b

class HtdLyncConstants:

    RECEIVE_COMMAND_EXPECTED_LENGTH_MAP = {
        HtdLyncCommands.UNDEFINED_RECEIVE_COMMAND: 1,
        HtdLyncCommands.ZONE_STATUS_RECEIVE_COMMAND: 9,
        HtdLyncCommands.KEYPAD_EXISTS_RECEIVE_COMMAND: 9,
        HtdLyncCommands.MP3_PLAY_END_RECEIVE_COMMAND: 1,
        HtdLyncCommands.ZONE_SOURCE_NAME_RECEIVE_COMMAND: 12,
        HtdLyncCommands.ZONE_NAME_RECEIVE_COMMAND: 13, # should be 11
        HtdLyncCommands.SOURCE_NAME_RECEIVE_COMMAND: 13, # should be 11
        HtdLyncCommands.MP3_FILE_NAME_RECEIVE_COMMAND: 64,
        HtdLyncCommands.MP3_ARTIST_NAME_RECEIVE_COMMAND: 64,
        HtdLyncCommands.MP3_ON_RECEIVE_COMMAND: 1,
        HtdLyncCommands.MP3_OFF_RECEIVE_COMMAND: 17,
        HtdLyncCommands.ERROR_RECEIVE_COMMAND: 9,
    }

    # state toggles represent on and off values only. they are all stored
    # within one byte. each binary digit is treated as a flag. these are
    # indexes of each state toggle

    POWER_STATE_TOGGLE_INDEX = 0
    MUTE_STATE_TOGGLE_INDEX = 1
    MODE_STATE_TOGGLE_INDEX = 2

    SOURCE_ZONE_DATA_INDEX = 4
    VOLUME_ZONE_DATA_INDEX = 9 - 4
    TREBLE_ZONE_DATA_INDEX = 10 - 4
    BASS_ZONE_DATA_INDEX = 11 - 4
    BALANCE_ZONE_DATA_INDEX = 12 - 4

    # when setting the source, you use the SET command and add this to the
    # source number desired, e.g Zone 3 + 15 = data value 18, or 0x12 for lync
    SOURCE_COMMAND_OFFSET = 0x10 - 1
    SOURCE_EXTRA_ZONE_COMMAND_OFFSET = 0x63 - 1
    PARTY_MODE_COMMAND_OFFSET = 0x36 - 1
    PARTY_MODE_EXTRA_ZONE_COMMAND_OFFSET = 0x69 - 1

    MIN_BASS = -10
    MAX_BASS = 10

    MIN_TREBLE = -10
    MAX_TREBLE = 10

    MIN_BALANCE = -18
    MAX_BALANCE = 18

    BASS_COMMAND_OFFSET = 0x80
    TREBLE_COMMAND_OFFSET = 0x80

class HtdMcaCommands:
    COMMON_COMMAND_CODE = 0x04
    QUERY_COMMAND_CODE = 0x06

    # commands to be used for SET_COMMAND_CODE
    POWER_OFF_ZONE_COMMAND_CODE = 0x21
    POWER_ON_ZONE_COMMAND_CODE = 0x20
    POWER_ON_ALL_ZONES_COMMAND_CODE = 0x38
    POWER_OFF_ALL_ZONES_COMMAND_CODE = 0x39
    TOGGLE_MUTE_COMMAND = 0x22
    VOLUME_UP_COMMAND = 0x09
    VOLUME_DOWN_COMMAND = 0x0A
    BASS_UP_COMMAND = 0x26
    BASS_DOWN_COMMAND = 0x27
    TREBLE_UP_COMMAND = 0x28
    TREBLE_DOWN_COMMAND = 0x29
    BALANCE_RIGHT_COMMAND = 0x2A
    BALANCE_LEFT_COMMAND = 0x2B

    QUERY_SOURCE_NAME_COMMAND_CODE = 0x1e
    SET_SOURCE_NAME_COMMAND_CODE = 0x07

class HtdMcaConstants:
    # the byte index for where to locate the corresponding setting
    SOURCE_ZONE_DATA_INDEX = 8
    VOLUME_ZONE_DATA_INDEX = 9
    TREBLE_ZONE_DATA_INDEX = 10
    BASS_ZONE_DATA_INDEX = 11
    BALANCE_ZONE_DATA_INDEX = 12

    # state toggles represent on and off values only. they are all stored
    # within one byte. each binary digit is treated as a flag. these are
    # indexes of each state toggle
    POWER_STATE_TOGGLE_INDEX = 0
    MUTE_STATE_TOGGLE_INDEX = 1
    MODE_STATE_TOGGLE_INDEX = 2

    # when setting the source, you use the SET command and add this to the
    # source number desired, e.g Zone 3 + 2 = data value 5, or 0x05 for mca
    SOURCE_COMMAND_OFFSET = 2

