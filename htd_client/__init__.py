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


import logging
import socket
import time
from encodings import utf_8
from typing import Callable, Dict

import htd_client.utils
from constants import HtdModelInfo, HtdLyncConstants
from htd_client.constants import (
    MAX_BYTES_TO_RECEIVE,
    ONE_SECOND,
    HtdDeviceKind,
    HtdConstants,
    HtdCommonCommands,
    HtdLyncCommands,
    HtdMcaCommands, HtdMcaConstants,
)
from htd_client.models import ZoneDetail, NotSupportedError
from utils import validate_zone_response

_LOGGER = logging.getLogger(__name__)


class HtdClient:
    """
    This is the client for the HTD gateway device. It can communicate with the device and send instructions.

    Args:
        ip_address (str): ip address of the gateway to connect to
        port (int): the port number of the gateway to connect to
        retry_attempts(int): if a response is not valid or incorrect, how many times should we try again.
        command_delay(int): the device can get overworked, we delay this amount of time inbetween commands, in milliseconds
        socket_timeout(int): the amount of time before we will time out from the device, in milliseconds
    """
    _ip_address: str = None
    _port: int = None
    _command_delay_sec: float = None
    _retry_attempts: int = None
    _socket_timeout_sec: float = None

    _zone_data: Dict[int, ZoneDetail] = None

    def __init__(
        self,
        ip_address: str,
        port: int = HtdConstants.DEFAULT_HTD_PORT,
        retry_attempts: int = HtdConstants.DEFAULT_RETRY_ATTEMPTS,
        command_delay: int = HtdConstants.DEFAULT_COMMAND_DELAY,
        socket_timeout: int = HtdConstants.DEFAULT_SOCKET_TIMEOUT,
        kind: HtdDeviceKind | None = None,
    ):
        self._ip_address = ip_address
        self._port = port
        self._retry_attempts = retry_attempts
        self._command_delay_sec = command_delay / ONE_SECOND
        self._socket_timeout_sec = socket_timeout / ONE_SECOND

        self.kind = self._set_kind(kind)
        self.refresh()

        print(f"detected {self.kind}")


    def get_model_info(self) -> HtdModelInfo:
        """
        Get the model information from the gateway.

        Returns:
             (str, str): the raw model name from the gateway and the friendly name, in a Tuple.
        """
        response = self._send(1, HtdCommonCommands.MODEL_QUERY_COMMAND_CODE, 0)
        model_info = response.decode(utf_8.getregentry().name)
        return htd_client.utils.get_model_info(model_info)

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


    def query_zone_name(self, zone: int) -> str:
        """
        Query a zone and return `ZoneDetail`

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """

        # htd_client.utils.validate_zone(zone)
        self._assert_lync()

        response = self._send_and_validate(
            zone,
            HtdLyncCommands.QUERY_ZONE_NAME_COMMAND_CODE,
            0
        )
        
        return htd_client.utils.parse_zone_name(response)


    def refresh(self):
        """
        Query all zones and return a dict of `ZoneDetail`

        Returns:
            dict[int, ZoneDetail]: a dict where the key represents the zone number, and the value are the details of the zone
        """

        response = self._send_and_validate(0, self._get_common_command(), 0)
        self._zone_data = htd_client.utils.parse_all_zones(response, self.kind)


    def set_source(self, zone: int, source: int):
        """
        Set the source of a zone.

        Args:
            zone (int): the zone
            source (int): the source to set

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid or source X is invalid
        """
        htd_client.utils.validate_zone(zone)
        htd_client.utils.validate_source(source)

        offset = self._pick_kind(
            HtdMcaConstants.SOURCE_COMMAND_OFFSET,
            HtdLyncConstants.SOURCE_COMMAND_OFFSET
        )

        self._send_and_validate(
            zone,
            self._get_common_command(),
            offset  + source
        )

    def volume_up(self, zone: int):
        """
        Increase the volume of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """

        self._assert_mca()

        htd_client.utils.validate_zone(zone)
        self._send_and_validate(
            zone,
            self._get_common_command(),
            HtdMcaCommands.VOLUME_UP_COMMAND
        )


    def volume_down(self, zone: int):
        """
        Decrease the volume of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        self._assert_mca()

        htd_client.utils.validate_zone(zone)
        return self._send_and_validate(
            zone,
            self._get_common_command(),
            HtdMcaCommands.VOLUME_DOWN_COMMAND
        )

    def toggle_mute(self, zone: int):
        """
        Toggle the mute state of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """

        self._assert_mca()

        htd_client.utils.validate_zone(zone)
        return self._send_and_validate(
            zone,
            HtdMcaCommands.QUERY_COMMAND_CODE,
            HtdMcaCommands.TOGGLE_MUTE_COMMAND
        )

    def power_on(self, zone: int):
        """
        Power on a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """

        htd_client.utils.validate_zone(zone)

        cmd = self._pick_kind(
            HtdMcaCommands.POWER_ON_ZONE_COMMAND_CODE,
            HtdLyncCommands.POWER_ON_ZONE_COMMAND_CODE
        )

        return self._send_and_validate(
            zone,
            self._get_common_command(),
            cmd
        )

    def power_on_all_zones(self) -> None:
        """
        Power on all zones.
        """
        cmd = self._pick_kind(
            HtdMcaCommands.POWER_ON_ALL_ZONES_COMMAND_CODE,
            HtdLyncCommands.POWER_ON_ALL_ZONES_COMMAND_CODE
        )

        self._send_and_validate(
            1,
            self._get_common_command(),
            cmd
        )

    def power_off(self, zone: int):
        """
        Power off a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """

        htd_client.utils.validate_zone(zone)

        cmd = self._pick_kind(
            HtdMcaCommands.POWER_OFF_ZONE_COMMAND_CODE,
            HtdLyncCommands.POWER_OFF_ZONE_COMMAND_CODE
        )

        return self._send_and_validate(
            zone,
            self._get_common_command(),
            cmd
        )

    def power_off_all_zones(self) -> None:
        """
        Power off all zones.
        """
        cmd = self._pick_kind(
            HtdMcaCommands.POWER_OFF_ALL_ZONES_COMMAND_CODE,
            HtdLyncCommands.POWER_OFF_ALL_ZONES_COMMAND_CODE
        )

        self._send_and_validate(
            1,
            self._get_common_command(),
            cmd
        )

    def bass_up(self, zone: int):
        """
        Increase the bass of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """

        self._assert_mca()
        htd_client.utils.validate_zone(zone)
        self._send_and_validate(
            zone,
            self._get_common_command(),
            HtdMcaCommands.BASS_UP_COMMAND
        )

    def bass_down(self, zone: int):
        """
        Decrease the bass of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        self._assert_mca()
        htd_client.utils.validate_zone(zone)
        return self._send_and_validate(
            zone,
            self._get_common_command(),
            HtdMcaCommands.BASS_DOWN_COMMAND
        )

    def treble_up(self, zone: int):
        """
        Increase the treble of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        self._assert_mca()
        htd_client.utils.validate_zone(zone)
        return self._send_and_validate(
            zone,
            self._get_common_command(),
            HtdMcaCommands.TREBLE_UP_COMMAND
        )

    def treble_down(self, zone: int):
        """
        Decrease the treble of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        self._assert_mca()
        htd_client.utils.validate_zone(zone)
        return self._send_and_validate(
            zone,
            self._get_common_command(),
            HtdMcaCommands.TREBLE_DOWN_COMMAND
        )

    def balance_left(self, zone: int):
        """
        Increase the balance toward the left for a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        self._assert_mca()
        htd_client.utils.validate_zone(zone)
        return self._send_and_validate(
            zone,
            self._get_common_command(),
            HtdMcaCommands.BALANCE_LEFT_COMMAND
        )

    def balance_right(self, zone: int):
        """
        Increase the balance toward the right for a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        self._assert_mca()
        htd_client.utils.validate_zone(zone)
        return self._send_and_validate(
            zone,
            self._get_common_command(),
            HtdMcaCommands.BALANCE_RIGHT_COMMAND
        )

    def set_volume(
        self,
        zone: int,
        volume: float,
        on_increment: Callable[[float, ZoneDetail], int | None] = None,
        zone_info: ZoneDetail | None = None
    ):
        if self.kind == HtdDeviceKind.mca:
            return self._set_volume_mca(zone, volume, on_increment, zone_info)
        elif self.kind == HtdDeviceKind.lync:
            return self._set_volume_lync(zone, volume)


    def _set_volume_lync(
        self,
        zone: int,
        volume: float
    ):
        pass


    def _set_volume_mca(
        self,
        zone: int,
        volume: float,
        on_increment: Callable[[float, ZoneDetail], int | None] = None,
        zone_info: ZoneDetail | None = None
    ):
        """
        Set the volume of a zone.

        Args:
            zone (int): the zone
            volume (float): the volume
            on_increment (Callable[[float, ZoneDetail], int | None]): a callback to be called when the volume is incremented
            zone_info (ZoneDetail): an existing zone info, if available

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested
        """
        if zone_info is None:
            zone_info = self._zone_data[zone]

        diff = round(volume) - zone_info.volume

        # the HTD volume max is 60, HASS goes to 100, so we're never ever going
        # to set this to the exact volume that the user desired, so we go
        # within a tolerance of 1.
        if 1 >= diff >= -1:
            return zone_info

        if diff < 0:
            volume_command = HtdMcaCommands.VOLUME_DOWN_COMMAND
        else:
            volume_command = HtdMcaCommands.VOLUME_UP_COMMAND

        response = self._send_and_validate(
            zone,
            self._get_common_command(),
            volume_command,
            enable_retry=False,
        )

        zones = htd_client.utils.parse_all_zones(response, HtdDeviceKind.mca)
        zone_info = zones[zone]

        if on_increment is not None:
            # we allow the user to change the volume again and interrupt
            # the volume setting during an adjustment, simply just set it and
            # continue going towards it
            override_volume = on_increment(volume, zone_info)

            if override_volume is not None:
                volume = override_volume

        return self._set_volume_mca(zone, volume, on_increment, zone_info)


    def _send_and_validate(
        self,
        zone: int,
        command: bytes,
        data_code: int,
        attempt: int = 0,
        enable_retry: bool = True
    ) -> bytes:
        """
        Send a command to the gateway and parse the response.

        Args:
            zone (int): the zone to send this instruction to
            command (bytes): the command to send
            data_code (int): the data value for the accompany command
            attempt (int): the number of attempts made
            enable_retry (bool): whether to attempt a retry

        Returns:
            bytes: the response of the command
        """
        response = self._send(zone, command, data_code)
        is_valid = validate_zone_response(response, command)

        if is_valid:
            return response

        if enable_retry and attempt < self._retry_attempts:
            _LOGGER.warning(
                "Bad response, will retry. zone = %d, retry = %d" %
                (zone, attempt)
            )

            # sleep longer each time to be sure.
            delay = self._command_delay_sec * (attempt + 1)
            time.sleep(delay)

            return self._send_and_validate(
                zone,
                command,
                data_code,
                attempt + 1
            )

        _LOGGER.critical("Still bad response after retrying! zone = %d! " % zone)


    def _send(self, zone: int, command: bytes, data_code: int) -> bytes:
        """
        Send a command to the gateway.

        Args:
            zone (int): the zone to send this instruction to
            command (bytes): the command to send
            data_code (int): the data value for the accompany command

        Returns:
            bytes: the raw response from the gateway
        """
        cmd = htd_client.utils.get_command(zone, command, data_code)

        connection = socket.create_connection(
            address=(self._ip_address, self._port),
            timeout=self._socket_timeout_sec,
        )
        connection.send(cmd)
        data = connection.recv(MAX_BYTES_TO_RECEIVE)
        connection.close()

        return data

    def _set_kind(self, kind: HtdDeviceKind | None):
        if kind is None:
            model_info = self.get_model_info()
            kind = model_info["kind"]

        else:
            if all(entry.get('kind') != kind for entry in HtdConstants.SUPPORTED_MODELS.values()):
                kind = None

        if kind is None:
            raise NotSupportedError("Could not identify model")

        return kind

    def _get_common_command(self):
        return self._pick_kind(HtdMcaCommands.QUERY_COMMAND_CODE, HtdLyncCommands.QUERY_COMMAND_CODE)

    def _pick_kind(self, mca, lync):
        return mca if self.is_mca() else lync

    def _assert_lync(self):
        if not self.is_lync():
            raise NotSupportedError("Device is not a Lync")

    def _assert_mca(self):
        if not self.is_mca():
            raise NotSupportedError("Device is not a MCA")

    def is_lync(self):
        return self.kind == HtdDeviceKind.lync

    def is_mca(self):
        return self.kind == HtdDeviceKind.mca