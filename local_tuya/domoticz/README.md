# Domoticz
The purpose of this module is to provide tools to create a plugin for a tuya device.

> 💡 The Domoticz version should be `2022.1` or higher.

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
from local_tuya.domoticz import UnitManager, switch_unit

from my_device import SwitchState, SwitchDevice


def on_start(
    protocol_config: ProtocolConfig,
    _: Dict[str, str],
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
- create/remove units: `register` method
- dispatch the commands from units: `on_command` method
- update units state: `update` method

#### Unit types
- [switch](./units/switch.py)
- [selector switch](./units/selector_switch.py)
- [temperature](./units/temperature.py) (accepts values preprocessor)
- [set point](./units/set_point.py)

For common units parameters, see the [base](./units/base.py).

## Installing the plugin
You should provide a script that will be used to install the plugin.
It would look like:
```python
from local_tuya.domoticz import install_plugin, PluginMetadata

def on_start(...):
    ...


if __name__ == "__main__":
    install_plugin(
        metadata=PluginMetadata(...),
        on_start=on_start,
        import_path="my_device.domoticz",
    )
```

> 💡 Domoticz path defaults to `~/domoticz` a `-p` option can be passed to change that.

### Filtering units
You can automatically add an option to the plugin to filter created units.

To enable it, you need to implement `local_tuya.domoticz.UnitId` and add all unit IDs, then simply pass it to the `install` function. `UnitManager.register` will handle device deletion.