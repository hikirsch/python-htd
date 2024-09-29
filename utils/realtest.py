
from htd_client import HtdClient, NotSupportedError

def main_lync():
    client = HtdClient('127.0.0.1')
    # client = HtdClient('65.31.204.15', port=9001)
    test_client(client)

def main_mca():
    client = HtdClient('192.168.200.145')
    test_client(client)

def test_client(client):
    model_info = client.get_model_info()

    print("Model Info")
    print(f"- {model_info}")

    print("All Zones")
    for i in range(1, model_info["zones"] + 1):
        print(f"- {client.get_zone(i)}")

    print("Testing zone actions")
    test_command(client.refresh, "refresh")
    test_command(client.power_on_all_zones, "power_on_all_zones")
    test_command(client.power_off_all_zones, "power_off_all_zones")
    test_command(lambda: client.set_source(1, 5), "set_source")

    test_zone_command(client.volume_up, 1, "volume_up")
    test_zone_command(client.volume_down, 1, "volume_down")
    test_zone_command(client.toggle_mute, 1, "toggle_mute")
    test_zone_command(client.power_on, 1, "power_on")
    test_zone_command(client.power_off, 1, "power_off")
    test_zone_command(client.bass_up, 1, "bass_up")
    test_zone_command(client.bass_down, 1, "bass_down")
    test_zone_command(client.treble_up, 1, "treble_up")
    test_zone_command(client.treble_down, 1, "treble_down")
    test_zone_command(client.balance_left, 1, "balance_left")
    test_zone_command(client.balance_right, 1, "balance_right")


def test_command(method, message):
    extras = 30 - len(message)
    dots = "." * extras

    print(f"- {message} {dots} ", end='')

    try:
        method()
        print('OK')
    except NotSupportedError:
        print("NOT SUPPORTED")
    except Exception as e:
        print("FAILED")
        print(e)


def test_zone_command(method, zone, message):
    test_command(lambda: method(zone), f"{message} - Zone {zone}")


# if __name__ == "main":
main_mca()
main_lync()
