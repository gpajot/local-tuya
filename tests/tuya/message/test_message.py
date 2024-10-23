import pytest

from local_tuya.errors import ResponseError
from local_tuya.tuya.message.messages import StatusResponse


@pytest.mark.parametrize(
    ("payload", "error", "expected_values", "expected_error_msg"),
    [
        (None, None, {}, "no dps in response"),
        (None, ResponseError("other error"), {}, "other error"),
        ({}, ResponseError("other error"), {}, "other error"),
        ({"dps": {}}, ResponseError("other error"), {}, "other error"),
        ({"dps": {"1": 1}}, ResponseError("other error"), {"1": 1}, "other error"),
        ({"dps": {"1": 1}}, None, {"1": 1}, None),
    ],
)
def test_status_response_values(payload, error, expected_values, expected_error_msg):
    response = StatusResponse(payload, error)
    assert response.values == expected_values
    if expected_error_msg:
        assert response.error is not None
        assert str(response.error) == expected_error_msg
    else:
        assert response.error is None
