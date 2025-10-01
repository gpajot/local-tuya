import asyncio
import contextlib
import json
import logging
from time import time_ns
from typing import Any, AsyncIterator

import aiomqtt
from concurrent_tasks import BackgroundTask

from local_tuya.mqtt.config import (
    MQTTConfig,
    get_state_topic,
    get_status_topic,
)
from local_tuya.mqtt.discovery import DiscoveryMessage
from local_tuya.protocol import DeviceDiscovery, Protocol, Values

logger = logging.getLogger(__name__)


class MQTTClient(Protocol):
    def __init__(self, config: MQTTConfig):
        self.timeout = config.timeout
        self._discovery_prefix = config.discovery_prefix
        self._driver_prefix = config.driver_prefix
        self._status_topic = get_status_topic(config.driver_prefix, "driver")
        self._client = aiomqtt.Client(
            hostname=config.hostname,
            port=config.port,
            username=config.username,
            password=config.password,
            timeout=config.timeout,
            keepalive=config.keepalive,
            will=aiomqtt.Will(self._status_topic, b"offline", retain=True),
        )
        self._connect_task = BackgroundTask(self._connect)
        self._connected = asyncio.Event()
        self._backoff = config.backoff
        self._closed = True

    async def __aenter__(self):
        self._closed = False
        self._connect_task.create()
        await self._connected.wait()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._closed = True
        self._connect_task.cancel()
        with contextlib.suppress(aiomqtt.MqttError):
            # Send offline status if disconnecting cleanly.
            # In case connection is not acquired, the Will will have already been done by broker.
            if self._connected.is_set():
                await self._client.publish(self._status_topic, b"offline", retain=True)
            self._connected.clear()
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def _connect(self) -> None:
        with self._backoff:
            while True:
                await self._backoff.wait()
                try:
                    await self._client.__aenter__()
                    break
                except Exception:
                    logger.error("could not connect, retrying...", exc_info=True)
        self._connected.set()
        # Send birth message and subscribe to commands.
        await self._client.publish(self._status_topic, b"online", retain=True)
        await self._client.subscribe(f"{self._driver_prefix}/set/#")
        logger.info("connected to mqtt")

    async def _reconnect(self) -> None:
        if not self._closed and self._connected.is_set():
            self._connected.clear()
            with contextlib.suppress(aiomqtt.MqttError):
                await self._client.__aexit__(None, None, None)
            self._connect_task.create()

    async def receive_commands(self) -> AsyncIterator[tuple[str, Values]]:
        if self._closed:
            raise RuntimeError("client is closed")
        while True:
            if self._closed:
                break
            await self._connected.wait()
            try:
                async for message in self._client.messages:
                    if result := self._process_message(message):
                        yield result
                break
            except aiomqtt.MqttError:
                logger.warning("error receiving messages, reconnecting")
                await self._reconnect()

    def _process_message(self, message: aiomqtt.Message) -> tuple[str, Values] | None:
        logger.debug(
            "received message in %s: %s",
            message.topic.value,
            message.payload,
        )
        # Get information from the topic.
        topic_parts = message.topic.value.split("/")
        if (
            len(topic_parts) != 4
            or topic_parts[0] != self._driver_prefix
            or topic_parts[1] != "set"
        ):
            # Doesn't match the topic structure we want.
            return None
        device_id = topic_parts[2]
        component_property = topic_parts[3]
        value: Any
        if message.payload is None or isinstance(message.payload, (int, float)):
            value = message.payload
        else:
            try:
                value = json.loads(message.payload)
            except Exception:
                value = (
                    message.payload.decode()
                    if isinstance(message.payload, (bytes, bytearray))
                    else str(message.payload)
                )
        logger.debug(
            "received value for device %s:%s: %s",
            device_id,
            component_property,
            value,
        )
        return device_id, {component_property: value}

    async def send_state(self, device_id: str, payload: Values) -> None:
        await self._publish(
            get_state_topic(self._driver_prefix, device_id),
            json.dumps(
                {
                    # Timestamp in milliseconds.
                    "time": int(round(time_ns() / 1e6, 0)),
                    **payload,
                }
            ),
        )

    async def set_availability(self, device_id: str, status: bool) -> None:
        await self._publish(
            get_status_topic(self._driver_prefix, device_id),
            b"online" if status else b"offline",
            retain=True,
        )

    async def send_discovery(
        self,
        device: DeviceDiscovery,
        device_id: str,
        device_name: str,
    ) -> None:
        message = DiscoveryMessage(
            discovery_prefix=self._discovery_prefix,
            driver_prefix=self._driver_prefix,
            device=device,
            device_id=device_id,
            device_name=device_name,
        )
        for component in device.components:
            topic, payload = message.get(component)
            await self._publish(topic, json.dumps(payload), retain=True)

    async def _publish(
        self,
        topic: str,
        payload: str | bytes,
        *,
        retain: bool = False,
    ):
        if self._closed:
            raise RuntimeError("client is closed")
        while True:
            if self._closed:
                break
            await self._connected.wait()
            try:
                await self._client.publish(
                    topic,
                    payload,
                    retain=retain,
                )
                break
            except aiomqtt.MqttError:
                logger.warning("error sending message, reconnecting")
                await self._reconnect()
