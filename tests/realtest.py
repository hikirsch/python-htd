import logging
import time

from htd_client import BaseClient, get_client, HtdDeviceKind, get_model_info

MCA66_IP = ""
LYNC_12_TEST = ""

def reset_to_normal(power=True):
    client = get_client(HtdDeviceKind.mca, MCA66_IP, 10006)

    delay = 25 / 1000
    attempts_until_refresh = 20
    zone_count = 6

    print("Resetting to normal state")
    if power:
        print(f"Power on -")
    else:
        print(f"Power off -")
    for i in range(1, zone_count + 1):
        attempt = 0
        print(f"zone {i}", end='')
        while client.get_zone(i).power != power:
            print(".", end='')
            attempt += 1
            if attempt % attempts_until_refresh == 0:
                client.refresh()
            if power:
                client.power_on(i)
            else:
                client.power_off(i)
            time.sleep(delay)

        print("")

    if not power:
        return

    print(f"Unmute -")
    for i in range(1, zone_count + 1):
        attempt = 0
        print(f"zone {i}", end='')
        while not client.get_zone(i).power:
            print(".", end='')
            attempt += 1
            if attempt % attempts_until_refresh == 0:
                client.refresh()
            client.unmute(i)
            # sleep(delay)
        print("")

def countdown(seconds):
    while seconds > 0:
        print(f"{seconds} ... ", end='')
        time.sleep(1)
        seconds -= 1

def identify_test():
    model_info = get_model_info(MCA66_IP)
    print(model_info)
    model_info = get_model_info(LYNC_12_TEST, 9001)
    print(model_info)
    client_mca = get_client(HtdDeviceKind.mca, MCA66_IP, port=10006)
    client_lync = get_client(HtdDeviceKind.lync, LYNC_12_TEST, 9001)
    # print(response)

    # client.power_off(6)

    # client.get_zone_names()

    #
    # zone_count = client.get_zone_count()
    # for i in range(zone_count):
    #     client.set_source(1 + i, 7)

    countdown(1)

    def run_test(description: str, client: BaseClient):
        print("")
        print(f"Showing all zones for {description}")
        print("")
        zone_count = client.get_zone_count()
        for i in range(1, zone_count + 1):
            print(client.get_zone(i))

        # client.volume_test()
        #
        # print("")
        # print("Showing all zones")
        # print("")
        # zone_count = client.get_zone_count()
        # for i in range(1, zone_count + 1):
        #     print(client.get_zone(i))

    run_test("MCA", client_mca)
    run_test("LYNC", client_lync)


    # print("")
    # test_zone_command(client.power_off, 1, "power_off")
    # test_zone_command(client.power_on, 1, "power_on")
    # # test_zone_command(client.volume_up, 1, "volume_up")
    # # test_zone_command(client.volume_down, 1, "volume_down")
    # test_command(lambda: client.set_volume(1, 50), "set_volume")
    # while client.get_zone(1).htd_volume != 50:
    #     pass
    #
    # test_zone_command(client.set_volume, 10, "set_volume")
    #
    # while client.get_zone(1).htd_volume != 10:
    #     pass
    #
    # test_zone_command(client.mute, 1, "mute")
    # test_zone_command(client.unmute, 1, "unmute")
    # test_client(client)
    # model_info = client.get_model_info()
    # client.set_zone_name_lync(1, "Zone 1")
    # client.set_source_name_lync(1, 0, 'PY_YAY_1')
    # client.set_source_name_lync(2, 1, 'SRC 2')

    # for i in range(1, model_info["zones"] + 1):
        # test_zone_command(client.query_zone_name, i, "query_zone_name")
    #
    # for zone in range(1, model_info["zones"] + 1):
    #     for source in range(1, model_info["sources"] + 1):
    #         test_source_command(client.query_source_name_lync, source, zone, "query_source_name_lync")


# delay = 25 / 1000
# attempts_until_refresh = 5


def device_test():
    client = get_client(HtdDeviceKind.lync, MCA66_IP, 10006)
    # client = get_client(HtdDeviceKind.lync, "69.76.150.235", 9001)
    if client._connected:
        print("Connected ")
        while not client._is_ready:
            print(".", end='')
            time.sleep(.25)

    print("")
    print("Loaded")
    # countdown(3)

    zone_count = client.get_zone_count()
    for zone in range(1, zone_count + 1):
        target_zone_info = client.get_zone(zone)
        volume = target_zone_info.htd_volume
        target_volume = 20 if volume == 15 else 15
        print(f"Setting zone {zone} to volume {target_volume}")
        client.power_on(zone)
        client.set_volume(zone, target_volume)

    test_zone_command(client.power_off, 1, "power_off")
    test_zone_command(client.power_on, 1, "power_on")
    test_zone_command(client.volume_up, 1, "volume_up")
    test_zone_command(client.volume_down, 1, "volume_down")
    test_zone_command(client.unmute, 1, "unmute")
    test_zone_command(client.unmute, 1, "mute")
    test_zone_command(client.unmute, 1, "unmute")
    test_zone_command(client.toggle_mute, 1, "toggle_mute")
    test_zone_command(client.toggle_mute, 1, "toggle_mute")
    # print(client.get_zone(1))
    # print("FIRMWARE: %s" % client.get_firmware_version())
    # if not client.get_zone(1).power:
    #     print("zone 1 is off, turning it on")
    #     client.power_on(1)
    #     print("")
    #     print("zone 1 is now on")
    # else:
    #     print("zone 1 is on, turning it off")
    #     client.power_off(1)
    #     print("")
    #     print("zone 1 is now off")

    # response = get_model_info(REMOTE_IP, port=9001)
    # print(response)
    # response = get_model_info('192.168.200.145', port=10006)
    # print(response)
    # # test_client(client)

    # client = get_client(HtdDeviceKind.mca, MY_IP, 10006)

    # print("")
    # print("Showing all zones")
    # print("")
    zone_count = client.get_zone_count()
    for i in range(1, zone_count + 1):
        print(client.get_zone(i))

    print("")
    print("Testing zone actions")
    print("")

    # print(f"Power on -")
    # for i in range(1, zone_count + 1):
    #     attempt = 0
    #     print(f"zone {i}", end = '')
    #     while not client.get_zone(i).power:
    #         print(".", end='')
    #         attempt += 1
    #         if attempt % attempts_until_refresh == 0:
    #             client.refresh()
    #         client.power_on(i)
    #         # sleep(delay)
    #
    #     print("")
    #
    # print(f"Unmute -")
    # for i in range(1, zone_count + 1):
    #     attempt = 0
    #     print(f"zone {i} - ", end='')
    #
    #     while client.get_zone(i).mute:
    #         print(".", end='')
    #         attempt += 1
    #         if attempt % attempts_until_refresh == 0:
    #             client.refresh()
    #             print("R", end='')
    #         client.unmute(i)
    #         # sleep(delay)
    #
    #     print("")
    #
    # print(f"Mute -")
    # for i in range(1, zone_count + 1):
    #     attempt = 0
    #     print(f"zone {i} - ", end='')
    #     while not client.get_zone(i).mute:
    #         print(".", end='')
    #         attempt += 1
    #         if attempt % attempts_until_refresh == 0:
    #             client.refresh()
    #             print("R", end='')
    #         client.mute(i)
    #         # sleep(delay)
    #     print("")
    #
    # print(f"Unmute")
    # for i in range(1, zone_count + 1):
    #     attempt = 0
    #     print(f"zone {i} - ", end='')
    #     while client.get_zone(i).mute:
    #         print(".", end='')
    #         attempt += 1
    #         if attempt % attempts_until_refresh == 0:
    #             client.refresh()
    #             print("R", end='')
    #         client.unmute(i)
    #         # sleep(delay)
    #     print("")
    #
    # print(f"Power off -")
    # for i in range(1, zone_count + 1):
    #     attempt = 0
    #     print(f"zone {i} - ", end='')
    #     while client.get_zone(i).power:
    #         print(".", end='')
    #         attempt += 1
    #         if attempt % attempts_until_refresh == 0:
    #             client.refresh()
    #             print("R", end='')
    #         client.power_off(i)
    #         # sleep(delay)
    #     print("")
    #
    # reset_to_normal()


def test_client(client: BaseClient):
    zone_count = client.get_zone_count()
    for i in range(1, zone_count + 1):
        print(f"- {client.get_zone(i)}")

    # print("Testing zone actions")
    # test_command(client.refresh, "refresh")
    # test_command(client.power_off_all_zones, "power_off_all_zones")
    # sleep(10)
    # test_command(client.power_on_all_zones, "power_on_all_zones")
    # sleep(10)
    # test_command(lambda: client.set_source(1, 4), "set_source")
    if not client.get_zone(1).power:
        test_zone_command(client.power_on, 1, "power_on")

    test_zone_command(client.power_off, 1, "power_off")
    test_zone_command(client.power_on, 1, "power_on")
    test_zone_command(client.volume_up, 1, "volume_up")
    test_zone_command(client.volume_down, 1, "volume_down")
    test_zone_command(client.toggle_mute, 1, "toggle_mute")
    # test_zone_command(client.bass_up, 1, "bass_up")
    # test_zone_command(client.bass_down, 1, "bass_down")
    # test_zone_command(client.treble_up, 1, "treble_up")
    # test_zone_command(client.treble_down, 1, "treble_down")
    # test_zone_command(client.balance_left, 1, "balance_left")
    # test_zone_command(client.balance_right, 1, "balance_right")


def test_command(method, message):
    extras = 30 - len(message)
    dots = "." * extras

    print(f"- {message} {dots} ", end='')

    try:
        response = method()

        if response is None:
            print("OK")
        else:
            if isinstance(response, bytes):
                print(f"OK - Response - {chunkize([byte for byte in response], 14)}")
            else:
                print(f"OK - Response - {response}")

    except Exception as e:
        print("FAILED")
        print(e)

    # sleep(.1)


def test_zone_command(method, zone, message):
    test_command(lambda: method(zone), f"{message} - Zone {zone}")


def test_source_command(method, source, zone, message):
    test_command(lambda: method(source, zone), f"{message} - Zone {zone}")


def chunkize(data, chunk_size):
    """
    Breaks a list or byte array into chunks of specified size.

    Parameters:
    data (list or bytes): The data to be chunked.
    chunk_size (int): The size of each chunk.

    Returns:
    list: A list containing the chunks.
    """
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    # reset_to_normal()
    # device_test()
    identify_test()
