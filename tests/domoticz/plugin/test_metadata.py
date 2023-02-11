from pathlib import Path

from local_tuya.domoticz.plugin.metadata import Option, Parameter, PluginMetadata
from local_tuya.domoticz.units import UnitId


class TheUnitId(UnitId):
    ONE = 1
    TWO = 2


def test_definition():
    metadata = PluginMetadata(
        name="Test",
        package="local_tuya",
        description={
            "h1": "Test plugin",
            "ul": {"li": ["feature 1", "feature 2"]},
        },
        parameters=(
            Parameter(
                field="Field1",
                label="Field",
                description="field desc",
                options=(
                    Option(label="option 1", value="1", default=True),
                    Option(label="option 2", value="2"),
                ),
            ),
        ),
    )
    test_file = Path(__file__).parent / "test_metadata.txt"
    assert metadata.definition(TheUnitId) == test_file.read_text()
