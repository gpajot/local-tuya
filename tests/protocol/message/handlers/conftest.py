import pytest

from local_tuya.protocol.message.handlers.crypto import AESCipher


@pytest.fixture()
def key() -> bytes:
    return b"9efe59a10acd6ccf"


@pytest.fixture()
def cipher(key: bytes) -> AESCipher:
    return AESCipher(key)
