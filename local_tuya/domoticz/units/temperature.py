from typing import Optional

from local_tuya.domoticz.units.base import Unit, UnitValues
from local_tuya.domoticz.units.value_preprocessors import ValuePreprocessor


def temperature_unit(
    id_: int,
    name: str,
    image: int,
    value_preprocessor: Optional[ValuePreprocessor[float]] = None,
) -> Unit[float]:
    def _to_unit_values(value: float) -> UnitValues:
        value = value if not value_preprocessor else value_preprocessor(value)
        return UnitValues(n_value=1, s_value=str(round(value, 2)))

    return Unit(
        id_=id_,
        type_="Temperature",
        name=name,
        image=image,
        to_unit_values=_to_unit_values,
    )
