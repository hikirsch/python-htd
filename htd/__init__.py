import logging
import socket
import time
from encodings import utf_8
from typing import Callable

import htd.utils

from htd.constants import HtdConstants
from htd.models import ZoneDetail

_LOGGER = logging.getLogger(__name__)

MAX_BYTES_TO_RECEIVE = 2 ** 10  # receive 1024 bytes
ONE_SECOND = 1_000


class HtdClient:
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
        socket_timeout: float = HtdConstants.DEFAULT_SOCKET_TIMEOUT,
    ):
        self._ip_address = ip_address
        self._port = port
        self._retry_attempts = retry_attempts
        self._command_delay_sec = command_delay / ONE_SECOND
        self._socket_timeout_sec = socket_timeout / ONE_SECOND

    def get_model_info(self) -> (str, str):
        response = self._send(1, HtdConstants.MODEL_QUERY_COMMAND_CODE, 0)
        model_info = response.decode(utf_8.getregentry().name)
        friendly_name = htd.utils.get_friendly_name(model_info)
        return model_info, friendly_name

    def query_zone(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.QUERY_COMMAND_CODE,
            0
        )

    def query_all_zones(self) -> dict[int, ZoneDetail]:
        return self._send_and_parse_all(
            0,
            HtdConstants.QUERY_COMMAND_CODE,
            0
        )

    def set_source(self, zone: int, source: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        htd.utils.validate_source(source)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.SOURCE_COMMAND_OFFSET + source
        )

    def volume_up(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.VOLUME_UP_COMMAND
        )

    def volume_down(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.VOLUME_DOWN_COMMAND
        )

    def toggle_mute(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.TOGGLE_MUTE_COMMAND
        )

    def power_on(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.POWER_ON_ZONE_COMMAND
        )

    def power_on_all_zones(self) -> None:
        self._send_and_parse_all(
            1,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.POWER_ON_ALL_ZONES_COMMAND
        )

    def power_off(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)

        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.POWER_OFF_ZONE_COMMAND,
        )

    def power_off_all_zones(self) -> None:
        self._send_and_parse_all(
            1,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.POWER_OFF_ALL_ZONES_COMMAND
        )

    def bass_up(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.BASS_UP_COMMAND
        )

    def bass_down(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.BASS_DOWN_COMMAND
        )

    def treble_up(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.TREBLE_UP_COMMAND
        )

    def treble_down(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.TREBLE_DOWN_COMMAND
        )

    def balance_left(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
        return self._send_and_parse(
            zone,
            HtdConstants.SET_COMMAND_CODE,
            HtdConstants.BALANCE_LEFT_COMMAND
        )

    def balance_right(self, zone: int) -> ZoneDetail:
        htd.utils.validate_zone(zone)
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
        response = self._send(zone, command, data_code)

        # parser = htd.utils.parse_all_zones if is_multiple else htd.utils.parse_zone
        if is_multiple:
            parser = htd.utils.parse_all_zones
        else:
            parser = htd.utils.parse_zone

        parsed = parser(response)

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
        cmd = htd.utils.get_command(zone, command, data_code)

        connection = socket.create_connection(
            address=(self._ip_address, self._port),
            timeout=self._socket_timeout_sec,
        )
        connection.send(cmd)
        data = connection.recv(MAX_BYTES_TO_RECEIVE)
        connection.close()

        return data
