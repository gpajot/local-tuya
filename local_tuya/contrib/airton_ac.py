from enum import Enum
from typing import Collection, Optional

from local_tuya.device import (
    Constraint,
    Constraints,
    Device,
    compose,
    debounce,
    moving_average,
    round_,
)
from local_tuya.protocol import (
    DeviceDiscovery,
    SelectComponentDiscovery,
    SensorComponentDiscovery,
    SwitchComponentDiscovery,
    TemperatureSetPointComponentDiscovery,
    Values,
)


class ACDataPoint(str, Enum):
    power = "1"
    set_point = "2"
    temperature = "3"
    mode = "4"
    fan = "5"
    eco = "8"
    light = "13"
    swing = "15"
    swing_direction = "107"
    sleep = "109"
    health = "110"


class ACMode(str, Enum):
    auto = "auto"
    cool = "cold"
    heat = "heat"
    dry = "wet"
    vent = "fan"


class ACFanSpeed(str, Enum):
    auto = "auto"
    quiet = "mute"
    L1 = "low"
    L2 = "low_mid"
    L3 = "mid"
    L4 = "mid_high"
    L5 = "high"
    turbo = "turbo"


class AirtonACDevice(Device):
    DISCOVERY = DeviceDiscovery(
        model="Airton AC",
        components=(
            SwitchComponentDiscovery(
                name=ACDataPoint.power.name,
                icon="mdi:air-conditioner",
                property=ACDataPoint.power.name,
            ),
            TemperatureSetPointComponentDiscovery(
                name=ACDataPoint.set_point.name,
                icon="mdi:thermometer-lines",
                property=ACDataPoint.set_point.name,
                min=16,
                max=31,
                step=1,
            ),
            SensorComponentDiscovery(
                name=ACDataPoint.temperature.name,
                icon="mdi:thermometer",
                property=ACDataPoint.temperature.name,
                unit="°C",
                class_="temperature",
            ),
            SelectComponentDiscovery(
                name=ACDataPoint.mode.name,
                icon="mdi:format-list-bulleted",
                property=ACDataPoint.mode.name,
                options=ACMode,
            ),
            SelectComponentDiscovery(
                name=ACDataPoint.fan.name,
                icon="mdi:fan",
                property=ACDataPoint.fan.name,
                options=ACFanSpeed,
            ),
            SwitchComponentDiscovery(
                name=ACDataPoint.eco.name,
                icon="mdi:sprout",
                property=ACDataPoint.eco.name,
            ),
            SwitchComponentDiscovery(
                name=ACDataPoint.light.name,
                icon="mdi:lightbulb",
                property=ACDataPoint.light.name,
            ),
            SwitchComponentDiscovery(
                name=ACDataPoint.swing.name,
                icon="mdi:arrow-oscillating",
                property=ACDataPoint.swing.name,
            ),
            SwitchComponentDiscovery(
                name=ACDataPoint.sleep.name,
                icon="mdi:power-sleep",
                property=ACDataPoint.sleep.name,
            ),
            SwitchComponentDiscovery(
                name=ACDataPoint.health.name,
                icon="mdi:air-purifier",
                property=ACDataPoint.health.name,
            ),
        ),
    )
    CONSTRAINTS = Constraints(
        Constraint(
            ACDataPoint.eco,
            True,
            (ACDataPoint.set_point, None),
            (ACDataPoint.fan, {ACFanSpeed.turbo}),
            (ACDataPoint.sleep, None),
        ),
        Constraint(
            ACDataPoint.mode,
            ACMode.auto,
            (ACDataPoint.set_point, None),
            (ACDataPoint.fan, {ACFanSpeed.turbo}),
            (ACDataPoint.eco, None),
            (ACDataPoint.sleep, None),
        ),
        Constraint(
            ACDataPoint.mode,
            ACMode.vent,
            (ACDataPoint.set_point, None),
            (ACDataPoint.eco, None),
            (ACDataPoint.sleep, None),
        ),
        Constraint(
            ACDataPoint.mode,
            ACMode.dry,
            (ACDataPoint.fan, None),
            (ACDataPoint.eco, None),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Temperature can oscillate a lot as it is reported in 0.5 steps.
        self._temperature_processor = compose(
            moving_average(4),
            debounce(30),
            round_(1),
        )
        self._from_tuya_value = {
            e: f
            for e, f in (
                (ACDataPoint.power, bool),
                (ACDataPoint.set_point, lambda v: int(v) / 10),
                (
                    ACDataPoint.temperature,
                    lambda v: self._temperature_processor(int(v) / 10),
                ),
                (ACDataPoint.mode, lambda v: ACMode(v).name),
                (ACDataPoint.fan, lambda v: ACFanSpeed(v).name),
                (ACDataPoint.eco, bool),
                (ACDataPoint.light, bool),
                (ACDataPoint.sleep, bool),
                (ACDataPoint.health, bool),
            )
            if self._cfg.included_components is None
            or e.name in self._cfg.included_components
        }
        self._to_tuya_value = {
            e: f
            for e, f in (
                (ACDataPoint.power, lambda e: e),
                (ACDataPoint.set_point, lambda v: max(min(round(v), 31), 16) * 10),
                (ACDataPoint.mode, lambda v: ACMode[v].value),
                (ACDataPoint.fan, lambda v: ACFanSpeed[v].value),
                (ACDataPoint.eco, lambda e: e),
                (ACDataPoint.light, lambda e: e),
                (ACDataPoint.sleep, lambda e: e),
                (ACDataPoint.health, lambda e: e),
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
            for e in ACDataPoint
            if included_components is None
            or e.name in included_components
            or e is ACDataPoint.swing_direction
            and ACDataPoint.swing.name in included_components
        }

    def _from_tuya_payload(self, tuya_payload: Values) -> Values:
        payload: Values = {}
        for e, f in self._from_tuya_value.items():
            if e in tuya_payload:
                payload[e.name] = f(tuya_payload[e])
        if (
            (
                self._cfg.included_components is None
                or ACDataPoint.swing.name in self._cfg.included_components
            )
            and ACDataPoint.swing in tuya_payload
            and ACDataPoint.swing_direction in tuya_payload
        ):
            payload[ACDataPoint.swing.name] = (
                tuya_payload[ACDataPoint.swing] == "un_down"
                and tuya_payload[ACDataPoint.swing_direction] == ACDataPoint.swing
            )
        return payload

    def _to_tuya_payload(self, payload: Values) -> Values:
        tuya_payload: Values = {}
        for e, f in self._to_tuya_value.items():
            if e.name in payload:
                tuya_payload[e] = f(payload[e.name])
        if (
            self._cfg.included_components is None
            or ACDataPoint.swing.name in self._cfg.included_components
        ) and ACDataPoint.swing.name in payload:
            status = payload[ACDataPoint.swing.name]
            tuya_payload[ACDataPoint.swing] = "un_down" if status else "off"
            tuya_payload[ACDataPoint.swing_direction] = (
                ACDataPoint.swing.value if status else "off"
            )
        return tuya_payload
