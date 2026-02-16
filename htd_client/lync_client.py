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
from typing import Tuple

import htd_client.utils
from .base_client import BaseClient
from .constants import HtdConstants, HtdLyncCommands, HtdLyncConstants, HtdModelInfo

_LOGGER = logging.getLogger(__name__)


class HtdLyncClient(BaseClient):
    """
    This is the client for the HTD gateway device. It can communicate with
    the device and send instructions.

    Args:
        model_info (HtdModelInfo): the model info of the device
        serial_address (str): serial address of the gateway
        network_address (Tuple[str, int]): ip address and port of the gateway
        retry_attempts(int): if a response is not valid or incorrect,
        socket_timeout(int): the amount of time before we will time out from the device, in milliseconds
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        model_info: HtdModelInfo,
        serial_address: str = None,
        network_address: Tuple[str, int] = None,
        command_retry_timeout: int = HtdConstants.DEFAULT_COMMAND_RETRY_TIMEOUT,
        retry_attempts: int = HtdConstants.DEFAULT_RETRY_ATTEMPTS,
        socket_timeout: int = HtdConstants.DEFAULT_SOCKET_TIMEOUT,
    ):

        super().__init__(
            loop,
            model_info,
            serial_address=serial_address,
            network_address=network_address,
            command_retry_timeout=command_retry_timeout,
            retry_attempts=retry_attempts,
            socket_timeout=socket_timeout,
        )

    async def async_set_volume(self, zone: int, volume: int):
        """
        Set the volume of a zone.

        Args:
            zone (int): the zone
            volume (int): the volume to set as an HTD value, usually between 0 and 60 (HtdConstants.MAX_VOLUME)
        """

        volume_raw = htd_client.utils.convert_volume_to_raw(volume)

        await self._async_send_and_validate(
            lambda z: z.volume == volume,
            zone,
            HtdLyncCommands.VOLUME_SETTING_CONTROL_COMMAND_CODE,
            volume_raw,
            follow_up=(HtdLyncCommands.COMMON_COMMAND_CODE, HtdLyncCommands.MUTE_OFF_COMMAND_CODE)
        )


    async def refresh(self, zone: int = None):
        """
        Refresh a zone or all zones.

        Args:
            zone (int): the zone to refresh, or None to refresh all zones
        """
        await self._send_cmd(
            zone if zone is not None else 0,
            HtdLyncCommands.QUERY_COMMAND_CODE,
            1
        )

    async def power_on_all_zones(self):
        """
        Power on all zones.
        """

        return await self._send_cmd(
            1,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.POWER_ON_ALL_ZONES_COMMAND_CODE
        )

    async def power_off_all_zones(self):
        """
        Power off all zones.
        """

        return await self._send_cmd(
            1,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.POWER_OFF_ALL_ZONES_COMMAND_CODE
        )

    async def async_set_source(self, zone: int, source: int):
        """
        Set the source of a zone.

        Args:
            zone (int): the zone
            source (int): the source to set
        """
        if source == self.model["sources"]:
            source_data = HtdLyncConstants.INTERCOM_SOURCE_DATA
        else:
            source_offset = HtdLyncConstants.SOURCE_13_HIGHER_COMMAND_OFFSET if source > 12 else HtdLyncConstants.SOURCE_COMMAND_OFFSET
            source_data = source + source_offset

        return await self._async_send_and_validate(
            lambda z: z.source == source,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            source_data,
        )

    async def async_volume_up(self, zone: int):
        """
        Increase the volume of a zone.

        Args:
            zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_volume = current_zone.volume + 1

        if new_volume > HtdConstants.MAX_VOLUME:
            return

        await self.async_set_volume(zone, new_volume)

    async def async_volume_down(self, zone: int):
        """
        Decrease the volume of a zone.

        Args:
            zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_volume = current_zone.volume - 1

        if new_volume < 0:
            return

        await self.async_set_volume(zone, new_volume)

    async def async_mute(self, zone: int):
        """
        Toggle the mute state of a zone.

        Args:
            zone (int): the zone
        """

        await self._async_send_and_validate(
            lambda z: z.mute,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.MUTE_ON_COMMAND_CODE
        )

    async def async_unmute(self, zone: int):
        """
        Unmute this zone.

        Args:
            zone (int): the zone
        """

        await self._async_send_and_validate(
            lambda z: not z.mute,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.MUTE_OFF_COMMAND_CODE
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
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.POWER_ON_ZONE_COMMAND_CODE
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
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.POWER_OFF_ZONE_COMMAND_CODE
        )

    async def async_bass_up(self, zone: int):
        """
        Increase the bass of a zone.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_bass = current_zone.bass + 1
        if new_bass > HtdConstants.LYNC_MAX_BASS:
            return

        await self.async_set_bass(zone, new_bass)

    async def async_bass_down(self, zone: int):
        """
        Decrease the bass of a zone.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_bass = current_zone.bass - 1
        if new_bass < HtdConstants.LYNC_MIN_BASS:
            return

        await self.async_set_bass(zone, new_bass)


    async def async_set_bass(self, zone: int, bass: int):
        """
        Set the bass of a zone.

        Args:
            zone (int): the zone
            bass (int): the bass value to set
        """

        logging.debug(f"Setting bass for zone {zone} to {bass}")

        zone_info = self.get_zone(zone)

        if zone_info.bass == bass:
            return

        encoded_bass = bass & 0xFF

        await self._send_cmd(
            zone,
            HtdLyncCommands.BASS_SETTING_CONTROL_COMMAND_CODE,
            encoded_bass
        )

        await self._async_send_and_validate(
            lambda z: z.bass == bass,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncConstants.STATUS_REFRESH_CODE
        )

    async def async_treble_up(self, zone: int):
        """
        Increase the treble of a zone.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_treble = current_zone.treble + 1
        if new_treble > HtdConstants.LYNC_MAX_TREBLE:
            return

        await self.async_set_treble(zone, new_treble)

    async def async_treble_down(self, zone: int):
        """
        Decrease the treble of a zone.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_treble = current_zone.treble - 1
        if new_treble < HtdConstants.LYNC_MIN_TREBLE:
            return

        await self.async_set_treble(zone, new_treble)

    async def async_set_treble(self, zone: int, treble: int):
        """
        Set the treble of a zone.

        Args:
            zone (int): the zone
            treble (int): the treble value to set
        """

        zone_info = self.get_zone(zone)

        if treble == zone_info.treble:
            return

        encoded_treble = treble & 0xFF

        await self._send_cmd(
            zone,
            HtdLyncCommands.TREBLE_SETTING_CONTROL_COMMAND_CODE,
            encoded_treble
        )

        await self._async_send_and_validate(
            lambda z: z.treble == treble,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncConstants.STATUS_REFRESH_CODE
        )

    async def async_balance_left(self, zone: int):
        """
        Increase the balance of a zone to the left.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_balance = current_zone.balance - 1
        if new_balance < HtdConstants.LYNC_MIN_BALANCE:
            return

        await self.async_set_balance(zone, new_balance)

    async def async_balance_right(self, zone: int):
        """
        Increase the balance of a zone to the right.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_balance = current_zone.balance + 1
        if new_balance > HtdConstants.LYNC_MAX_BALANCE:
            return

        await self.async_set_balance(zone, new_balance)

    async def async_set_balance(self, zone: int, balance: int):
        """
        Set the balance of a zone.

        Args:
            zone (int): the zone
            balance (int): the balance value to set
        """

        current_zone = self.get_zone(zone)

        if balance == current_zone.balance:
            return

        encoded_balance = balance & 0xFF

        await self._send_cmd(
            zone,
            HtdLyncCommands.BALANCE_SETTING_CONTROL_COMMAND_CODE,
            encoded_balance
        )

        await self._async_send_and_validate(
            lambda z: z.balance == balance,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncConstants.STATUS_REFRESH_CODE
        )

    # def query_zone_name(self, zone: int) -> str:
    #     """
    #     Query a zone and return `ZoneDetail`
    #
    #     Args:
    #         zone (int): the zone
    #
    #     Returns:
    #         ZoneDetail: a ZoneDetail instance representing the zone requested
    #
    #     Raises:
    #         Exception: zone X is invalid
    #     """
    #
    #     # htd_client.utils.validate_zone(zo+ne)
    #
    #     self._send_and_validate(
    #         zone,
    #         HtdLyncCommands.QUERY_ZONE_NAME_COMMAND_CODE,
    #         0
    #     )

    # def query_source_name(self, source: int, zone: int) -> str:
    #     source_offset = source - 1
    #
    #     self._send_and_validate(
    #         zone, HtdLyncCommands.QUERY_SOURCE_NAME_COMMAND_CODE, source_offset
    #     )
    #
    #     source_name_bytes = response[4:14].strip(b'\x00')
    #     source_name = htd_client.utils.decode_response(source_name_bytes)
    #
    #     return source_name

    # def set_source_name(self, source: int, zone: int, name: str):
    #     """
    #     Query a zone and return `ZoneDetail`
    #
    #     Args:
    #         source (int): the source
    #         zone: (int): the zone
    #         name (str): the name of the source (max length of 7)
    #
    #     Returns:
    #         bytes: a ZoneDetail instance representing the zone requested
    #
    #     Raises:
    #         Exception: zone X is invalid
    #     """
    #
    #     # htd_client.utils.validate_zone(zone)
    #
    #     extra_data = bytes(
    #         [ord(char) for char in name] + [0] * (11 - len(name))
    #     )
    #
    #     self._send_and_validate(
    #         zone,
    #         HtdLyncCommands.SET_SOURCE_NAME_COMMAND_CODE,
    #         source)
    #         extra_data
    #     )
    #
    # def get_zone_names(self):
    #     self._send_cmd(
    #         1,
    #         HtdLyncCommands.QUERY_ZONE_NAME_COMMAND_CODE,
    #         1
    #     )
    # def set_zone_name(self, zone: int, name: str):
    #     """
    #     Query a zone and return `ZoneDetail`
    #
    #     Args:
    #         zone: (int): the zone
    #         name (str): the name of the source (max length of 7)
    #
    #     Returns:
    #         bytes: a ZoneDetail instance representing the zone requested
    #
    #     Raises:
    #         Exception: zone X is invalid
    #     """
    #
    #     # htd_client.utils.validate_zone(zone)
    #
    #     extra_data = bytes(
    #         [ord(char) for char in name] + [0] * (11 - len(name))
    #     )
    #
    #     self._send_and_validate(
    #         zone,
    #         HtdLyncCommands.SET_ZONE_NAME_COMMAND_CODE,
    #         0)
    #         extra_data
    #     )
