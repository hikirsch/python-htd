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

import htd_client.utils
from .base_client import BaseClient
from .constants import HtdConstants, HtdDeviceKind, HtdLyncCommands, HtdLyncConstants
from .models import ZoneDetail

_LOGGER = logging.getLogger(__name__)


class HtdLyncClient(BaseClient):
    """
    This is the client for the HTD gateway device. It can communicate with
    the device and send instructions.

    Args:
        ip_address (str): ip address of the gateway to connect to
        port (int): the port number of the gateway to connect to
        retry_attempts(int): if a response is not valid or incorrect,
        how many times should we try again.
        amount of time inbetween commands, in milliseconds
        socket_timeout(int): the amount of time before we will time out from
        the device, in milliseconds
    """

    def __init__(
        self,
        ip_address: str,
        port: int = HtdConstants.DEFAULT_PORT,
        retry_attempts: int = HtdConstants.DEFAULT_RETRY_ATTEMPTS,
        socket_timeout: int = HtdConstants.DEFAULT_SOCKET_TIMEOUT
    ):
        super().__init__(
            HtdDeviceKind.lync,
            ip_address,
            port,
            retry_attempts,
            socket_timeout
        )

    def _parse_command(self, zone, cmd, data):
        if cmd == HtdLyncCommands.KEYPAD_EXISTS_RECEIVE_COMMAND:
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

        elif cmd == HtdLyncCommands.ZONE_STATUS_RECEIVE_COMMAND:
            zone_data = htd_client.utils.parse_zone_lync(zone, data)
            zone_data.enabled = self._zone_data[zone].enabled
            self._zone_data[zone] = zone_data
            _LOGGER.debug("Got new state: %s", zone_data)

        elif cmd == HtdLyncCommands.ZONE_SOURCE_NAME_RECEIVE_COMMAND:
            # remove the extra null bytes
            zone_source_name = str(data[0:11].decode().rstrip('\0')).lower()
            print("ZONE SOURCE NAME NOT USED, zone_source_name = %s" % zone_source_name)

        elif cmd == HtdLyncCommands.ZONE_NAME_RECEIVE_COMMAND:
            name = str(data[0:11].decode().rstrip('\0')).lower()
            self._zone_data[zone].name = name

        elif cmd == HtdLyncCommands.SOURCE_NAME_RECEIVE_COMMAND:
            source = data[11]
            name = str(data[0:10].decode().rstrip('\0')).lower()
            print("GOT SOURCE NAME NOT USED, source = %s, name = %s" % (source, name))
            # self.zone_info[zone]['source_list'][source] = name
            # self.source_info[zone][name] = source
        #
        # elif cmd == HtdLyncCommands.MP3_ON_RECEIVE_COMMAND:
        #     self.mp3_status['state'] = 'on'
        #
        # elif cmd == HtdLyncCommands.MP3_OFF_RECEIVE_COMMAND:
        #     self.mp3_status['state'] = 'off'
        #
        # elif cmd == HtdLyncCommands.MP3_FILE_NAME_RECEIVE_COMMAND:
        #     self.mp3_status['file'] = data.decode().rstrip('\0')
        #
        # elif cmd == HtdLyncCommands.MP3_ARTIST_NAME_RECEIVE_COMMAND:
        #     self.mp3_status['artist'] = data.decode().rstrip('\0')

        elif cmd == HtdLyncCommands.ERROR_RECEIVE_COMMAND:
            _LOGGER.warning("Error response: %d", int(self.__signed_byte(data[0])))

        else:
            _LOGGER.info("Not processing packet type: %s", cmd)

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

    def __signed_byte(self, c):
        unsigned = ord(c.to_bytes(1, byteorder='little'))
        signed = unsigned - 256 if unsigned > 127 else unsigned
        return signed


    def set_volume(self, zone: int, htd_volume: int):
        volume_raw = htd_client.utils.convert_htd_volume_to_raw(htd_volume)

        self._send_and_validate(
            lambda z: z.htd_volume == htd_volume,
            zone,
            HtdLyncCommands.VOLUME_SETTING_CONTROL_COMMAND_CODE,
            volume_raw,
            follow_up=[HtdLyncCommands.COMMON_COMMAND_CODE, HtdLyncCommands.MUTE_OFF_COMMAND_CODE]
        )

    def get_zone_names(self):
        self._send_cmd(
            1,
            HtdLyncCommands.QUERY_ZONE_NAME_COMMAND_CODE,
            1
        )

    def refresh(self):
        """
        Query all zones and return a dict of `ZoneDetail`
-
        Returns:
            dict[int, ZoneDetail]: a dict where the key represents the zone
            number, and the value are the details of the zone
        """


        self._send_cmd(
            0,
            HtdLyncCommands.QUERY_COMMAND_CODE,
            1
        )

    def power_on_all_zones(self):
        """
        Power on all zones.
        """

        return self._send_cmd(
            1,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.POWER_ON_ALL_ZONES_COMMAND_CODE
        )

    def power_off_all_zones(self):
        """
        Power off all zones.
        """

        return self._send_cmd(
            1,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.POWER_OFF_ALL_ZONES_COMMAND_CODE
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
            lambda z: z.source == source,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncConstants.SOURCE_COMMAND_OFFSET + source
        )


    def volume_up(self, zone: int):
        current_zone = self.get_zone(zone)

        new_volume = current_zone.htd_volume + 1

        if new_volume > HtdConstants.MAX_RAW_VOLUME:
            return

        self.set_volume(zone, new_volume)


    def volume_down(self, zone: int):
        current_zone = self.get_zone(zone)

        new_volume = current_zone.htd_volume - 1

        if new_volume < 0:
            return

        self.set_volume(zone, new_volume)

    def mute(self, zone: int):
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

        self._send_and_validate(
            lambda z: z.mute,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.MUTE_ON_COMMAND_CODE
        )

    def unmute(self, zone: int):
        """
        Unmute this zone.

        Args:
            zone (int): the zone

        Raises:
            Exception: zone X is invalid
        """
        htd_client.utils.validate_zone(zone)

        self._send_and_validate(
            lambda z: not z.mute,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.MUTE_OFF_COMMAND_CODE
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


        self._send_and_validate(
            lambda z: z.power,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.POWER_ON_ZONE_COMMAND_CODE
        )

    # def get_firmware_version(self):
    #     cmd = htd_client.utils.get_command(0, HtdLyncCommands.FIRMWARE_VERSION_COMMAND_CODE, bytes([0x00]))
    #     response = htd_client.utils.send_command(cmd, self._ip_address, self._port)
    #     return response

    def power_off(self, zone: int):
        """
        Power off a zone.

        Args:
            zone (int): the zone

        Returns:
            ZoneDetail: a ZoneDetail instance representing the zone requested

        Raisies:
            Exception: zone X is invalid
        """

        htd_client.utils.validate_zone(zone)


        self._send_and_validate(
            lambda z: not z.power,
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.POWER_OFF_ZONE_COMMAND_CODE
        )

    def bass_up(self, zone: int):
        """
        Increase the bass of a zone.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_bass = current_zone.bass + 1
        if new_bass >= HtdLyncConstants.MAX_BASS:
            return

        self.set_bass(zone, new_bass)

    def bass_down(self, zone: int):
        """
        Decrease the bass of a zone.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_bass = current_zone.bass - 1
        if new_bass < HtdLyncConstants.MIN_BASS:
            return

        self.set_bass(zone, new_bass)

    def set_bass(self, zone: int, bass: int):
        htd_client.utils.validate_zone(zone)

        return self._send_cmd(
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.BASS_SETTING_CONTROL_COMMAND_CODE,
            bass
        )

    def treble_up(self, zone: int):
        """
        Increase the treble of a zone.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_treble = current_zone.treble + 1
        if new_treble >= HtdLyncConstants.MAX_TREBLE:
            return

        self.set_treble(zone, new_treble)

    def treble_down(self, zone: int):
        """
        Decrease the treble of a zone.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_treble = current_zone.treble - 1
        if new_treble < HtdLyncConstants.MIN_TREBLE:
            return

        self.set_treble(zone, new_treble)

    def set_treble(self, zone: int, treble: int):
        htd_client.utils.validate_zone(zone)

        return self._send_cmd(
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.TREBLE_SETTING_CONTROL_COMMAND_CODE,
            treble
        )

    def balance_left(self, zone: int):
        """
        Increase the balance of a zone to the left.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_balance = current_zone.balance - 1
        if new_balance < HtdLyncConstants.MIN_BALANCE:
            return

        self.set_balance(zone, new_balance)

    def balance_right(self, zone: int):
        """
        Increase the balance of a zone to the right.

        Args:
             zone (int): the zone
        """

        current_zone = self.get_zone(zone)

        new_balance = current_zone.balance + 1
        if new_balance > HtdLyncConstants.MAX_BALANCE:
            return

        self.set_balance(zone, new_balance)

    def set_balance(self, zone: int, balance: int):
        htd_client.utils.validate_zone(zone)

        return self._send_cmd(
            zone,
            HtdLyncCommands.COMMON_COMMAND_CODE,
            HtdLyncCommands.BALANCE_SETTING_CONTROL_COMMAND_CODE,
            balance
        )
