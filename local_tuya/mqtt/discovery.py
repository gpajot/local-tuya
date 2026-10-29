from collections.abc import Iterator
from typing import Any, cast

from local_tuya.mqtt.config import get_state_topic, get_status_topic
from local_tuya.protocol import (
    ComponentDiscovery,
    DeviceDiscovery,
    SelectComponentDiscovery,
    SensorComponentDiscovery,
    SwitchComponentDiscovery,
    TemperatureSetPointComponentDiscovery,
)


def get_discovery_message(
    driver_prefix: str,
    device: DeviceDiscovery,
    device_id: str,
    device_name: str,
    version: str,
) -> dict[str, Any]:
    return {
        "device": {
            "ids": f"{driver_prefix}-{device_id}",
            "manufacturer": "Tuya",
            "model": device.model,
            "name": device_name,
        },
        "origin": {
            "name": "local-tuya",
            "sw": version,
            "url": "https://github.com/gpajot/local-tuya",
        },
        "availability": [
            {"topic": get_status_topic(driver_prefix, "driver")},
            {"topic": get_status_topic(driver_prefix, device_id)},
        ],
        "availability_mode": "all",
        "state_topic": get_state_topic(driver_prefix, device_id),
        "components": {
            comp.property: {
                "name": comp.name,
                "icon": comp.icon,
                "unique_id": f"{driver_prefix}-{device_id}-{comp.property}",
                **_get_component(comp, driver_prefix, device_id),
            }
            for comp in device.components
        },
    }


def convert_to_component_messages(
    message: dict[str, Any],
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for prop, component in message.pop("components", {}).items():
        yield (
            prop,
            cast(str, component.pop("platform")),
            {
                **message,
                **component,
            },
        )


def _get_component(
    component: ComponentDiscovery,
    driver_prefix: str,
    device_id: str,
) -> dict[str, Any]:
    match component:
        case SwitchComponentDiscovery():
            return {
                "platform": "switch",
                "payload_on": "true",
                "payload_off": "false",
                "command_topic": _get_command_topic(
                    driver_prefix, device_id, component.property
                ),
                "value_template": _get_value_template(component.property),
            }
        case SensorComponentDiscovery():
            return {
                "platform": "sensor",
                "device_class": component.class_,
                "state_class": "measurement",
                "unit_of_measurement": component.unit,
                "value_template": _get_value_template(component.property),
            }
        case SelectComponentDiscovery():
            return {
                "platform": "select",
                "options": [o.name for o in component.options],
                "command_topic": _get_command_topic(
                    driver_prefix, device_id, component.property
                ),
                "value_template": _get_value_template(component.property),
            }
        case TemperatureSetPointComponentDiscovery():
            return {
                "platform": "climate",
                "temperature_command_topic": _get_command_topic(
                    driver_prefix, device_id, component.property
                ),
                "temperature_state_topic": get_state_topic(driver_prefix, device_id),
                "temperature_state_template": _get_value_template(component.property),
                "min_temp": component.min,
                "max_temp": component.max,
                "temp_step": component.step,
                "temperature_unit": component.unit,
            }
        case _:
            raise ValueError(
                f"{component.__class__.__name__} component is not supported"
            )


def _get_command_topic(
    driver_prefix: str,
    device_id: str,
    component_property: str,
) -> str:
    return f"{driver_prefix}/set/{device_id}/{component_property}"


def _get_value_template(component_property: str) -> str:
    return "{{ value_json.%s }}" % component_property  # noqa: UP031
