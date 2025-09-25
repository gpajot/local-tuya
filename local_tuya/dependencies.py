from imbue import Container

from local_tuya.config import Config
from local_tuya.mqtt import MQTTPackage


def load_container(config: Config) -> Container:
    return Container(MQTTPackage(config.mqtt))
