import pytest

from local_tuya.device.constraints import Constraint, Constraints
from local_tuya.device.enums import DataPoint


class DPS(DataPoint):
    A = "1"
    B = "2"
    C = "3"


@pytest.mark.parametrize(
    ("constraint", "values", "expected"),
    [
        (Constraint(DPS.B, 10, (DPS.A, None)), {DPS.A: 1, DPS.B: 10}, {DPS.A: None}),
        (Constraint(DPS.B, 11, (DPS.A, None)), {DPS.A: 1, DPS.B: 10}, {}),
    ],
)
def test_constraint_blacklist(constraint, values, expected):
    assert constraint.blacklist(values) == expected


@pytest.mark.parametrize(
    ("values", "current", "expected"),
    [
        ({}, {DPS.A: 1, DPS.B: 10, DPS.C: 20}, {}),
        ({DPS.A: 2}, {DPS.A: 1, DPS.B: 10, DPS.C: 20}, {}),
        ({DPS.A: 2, DPS.B: 10}, {DPS.A: 1, DPS.B: 11, DPS.C: 20}, {DPS.B: 10}),
        ({DPS.A: 2}, {DPS.A: 1, DPS.B: 11, DPS.C: 20}, {DPS.A: 2}),
        ({DPS.C: 20}, {DPS.A: 1, DPS.B: 10, DPS.C: 21}, {}),
        ({DPS.C: 21}, {DPS.A: 1, DPS.B: 10, DPS.C: 20}, {DPS.C: 21}),
    ],
)
def test_constraints_filter_values(values, current, expected):
    constraints = Constraints(
        Constraint(DPS.B, 10, (DPS.A, None)),
        Constraint(DPS.B, 10, (DPS.C, {20})),
    )
    assert constraints.filter_values(values, current) == expected
