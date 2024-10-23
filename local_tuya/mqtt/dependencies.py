from typing import AsyncIterator

from imbue import Package, auto_context

from local_tuya.mqtt.client import MQTTClient
from local_tuya.mqtt.config import MQTTConfig
from local_tuya.protocol import Protocol


class MQTTPackage(Package):
    def __init__(self, config: MQTTConfig):
        self._cfg = config

    @auto_context
    async def client(self) -> AsyncIterator[Protocol]:
        async with MQTTClient(self._cfg) as client:
            yield client
