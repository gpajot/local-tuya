from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import TypeAlias
from zenconfig import ReadOnlyConfig

from local_tuya.contrib import FullDeviceConfig
from local_tuya.mqtt import MQTTConfig

DeviceConfigs: TypeAlias = tuple[FullDeviceConfig, ...]


class Config(BaseModel, ReadOnlyConfig):
    mqtt: MQTTConfig
    devices: DeviceConfigs
    logging: dict[str, Any] = Field(
        default_factory=lambda: {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "formatter": {
                    "validate": True,
                    "format": "%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "formatter",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["console"],
            },
        }
    )
    debug: bool = False
