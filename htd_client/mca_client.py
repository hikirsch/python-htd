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
import json
import logging
from typing import Callable, Dict

import htd_client

from .base_client import BaseClient
from .constants import HtdConstants, HtdDeviceKind, HtdMcaCommands, HtdMcaConstants
from .models import ZoneDetail

_LOGGER = logging.getLogger(__name__)


class HtdMcaClient(BaseClient):
    """
    This is the client for the HTD gateway device. It can communicate with
    the device and send instructions.

    Args:
        ip_address (str): ip address of the gateway to connect to
        port (int): the port number of the gateway to connect to
        retry_attempts(int): if a response is not valid or incorrect,
        how many times should we try again.
        command_delay(int): the device can get overworked, we delay this
        amount of time inbetween commands, in milliseconds
        socket_timeout(int): the amount of time before we will time out from
        the device, in milliseconds
    """
    _zone_data: Dict[int, ZoneDetail] = None

    def __init__(
        self,
        ip_address: str,
        port: int = HtdConstants.DEFAULT_PORT,
        retry_attempts: int = HtdConstants.DEFAULT_RETRY_ATTEMPTS,
        command_delay: int = HtdConstants.DEFAULT_COMMAND_DELAY,
        socket_timeout: int = HtdConstants.DEFAULT_SOCKET_TIMEOUT
    ):
        super().__init__(
            HtdDeviceKind.mca,
            ip_address,
            port,
            retry_attempts,
            command_delay,
            socket_timeout
        )

    def get_firmware_version(self) -> str:
        raise "unsupported"

    def query_source_names(self) -> Dict[int, str]:
        """
        Query a zone and return `ZoneDetail`

        Returns:
            Dict[int, str]: a dictionary where each zone has a string value
            of the source name
        """

        response = self._send_cmd(
            1,
            HtdMcaCommands.QUERY_SOURCE_NAME_COMMAND_CODE,
            htd_client.utils.int_to_bytes(0)
        )

        sources = {}
        source = 0
        chunks = [response[i:i + HtdConstants.MESSAGE_CHUNK_SIZE] for i in
                  range(0, len(response), HtdConstants.MESSAGE_CHUNK_SIZE)]
        chunks_to_use = chunks[6:12]
        for chunk in chunks_to_use:
            source_name_bin = chunk[4:-1].strip(b"\x00")
            source_name = htd_client.utils.decode_response(source_name_bin)
            source += 1
            sources[source] = source_name

        # decoded = htd_client.utils.decode_response(response)

        return sources

    def set_source_name(self, source: int, name: str):
        """
        Query a zone and return `ZoneDetail`

        Args:
            source (int): the source
            name (str): the name of the source (max length of 7)

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raises:
            Exception: zone X is invalid
        """

        # htd_client.utils.validate_zone(zone)

        extra_data = bytes(
            [ord(char) for char in name] + [0] * (7 - len(name)) + [0x00]
        )

        self._send_cmd(
            0,
            HtdMcaCommands.SET_SOURCE_NAME_COMMAND_CODE,
            source,
            extra_data
        )

    def set_volume(self, zone: int, volume: int):
        return self._set_volume(zone, volume)

    def _set_volume(self, zone: int, volume: int, on_increment: Callable[[float, ZoneDetail], int | None] = None):
        """
        Set the volume of a zone.

        Args:
            zone (int): the zone
            volume (int): the volume
            on_increment (Callable[[float, ZoneDetail], int | None]): a
            callback to be called when the volume is incremented

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested
        """

        zone_info = self._zone_data[zone]

        diff = volume - zone_info.volume

        # the HTD volume max is 60, HASS goes to 100, so we're never ever going
        # to set this to the exact volume that the user desired, so we go
        # within a tolerance of 1.
        if 1 >= diff >= -1:
            return zone_info

        if diff < 0:
            volume_command = HtdMcaCommands.VOLUME_DOWN_COMMAND
        else:
            volume_command = HtdMcaCommands.VOLUME_UP_COMMAND

        self._send_cmd(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            volume_command
        )

        if on_increment is not None:
            # we allow the user to change the volume again and interrupt
            # the volume setting during an adjustment, simply just set it and
            # continue going towards it
            override_volume = on_increment(volume, zone_info)

            if override_volume is not None:
                volume = override_volume

        return self._set_volume(zone, volume, on_increment)

    def refresh(self):
        """
        Query all zones and return a dict of `ZoneDetail`

        Returns:
            dict[int, ZoneDetail]: a dict where the key represents the zone
            number, and the value are the details of the zone
        """
        response = self._send_and_validate(
            0,
            HtdMcaCommands.QUERY_COMMAND_CODE,
            htd_client.utils.int_to_bytes(0)
        )

        self._zone_data = htd_client.utils.parse_all_zones(response, self._kind)

    def power_on_all_zones(self):
        """
        Power on all zones.
        """

        return self._send_and_validate(
            1,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_ON_ALL_ZONES_COMMAND_CODE
        )

    def power_off_all_zones(self):
        """
        Power off all zones.
        """

        return self._send_and_validate(
            1,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_OFF_ALL_ZONES_COMMAND_CODE
        )

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

        return self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaConstants.SOURCE_COMMAND_OFFSET + source
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

        htd_client.utils.validate_zone(zone)

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.VOLUME_UP_COMMAND
        )

        self._update(response)

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

        htd_client.utils.validate_zone(zone)

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.VOLUME_DOWN_COMMAND
        )

        self._update(response)

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

        htd_client.utils.validate_zone(zone)

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.QUERY_COMMAND_CODE,
            HtdMcaCommands.TOGGLE_MUTE_COMMAND
        )

        self._update(response)

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

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_ON_ZONE_COMMAND_CODE
        )

        self._update(response)

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

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_OFF_ZONE_COMMAND_CODE
        )

        self._update(response)

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

        htd_client.utils.validate_zone(zone)

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BASS_UP_COMMAND
        )

        self._update(response)

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

        htd_client.utils.validate_zone(zone)

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BASS_DOWN_COMMAND
        )

        self._update(response)

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

        htd_client.utils.validate_zone(zone)

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.TREBLE_UP_COMMAND
        )

        self._update(response)

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

        htd_client.utils.validate_zone(zone)

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.TREBLE_DOWN_COMMAND
        )

        self._update(response)

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

        htd_client.utils.validate_zone(zone)

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BALANCE_LEFT_COMMAND
        )

        self._update(response)

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

        htd_client.utils.validate_zone(zone)

        response = self._send_and_validate(
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BALANCE_RIGHT_COMMAND
        )

        self._update(response)
