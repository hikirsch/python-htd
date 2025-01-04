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
import socket

LYNC_HEADER = b'\x02\x00'
MESSAGE_HEADER_LENGTH = len(LYNC_HEADER)

import logging
import threading
import time
from abc import abstractmethod
from typing import Dict

import htd_client

from .constants import (
    HtdConstants,
    HtdDeviceKind,
    ONE_SECOND,
    HtdLyncConstants,
    HtdLyncCommands,
    MAX_BYTES_TO_RECEIVE,
    HtdModelInfo,
)
from .models import ZoneDetail

_LOGGER = logging.getLogger(__name__)


class BaseClient:
    _kind: HtdDeviceKind = None
    _ip_address: str = None
    _port: int = None
    _retry_attempts: int = None
    _socket_timeout_sec: float = None
    _buf: bytearray = None
    _zone_data: Dict[int, ZoneDetail] = None
    _model_info: HtdModelInfo = None
    _connection: socket.socket = None
    _socket_thread: threading.Thread = None
    _socket_lock: threading.Lock = None

    _is_ready: bool = False
    _zones_loaded: int = 0
    _callbacks: set = None
    _connected: bool = False
    _loop: asyncio.AbstractEventLoop = None

    def __init__(
        self,
        kind: HtdDeviceKind,
        ip_address: str,
        port: int = HtdConstants.DEFAULT_PORT,
        retry_attempts: int = HtdConstants.DEFAULT_RETRY_ATTEMPTS,
        socket_timeout: int = HtdConstants.DEFAULT_SOCKET_TIMEOUT
    ):
        self._kind = kind
        self._ip_address = ip_address
        self._port = port
        self._retry_attempts = retry_attempts
        self._socket_timeout_sec = socket_timeout / ONE_SECOND
        self._buf = bytearray()
        self._zone_data = {}
        self._callbacks = set()
        self._socket_lock = threading.Lock()
        self._loop = asyncio.get_event_loop()
        self._model_info = htd_client.get_model_info(self._ip_address, self._port)

        self._connect()


    def register_callback(self, callback):
        self._callbacks.add(callback)

        if self._is_ready:
            callback()

    def remove_callback(self, callback):
        self._callbacks.discard(callback)

    def _connect(self):
        address = (self._ip_address, self._port)

        _LOGGER.info("connecting to %s:%s" % address)

        self._connection = socket.create_connection(
            address=address,
            timeout=self._socket_timeout_sec,
        )

        self._socket_thread = threading.Thread(target=self._on_message)
        self._socket_thread.daemon = True
        self._socket_thread.start()

        start_time = time.time()
        current_time = time.time()
        refresh_count = 0
        refresh_timeout = 5

        while len(self._zone_data) == 0 and current_time - start_time < self._socket_timeout_sec:
            current_time = time.time()

            if refresh_count * refresh_timeout < int(current_time - start_time):
                refresh_count += 1
                self.refresh()

        self._connected = True

    def _on_message(self):
        while True:
            try:
                data = self._connection.recv(MAX_BYTES_TO_RECEIVE)

                if len(data) == 0:
                    break

                with self._socket_lock:
                    while len(data) > 0:
                        chunk_length = self.process_next_command(data)
                        data = data[chunk_length:]

            except Exception as e:
                print(f"Error receiving data: {e}")
                break

            self.publish_update()


    def process_next_command(self, data):
        """ Process the lync frame data.  Search for the frame sync bytes and process one
            frame from the buffer.  Return the start of the next frame. """

        # start with search for command header and id the command
        # not enough data, 2 reserved header bits, zone + command + data + checksum = 4, is minimum length
        if len(data) < MESSAGE_HEADER_LENGTH + 4:
            return 0

        start_message_index = data.find(LYNC_HEADER)

        if start_message_index < 0:
            return len(data)

        if start_message_index != 0:
            _LOGGER.debug("Bad sync buffer! %s" % htd_client.utils.stringify_bytes(data))

        # offsets to packet data, zones, command, and then data
        zone_idx = start_message_index + MESSAGE_HEADER_LENGTH
        cmd_idx = zone_idx + 1
        data_idx = cmd_idx + 1

        # not enough data, wait for more
        if len(data) < data_idx:
            return 0

        zone = int(data[zone_idx])
        command = data[cmd_idx]

        # Skip over bad command
        # return the minimum packet size for resync
        if command not in HtdLyncConstants.RECEIVE_COMMAND_EXPECTED_LENGTH_MAP:
            _LOGGER.error(
                "Invalid command value: zone = %d, command = %s, data = %s" %
                (
                    zone,
                    htd_client.utils.stringify_bytes(command),
                    htd_client.utils.stringify_bytes(data),
                )
            )

            return start_message_index + MESSAGE_HEADER_LENGTH

        expected_length = HtdLyncConstants.RECEIVE_COMMAND_EXPECTED_LENGTH_MAP[command]

        # _LOGGER.debug("Got command: %s zone: %d name: %s", c[cmd_idx], zone, cmd_name)
        if command == HtdLyncCommands.UNDEFINED_RECEIVE_COMMAND:
            _LOGGER.info("Undefined response command: %02x", int(command))
            _LOGGER.debug("Packet buffer: %s", htd_client.utils.stringify_bytes(data[0:20]))
            return start_message_index + MESSAGE_HEADER_LENGTH

        # not enough data, wait for more
        if len(data) < data_idx + expected_length:
            return 0

        end_message_index = start_message_index + MESSAGE_HEADER_LENGTH + 2 + expected_length
        chunk_length = end_message_index + 1

        # process the content to the current state
        frame = data[start_message_index:end_message_index]
        checksum = data[end_message_index]
        frame_sum_checksum = sum(frame) & 0xff

        # validate the checksum
        if frame_sum_checksum == checksum:
            chunk = data[0:chunk_length]

            _LOGGER.debug("Processing chunk %s" % htd_client.utils.stringify_bytes(chunk))

            frame = data[data_idx:data_idx + expected_length]
            self._parse_command(zone, command, frame)

            if not self._is_ready and command == HtdLyncCommands.ZONE_STATUS_RECEIVE_COMMAND:
                self._zones_loaded += 1
                if self._zones_loaded == self._model_info['zones']:
                    self._is_ready = True


        else:
            _LOGGER.info("Bad checksum %02x != %02x", frame_sum_checksum, checksum)

        return chunk_length

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

        Returns:
            bytes: the response of the command
        """

        attempts = 0
        retry_time = .25
        last_attempt_time = 0

        while not validate(self.get_zone(zone)):
            if time.time() - last_attempt_time > retry_time:
                attempts += 1

                if attempts > self._retry_attempts:
                    raise Exception(f"Failed to execute command after {self._retry_attempts} attempts")

                # we only want to call refresh if we have already tried
                if last_attempt_time != 0:
                    self.refresh()
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
        _LOGGER.debug("sending command %s" % htd_client.utils.stringify_bytes(cmd))
        self._connection.send(cmd)

    @abstractmethod
    def get_zone_names(self) -> str:
        pass

    def get_zone_count(self) -> int:
        """
        Get the number of zones available

        Returns:
            int: the number of zones available
        """
        return self._model_info['zones']

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


    @abstractmethod
    def refresh(self):
        pass

    @abstractmethod
    def _parse_command(self, zone: int, command: int, data: bytearray):
        pass

    @abstractmethod
    def get_firmware_version(self) -> str:
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

    def publish_update(self):
        for callback in self._callbacks:
            callback()
