# python-htd

A client supporting Home Theater Direct's gateway device.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Installation

To install the package, use:

```bash
pip install htd
```

## Usage

```python

import HtdClient from htd

client = HtdClient("192.168.1.2")
(friendly_name, model_info) = client.get_model_info()
client.volume_up()
client.volume_down()

```
