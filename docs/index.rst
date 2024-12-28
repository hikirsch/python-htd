Overview
========================

This library contains a client to communicate with the HTD MC/MCA66 gateway. Future support
for the Lync system is planned.

.. toctree::
  :maxdepth: 1

  self
  api

Installation
-------------
Use pip to install this package

.. code-block:: shell

    pip install htd_client

Usage
-----
Here's a basic example.

.. code-block:: python

    from htd_client import HtdClient

    client = HtdClient("192.168.1.2")
    (friendly_name, model_info) = client.get_model_info()
    client.volume_up()
    client.volume_down()


Contributing
------------
`Poetry <https://python-poetry.org/docs/#installation>`_ is used to manage dependencies, run tests, and publish.

Run unit tests

.. code-block:: shell
    poetry run pytest

Generate documentation

.. code-block:: shell
    poetry run sphinx-build -b html docs docs/_build


License
-------
htd_client is licensed under the MIT License. See the `LICENSE`_ file for more details.
