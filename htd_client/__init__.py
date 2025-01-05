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
from .constants import HtdCommonCommands, HtdModelInfo, HtdDeviceKind, HtdConstants
from .lync_client import HtdLyncClient
from .mca_client import HtdMcaClient

_LOGGER = logging.getLogger(__name__)


def get_client(kind: HtdDeviceKind, ip_address: str, port: int) -> BaseClient:
    """
    Create a new client object.

    Args:
        kind (HtdDeviceKind): The type
        ip_address (str): The IP address of the gateway.
        port (int): The port number of the gateway.

    Returns:
        HtdClient: The new client object.
    """

    if kind == HtdDeviceKind.mca:
        return HtdMcaClient(ip_address, port)

    elif kind == HtdDeviceKind.lync:
        return HtdLyncClient(ip_address, port)

    raise ValueError(f"Unknown Device Kind: {kind}")


def get_model_info(ip_address: str, port: int = HtdConstants.DEFAULT_PORT) -> HtdModelInfo | None:
    """
    Get the model information from the gateway.

    Returns:
         (str, str): the raw model name from the gateway and the friendly
         name, in a Tuple.
    """

    cmd = htd_client.utils.build_command(
        1, HtdCommonCommands.MODEL_QUERY_COMMAND_CODE, 0
    )

    model_id = htd_client.utils.send_command(cmd, ip_address, port)

    for model_name in HtdConstants.SUPPORTED_MODELS:
        model = HtdConstants.SUPPORTED_MODELS[model_name]
        if model_id in model["identifier"]:
            return model

    return None
