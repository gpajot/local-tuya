from dataclasses import dataclass
from typing import ClassVar

from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad


@dataclass
class AESCipher:
    key: bytes

    BLOCK_SIZE: ClassVar[int] = 16

    def encrypt(self, s: bytes) -> bytes:
        if not s:
            return s
        cipher = AES.new(self.key, AES.MODE_ECB)
        return cipher.encrypt(pad(s, self.BLOCK_SIZE))

    def decrypt(self, s: bytes) -> bytes:
        if not s:
            return s
        if len(s) % self.BLOCK_SIZE:
            raise ValueError(
                f"length {len(s)} should be a multiple of {self.BLOCK_SIZE}"
            )
        cipher = AES.new(self.key, AES.MODE_ECB)
        return unpad(cipher.decrypt(s), self.BLOCK_SIZE)
