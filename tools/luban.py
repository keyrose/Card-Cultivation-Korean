"""Luban 바이너리 테이블용 최소 reader/writer."""


class Reader:
    def __init__(self, data: bytes):
        self.d = data
        self.p = 0

    def uint(self) -> int:
        d, p = self.d, self.p
        h = d[p]
        if h < 0x80:
            self.p += 1
            return h
        if h < 0xC0:
            self.p += 2
            return ((h & 0x3F) << 8) | d[p + 1]
        if h < 0xE0:
            self.p += 3
            return ((h & 0x1F) << 16) | (d[p + 1] << 8) | d[p + 2]
        if h < 0xF0:
            self.p += 4
            return ((h & 0x0F) << 24) | (d[p + 1] << 16) | (d[p + 2] << 8) | d[p + 3]
        self.p += 5
        return int.from_bytes(d[p + 1:p + 5], "big")

    def str(self) -> str:
        n = self.uint()
        s = self.d[self.p:self.p + n].decode("utf-8")
        self.p += n
        return s

    def eof(self) -> bool:
        return self.p >= len(self.d)


def w_uint(x: int) -> bytes:
    if x < 0x80:
        return bytes([x])
    if x < 0x4000:
        return bytes([0x80 | (x >> 8), x & 0xFF])
    if x < 0x200000:
        return bytes([0xC0 | (x >> 16), (x >> 8) & 0xFF, x & 0xFF])
    if x < 0x10000000:
        return bytes([0xE0 | (x >> 24), (x >> 16) & 0xFF, (x >> 8) & 0xFF, x & 0xFF])
    return bytes([0xF0]) + x.to_bytes(4, "big")


def w_str(s: str) -> bytes:
    b = s.encode("utf-8")
    return w_uint(len(b)) + b
