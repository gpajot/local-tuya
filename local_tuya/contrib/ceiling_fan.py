from enum import Enum
from typing import Collection, Optional

from local_tuya.device import (
    Constraint,
    Constraints,
    Device,
)
from local_tuya.protocol import (
    DeviceDiscovery,
    SelectComponentDiscovery,
    SwitchComponentDiscovery,
    Values,
)


class FanDataPoint(str, Enum):
    power = "1"
    speed = "3"
    direction = "4"
    light = "9"
    mode = "102"


class FanSpeed(str, Enum):
    L1 = "1"
    L2 = "2"
    L3 = "3"
    L4 = "4"
    L5 = "5"
    L6 = "6"


class FanDirection(str, Enum):
    forward = "forward"
    reverse = "reverse"


class FanMode(str, Enum):
    normal = "normal"
    sleep = "sleep"
    nature = "nature"
    temperature = "temprature"  # Typo on device.


class CeilingFanDevice(Device):
    DISCOVERY = DeviceDiscovery(
        model="Ceiling Fan",
        components=(
            SwitchComponentDiscovery(
                name=FanDataPoint.power.name,
                icon="mdi:ceiling-fan",
                property=FanDataPoint.power.name,
            ),
            SelectComponentDiscovery(
                name=FanDataPoint.speed.name,
                icon="mdi:speedometer",
                property=FanDataPoint.speed.name,
                options=FanSpeed,
            ),
            SelectComponentDiscovery(
                name=FanDataPoint.direction.name,
                icon="mdi:directions-fork",
                property=FanDataPoint.direction.name,
                options=FanDirection,
            ),
            SwitchComponentDiscovery(
                name=FanDataPoint.light.name,
                icon="mdi:lightbulb",
                property=FanDataPoint.light.name,
            ),
            SelectComponentDiscovery(
                name=FanDataPoint.mode.name,
                icon="mdi:format-list-bulleted",
                property=FanDataPoint.mode.name,
                options=FanMode,
            ),
        ),
    )
    CONSTRAINTS = Constraints(
        Constraint(
            FanDataPoint.mode,
            FanMode.temperature,
            (FanDataPoint.speed, None),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._from_tuya_value = {
            e: f
            for e, f in (
                (FanDataPoint.power, bool),
                (FanDataPoint.speed, lambda v: FanSpeed(v).name),
                (FanDataPoint.direction, lambda v: FanDirection(v).name),
                (FanDataPoint.light, bool),
                (FanDataPoint.mode, lambda v: FanMode(v).name),
            )
            if self._cfg.included_components is None
            or e.name in self._cfg.included_components
        }
        self._to_tuya_value = {
            e: f
            for e, f in (
                (FanDataPoint.power, lambda e: e),
                (FanDataPoint.speed, lambda v: FanSpeed[v].value),
                (FanDataPoint.direction, lambda v: FanDirection[v].value),
                (FanDataPoint.light, lambda e: e),
                (FanDataPoint.mode, lambda v: FanMode[v].value),
            )
            if self._cfg.included_components is None
            or e.name in self._cfg.included_components
        }

    @classmethod
    def filter_data_points(
        cls,
        included_components: Optional[Collection[str]],
    ) -> set[str]:
        return {
            e
            for e in FanDataPoint
            if included_components is None or e.name in included_components
        }

    def _from_tuya_payload(self, tuya_payload: Values) -> Values:
        payload: Values = {}
        for e, f in self._from_tuya_value.items():
            if e in tuya_payload:
                payload[e.name] = f(tuya_payload[e])
        return payload

    def _to_tuya_payload(self, payload: Values) -> Values:
        tuya_payload: Values = {}
        for e, f in self._to_tuya_value.items():
            if e.name in payload:
                tuya_payload[e] = f(payload[e.name])
        return tuya_payload
