from __future__ import annotations

from blake3 import blake3
from google_crc32c import value as crc32c_value


def crc32c_be(data: bytes) -> bytes:
    return int(crc32c_value(data)).to_bytes(4, byteorder="big", signed=False)


def blake3_256(data: bytes) -> bytes:
    return blake3(data).digest(length=32)

