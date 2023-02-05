import sys
from logging import NullHandler
from typing import Any

import pytest

from local_tuya.device import Device
from local_tuya.domoticz.plugin.metadata import PluginMetadata
from local_tuya.domoticz.plugin.plugin import Plugin
from local_tuya.domoticz.units.base import UnitCommand
from local_tuya.domoticz.units.manager import UnitManager
from local_tuya.protocol import ProtocolConfig


@pytest.fixture()
def metadata(mocker):
    metadata = mocker.Mock(spec=PluginMetadata)
    metadata.package = "test"
    return metadata


@pytest.fixture()
def device(mocker):
    return mocker.MagicMock(spec=Device)


@pytest.fixture()
def units(mocker):
    return mocker.Mock()


@pytest.fixture()
def manager(mocker):
    manager = mocker.Mock(spec=UnitManager)
    mocker.patch("local_tuya.domoticz.plugin.plugin.UnitManager", return_value=manager)
    return manager


@pytest.fixture()
def on_start(mocker, device):
    return mocker.Mock(return_value=device)


@pytest.fixture()
def parameters():
    return {
        "Name": "test",
        "Username": "id",
        "Address": "localhost",
        "Port": "6666",
        "Password": "key",
    }


@pytest.fixture()
def plugin(mocker, metadata, units, parameters, manager, on_start):
    mocker.patch("local_tuya.domoticz.plugin.plugin.LOG_HANDLER", new=NullHandler())
    plugin: Plugin[Any] = Plugin("test", on_start)
    _device = mocker.Mock()
    _device.Units = units
    plugin.start(parameters, {"test": _device})
    try:
        yield plugin
    finally:
        plugin.stop()


@pytest.mark.skipif(
    sys.version_info < (3, 8),
    reason="requires python3.8 or higher for AsyncMock",
)
@pytest.mark.usefixtures("plugin")
def test_start(plugin, parameters, manager, on_start, device):
    device.__aenter__.assert_awaited_once()
    on_start.assert_called_once_with(
        ProtocolConfig(
            id_="id",
            address="localhost",
            port=6666,
            key=b"key",
        ),
        parameters,
        manager,
    )


@pytest.mark.skipif(
    sys.version_info < (3, 8),
    reason="requires python3.8 or higher for AsyncMock",
)
def test_on_command(plugin, manager):
    plugin.on_command(1, UnitCommand("cmd", 10.2, ""))
    plugin.stop()  # drain pool

    manager.on_command.assert_awaited_once_with(1, UnitCommand("cmd", 10.2, ""))
