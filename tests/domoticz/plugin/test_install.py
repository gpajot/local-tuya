import contextlib
import shutil
import subprocess
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import pytest

from local_tuya.domoticz.plugin.install import install_plugin
from local_tuya.domoticz.plugin.metadata import PluginMetadata
from local_tuya.domoticz.plugin.plugin import Plugin
from local_tuya.domoticz.units import UnitCommand, UnitId

# Mocked later on.
on_start_mock = None


@pytest.fixture()
def path(mocker):
    path = Path(__file__).parent / str(uuid4())
    mocker.patch(
        "local_tuya.domoticz.plugin.install._get_domoticz_path",
        return_value=path,
    )
    try:
        yield path
    finally:
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(str(path))


@pytest.fixture()
def metadata(mocker):
    metadata = mocker.Mock(spec=PluginMetadata)
    metadata.package = "local_tuya"
    metadata.definition.return_value = "test definition {version:s}"
    return metadata


@pytest.fixture()
def on_start(mocker, metadata):
    global on_start_mock
    on_start_mock = mocker.MagicMock()
    on_start_mock.__name__ = "on_start_mock"
    return on_start_mock


@pytest.fixture()
def plugin_module(path):
    return ".".join(
        __name__.split(".")[:-1] + [path.name, "plugins", "local_tuya", "plugin"]
    )


@pytest.fixture()
def plugin(mocker):
    return mocker.Mock(spec=Plugin)


@pytest.fixture()
def plugin_init(mocker, plugin):
    return mocker.patch("local_tuya.domoticz.plugin.plugin.Plugin", return_value=plugin)


def test_install_plugin(path, metadata, on_start, plugin, plugin_init, plugin_module):
    install_plugin(metadata, on_start, __name__)
    generated_plugin = import_module(plugin_module)
    parameters, devices = object(), object()
    generated_plugin.Parameters = parameters  # type: ignore
    generated_plugin.Devices = devices  # type: ignore
    version = subprocess.check_output(
        ["poetry", "version", "--short"], encoding="utf-8"
    ).strip()

    assert generated_plugin.__doc__ == f"\ntest definition {version}\n"
    plugin_init.assert_called_once_with(
        package="local_tuya",
        on_start=on_start,
        unit_ids=None,
    )
    generated_plugin.onStart()
    generated_plugin.onStop()
    generated_plugin.onCommand(None, 1, "cmd", 1.2, "color")
    plugin.start.assert_called_once_with(parameters, devices)
    plugin.stop.assert_called_once()
    plugin.on_command.assert_called_once_with(1, UnitCommand("cmd", 1.2, "color"))


@pytest.mark.usefixtures("path")
def test_install_plugin_with_unit_id(metadata, on_start, plugin_init, plugin_module):
    install_plugin(metadata, on_start, __name__, UnitId)
    import_module(plugin_module)

    plugin_init.assert_called_once_with(
        package="local_tuya",
        on_start=on_start,
        unit_ids=UnitId,
    )
