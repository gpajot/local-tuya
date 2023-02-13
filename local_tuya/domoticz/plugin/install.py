from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Type, TypeVar

from local_tuya.device import State
from local_tuya.domoticz.plugin.metadata import PluginMetadata
from local_tuya.domoticz.plugin.plugin import OnStart
from local_tuya.domoticz.units import UnitId

T = TypeVar("T", bound=State)


def _get_domoticz_path() -> Path:
    parser = ArgumentParser(prog="Domoticz plugin installer")
    parser.add_argument("-p", "--domoticz-path", dest="path", action="store")
    domoticz_path: Optional[str] = parser.parse_args().path
    if domoticz_path:
        return Path(domoticz_path)
    return Path("~/domoticz").expanduser()


def install_plugin(
    metadata: PluginMetadata,
    on_start: OnStart,
    import_path: str,
    unit_ids: Optional[Type[UnitId]] = None,
) -> None:
    target = _get_domoticz_path() / "plugins" / metadata.package / "plugin.py"
    if not target.parent.exists():
        target.parent.mkdir(parents=True)
    template = (Path(__file__).parent / "template.txt").read_text()
    target.write_text(
        template.format(
            definition=metadata.definition(unit_ids),
            package=metadata.package,
            import_path=import_path,
            on_start_name=on_start.__name__,
            unit_ids_name=unit_ids.__name__ if unit_ids else "__NOOP_UNIT_ID__",
        ),
    )
