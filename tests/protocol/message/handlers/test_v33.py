import pytest

from local_tuya.protocol.config import ProtocolConfig, Version
from local_tuya.protocol.message.handlers.v33 import V33MessageHandler
from local_tuya.protocol.message.messages import (
    HeartbeatCommand,
    HeartbeatResponse,
    StateCommand,
    StateResponse,
    StatusResponse,
    UpdateCommand,
    UpdateResponse,
)


class TestV33MessageHandler:
    @pytest.fixture
    def config(self, mocker, key) -> ProtocolConfig:
        cfg = mocker.Mock(spec=ProtocolConfig)
        cfg.key = key
        cfg.version = Version.v33
        return cfg

    @pytest.fixture
    def handler(self, config) -> V33MessageHandler:
        return V33MessageHandler(config)

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            (
                HeartbeatCommand(),
                b"\x00\x00U\xaa\x00\x00\x00\x01\x00\x00\x00\t\x00\x00\x00\x18\x0f\x91\x92\xfe\xdb\x82x\xb6\x81C\xc5\\Gx+S\x8a\x909\x03\x00\x00\xaaU",
            ),
            (
                StateCommand(),
                b"\x00\x00U\xaa\x00\x00\x00\x01\x00\x00\x00\n\x00\x00\x00\x18\x0f\x91\x92\xfe\xdb\x82x\xb6\x81C\xc5\\Gx+S\xf1\x8e\xbb\xe0\x00\x00\xaaU",
            ),
            (
                UpdateCommand({"1": 1}),
                b"\x00\x00U\xaa\x00\x00\x00\x01\x00\x00\x00\x07\x00\x00\x00'3.3\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00i\n\x8b\xd70\xa0\x102^\xa6\xa2#\xe4\xa7\x9b\xfa\xa5\xfb8\xc9\x00\x00\xaaU",
            ),
        ],
    )
    def test_pack(self, handler, message, expected):
        assert handler.pack(1, message) == expected

    @pytest.mark.parametrize(
        ("data", "expected_seq", "expected_response_class", "expected_command_class"),
        [
            (
                b"\x00\x00U\xaa\x00\x00\x00\x02\x00\x00\x00\x07\x00\x00\x00\x0c\x00\x00\x00\x00\x18\xcf\xc5\xda\x00\x00\xaaU",
                2,
                UpdateResponse,
                UpdateCommand,
            ),
            (
                b"\x00\x00U\xaa\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00+\x00\x00\x00\x003.3\x00\x00\x00\x00\x00\x00+\xf8\x00\x00\x00\x01i\n\x8b\xd70\xa0\x102^\xa6\xa2#\xe4\xa7\x9b\xfa\xa5\xfb8\xc9\x00\x00\xaaU",
                0,
                StatusResponse,
                None,
            ),
            (
                b"\x00\x00U\xaa\x00\x00\x00\x00\x00\x00\x00\t\x00\x00\x00\x0c\x00\x00\x00\x00\xb0Q\xab\x03\x00\x00\xaaU",
                0,
                HeartbeatResponse,
                HeartbeatCommand,
            ),
            (
                b"\x00\x00U\xaa\x00\x00\x00\x01\x00\x00\x00\n\x00\x00\x00\x1c\x00\x00\x00\x00i\n\x8b\xd70\xa0\x102^\xa6\xa2#\xe4\xa7\x9b\xfa\xa5\xfb8\xc9\x00\x00\xaaU",
                1,
                StateResponse,
                StateCommand,
            ),
        ],
    )
    def test_unpack(
        self,
        handler,
        data,
        expected_seq,
        expected_response_class,
        expected_command_class,
    ):
        seq, resp, cmd_class, left = handler.unpack(data)
        assert seq == expected_seq
        assert isinstance(resp, expected_response_class)
        assert resp.error is None
        assert cmd_class is expected_command_class
        assert not left
        if expected_response_class in {StatusResponse, StateResponse}:
            assert resp.values == {"1": 1}

    @pytest.mark.parametrize(
        "data",
        [
            b"\x00\x00U",
            b"\x00\x00U\xaa\x00\x00\x00\x01\x00\x00\x00\n\x00\x00\x00\x1c\x00\x00\x00\x00",
            b"\x00\x00U\xaa\x00\x00\x00\x01\x00\x00\x00\n\x00\x00\x00\x1c",
            b"\x00\x00U\xaa\x00\x00\x00\x01\x00\x00\x00\n\x00\x00\x00\x1c\x00\x00\x00\x00i\n\x8b\xd70\xa0\x102^\xa6\xa2#\xe4",
        ],
    )
    def test_unpack_not_enough_data(self, handler, data):
        seq, resp, cmd_class, left = handler.unpack(data)
        assert seq == 0
        assert resp is None
        assert cmd_class is None
        assert left == data

    def test_unpack_multiple(self, handler):
        data = b"\x00\x00U\xaa\x00\x00\x00\x02\x00\x00\x00\x07\x00\x00\x00\x0c\x00\x00\x00\x00\x18\xcf\xc5\xda\x00\x00\xaaU\x00\x00U"
        seq, resp, cmd_class, left = handler.unpack(data)
        assert seq == 2
        assert resp is not None
        assert cmd_class is not None
        assert left == b"\x00\x00U"
