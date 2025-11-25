import logging.config
from typing import Annotated

import uvloop
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from local_tuya.config import Config
from local_tuya.manager import DeviceManager


class Options(BaseSettings):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
        cli_prog_name="local-tuya",
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_shortcuts={"verbose": "v"},
    )

    config: Annotated[
        str,
        Field(description="The path containing the configuration."),
    ]
    verbose: Annotated[bool, Field(description="Show all logs.")] = False


options = Options()
Config.YAML_FILE = options.config
config = Config()
logging.config.dictConfig(config.logging)
if options.verbose:
    logging.getLogger().setLevel(logging.DEBUG)

uvloop.run(DeviceManager(config).run())
