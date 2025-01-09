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
from typing import Dict

from .base_client import BaseClient
from .constants import HtdConstants, HtdDeviceKind, HtdMcaCommands, HtdMcaConstants
from .models import ZoneDetail

_LOGGER = logging.getLogger(__name__)


class HtdMcaClient(BaseClient):
    _target_volumes: Dict[int, int | None] = None

    def __init__(
        self,
        ip_address: str,
        port: int = HtdConstants.DEFAULT_PORT,
        retry_attempts: int = HtdConstants.DEFAULT_RETRY_ATTEMPTS,
        socket_timeout: int = HtdConstants.DEFAULT_SOCKET_TIMEOUT
    ):
        """
        This is the client for the HTD gateway device. It can communicate with
        the device and send instructions.

        Args:
            ip_address (str): ip address of the gateway to connect to
            port (int): the port number of the gateway to connect to
            retry_attempts(int): if a response is not valid or incorrect, how many times should we try again.
            amount of time inbetween commands, in milliseconds
            socket_timeout(int): the amount of time before we will time out from
            the device, in milliseconds
        """
        self._model_info = HtdConstants.SUPPORTED_MODELS["mca66"]

        # the mca does not support changing the volume directly to the target, therefore we record the target,
        # and everytime we get a zone status update, we'll check to see if there is a new volume being targeted, if so
        # we'll re-run _set_volume to get to the target
        self._target_volumes = {key: None for key in range(1, self._model_info["sources"] + 1)}

        super().__init__(
            HtdDeviceKind.mca,
            ip_address,
            port,
            retry_attempts,
            socket_timeout
        )

        self.subscribe(self._on_zone_update)

    def _on_zone_update(self, zone: int = None):
        if zone is None or zone == 0:
            return

        if self._target_volumes[zone] is not None:
            if self._zone_data[zone].volume == self._target_volumes[zone]:
                self._target_volumes[zone] = None
            else:
                self._set_volume(zone)

    def mute(self, zone: int):
        if self._zone_data[zone].mute:
            return

        self._toggle_mute(zone)

    def unmute(self, zone: int):
        if not self._zone_data[zone].mute:
            return

        self._toggle_mute(zone)

    def has_volume_target(self, zone: int):
        return self._target_volumes[zone] is not None

    def set_volume(self, zone: int, volume: int):
        self._target_volumes[zone] = volume

        return self._set_volume(zone)

    def _set_volume(self, zone: int):
        """
        Resume setting the volume of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        diff = self._target_volumes[zone] - zone_info.volume

        if diff == 0:
            return zone_info

        if diff < 0:
            volume_command = HtdMcaCommands.VOLUME_DOWN_COMMAND
        else:
            volume_command = HtdMcaCommands.VOLUME_UP_COMMAND

        self._send_and_validate(
            lambda z: z.volume != zone_info.volume,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            volume_command
        )

    def refresh(self, zone: int = None):
        """
        Query all zones and return a dict of `ZoneDetail`

        Returns:
            dict[int, ZoneDetail]: a dict where the key represents the zone
            number, and the value are the details of the zone
        """

        refresh_zone = zone if zone is not None else 0
        self.refresh_zone(refresh_zone)

    def refresh_zone(self, zone: int):
        """
        Refresh a specific zone

        Args:
            zone (int): the zone number
        """

        self._send_cmd(
            zone,
            HtdMcaCommands.QUERY_COMMAND_CODE,
            0
        )

    def power_on_all_zones(self):
        """
        Power on all zones.
        """

        return self._send_cmd(
            1,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_ON_ALL_ZONES_COMMAND_CODE
        )

    def power_off_all_zones(self):
        """
        Power off all zones.
        """

        return self._send_cmd(
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
        """
        # htd_client.utils.validate_zone(zone)
        # htd_client.utils.validate_source(source)

        return self._send_and_validate(
            lambda z: z.source == source,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaConstants.SOURCE_COMMAND_OFFSET + source
        )

    def volume_up(self, zone: int):
        """
        Increase the volume of a zone.

        Args:
            zone (int): the zone
        """

        # htd_client.utils.validate_zone(zone)

        zone_info = self._zone_data[zone]

        if zone_info.volume == HtdConstants.MAX_VOLUME:
            return

        self._send_and_validate(
            lambda z: z.volume >= zone_info.volume + 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.VOLUME_UP_COMMAND
        )

    def volume_down(self, zone: int):
        """
        Decrease the volume of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        self._send_and_validate(
            lambda z: z.volume >= zone_info.volume - 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.VOLUME_DOWN_COMMAND
        )

    def _toggle_mute(self, zone: int):
        """
        Toggle the mute state of a zone.

        Args:
            zone (int): the zone
        """

        self._send_and_validate(
            lambda z: z.mute != self._zone_data[zone].mute,
            zone,
            HtdMcaCommands.QUERY_COMMAND_CODE,
            HtdMcaCommands.TOGGLE_MUTE_COMMAND
        )

    def power_on(self, zone: int):
        """
        Power on a zone.

        Args:
            zone (int): the zone
        """

        self._send_and_validate(
            lambda z: z.power,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_ON_ZONE_COMMAND_CODE
        )

    def power_off(self, zone: int):
        """
        Power off a zone.

        Args:
            zone (int): the zone

        """

        self._send_and_validate(
            lambda z: not z.power,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_OFF_ZONE_COMMAND_CODE
        )

    def bass_up(self, zone: int):
        """
        Increase the bass of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_bass = zone_info.bass + 1
        if new_bass < HtdConstants.MAX_BASS:
            return

        self._send_and_validate(
            lambda z: z.bass >= zone_info.bass + 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BASS_UP_COMMAND
        )

    def bass_down(self, zone: int):
        """
        Decrease the bass of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_bass = zone_info.bass - 1
        if new_bass < HtdConstants.MIN_BASS:
            return

        self._send_and_validate(
            lambda z: z.bass <= zone_info.bass - 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BASS_DOWN_COMMAND
        )

    def treble_up(self, zone: int):
        """
        Increase the treble of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_treble = zone_info.treble + 1
        if new_treble < HtdConstants.MAX_TREBLE:
            return

        self._send_and_validate(
            lambda z: z.treble >= zone_info.treble + 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.TREBLE_UP_COMMAND
        )

    def treble_down(self, zone: int):
        """
        Decrease the treble of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_treble = zone_info.treble - 1
        if new_treble < HtdConstants.MIN_TREBLE:
            return

        self._send_and_validate(
            lambda z: z.treble <= zone_info.treble - 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.TREBLE_DOWN_COMMAND
        )

    def balance_left(self, zone: int):
        """
        Increase the balance toward the left for a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_balance = zone_info.balance - 1
        if new_balance < HtdConstants.MIN_BALANCE:
            return

        self._send_and_validate(
            lambda z: z.balance <= zone_info.balance - 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BALANCE_LEFT_COMMAND
        )

    def balance_right(self, zone: int):
        """
        Increase the balance toward the right for a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_balance = zone_info.balance + 1
        if new_balance > HtdConstants.MAX_BALANCE:
            return

        self._send_and_validate(
            lambda z: z.balance >= zone_info.balance + 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BALANCE_RIGHT_COMMAND
        )

    # def get_source_names(self):
    #     """
    #     Query a zone and return `ZoneDetail`
    #
    #     Returns:
    #         Dict[int, str]: a dictionary where each zone has a string value
    #         of the source name
    #     """
    #
    #     self._send_cmd(
    #         0,
    #         HtdMcaCommands.QUERY_SOURCE_NAME_COMMAND_CODE,
    #         0
    #     )
    #
    # def set_source_name(self, source: int, name: str):
    #     """
    #     Query a zone and return `ZoneDetail`
    #
    #     Args:
    #         source (int): the source
    #         name (str): the name of the source (max length of 7)
    #
    #     Returns:
    #         ZoneDetail: a ZoneDetail instance representing the zone requested
    #
    #     Raises:
    #         Exception: zone X is invalid
    #     """
    #
    #     # htd_client.utils.validate_zone(zone)
    #
    #     extra_data = bytearray(
    #         [ord(char) for char in name] + [0] * (7 - len(name)) + [0x00]
    #     )
    #
    #     self._send_cmd(
    #         0,
    #         HtdMcaCommands.SET_SOURCE_NAME_COMMAND_CODE,
    #         source,
    #         extra_data
    #     )
    #
    # def get_zone_names(self):
    #     pass
