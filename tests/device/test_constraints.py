import pytest

from local_tuya.device.constraints import Constraint, Constraints
from local_tuya.device.enums import DataPoint


class DPS(DataPoint):
    A = "1"
    B = "2"
    C = "3"


class TestConstraint:
    @pytest.mark.parametrize(
        ("constraint", "value", "expected"),
        [
            (Constraint(DPS.A), 1, True),
            (Constraint(DPS.A, restrict_to={2}), 1, False),
        ],
    )
    def test_applicable(self, constraint, value, expected):
        assert constraint.applicable(value) is expected

    @pytest.mark.parametrize(
        ("constraint", "values", "expected"),
        [
            (Constraint(DPS.A, (DPS.B, {10})), {DPS.A: 1, DPS.B: 10}, True),
            (Constraint(DPS.A, (DPS.B, {11})), {DPS.A: 1, DPS.B: 10}, False),
            (
                Constraint(DPS.A, (DPS.B, {11}), (DPS.C, {20})),
                {DPS.A: 1, DPS.B: 10, DPS.C: 20},
                True,
            ),
            (
                Constraint(DPS.A, (DPS.B, {11}), (DPS.C, {21})),
                {DPS.A: 1, DPS.B: 10, DPS.C: 20},
                False,
            ),
        ],
    )
    def test_ko(self, constraint, values, expected):
        assert constraint.ko(values) is expected


class TestConstraints:
    @pytest.mark.parametrize(
        ("values", "current", "expected"),
        [
            ({}, {}, {}),
            ({DPS.A: 2}, {DPS.A: 1, DPS.B: 10, DPS.C: 20}, {}),
            ({DPS.A: 2, DPS.B: 10}, {DPS.A: 1, DPS.B: 11, DPS.C: 20}, {DPS.B: 10}),
            ({DPS.A: 2}, {DPS.A: 1, DPS.B: 11, DPS.C: 20}, {DPS.A: 2}),
            ({DPS.C: 20}, {DPS.A: 1, DPS.B: 10, DPS.C: 21}, {}),
            ({DPS.C: 21}, {DPS.A: 1, DPS.B: 10, DPS.C: 20}, {DPS.C: 21}),
        ],
    )
    def test_filter(self, values, current, expected):
        constraints = Constraints(
            Constraint(DPS.A, (DPS.B, {10})),
            Constraint(DPS.C, (DPS.B, {10}), restrict_to={20}),
        )
        assert constraints.filter(values, current) == expected
