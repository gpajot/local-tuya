from typing import Any

from local_tuya.mqtt.config import DRIVER_PREFIX, get_state_topic, get_status_topic
from local_tuya.protocol import (
    ComponentDiscovery,
    DeviceDiscovery,
    SelectComponentDiscovery,
    SensorComponentDiscovery,
    SwitchComponentDiscovery,
    TemperatureSetPointComponentDiscovery,
)


def get_discovery_message(
    discovery_prefix: str,
    device: DeviceDiscovery,
    device_id: str,
    device_name: str,
    component: ComponentDiscovery,
) -> tuple[str, dict[str, Any]]:
    common_payload = _get_discovery_payload_common(
        device,
        device_id,
        device_name,
        component,
    )
    if isinstance(component, SwitchComponentDiscovery):
        specific_payload = _get_discovery_payload_switch(device_id, component)
        component_type = "switch"
    elif isinstance(component, SensorComponentDiscovery):
        specific_payload = _get_discovery_payload_sensor(device_id, component)
        component_type = "sensor"
    elif isinstance(component, SelectComponentDiscovery):
        specific_payload = _get_discovery_payload_select(device_id, component)
        component_type = "select"
    elif isinstance(component, TemperatureSetPointComponentDiscovery):
        specific_payload = _get_discovery_payload_temperature_set_point(
            device_id, component
        )
        component_type = "climate"
    else:
        raise ValueError(f"{component.__class__.__name__} component is not supported")
    return (
        _get_discovery_topic(
            discovery_prefix,
            component_type,
            device_id,
            component.property,
        ),
        {**specific_payload, **common_payload},
    )


def _get_discovery_topic(
    discovery_prefix: str,
    component_type: str,
    device_id: str,
    component_property,
) -> str:
    return (
        f"{discovery_prefix}/{component_type}/{device_id}/{component_property}/config"
    )


def _get_command_topic(device_id: str, component_property: str) -> str:
    return f"{DRIVER_PREFIX}/set/{device_id}/{component_property}"


def _get_value_template(component_property: str) -> str:
    return "{{ value_json.%s }}" % component_property


def _get_discovery_payload_common(
    device: DeviceDiscovery,
    device_id: str,
    device_name: str,
    component: ComponentDiscovery,
) -> dict[str, Any]:
    return {
        "name": component.name,
        "icon": component.icon,
        "unique_id": f"{DRIVER_PREFIX}-{device_id}-{component.property}",
        "device": {
            "identifiers": [f"{DRIVER_PREFIX}-{device_id}"],
            "manufacturer": "Tuya",
            "model": device.model,
            "name": device_name,
        },
        "availability": [
            {"topic": get_status_topic(device_id)},
            {"topic": get_status_topic("driver")},
        ],
        "availability_mode": "all",
    }


def _get_discovery_payload_switch(
    device_id: str,
    component: SwitchComponentDiscovery,
) -> dict:
    return {
        "payload_on": "true",
        "payload_off": "false",
        "command_topic": _get_command_topic(device_id, component.property),
        "state_topic": get_state_topic(device_id),
        "value_template": _get_value_template(component.property),
    }


def _get_discovery_payload_sensor(
    device_id: str,
    component: SensorComponentDiscovery,
) -> dict:
    return {
        "state_topic": get_state_topic(device_id),
        "value_template": _get_value_template(component.property),
        "unit_of_measurement": component.unit,
        "state_class": "measurement",
        "device_class": component.class_,
    }


def _get_discovery_payload_select(
    device_id: str,
    component: SelectComponentDiscovery,
) -> dict[str, Any]:
    return {
        "command_topic": _get_command_topic(device_id, component.property),
        "state_topic": get_state_topic(device_id),
        "value_template": _get_value_template(component.property),
        "options": [o.name for o in component.options],
    }


def _get_discovery_payload_temperature_set_point(
    device_id: str,
    component: TemperatureSetPointComponentDiscovery,
) -> dict[str, Any]:
    return {
        "temperature_command_topic": _get_command_topic(device_id, component.property),
        "temperature_state_topic": get_state_topic(device_id),
        "temperature_state_template": _get_value_template(component.property),
        "min_temp": component.min,
        "max_temp": component.max,
        "temp_step": component.step,
        "temperature_unit": component.unit,
    }
