import logging.config

from imbue import Container, Package, auto_context

from local_tuya.config import Config, DeviceConfigs
from local_tuya.mqtt import MQTTPackage


class DeviceConfigPackage(Package):
    def __init__(self, config: DeviceConfigs):
        self._cfg = config

    @auto_context
    def config(self) -> DeviceConfigs:
        return self._cfg


def load_container(debug: bool = False) -> Container:
    config = Config.load()
    logging.config.dictConfig(config.logging)
    if debug or config.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    return Container(
        DeviceConfigPackage(config.devices),
        MQTTPackage(config.mqtt),
    )
