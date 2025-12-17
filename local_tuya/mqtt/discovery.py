from dataclasses import dataclass
from typing import Any

from local_tuya.mqtt.config import get_state_topic, get_status_topic
from local_tuya.protocol import (
    ComponentDiscovery,
    DeviceDiscovery,
    SelectComponentDiscovery,
    SensorComponentDiscovery,
    SwitchComponentDiscovery,
    TemperatureSetPointComponentDiscovery,
)


@dataclass
class DiscoveryMessage:
    discovery_prefix: str
    driver_prefix: str
    device: DeviceDiscovery
    device_id: str
    device_name: str

    def get(
        self,
        component: ComponentDiscovery,
    ) -> tuple[str, dict[str, Any]]:
        common_payload = self._get_payload_common(component)
        if isinstance(component, SwitchComponentDiscovery):
            specific_payload = self._get_payload_switch(component)
            component_type = "switch"
        elif isinstance(component, SensorComponentDiscovery):
            specific_payload = self._get_payload_sensor(component)
            component_type = "sensor"
        elif isinstance(component, SelectComponentDiscovery):
            specific_payload = self._get_payload_select(component)
            component_type = "select"
        elif isinstance(component, TemperatureSetPointComponentDiscovery):
            specific_payload = self._get_payload_temperature_set_point(component)
            component_type = "climate"
        else:
            raise ValueError(
                f"{component.__class__.__name__} component is not supported"
            )
        return (
            self._get_topic(component_type, component.property),
            {**specific_payload, **common_payload},
        )

    def _get_topic(self, component_type: str, component_property) -> str:
        return f"{self.discovery_prefix}/{component_type}/{self.device_id}/{component_property}/config"

    def _get_command_topic(self, component_property: str) -> str:
        return f"{self.driver_prefix}/set/{self.device_id}/{component_property}"

    def _get_payload_common(
        self,
        component: ComponentDiscovery,
    ) -> dict[str, Any]:
        return {
            "name": component.name,
            "icon": component.icon,
            "unique_id": f"{self.driver_prefix}-{self.device_id}-{component.property}",
            "device": {
                "identifiers": [f"{self.driver_prefix}-{self.device_id}"],
                "manufacturer": "Tuya",
                "model": self.device.model,
                "name": self.device_name,
            },
            "availability": [
                {"topic": get_status_topic(self.driver_prefix, self.device_id)},
                {"topic": get_status_topic(self.driver_prefix, "driver")},
            ],
            "availability_mode": "all",
        }

    def _get_payload_switch(
        self,
        component: SwitchComponentDiscovery,
    ) -> dict:
        return {
            "payload_on": "true",
            "payload_off": "false",
            "command_topic": self._get_command_topic(component.property),
            "state_topic": get_state_topic(self.driver_prefix, self.device_id),
            "value_template": _get_value_template(component.property),
        }

    def _get_payload_sensor(
        self,
        component: SensorComponentDiscovery,
    ) -> dict:
        return {
            "state_topic": get_state_topic(self.driver_prefix, self.device_id),
            "value_template": _get_value_template(component.property),
            "unit_of_measurement": component.unit,
            "state_class": "measurement",
            "device_class": component.class_,
        }

    def _get_payload_select(
        self,
        component: SelectComponentDiscovery,
    ) -> dict[str, Any]:
        return {
            "command_topic": self._get_command_topic(component.property),
            "state_topic": get_state_topic(self.driver_prefix, self.device_id),
            "value_template": _get_value_template(component.property),
            "options": [o.name for o in component.options],
        }

    def _get_payload_temperature_set_point(
        self,
        component: TemperatureSetPointComponentDiscovery,
    ) -> dict[str, Any]:
        return {
            "temperature_command_topic": self._get_command_topic(component.property),
            "temperature_state_topic": get_state_topic(
                self.driver_prefix, self.device_id
            ),
            "temperature_state_template": _get_value_template(component.property),
            "min_temp": component.min,
            "max_temp": component.max,
            "temp_step": component.step,
            "temperature_unit": component.unit,
        }


def _get_value_template(component_property: str) -> str:
    return "{{ value_json.%s }}" % component_property  # noqa: UP031
