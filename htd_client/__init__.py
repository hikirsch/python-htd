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
from typing import Tuple

import htd_client.utils
from .base_client import BaseClient
from .constants import HtdCommonCommands, HtdModelInfo, HtdDeviceKind, HtdConstants
from .lync_client import HtdLyncClient
from .mca_client import HtdMcaClient

_LOGGER = logging.getLogger(__name__)


def get_client(network_address: Tuple[str, int] = None, serial_address: str = None) -> BaseClient:
    """
    Create a new client object.

    Args:
        kind (HtdDeviceKind): The type
        network_address (str): The address to communicate with over TCP.
        serial_address (str): The location of the serial port.

    Returns:
        HtdClient: The new client object.
    """

    model_info = get_model_info(serial_address=serial_address, network_address=network_address)

    if model_info["kind"] == HtdDeviceKind.mca:
        return HtdMcaClient(model_info, network_address=network_address, serial_address=serial_address)

    elif model_info["kind"] == HtdDeviceKind.lync:
        return HtdLyncClient(model_info, network_address=network_address, serial_address=serial_address)

    raise ValueError(f"Unknown Device Kind: {model_info["kind"]}")


def get_model_info(serial_address:str=None, network_address: Tuple[str, int] = None) -> HtdModelInfo | None:
    """
    Get the model information from the gateway.

    Returns:
         (str, str): the raw model name from the gateway and the friendly
         name, in a Tuple.
    """

    cmd = htd_client.utils.build_command(
        1, HtdCommonCommands.MODEL_QUERY_COMMAND_CODE, 0
    )

    model_id = htd_client.utils.send_command(cmd, network_address=network_address, serial_address=serial_address)

    for model_name in HtdConstants.SUPPORTED_MODELS:
        model = HtdConstants.SUPPORTED_MODELS[model_name]
        if model_id in model["identifier"]:
            return model

    return None
