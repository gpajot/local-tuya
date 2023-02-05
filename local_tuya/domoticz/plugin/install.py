from pathlib import Path
from typing import TypeVar

from local_tuya.device import State
from local_tuya.domoticz.plugin.metadata import PluginMetadata
from local_tuya.domoticz.plugin.plugin import OnStart

T = TypeVar("T", bound=State)


def install_plugin(
    metadata: PluginMetadata,
    on_start: OnStart,
    on_start_import_path: str,
    domoticz_path: Path = Path("~/domoticz").expanduser(),
) -> None:
    target = domoticz_path / "plugins" / metadata.package / "plugin.py"
    if not target.parent.exists():
        target.parent.mkdir(parents=True)
    template = (Path(__file__).parent / "template.txt").read_text()
    target.write_text(
        template.format(
            definition=metadata.definition(),
            on_start_import_path=on_start_import_path,
            on_start_name=on_start.__name__,
            package=metadata.package,
        ),
    )
