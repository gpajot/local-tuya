# Device
The device handles higher level functional logic such as buffering, constraints and specific device commands.

## Constraints
For some devices, certain modes don't support all commands.

As an example, to forbid setting turbo mode of a fan on eco mode:
```python
from local_tuya import Constraint
constraint = Constraint(
    DataPoint.FAN,
    (DataPoint.ECO, {True}),
    restrict_to={FanSpeed.TURBO},
)
```

Constraints will avoid sending the command to the device.

For more details, see [constraints](./constraints.py).

## Buffering
Can be activated to group multiple commands into a single one.

> 💡 If 2 commands cancel each other nothing will be sent to the device.

## Creating a device
You first need to create a state that the device will act on, then simply add methods for updating that state:
```python
from dataclasses import dataclass
from typing import Optional, Callable, Any
from local_tuya import DataPoint, State, Device, Values, DeviceConfig

class SwitchDataPoint(DataPoint):
    POWER = "1"

@dataclass
class SwitchState(State):
    power: bool

    @classmethod
    def load(cls, values: Values) -> "SwitchState":
        return cls(power=bool(values[SwitchDataPoint.POWER]))

class SwitchDevice(Device[SwitchState]):
    def __init__(
        self,
        config: DeviceConfig,
        state_updated_callback: Optional[Callable[[SwitchState], Any]] = None,
    ):
        super().__init__(config, SwitchState.load, state_updated_callback)

    async def switch(self, status: bool) -> None:
        await self._update({SwitchDataPoint.POWER: status})
```
