import pytest

from local_tuya.protocol.message.handlers.crypto import AESCipher


class TestAESCipher:
    @pytest.mark.parametrize(
        "s",
        [b"", b"0", b"test", b'{"some":["json","content"]}'],
    )
    def test_encrypt_decrypt(self, s: bytes, cipher: AESCipher):
        assert cipher.decrypt(cipher.encrypt(s)) == s
