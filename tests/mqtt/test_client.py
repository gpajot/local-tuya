import asyncio
from unittest.mock import call

import paho.mqtt.client as mqtt
import pytest

from local_tuya.backoff import SequenceBackoff
from local_tuya.mqtt.client import MQTTClient
from local_tuya.mqtt.config import MQTTConfig


class TestMQTTClient:
    @pytest.fixture
    def backoff(self, mocker):
        return mocker.MagicMock(spec=SequenceBackoff)

    @pytest.fixture
    async def client(self, mocker, backoff):
        config = MQTTConfig(discovery_prefix="discover", hostname="address")
        mocker.patch.object(config, "backoff", new=backoff)
        return MQTTClient(config)

    @pytest.fixture
    async def aenter_future(self):
        return asyncio.Future()

    @pytest.fixture
    async def aexit_future(self):
        return asyncio.Future()

    @pytest.fixture
    def mock_client(self, mocker, client, aenter_future, aexit_future):
        mock = mocker.MagicMock()
        mock.publish = mocker.AsyncMock()
        mock.subscribe = mocker.AsyncMock()

        async def _aenter():
            await aenter_future
            client._connected.set()

        async def _aexit(*_, **__):
            await aexit_future
            client._closed.set()

        mock.__aenter__.side_effect = _aenter
        mock.__aexit__.side_effect = _aexit
        aexit_future.set_result(None)

        mocker.patch.object(client, "_client", mock)
        return mock

    @pytest.fixture
    async def connected_client(
        self,
        client,
        mock_client,
        aenter_future,
        aexit_future,
    ):
        aenter_future.set_result(None)
        async with client:
            yield client

    async def test_publish_disconnected(self, client):
        with pytest.raises(RuntimeError, match="client is closed"):
            await client._publish("test-topic", "")

    async def test_publish_connected(self, connected_client, mock_client):
        await connected_client._publish("test-topic", "{}")
        assert mock_client.publish.call_args_list == [
            call("local-tuya/status/driver", b"online", retain=True),
            call("test-topic", "{}", retain=False),
        ]

    async def test_publish_connecting(self, client, mock_client, aenter_future):
        async with client:
            publish_task = asyncio.create_task(client._publish("test-topic", "{}"))
            await asyncio.sleep(0.001)  # context switch.
            assert mock_client.publish.call_args_list == []
            aenter_future.set_result(None)
            await asyncio.sleep(0.001)  # context switch.
            assert mock_client.publish.call_args_list == [
                call("local-tuya/status/driver", b"online", retain=True),
                call("test-topic", "{}", retain=False),
            ]
            # Cleanup.
            await publish_task

    async def test_receive(self, mocker, connected_client, mock_client):
        mock_message = mocker.Mock()
        mock_message.topic = mocker.Mock()
        mock_message.topic.value = "local-tuya/set/dev-id/temp"
        mock_message.payload = b"18.5"
        mock_client.messages.__aiter__.return_value = iter([mock_message])
        commands = []
        async for cmd in connected_client.receive_commands():
            commands.append(cmd)
        assert commands == [("dev-id", {"temp": 18.5})]

    async def test_reconnect(self, mocker, connected_client, backoff):
        await asyncio.sleep(0.001)  # context switch.
        assert backoff.wait.call_count == 1
        assert backoff.reset.call_count == 1
        connected_client._on_disconnect(
            mocker.Mock(), mocker.Mock(), mocker.Mock(), mqtt.MQTT_ERR_CONN_LOST
        )
        await asyncio.sleep(0)  # context switch.
        assert backoff.wait.call_count == 2
        assert backoff.reset.call_count == 2
