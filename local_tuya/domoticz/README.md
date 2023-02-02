# Domoticz
The purpose of this module is to provide tools to create a plugin for a tuya device.

## Creating the plugin
To create a plugin, you will need to create 2 things.

### Plugin metadata
This is the XML header that is used to populate the plugin creation page in Domoticz.
You can create it using `local_tuya.domoticz.PluginMetadata`.

### Starting the device.
To start the plugin, you need to create the device and register the units.

Check `local_tuya.domoticz.plugin.plugin.OnStart` for the function signature.

Units should be created using `manager.register(...)`.

For a switch unit, it would look like:
```python
from typing import Dict

from local_tuya import DeviceConfig, ProtocolConfig
from my_device import SwitchState, SwitchDevice
from local_tuya.domoticz import UnitManager, switch_unit


def on_start(
    protocol_config: ProtocolConfig,
    parameters: Dict[str, str],
    manager: UnitManager[SwitchState],
) -> SwitchDevice:
    device = SwitchDevice(config=DeviceConfig(protocol=protocol_config))
    manager.register(
        switch_unit(
            id_=1,
            name="power",
            image=9,
            command_func=device.switch,
        ),
        lambda s: s.power,
    )
    return device
```

### Units
Units represent a Domoticz device and is associated to a Domoticz hardware.

#### Manager
The role of the manager is to
- create units: `register` method
- dispatch the commands from units: `on_command` method
- update units state: `update` method

#### Unit types
- [switch](./units/switch.py)
- [selector switch](./units/selector_switch.py)
- [temperature](./units/temperature.py)
- [set point](./units/set_point.py)

For common units parameters, see the [base](./units/base.py).

## Installing the plugin
You should provide a script that will be used to install the plugin.
It would look like:
```python
from pathlib import Path
import sys

from local_tuya.domoticz import install_plugin, PluginMetadata

def on_start(...):
    ...


if __name__ == "__main__":
    install_plugin(
        domoticz_path=Path(sys.argv[1] if len(sys.argv) > 1 else "/home/domoticz/domoticz"),
        metadata=PluginMetadata(...),
        on_start=on_start,
        on_start_import_path="my_device.domoticz",
    )
```