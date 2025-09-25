import asyncio

import pytest
from imbue import Container, Package, auto_context

from local_tuya.config import Config
from local_tuya.device import Device, DeviceConfig
from local_tuya.manager import DeviceManager
from local_tuya.protocol import Protocol
from local_tuya.tuya import TuyaConfig


@pytest.fixture
def protocol(mocker):
    return mocker.MagicMock(spec=Protocol)


@pytest.fixture
def device_config(mocker):
    tuya_config = mocker.Mock(spec=TuyaConfig)
    tuya_config.id_ = "test-id"
    dev_config = mocker.Mock(spec=DeviceConfig)
    dev_config.tuya = tuya_config
    full_config = mocker.Mock()
    full_config.name = "TestName"
    full_config.model = "TestModel"
    full_config.config = dev_config
    return full_config


@pytest.fixture
def config(mocker, device_config):
    cfg = mocker.Mock(spec=Config)
    cfg.devices = (device_config,)
    return cfg


@pytest.fixture
def _container(mocker, protocol):
    class TestPackage(Package):
        @auto_context
        def protocol(self) -> Protocol:
            return protocol

    mocker.patch(
        "local_tuya.manager.load_container",
        return_value=Container(TestPackage()),
    )


@pytest.fixture
def device(mocker, device_config, protocol):
    mocker.patch("local_tuya.manager.Container", return_value=mocker.MagicMock())
    dev = mocker.MagicMock(spec=Device)
    dev.__aenter__.return_value = dev
    device_config.infer.return_value = mocker.Mock(return_value=dev)
    return dev


@pytest.mark.usefixtures("_container")
async def test_init(mocker, device, protocol, config):
    manager = DeviceManager(config)
    mock_receive_commands = mocker.patch.object(manager, "_receive_commands")

    async with manager:
        await asyncio.sleep(0.001)  # Context switch.

    mock_receive_commands.assert_called_once_with(protocol, {"test-id": device})
    device.__aenter__.assert_awaited_once()
    device.__aexit__.assert_awaited_once()


@pytest.mark.usefixtures("_container")
async def test_receive(device, protocol, config):
    manager = DeviceManager(config)
    protocol.receive_commands.return_value.__aiter__.return_value = iter(
        [
            ("fake_id", {}),
            ("test-id", {"temp": 18.5}),
        ]
    )

    async with manager:
        await asyncio.sleep(0.001)  # Context switch.

    device.update.assert_called_once_with({"temp": 18.5})
