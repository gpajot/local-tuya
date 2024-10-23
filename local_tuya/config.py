from pydantic import BaseModel
from typing_extensions import TypeAlias
from zenconfig import ReadOnlyConfig

from local_tuya.contrib import FullDeviceConfig
from local_tuya.mqtt import MQTTConfig

DeviceConfigs: TypeAlias = tuple[FullDeviceConfig, ...]


class Config(BaseModel, ReadOnlyConfig):
    mqtt: MQTTConfig
    devices: DeviceConfigs
    debug: bool = False
