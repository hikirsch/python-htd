"""
.. code-block:: python

    # import the client
    from htd_client import HtdClient

    # Call its only function
    client = HtdClient("192.168.1.2")

    model_info = client.get_model_info()
    zone_info = client.query_zone(1)
    updated_zone_info = client.volume_up(1)
"""
import asyncio
import logging
import socket
import threading
import time
from abc import abstractmethod
from typing import Dict, Tuple

import serial
from serial.serialutil import SerialException

import htd_client
from .constants import HtdConstants, HtdDeviceKind, ONE_SECOND, MAX_BYTES_TO_RECEIVE, HtdModelInfo, HtdCommonCommands
from .models import ZoneDetail

_LOGGER = logging.getLogger(__name__)


class BaseClient:
    _network_address: Tuple[str, int] = None
    _serial_address: str = None
    _command_retry_timeout: int = None
    _retry_attempts: int = None
    _socket_timeout_sec: float = None
    _zone_data: Dict[int, ZoneDetail] = None
    _model_info: HtdModelInfo = None
    _connection: serial = None
    _socket_thread: threading.Thread = None
    _socket_lock: threading.Lock = None

    _zones_loaded: int = 0
    _connected: bool = False
    _ready: bool = False

    _subscribers: set = None
    _loop: asyncio.AbstractEventLoop = None

    def __init__(
        self,
        model_info: HtdModelInfo,
        serial_address: str = None,
        network_address: Tuple[str, int] = None,
        command_retry_timeout: int = HtdConstants.DEFAULT_COMMAND_RETRY_TIMEOUT,
        retry_attempts: int = HtdConstants.DEFAULT_RETRY_ATTEMPTS,
        socket_timeout: int = HtdConstants.DEFAULT_SOCKET_TIMEOUT
    ):

        self._network_address = network_address
        self._command_retry_timeout = command_retry_timeout
        self._retry_attempts = retry_attempts
        self._socket_timeout_sec = socket_timeout / ONE_SECOND
        self._model_info = model_info
        self._zone_data = {}
        self._subscribers = set()
        self._socket_lock = threading.Lock()
        self._callback_lock = threading.Lock()
        self._loop = asyncio.get_event_loop()
        self._serial_address = serial_address
        self._connected = False
        self._should_disconnect = False

        self.connect()

    @property
    def connected(self):
        return self._connected

    @property
    def ready(self):
        return self._ready

    def connect(self):
        if self._serial_address is not None:
            self._connection = serial.Serial(
                port=self._serial_address,
                baudrate=38400,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=self._socket_timeout_sec
            )

        elif self._network_address is not None:
            ip_address, port = self._network_address

            self._connection = serial.serial_for_url(
                f"socket://{ip_address}:{port}",
                timeout=self._socket_timeout_sec,
                baudrate=38400
            )

        self._connected = True
        self._should_disconnect = False

        self.refresh()

        _LOGGER.debug("connected")

        self._socket_thread = threading.Thread(target=self._connection_thread)
        self._socket_thread.daemon = True
        self._socket_thread.start()

    def wait_until_ready(self):
        start_time = time.time()
        current_time = time.time()
        refresh_count = 0

        while not self._ready and current_time - start_time < self._socket_timeout_sec:
            current_time = time.time()

            if refresh_count * self._command_retry_timeout < int(current_time - start_time):
                refresh_count += 1
                self.refresh()

    def has_zone_data(self, zone: int):
        return zone in self._zone_data

    def disconnect(self):
        self._should_disconnect = True

    def _connection_thread(self):
        data = bytearray()

        while self.connected and not self._should_disconnect:
            try:
                new_data = self._connection.read_all()

                if len(new_data) == 0:
                    continue

                data += new_data

                _LOGGER.debug("Received new data %s" % htd_client.utils.stringify_bytes(data))

                with self._socket_lock:
                    while len(data) > 0:
                        (zone, chunk_length) = self._process_next_command(data)

                        if chunk_length == 0:
                            break

                        data = data[chunk_length:]

                        self._loop.run_in_executor(None, self._broadcast, zone)

            except SerialException:
                self._connected = False

            except Exception as e:
                _LOGGER.error(f"Error processing data!")
                _LOGGER.exception(e)

        # if we did not try to disconnect, reconnect
        if not self._should_disconnect:
            self.connect()


    def _process_next_command(self, data: bytes):
        """
        Process the next command in the buffer.
        Credit to https://github.com/dustinmcintire/htd-lync

        Args:
            data (bytes): the data to process
        """

        # start with search for command header and id the command
        # not enough data, 2 reserved header bits, zone + command + data + checksum = 4, is minimum length
        if len(data) < HtdConstants.MESSAGE_HEADER_LENGTH + 4:
            return None, 0

        start_message_index = data.find(HtdConstants.MESSAGE_HEADER)

        if start_message_index < 0:
            return None, len(data)

        if start_message_index != 0:
            _LOGGER.debug("Bad sync buffer! %s" % htd_client.utils.stringify_bytes(data))

        # offsets to packet data, zones, command, and then data
        zone_idx = start_message_index + HtdConstants.MESSAGE_HEADER_LENGTH
        cmd_idx = zone_idx + 1
        data_idx = cmd_idx + 1

        # not enough data, wait for more-
        if len(data) < data_idx:
            return None, 0

        zone = int(data[zone_idx])
        command = data[cmd_idx]

        # Skip over bad command
        # return the minimum packet size for resync
        if command not in HtdCommonCommands.EXPECTED_MESSAGE_LENGTH_MAP:
            _LOGGER.error(
                "Invalid command value: zone = %d, command = %s (%d).  data = %s" %
                (
                    zone,
                    htd_client.utils.stringify_bytes_raw(bytearray([command])),
                    command,
                    htd_client.utils.stringify_bytes(data),
                )
            )

            return None, start_message_index + HtdConstants.MESSAGE_HEADER_LENGTH

        expected_length = HtdCommonCommands.EXPECTED_MESSAGE_LENGTH_MAP[command]

        if command == HtdCommonCommands.UNDEFINED_RECEIVE_COMMAND:
            _LOGGER.info("Undefined response command: %02x", int(command))
            _LOGGER.debug("Packet buffer: %s", htd_client.utils.stringify_bytes(data[0:20]))
            return start_message_index + HtdConstants.MESSAGE_HEADER_LENGTH

        # not enough data, wait for more
        if len(data) <= data_idx + expected_length:
            return None, 0

        end_message_index = start_message_index + HtdConstants.MESSAGE_HEADER_LENGTH + 2 + expected_length
        chunk_length = end_message_index + 1

        # process the content to the current state
        frame = data[start_message_index:end_message_index]
        checksum = data[end_message_index]
        frame_sum_checksum = htd_client.utils.calculate_checksum(frame)

        # validate the checksum
        if frame_sum_checksum == checksum:
            # chunk = data[start_message_index:end_message_index]
            _LOGGER.debug("Processing chunk %s" % htd_client.utils.stringify_bytes(frame))

            frame = data[data_idx:data_idx + expected_length]
            self._parse_command(zone, command, frame)

            if not self._ready and command == HtdCommonCommands.ZONE_STATUS_RECEIVE_COMMAND:
                self._zones_loaded += 1
                if self._zones_loaded == self._model_info['zones']:
                    self._ready = True

        else:
            _LOGGER.info("Bad checksum %02x != %02x", frame_sum_checksum, checksum)

        return zone, chunk_length

    def _parse_command(self, zone, cmd, data):
        if cmd == HtdCommonCommands.KEYPAD_EXISTS_RECEIVE_COMMAND:
            # this is zone 0 with all zone data
            # second byte is zone 1 - 8
            for i in range(8):
                enabled = data[1] & (1 << i) > 0
                self._zone_data[i + 1] = ZoneDetail(i + 1, enabled)

            # fourth byte is zone 9 - 16
            for i in range(8):
                enabled = data[3] & (1 << i) > 0
                self._zone_data[i + 9] = ZoneDetail(i + 9, enabled)

            # third byte is keypad 1 - 8
            # for i in range(8):
            #     if data[2] & (1 << i):
            #         self.zone_info[i]['keypad'] = 'yes'
            #     else:
            #         self.zone_info[i]['keypad'] = 'no'

            # fifth byte is keypad 8-15
            # for i in range(8):
            #     if data[4] & (1 << i):
            #         self.zone_info[i + 8]['keypad'] = 'yes'
            #     else:
            #         self.zone_info[i + 8]['keypad'] = 'no'

        elif cmd == HtdCommonCommands.ZONE_STATUS_RECEIVE_COMMAND:
            zone_data = self._parse_zone(zone, data)
            zone_data.enabled = self._zone_data[zone].enabled
            self._zone_data[zone] = zone_data
            _LOGGER.debug("Got new state: %s", zone_data)

        elif cmd == HtdCommonCommands.ZONE_SOURCE_NAME_RECEIVE_COMMAND_MCA:
            zone_source_name = str(data[2:9].decode(errors="ignore").strip('\0')).lower()
            # print("ZONE SOURCE NAME NOT USED, zone %d, zone_source_name = %s" % (zone, zone_source_name))

        elif cmd == HtdCommonCommands.ZONE_SOURCE_NAME_RECEIVE_COMMAND_LYNC:
            zone_source_name = str(data[0:11].decode().rstrip('\0')).lower()
            # remove the extra null bytes
            # print("ZONE SOURCE NAME NOT USED, zone_source_name = %s" % zone_source_name)

        elif cmd == HtdCommonCommands.ZONE_NAME_RECEIVE_COMMAND:
            name = str(data[0:11].decode().rstrip('\0')).lower()
            self._zone_data[zone].name = name

        elif cmd == HtdCommonCommands.SOURCE_NAME_RECEIVE_COMMAND:
            source = data[11]
            name = str(data[0:10].decode().rstrip('\0')).lower()
            # print("GOT SOURCE NAME NOT USED, source = %s, name = %s" % (source, name))
            # self.zone_info[zone]['source_list'][source] = name
            # self.source_info[zone][name] = source
        #
        # elif cmd == HtdCommonCommands.MP3_ON_RECEIVE_COMMAND:
        #     self.mp3_status['state'] = 'on'
        #
        # elif cmd == HtdCommonCommands.MP3_OFF_RECEIVE_COMMAND:
        #     self.mp3_status['state'] = 'off'
        #
        # elif cmd == HtdCommonCommands.MP3_FILE_NAME_RECEIVE_COMMAND:
        #     self.mp3_status['file'] = data.decode().rstrip('\0')
        #
        # elif cmd == HtdCommonCommands.MP3_ARTIST_NAME_RECEIVE_COMMAND:
        #     self.mp3_status['artist'] = data.decode().rstrip('\0')

        elif cmd == HtdCommonCommands.ERROR_RECEIVE_COMMAND:
            _LOGGER.warning("HTD Error Response Code: %s", data[0])

        else:
            _LOGGER.info("Unknown command processed, ignoring: %s", cmd)

    def _parse_zone(self, zone_number: int, zone_data: bytearray) -> ZoneDetail | None:
        """
        This will take a single message chunk of 14 bytes and parse this into a usable `ZoneDetail` model to read the state.

        Parameters:
            zone_number (int): the zone number this data is for
            zone_data (bytes): an array of bytes representing a zone

        Returns:
            ZoneDetail - a parsed instance of zone_data normalized or None if invalid
        """

        # the 4th position represent the toggles for power, mute, mode and party,
        state_toggles = htd_client.utils.to_binary_string(
            zone_data[HtdConstants.STATE_TOGGLES_ZONE_DATA_INDEX]
        )

        volume = htd_client.utils.convert_volume(
            zone_data[HtdConstants.VOLUME_ZONE_DATA_INDEX]
        )

        zone = ZoneDetail(zone_number)

        if self._model_info["kind"] == HtdDeviceKind.lync:
            state_toggles = state_toggles[::-1]

        zone.power = htd_client.utils.is_bit_on(
            state_toggles,
            HtdConstants.POWER_STATE_TOGGLE_INDEX
        )
        zone.mute = htd_client.utils.is_bit_on(state_toggles, HtdConstants.MUTE_STATE_TOGGLE_INDEX)
        zone.mode = htd_client.utils.is_bit_on(state_toggles, HtdConstants.MODE_STATE_TOGGLE_INDEX)

        zone.source = zone_data[HtdConstants.SOURCE_ZONE_DATA_INDEX] + HtdConstants.SOURCE_QUERY_OFFSET
        zone.volume = volume
        zone.treble = htd_client.utils.convert_value(zone_data[HtdConstants.TREBLE_ZONE_DATA_INDEX])
        zone.bass = htd_client.utils.convert_value(zone_data[HtdConstants.BASS_ZONE_DATA_INDEX])
        zone.balance = htd_client.utils.convert_value(zone_data[HtdConstants.BALANCE_ZONE_DATA_INDEX])

        return zone

    def subscribe(self, callback):
        self._subscribers.add(callback)

        # if we're already ready, call the callback immediately and let them update
        if self._ready:
            callback(None)

    def unsubscribe(self, callback):
        self._subscribers.discard(callback)

    def _broadcast(self, zone: int = None):
        while self._callback_lock.locked():
            pass

        with self._callback_lock:
            for callback in self._subscribers:
                callback(zone)

    def _send_and_validate(
        self,
        validate: callable,
        zone: int,
        command: int,
        data_code: int,
        extra_data: bytearray = None,
        follow_up=None
    ):
        """
        Send a command to the gateway and parse the response.

        Args:
            validate (callable): a function that validates the response
            zone (int): the zone to send this instruction to
            command (bytes): the command to send
            data_code (int): the data value for the accompany command
            extra_data (bytes): the extra data to send with the command
            follow_up (tuple): a tuple of command and data_code to send after the initial command

        Returns:
            bytes: the response of the command
        """

        attempts = 0
        last_attempt_time = 0

        while not validate(self.get_zone(zone)):
            if int(time.time() - last_attempt_time) > self._command_retry_timeout:
                attempts += 1

                if attempts > self._retry_attempts:
                    raise Exception(f"Failed to execute command after {self._retry_attempts} attempts")

                # we only want to call refresh if we have already tried
                if last_attempt_time != 0:
                    self.refresh(zone)

                self._send_cmd(zone, command, data_code, extra_data)

                # setting volume on lync requires you to unmute, so a followup command is used
                if follow_up is not None:
                    self._send_cmd(zone, follow_up[0], follow_up[1])

                last_attempt_time = time.time()

    def _send_cmd(
        self,
        zone: int,
        command: int,
        data_code: int,
        extra_data: bytearray = None
    ):
        while self._socket_lock.locked():
            pass

        cmd = htd_client.utils.build_command(zone, command, data_code, extra_data)

        try:
            _LOGGER.debug("sending command %s" % htd_client.utils.stringify_bytes(cmd))
            self._connection.write(cmd)
            self._connection.flush()
        except BrokenPipeError as e:
            _LOGGER.error("Failed to send command, reconnecting and retrying")
            self.connect()

            _LOGGER.debug("Reconnected, retrying command")
            self._connection.write(cmd)
            self._connection.flush()

    def get_zone_count(self) -> int:
        """
        Get the number of zones available

        Returns:
            int: the number of zones available
        """
        return self._model_info['zones']

    def get_source_count(self) -> int:
        """
        Get the number of sources available

        Returns:
            int: the number of sources available
        """
        return self._model_info['sources']

    def get_zone(self, zone: int):
        """
        Query a zone and return `ZoneDetail`

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        return self._zone_data[zone]

    def toggle_mute(self, zone: int):
        """
        Toggle the mute state of a zone.

        Args:
            zone (int): the zone to toggle
        """
        zone_detail = self.get_zone(zone)

        if zone_detail.mute:
            self.unmute(zone)
        else:
            self.mute(zone)

    @abstractmethod
    def refresh(self, zone: int = None):
        pass

    @abstractmethod
    def power_on_all_zones(self):
        pass

    @abstractmethod
    def power_off_all_zones(self):
        pass

    @abstractmethod
    def set_source(self, zone: int, source: int):
        pass

    @abstractmethod
    def volume_up(self, zone: int):
        pass

    @abstractmethod
    def set_volume(self, zone: int, volume: int):
        pass

    @abstractmethod
    def volume_down(self, zone: int):
        pass

    @abstractmethod
    def mute(self, zone: int):
        pass

    @abstractmethod
    def unmute(self, zone: int):
        pass

    @abstractmethod
    def power_on(self, zone: int):
        pass

    @abstractmethod
    def power_off(self, zone: int):
        pass

    @abstractmethod
    def bass_up(self, zone: int):
        pass

    @abstractmethod
    def bass_down(self, zone: int):
        pass

    @abstractmethod
    def treble_up(self, zone: int):
        pass

    @abstractmethod
    def treble_down(self, zone: int):
        pass

    @abstractmethod
    def balance_left(self, zone: int):
        pass

    @abstractmethod
    def balance_right(self, zone: int):
        pass
