import asyncio
import logging

from htd_client import BaseClient, async_get_client, async_get_model_info

# ASK_SERIAL = "/dev/virtual_ttyUSB0"
MCA_NETWORK = ("ajk.ivillage.cc", 10006)
# LYNC_12_TEST = ("192.168.200.146", 10006)
# LYNC_12_TEST = ("69.76.150.235", 9001)

async def async_identify_test():
    # ask_identify = await async_get_model_info(network_address=ASK_NETWORK)
    # print(ask_identify)
    # ask2_identify = await async_get_model_info(network_address=ASK_NETWORK2)
    # print(ask2_identify)
    # lync_model = await async_get_model_info(network_address=LYNC_12_TEST)
    # print(lync_model)
    # ask_serial = await async_get_model_info(serial_address=ASK_SERIAL)
    # print(ask_serial)
    # print("STARTING")
    # print("done")
    # ask_network = await async_get_client(network_address=ASK_NETWORK)
    mca_network = await async_get_client(network_address=MCA_NETWORK)
    # client_lync = await async_get_client(network_address=LYNC_12_TEST)
    # client_serial = await async_get_client(serial_address=ASK_SERIAL)

    # await client_lync.async_wait_until_ready()
    await mca_network.async_wait_until_ready()

    def show_zone_details(client: BaseClient, zone: int = None):
        if zone is not None and zone != 0:
            print(f"[{client.model["name"]}] {client.get_zone(zone)}")
            return

        zone_count = client.get_zone_count()
        for i in range(1, zone_count + 1):
            print(f"[{client.model["name"]}] {client.get_zone(i)}")

    async def setup_listener(client: BaseClient):
        await client.async_subscribe(
            lambda x: show_zone_details(client, x)
        )

    # await setup_listener(client_lync)
    await setup_listener(mca_network)

    # while not client_lync.ready:
    #     await asyncio.sleep(0)
    #

    while not mca_network.ready:
        await asyncio.sleep(0)

    await mca_network.async_set_volume(3, 10)
    #
    # async def countdown(n):
    #     while n > 0:
    #         print(f"{n} ... ")
    #         n -= 1
    #         await asyncio.sleep(1)
    #
    # while not ask_network.ready:
    #     await asyncio.sleep(0)

    # await ask_network2.async_set_source(1, 13)
    # await client_lync.async_subscribe(
    #     lambda x: show_zone_details(client_lync, x)
    # )

    #
    #     # client.volume_test()
    #     #
    #     # print("")
    #     # print("Showing all zones")
    #     # print("")
    #     # zone_count = client.get_zone_count()
    #     # for i in range(1, zone_count + 1):
    #     #     print(client.get_zone(i))
    #
    # show_zone_details("SERIAL %s" % client_serial._model_info["kind"], client_serial)
    # show_zone_details("NETWORK %s" % ask_network.model["kind"], ask_network)
    # show_zone_details("LYNC %s" % client_lync._model_info["kind"], client_lync)


    # show_zone_details("NETWORK %s" % ask_network.model["kind"], ask_network, 0)

    # print("sleeping for 10 seconds")
    # time.sleep(1)
    # print("sleeping for 10 more seconds")
    # time.sleep(1)
    # print("sleeping for last 10 more seconds")
    # time.sleep(1)

    # if ask_network.get_zone(1).power:
    #     ask_network.power_off(1)
    # else:
    #     ask_network.power_on(1)l

    # while ask_network.connected:
    #     pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # reset_to_normal()
    # device_test()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(async_identify_test())
    loop.run_forever()
