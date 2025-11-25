from typing import Any, ClassVar

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from local_tuya.contrib import FullDeviceConfig
from local_tuya.mqtt import MQTTConfig


class Config(BaseSettings):
    mqtt: MQTTConfig
    devices: tuple[FullDeviceConfig, ...]
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

    YAML_FILE: ClassVar[str] = ""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        *_,
        **__,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        if not cls.YAML_FILE:
            raise ValueError("no config path provided")
        return (YamlConfigSettingsSource(settings_cls, yaml_file=cls.YAML_FILE),)
