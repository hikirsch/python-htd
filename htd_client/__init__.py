"""
.. code-block:: python

    # import the client
    from htd_client import HtdClient

    # Call its only function
    client = HtdClient("192.168.1.2")

    (model_info, friendly_name) = client.get_model_info()
    zone_info = client.query_zone(1)
    updated_zone_info = client.volume_up(1)
"""


import logging
import socket
import time
from encodings import utf_8
from typing import Callable

import htd_client.utils
from htd_client.constants import HtdConstants, MAX_BYTES_TO_RECEIVE, ONE_SECOND
from htd_client.models import ZoneDetail

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

    def __init__(
        self,
        ip_address: str,
        port: int = HtdConstants.DEFAULT_HTD_MC_PORT,
        retry_attempts: int = HtdConstants.DEFAULT_RETRY_ATTEMPTS,
        command_delay: int = HtdConstants.DEFAULT_COMMAND_DELAY,
        socket_timeout: int = HtdConstants.DEFAULT_SOCKET_TIMEOUT,
    ):
        self._ip_address = ip_address
        self._port = port
        self._retry_attempts = retry_attempts
        self._command_delay_sec = command_delay / ONE_SECOND
        self._socket_timeout_sec = socket_timeout / ONE_SECOND

    def get_model_info(self) -> (str, str):
        """
        Get the model information from the gateway.

        Returns:
             (str, str): the raw model name from the gateway and the friendly name, in a Tuple.
        """
        response = self._send(1, HtdConstants.MODEL_QUERY_COMMAND_CODE, 0)
        model_info = response.decode(utf_8.getregentry().name)
        friendly_name = htd_client.utils.get_friendly_name(model_info)
        return model_info, friendly_name

    def query_zone(self, zone: int) -> ZoneDetail:
        """
        Query a zone and return `ZoneDetail`

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.QUERY_COMMAND_CODE,
            0
        )

    def query_all_zones(self) -> dict[int, ZoneDetail]:
        """
        Query all zones and return a dict of `ZoneDetail`

        Returns:
            dict[int, ZoneDetail]: a dict where the key represents the zone number, and the value are the details of the zone
        """
        return self._send_and_parse_all(
            0,
            HtdConstants.QUERY_COMMAND_CODE,
            0
        )

    def set_source(self, zone: int, source: int) -> ZoneDetail:
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
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.SOURCE_COMMAND_OFFSET + source
        )

    def volume_up(self, zone: int) -> ZoneDetail:
        """
        Increase the volume of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.VOLUME_UP_COMMAND
        )

    def volume_down(self, zone: int) -> ZoneDetail:
        """
        Decrease the volume of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.VOLUME_DOWN_COMMAND
        )

    def toggle_mute(self, zone: int) -> ZoneDetail:
        """
        Toggle the mute state of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.TOGGLE_MUTE_COMMAND
        )

    def power_on(self, zone: int) -> ZoneDetail:
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
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.POWER_ON_ZONE_COMMAND
        )

    def power_on_all_zones(self) -> None:
        """
        Power on all zones.
        """
        self._send_and_parse_all(
            1,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.POWER_ON_ALL_ZONES_COMMAND
        )

    def power_off(self, zone: int) -> ZoneDetail:
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

        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.POWER_OFF_ZONE_COMMAND,
        )

    def power_off_all_zones(self) -> None:
        """
        Power off all zones.
        """
        self._send_and_parse_all(
            1,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.POWER_OFF_ALL_ZONES_COMMAND
        )

    def bass_up(self, zone: int) -> ZoneDetail:
        """
        Increase the bass of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.BASS_UP_COMMAND
        )

    def bass_down(self, zone: int) -> ZoneDetail:
        """
        Decrease the bass of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.BASS_DOWN_COMMAND
        )

    def treble_up(self, zone: int) -> ZoneDetail:
        """
        Increase the treble of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.TREBLE_UP_COMMAND
        )

    def treble_down(self, zone: int) -> ZoneDetail:
        """
        Decrease the treble of a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.TREBLE_DOWN_COMMAND
        )

    def balance_left(self, zone: int) -> ZoneDetail:
        """
        Increase the balance toward the left for a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.BALANCE_LEFT_COMMAND
        )

    def balance_right(self, zone: int) -> ZoneDetail:
        """
        Increase the balance toward the right for a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.BALANCE_RIGHT_COMMAND
        )

    def set_volume(
        self,
        zone: int,
        volume: float,
        on_increment: Callable[[float, ZoneDetail], int | None] = None,
        zone_info: ZoneDetail | None = None
    ) -> ZoneDetail:
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
            zone_info = self.query_zone(zone)

        diff = round(volume) - zone_info.volume

        # the HTD volume max is 60, HASS goes to 100, so we're never ever going
        # to set this to the exact volume that the user desired, so we go
        # within a tolerance of 1.
        if 1 >= diff >= -1:
            return zone_info

        if diff < 0:
            volume_command = HtdConstants.VOLUME_DOWN_COMMAND
        else:
            volume_command = HtdConstants.VOLUME_UP_COMMAND

        zone_info = self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            volume_command,
            enable_retry=False,
        )

        if zone_info is None:
            zone_info = self.query_zone(zone)

        if on_increment is not None:
            # we allow the user to change the volume again and interrupt
            # the volume setting during an adjustment, simply just set it and
            # continue going towards it
            override_volume = on_increment(volume, zone_info)

            if override_volume is not None:
                volume = override_volume

        return self.set_volume(zone, volume, on_increment, zone_info)

    def _send_and_parse_all(
        self,
        zone: int,
        command: bytes,
        data_code: int,
    ) -> dict[int, ZoneDetail]:
        """
        A shorthand method to call _send_and_parse with the is_multiple flag set to True

        Args:
            zone (int): the zone to send this instruction to
            command (bytes): the command to send
            data_code (int): the data value for the accompany command

        Returns:
            dict[int, ZoneDetail]: a dict where the key represents the zone number, and the value are the details of the zone
        """
        return self._send_and_parse(zone, command, data_code, True)

    def _send_and_parse(
        self,
        zone: int,
        command: bytes,
        data_code: int,
        is_multiple: bool = False,
        attempt: int = 0,
        enable_retry: bool = True
    ) -> dict[int, ZoneDetail] | ZoneDetail:
        """
        Send a command to the gateway and parse the response.

        Args:
            zone (int): the zone to send this instruction to
            command (bytes): the command to send
            data_code (int): the data value for the accompany command
            is_multiple (bool): whether to parse multiple zones from the response
            attempt (int): the number of attempts made
            enable_retry (bool): whether to attempt a retry

        Returns:
            dict[int, ZoneDetail]: a single ZoneDetail if is_multiple is false, otherwise a dict where the key represents the zone number, and the value are the details of the zone
        """
        response = self._send(zone, command, data_code)

        if is_multiple:
            parsed = htd_client.utils.parse_all_zones(response)
        else:
            parsed = htd_client.utils.parse_single_zone(response, zone)

        if parsed is None and enable_retry and attempt < self._retry_attempts:
            _LOGGER.warning(
                "Bad response, will retry. zone = %d, retry = %d" %
                (zone, attempt)
            )

            # sleep longer each time to be sure.
            delay = self._command_delay_sec * (attempt + 1)
            time.sleep(delay)

            return self._send_and_parse(
                zone,
                command,
                data_code,
                is_multiple,
                attempt + 1
            )

        if parsed is None:
            _LOGGER.critical(
                (
                    "Still bad response after retrying! zone = %d! "
                    "Consider increasing your command_delay!"
                )
                % zone
            )

        return parsed

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
