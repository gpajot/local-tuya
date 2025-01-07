# Device
The device handles higher level functional logic such as buffering, constraints and specific device commands.

## Constraints
For some devices, certain modes don't support all commands.

As an example, to forbid setting turbo mode of a fan on eco mode:
```python
from local_tuya import Constraint
constraint = Constraint(
    DataPoint.eco,
    True,
    (DataPoint.fan, {FanSpeed.Turbo}),
)
```

Constraints will avoid sending the command to the device.

For more details, see [constraints](./constraints.py).

## Buffering
Can be activated to group multiple commands into a single one.

> [!NOTE]
> If 2 commands cancel each other nothing will be sent to the device.
