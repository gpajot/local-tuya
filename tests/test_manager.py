import asyncio

import pytest
from imbue import Container, Package, auto_context

from local_tuya.config import DeviceConfigs
from local_tuya.device import Device, DeviceConfig
from local_tuya.manager import DeviceManager
from local_tuya.protocol import Protocol
from local_tuya.tuya import TuyaConfig


class TestDeviceManager:
    @pytest.fixture
    def protocol(self, mocker):
        return mocker.MagicMock(spec=Protocol)

    @pytest.fixture
    def device_config(self, mocker):
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
    def _container(self, mocker, protocol, device_config):
        class TestPackage(Package):
            @auto_context
            def protocol(self) -> Protocol:
                return protocol

            @auto_context
            def dev_cfgs(self) -> DeviceConfigs:
                return (device_config,)

        mocker.patch(
            "local_tuya.manager.load_container",
            return_value=Container(TestPackage()),
        )

    @pytest.fixture
    def device(self, mocker, device_config, protocol):
        mocker.patch("local_tuya.manager.Container", return_value=mocker.MagicMock())
        dev = mocker.MagicMock(spec=Device)
        dev.__aenter__.return_value = dev
        device_config.infer.return_value = mocker.Mock(return_value=dev)
        return dev

    @pytest.mark.usefixtures("_container")
    async def test_init(self, mocker, device, protocol):
        manager = DeviceManager()
        mock_receive_commands = mocker.patch.object(manager, "_receive_commands")

        async with manager:
            await asyncio.sleep(0.001)  # Context switch.

        mock_receive_commands.assert_called_once_with(protocol, {"test-id": device})
        device.__aenter__.assert_awaited_once()
        device.__aexit__.assert_awaited_once()

    @pytest.mark.usefixtures("_container")
    async def test_receive(self, device, protocol):
        manager = DeviceManager()
        protocol.receive_commands.return_value.__aiter__.return_value = iter(
            [
                ("fake_id", {}),
                ("test-id", {"temp": 18.5}),
            ]
        )

        async with manager:
            await asyncio.sleep(0.001)  # Context switch.

        device.update.assert_called_once_with({"temp": 18.5})
