
import os

from htd_client import HtdClient


def main():
    client = HtdClient(os.environ['HTD_IP_ADDRESS'])

    print("-- model info ---")

    (model_info, friendly_name) = client.get_model_info()

    print(model_info, friendly_name)

    print("--- single zone ---")

    zone_info = client.query_zone(1)

    print(zone_info)

    print("--- all zones ---")

    zone_infos = client.query_all_zones()

    for i in zone_infos:
        print(zone_infos[i])


# if __name__ == "main":
main()