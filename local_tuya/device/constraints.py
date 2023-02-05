from typing import Dict, Optional, Set, Tuple

from local_tuya.device.enums import DataPoint
from local_tuya.protocol import Value, Values


class Constraint:
    """The data point is constrained if any of the exclusions is active."""

    def __init__(
        self,
        data_point: DataPoint,
        # An exclusion is active if its datapoint is in the set of values.
        *exclusions: Tuple[DataPoint, Set[Value]],
        # Only check the constraint if the data point is in those values.
        restrict_to: Optional[Set[Value]] = None,
    ):
        self.data_point = data_point
        self._exclusions: Dict[str, Set[Value]] = {
            data_point: values for data_point, values in exclusions
        }
        self._restrict_to = restrict_to

    def applicable(self, value: Value) -> bool:
        """Return whether the constraint should be checked."""
        return self._restrict_to is None or value in self._restrict_to

    def ko(self, values: Values) -> bool:
        """Returns whether an exclusion applies on the given values."""
        return any(
            v in self._exclusions[k] for k, v in values.items() if k in self._exclusions
        )


class Constraints:
    """Set of constraints for a device that forbids certain commands."""

    def __init__(self, *constraints: Constraint):
        self._constraints: Dict[str, Constraint] = {
            constraint.data_point: constraint for constraint in constraints
        }

    def filter_values(self, values: Values, current: Values) -> Values:
        """Filter values that can be updated given the device constraints."""
        # Check on merged values.
        merged = {**current, **values}
        filtered: Values = {}
        for data_point, value in values.items():
            constraint = self._constraints.get(data_point)
            if constraint and constraint.applicable(value) and constraint.ko(merged):
                continue
            filtered[data_point] = value
        return filtered
