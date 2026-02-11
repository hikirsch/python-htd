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
from typing import Dict, Tuple

from .base_client import BaseClient
from .constants import HtdConstants, HtdMcaCommands, HtdMcaConstants, HtdModelInfo
from .models import ZoneDetail

_LOGGER = logging.getLogger(__name__)


class HtdMcaClient(BaseClient):
    _target_volumes: Dict[int, int | None] = None
    _subscribed: bool = None

    def __init__(
        self,
        loop: asyncio.EventLoop,
        model_info: HtdModelInfo,
        network_address: Tuple[str, int] = None,
        serial_address: str = None,
        command_retry_timeout: int = HtdConstants.DEFAULT_COMMAND_RETRY_TIMEOUT,
        retry_attempts: int = HtdConstants.DEFAULT_RETRY_ATTEMPTS,
        socket_timeout: int = HtdConstants.DEFAULT_SOCKET_TIMEOUT,
    ):
        """
        This is the client for the HTD gateway device. It can communicate with
        the device and send instructions.

        Args:
            loop (asyncio.AbstractEventLoop): The event loop to use
            model_info (HtdModelInfo): the model information of the device
            network_address (Tuple[str, int]): ip address of the gateway to connect to
            serial_address (str): the port number of the gateway to connect to
            retry_attempts(int): if a response is not valid or incorrect, how many times should we try again.
            amount of time inbetween commands, in milliseconds
            socket_timeout(int): the amount of time before we will time out from
            the device, in milliseconds
        """
        super().__init__(
            loop,
            model_info,
            serial_address=serial_address,
            network_address=network_address,
            command_retry_timeout=command_retry_timeout,
            retry_attempts=retry_attempts,
            socket_timeout=socket_timeout,
        )

        # the mca does not support changing the volume directly to the target, therefore we record the target,
        # and everytime we get a zone status update, we'll check to see if there is a new volume being targeted, if so
        # we'll re-run _set_volume to get to the target
        self._subscribed = False
        self._target_volumes = {key: None for key in range(1, self._model_info["sources"] + 1)}


    async def async_connect(self):
        if not self._subscribed:
            await self.async_subscribe(self._on_zone_update)
            self._subscribed = True

        await super().async_connect()


    def _on_zone_update(self, zone: int = None):
        if zone is None or zone == 0:
            return

        if self._target_volumes[zone] is not None:
            if self._zone_data[zone].volume == self._target_volumes[zone]:
                self._target_volumes[zone] = None
            else:
                asyncio.run_coroutine_threadsafe(self._async_set_volume(zone), self._loop)

    async def async_mute(self, zone: int):
        if self._zone_data[zone].mute:
            return

        await self._async_toggle_mute(zone)

    async def async_unmute(self, zone: int):
        if not self._zone_data[zone].mute:
            return

        await self._async_toggle_mute(zone)

    def has_volume_target(self, zone: int):
        return self._target_volumes[zone] is not None

    async def async_set_volume(self, zone: int, volume: int):
        existing = False

        if self._target_volumes[zone] is not None:
            existing = True

        self._target_volumes[zone] = volume

        if existing:
            return

        zone_info = self._zone_data[zone]

        if not zone_info.power:
            await self.async_power_on(zone)

        return await self._async_set_volume(zone)

    async def _async_set_volume(self, zone: int):
        """
        Resume setting the volume of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        if not zone_info.power:
            self._target_volumes[zone] = None
            return

        diff = self._target_volumes[zone] - zone_info.volume

        if diff == 0:
            return

        if diff < 0:
            volume_command = HtdMcaCommands.VOLUME_DOWN_COMMAND
        else:
            volume_command = HtdMcaCommands.VOLUME_UP_COMMAND

        await self._async_send_and_validate(
            lambda z: z.volume != zone_info.volume,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            volume_command
        )

    async def refresh(self, zone: int = None):
        """
        Query all zones and return a dict of `ZoneDetail`

        Returns:
            dict[int, ZoneDetail]: a dict where the key represents the zone
            number, and the value are the details of the zone
        """

        refresh_zone = zone if zone is not None else 0
        await self.refresh_zone(refresh_zone)

    async def refresh_zone(self, zone: int):
        """
        Refresh a specific zone

        Args:
            zone (int): the zone number
        """

        await self._send_cmd(
            zone,
            HtdMcaCommands.QUERY_COMMAND_CODE,
            0
        )

    async def power_on_all_zones(self):
        """
        Power on all zones.
        """

        return await self._send_cmd(
            1,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_ON_ALL_ZONES_COMMAND_CODE
        )

    async def power_off_all_zones(self):
        """
        Power off all zones.
        """

        return await self._send_cmd(
            1,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_OFF_ALL_ZONES_COMMAND_CODE
        )

    async def async_set_source(self, zone: int, source: int):
        """
        Set the source of a zone.

        Args:
            zone (int): the zone
            source (int): the source to set
        """

        return await self._async_send_and_validate(
            lambda z: z.source == source,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaConstants.SOURCE_COMMAND_OFFSET + source
        )

    async def async_volume_up(self, zone: int):
        """
        Increase the volume of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        if zone_info.volume == HtdConstants.MAX_VOLUME:
            return

        await self._async_send_and_validate(
            lambda z: z.volume >= zone_info.volume + 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.VOLUME_UP_COMMAND
        )

    async def async_volume_down(self, zone: int):
        """
        Decrease the volume of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        await self._async_send_and_validate(
            lambda z: z.volume >= zone_info.volume - 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.VOLUME_DOWN_COMMAND
        )

    async def _async_toggle_mute(self, zone: int):
        """
        Toggle the mute state of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        await self._async_send_and_validate(
            lambda z: zone_info.mute != z.mute,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.TOGGLE_MUTE_COMMAND
        )

    async def async_power_on(self, zone: int):
        """
        Power on a zone.

        Args:
            zone (int): the zone
        """

        await self._async_send_and_validate(
            lambda z: z.power,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_ON_ZONE_COMMAND_CODE
        )

    async def async_power_off(self, zone: int):
        """
        Power off a zone.

        Args:
            zone (int): the zone

        """

        await self._async_send_and_validate(
            lambda z: not z.power,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.POWER_OFF_ZONE_COMMAND_CODE
        )

    async def async_bass_up(self, zone: int):
        """
        Increase the bass of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_bass = zone_info.bass + 1
        if new_bass < HtdConstants.MAX_BASS:
            return

        await self._async_send_and_validate(
            lambda z: z.bass >= zone_info.bass + 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BASS_UP_COMMAND
        )

    async def async_bass_down(self, zone: int):
        """
        Decrease the bass of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_bass = zone_info.bass - 1
        if new_bass < HtdConstants.MIN_BASS:
            return

        await self._async_send_and_validate(
            lambda z: z.bass <= zone_info.bass - 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BASS_DOWN_COMMAND
        )

    async def async_treble_up(self, zone: int):
        """
        Increase the treble of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_treble = zone_info.treble + 1
        if new_treble < HtdConstants.MAX_TREBLE:
            return

        await self._async_send_and_validate(
            lambda z: z.treble >= zone_info.treble + 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.TREBLE_UP_COMMAND
        )

    async def async_treble_down(self, zone: int):
        """
        Decrease the treble of a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_treble = zone_info.treble - 1
        if new_treble < HtdConstants.MIN_TREBLE:
            return

        await self._async_send_and_validate(
            lambda z: z.treble <= zone_info.treble - 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.TREBLE_DOWN_COMMAND
        )

    async def async_balance_left(self, zone: int):
        """
        Increase the balance toward the left for a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_balance = zone_info.balance - 1
        if new_balance < HtdConstants.MIN_BALANCE:
            return

        await self._async_send_and_validate(
            lambda z: z.balance <= zone_info.balance - 1,
            zone,
            HtdMcaCommands.COMMON_COMMAND_CODE,
            HtdMcaCommands.BALANCE_LEFT_COMMAND
        )

    async def async_balance_right(self, zone: int):
        """
        Increase the balance toward the right for a zone.

        Args:
            zone (int): the zone
        """

        zone_info = self._zone_data[zone]

        new_balance = zone_info.balance + 1
        if new_balance > HtdConstants.MAX_BALANCE:
            return

        await self._async_send_and_validate(
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
