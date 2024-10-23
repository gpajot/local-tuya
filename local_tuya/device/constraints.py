from typing import Optional

from local_tuya.protocol import Value, Values

Blacklist = dict[str, Optional[set[Value]]]
_Blacklist = dict[str, set[Value]]


class Constraint:
    """Represents other values that cannot be applied if the datapoint/value is set."""

    def __init__(
        self,
        data_point: str,
        value: Value,
        *blacklist: tuple[str, Optional[set[Value]]],
    ):
        self._data_point = data_point
        self._value = value
        self._blacklist: Blacklist = {dp: v for dp, v in blacklist}

    def blacklist(self, values: Values) -> Blacklist:
        if values[self._data_point] != self._value:
            return {}
        return self._blacklist


class Constraints:
    """Represent all constraints for a given device."""

    def __init__(self, *constraints: Constraint):
        self._constraints = constraints

    def _blacklist(self, values: Values) -> _Blacklist:
        blacklist: _Blacklist = {}
        for constraint in self._constraints:
            for k, v in constraint.blacklist(values).items():
                if k not in blacklist:
                    blacklist[k] = set()
                if v:
                    blacklist[k] |= v
        return blacklist

    def filter_values(self, values: Values, current: Values) -> Values:
        """Filter values that can be updated given the device constraints."""
        # Check on merged values.
        blacklist = self._blacklist({**current, **values})
        filtered: Values = {}
        for data_point, value in values.items():
            if data_point in blacklist and (
                not blacklist[data_point] or value in blacklist[data_point]
            ):
                continue
            filtered[data_point] = value
        return filtered
