import asyncio
import logging.config
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from typing import AsyncIterator

from concurrent_tasks import BackgroundTask, LoopExceptionHandler
from imbue import Container

from local_tuya.config import DeviceConfigs
from local_tuya.contrib import FullDeviceConfig
from local_tuya.dependencies import load_container
from local_tuya.device import Device
from local_tuya.events import EventNotifier
from local_tuya.protocol import Protocol
from local_tuya.tuya import TuyaPackage, TuyaProtocol

logger = logging.getLogger(__name__)


class DeviceManager(AsyncExitStack):
    def __init__(self):
        super().__init__()
        self._stop_event = asyncio.Event()

    async def __aenter__(self):
        logger.debug("initializing...")
        app_container = await self.enter_async_context(
            load_container().application_context()
        )
        protocol = await app_container.get(Protocol)
        device_configs = await app_container.get(DeviceConfigs)
        devices: dict[str, Device] = {}
        for device_config in device_configs:
            device = await self.enter_async_context(
                self._create_and_run_device(device_config, protocol)
            )
            devices[device_config.config.tuya.id_] = device
        self.enter_context(BackgroundTask(self._receive_commands, protocol, devices))
        logger.info("initialized %d device(s)", len(device_configs))

    async def _stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        async with LoopExceptionHandler(self._stop):
            async with self:
                await self._stop_event.wait()

    async def _receive_commands(
        self,
        protocol: Protocol,
        devices: dict[str, Device],
    ) -> None:
        """Receive commands and dispatch them to the devices."""
        logger.debug("receiving commands...")
        async for device_id, payload in protocol.receive_commands():
            if device := devices.get(device_id):
                device.update(payload)
            else:
                logger.warning("received command for unknown device: %s", device_id)

    @asynccontextmanager
    async def _create_and_run_device(
        self,
        device_config: FullDeviceConfig,
        protocol: Protocol,
    ) -> AsyncIterator[Device]:
        device_class = device_config.infer()
        async with Container(
            TuyaPackage(
                name=device_config.name,
                config=device_config.config.tuya,
            ),
        ).application_context() as device_container:
            event_notifier = await device_container.get(EventNotifier)
            tuya_protocol = await device_container.get(TuyaProtocol)
            async with device_class(
                device_config.name,
                device_config.config,
                protocol,
                event_notifier,
                tuya_protocol,
            ) as device:
                yield device


async def run():
    logging.config.dictConfig(
        {
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
                "level": logging.getLevelName(
                    logging.DEBUG if "-v" in sys.argv else logging.INFO
                ),
                "handlers": ["console"],
            },
        },
    )
    await DeviceManager().run()
