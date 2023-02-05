import contextlib
import shutil
from pathlib import Path

import pytest

from local_tuya.domoticz.plugin.install import install_plugin
from local_tuya.domoticz.plugin.metadata import PluginMetadata


@pytest.fixture()
def path(mocker):
    path = Path(__file__).parent
    mocker.patch(
        "local_tuya.domoticz.plugin.install._get_domoticz_path",
        return_value=path,
    )
    try:
        yield path
    finally:
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(str(path / "plugins"))


@pytest.fixture()
def metadata(mocker):
    metadata = mocker.Mock(spec=PluginMetadata)
    metadata.package = "test"
    metadata.definition.return_value = "test definition"
    return metadata


@pytest.fixture()
def on_start(mocker, metadata):
    func = mocker.MagicMock()
    func.__name__ = "on_start"
    return func


def test_install_plugin(path, metadata, on_start):
    install_plugin(metadata, on_start, "test.module")
    plugin_path = path / "plugins" / "test" / "plugin.py"
    assert plugin_path.read_text().split("\n")[:14] == [
        '"""',
        "test definition",
        '"""',
        "",
        "from local_tuya.domoticz.units import UnitCommand",
        "from local_tuya.domoticz.plugin.plugin import Plugin",
        "",
        "from test.module import on_start",
        "",
        "plugin = Plugin(",
        '    package="test",',
        "    on_start=on_start,",
        ")",
        "",
    ]
