from local_tuya.domoticz.units.base import AdjustFunc, Unit, UnitValues


def temperature_unit(
    id_: int,
    name: str,
    image: int,
) -> Unit[float]:
    def _to_unit_values(value: float, adjust: AdjustFunc) -> UnitValues:
        return UnitValues(n_value=1, s_value=str(round(adjust(value), 2)))

    return Unit(
        id_=id_,
        type_="Temperature",
        name=name,
        image=image,
        to_unit_values=_to_unit_values,
    )
