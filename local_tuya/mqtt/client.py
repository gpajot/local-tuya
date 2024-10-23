import asyncio
import contextlib
import json
import logging
from time import time_ns
from typing import Any, AsyncIterator, Optional, Union

import aiomqtt
import paho.mqtt.client as mqtt
import paho.mqtt.properties as mqtt_props
import paho.mqtt.reasoncodes as mqtt_rc
from concurrent_tasks import BackgroundTask

from local_tuya.mqtt.config import (
    DRIVER_PREFIX,
    MQTTConfig,
    get_state_topic,
    get_status_topic,
)
from local_tuya.mqtt.discovery import get_discovery_message
from local_tuya.protocol import DeviceDiscovery, Protocol, Values

logger = logging.getLogger(__name__)


class MQTTClient(Protocol):
    def __init__(self, config: MQTTConfig):
        self.timeout = config.timeout
        self._discovery_prefix = config.discovery_prefix
        self._client = aiomqtt.Client(
            hostname=config.hostname,
            port=config.port,
            username=config.username,
            password=config.password,
            timeout=config.timeout,
            keepalive=config.keepalive,
            will=aiomqtt.Will(
                get_status_topic("driver"),
                b"offline",
                retain=True,
            ),
        )
        self._connect_task = BackgroundTask(self._connect)
        self._connected = asyncio.Event()
        self._original_on_disconnect = self._client._client.on_disconnect or (
            lambda *_, **__: ...
        )
        self._client._client.on_disconnect = self._on_disconnect
        self._backoff = config.backoff
        self._closing = False
        self._closed = asyncio.Event()
        self._closed.set()

    async def __aenter__(self):
        self._closed.clear()
        self._connect_task.create()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._closing = True
        self._connect_task.cancel()
        with contextlib.suppress(aiomqtt.MqttError):
            # Send offline status if disconnecting cleanly.
            # In case connection is not acquired, the Will will have already been done by broker.
            if self._connected.is_set():
                await self._client.publish(
                    get_status_topic("driver"),
                    b"offline",
                    retain=True,
                )
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
        try:
            await asyncio.wait_for(self._closed.wait(), self.timeout)
            logger.info("disconnected from mqtt")
        except asyncio.TimeoutError:
            logger.warning("timeout waiting for client to close")

    async def _connect(self) -> None:
        if self._connected.is_set():
            # In case this is a reconnection.
            self._connected.clear()
            with contextlib.suppress(aiomqtt.MqttError):
                await self._client.__aexit__(None, None, None)
        while True:
            await self._backoff.wait()
            try:
                await self._client.__aenter__()
                break
            except Exception:
                logger.warning("could not connect, retrying...", exc_info=True)
        self._backoff.reset()
        self._connected.set()
        # Send birth message and subscribe to commands.
        await self._client.publish(
            get_status_topic("driver"),
            b"online",
            retain=True,
        )
        await self._client.subscribe(f"{DRIVER_PREFIX}/set/#")
        logger.info("connected to mqtt")

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.DisconnectFlags,
        reason_code: mqtt_rc.ReasonCode,
        properties: Optional[mqtt_props.Properties] = None,
    ) -> None:
        self._original_on_disconnect(client, userdata, flags, reason_code, properties)  # type: ignore[call-arg, arg-type]
        if reason_code == mqtt.MQTT_ERR_SUCCESS:
            # Wanted disconnection.
            self._closed.set()
        else:
            # Reconnect
            logger.warning("connection lost: %s, reconnecting...", reason_code)
            self._connect_task.create()

    async def receive_commands(self) -> AsyncIterator[tuple[str, Values]]:
        if self._closed.is_set():
            raise RuntimeError("client is closed")
        if self._closing:
            raise RuntimeError("client is closing")
        while True:
            if self._closing or self._closed.is_set():
                break
            await self._connected.wait()
            try:
                async for message in self._client.messages:
                    if result := self._process_message(message):
                        yield result
                break
            except aiomqtt.MqttError as e:
                logger.warning("error receiving messages: %s", e)

    def _process_message(
        self, message: aiomqtt.Message
    ) -> Optional[tuple[str, Values]]:
        logger.debug(
            "received message in %s: %s",
            message.topic.value,
            message.payload,
        )
        # Get information from the topic.
        topic_parts = message.topic.value.split("/")
        if (
            len(topic_parts) != 4
            or topic_parts[0] != DRIVER_PREFIX
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
            get_state_topic(device_id),
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
            get_status_topic(device_id),
            b"online" if status else b"offline",
            retain=True,
        )

    async def send_discovery(
        self,
        device: DeviceDiscovery,
        device_id: str,
        device_name: str,
    ) -> None:
        for component in device.components:
            topic, payload = get_discovery_message(
                self._discovery_prefix,
                device,
                device_id,
                device_name,
                component,
            )
            await self._publish(topic, json.dumps(payload), retain=True)

    async def _publish(
        self,
        topic: str,
        payload: Union[str, bytes],
        *,
        retain: bool = False,
    ):
        if self._closed.is_set():
            raise RuntimeError("client is closed")
        if self._closing:
            raise RuntimeError("client is closing")
        while True:
            if self._closing or self._closed.is_set():
                break
            await self._connected.wait()
            try:
                await self._client.publish(
                    topic,
                    payload,
                    retain=retain,
                )
                break
            except aiomqtt.MqttError as e:
                logger.warning("error sending message: %s", e)
