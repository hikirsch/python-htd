# htd_client

This library contains a client to communicate with the HTD MC/MCA66 gateway. Future support
for the Lync system is planned.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Installation

Use pip to install this package

```bash
pip install htd_client
```

## Usage

Here's a basic example.

```python

import HtdClient from htd_client

client = HtdClient("192.168.1.2")
model_info = client.get_model_info()
client.volume_up()
client.volume_down()

```

## Contributing

[Poetry](https://python-poetry.org/docs/#installation) is used to manage dependencies, run tests, and publish.

Run unit tests

```bash
$ poetry run pytest
```

Generate documentation

```bash
$ poetry run sphinx-build -b html docs docs/_build 
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
