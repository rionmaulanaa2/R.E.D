#!/usr/bin/env python3
import math
import typing


class RotorCipher:
    def __init__(self, key: typing.Union[str, bytes], num_rotors: int = 6):
        if isinstance(key, str):
            key_bytes = key.encode("latin1")
        else:
            key_bytes = bytes(key)

        self._rotors = num_rotors
        self._size = 256
        self._size_mask = 0
        self._seed = [0, 0, 0]
        self._key = [0, 0, 0, 0, 0]
        self._isinited = False
        self._e_rotor = [0] * (self._rotors * self._size)
        self._d_rotor = [0] * (self._rotors * self._size)
        self._positions = [0] * self._rotors
        self._advances = [0] * self._rotors
        self.setkey(key_bytes)

    @staticmethod
    def _to_short(value: int) -> int:
        value &= 0xFFFF
        if value >= 0x8000:
            value -= 0x10000
        return value

    @staticmethod
    def _c_div(a: int, b: int) -> int:
        return int(a / b)

    @classmethod
    def _c_mod(cls, a: int, b: int) -> int:
        return a - (cls._c_div(a, b) * b)

    def setkey(self, key: typing.Union[str, bytes]) -> None:
        if isinstance(key, str):
            key_bytes = key.encode("latin1")
        else:
            key_bytes = bytes(key)

        k1, k2, k3, k4, k5 = 995, 576, 767, 671, 463
        for b in key_bytes:
            ki = b & 0xFF
            k1 = (((k1 << 3) | (k1 >> 13)) + ki) & 0xFFFF
            k2 = (((k2 << 3) | (k2 >> 13)) ^ ki) & 0xFFFF
            k3 = (((k3 << 3) | (k3 >> 13)) - ki) & 0xFFFF
            k4 = (ki - ((k4 << 3) | (k4 >> 13))) & 0xFFFF
            k5 = (((k5 << 3) | (k5 >> 13)) ^ (~ki & 0xFFFF)) & 0xFFFF

        self._key[0] = self._to_short(k1)
        self._key[1] = self._to_short(k2 | 1)
        self._key[2] = self._to_short(k3)
        self._key[3] = self._to_short(k4)
        self._key[4] = self._to_short(k5)
        self._set_seed()

    def _set_seed(self) -> None:
        self._seed[0] = self._key[0]
        self._seed[1] = self._key[1]
        self._seed[2] = self._key[2]
        self._isinited = False

    def _r_random(self) -> float:
        x, y, z = self._seed
        x = 171 * self._c_mod(x, 177) - 2 * self._c_div(x, 177)
        y = 172 * self._c_mod(y, 176) - 35 * self._c_div(y, 176)
        z = 170 * self._c_mod(z, 178) - 63 * self._c_div(z, 178)

        if x < 0:
            x += 30269
        if y < 0:
            y += 30307
        if z < 0:
            z += 30323

        self._seed[0] = x
        self._seed[1] = y
        self._seed[2] = z

        term = (x / 30269.0) + (y / 30307.0) + (z / 30323.0)
        val = term - math.floor(term)
        if val >= 1.0:
            val = 0.0
        return val

    def _r_rand(self, s: int) -> int:
        if s <= 0:
            return 0
        return int((self._r_random() * float(s)) % s)

    def _make_id_rotor(self, offset: int) -> None:
        for j in range(self._size):
            self._e_rotor[offset + j] = j

    def _e_rotors(self) -> None:
        for i in range(self._rotors):
            self._make_id_rotor(i * self._size)

    def _d_rotors(self) -> None:
        for i in range(self._rotors):
            base = i * self._size
            for j in range(self._size):
                self._d_rotor[base + j] = j

    def _positions_init(self) -> None:
        for i in range(self._rotors):
            self._positions[i] = 1

    def _advances_init(self) -> None:
        for i in range(self._rotors):
            self._advances[i] = 1

    def _permute_rotor(self, base: int) -> None:
        i = self._size
        self._make_id_rotor(base)
        while 2 <= i:
            q = self._r_rand(i)
            i -= 1
            j = self._e_rotor[base + q]
            self._e_rotor[base + q] = self._e_rotor[base + i]
            self._e_rotor[base + i] = j
            self._d_rotor[base + j] = i
        e0 = self._e_rotor[base + 0]
        self._d_rotor[base + e0] = 0

    def _init(self) -> None:
        self._set_seed()
        self._positions_init()
        self._advances_init()
        self._e_rotors()
        self._d_rotors()
        for i in range(self._rotors):
            self._positions[i] = self._r_rand(self._size)
            self._advances[i] = 1 + (2 * self._r_rand(self._size // 2))
            self._permute_rotor(i * self._size)
        self._isinited = True

    def _advance(self) -> None:
        for i in range(self._rotors):
            temp = self._positions[i] + self._advances[i]
            self._positions[i] = temp % self._size
            if temp >= self._size and i < (self._rotors - 1):
                self._positions[i + 1] = (1 + self._positions[i + 1]) % self._size

    def _e_char(self, p: int) -> int:
        tp = p
        for i in range(self._rotors):
            idx = (self._positions[i] ^ tp) % self._size
            tp = self._e_rotor[(i * self._size) + idx]
        self._advance()
        return tp & 0xFF

    def _d_char(self, c: int) -> int:
        tc = c
        for i in range(self._rotors - 1, -1, -1):
            tc = (self._positions[i] ^ self._d_rotor[(i * self._size) + tc]) % self._size
        self._advance()
        return tc & 0xFF

    def _process(self, data: bytes, encrypting: bool, reinit: bool) -> bytes:
        if reinit or not self._isinited:
            self._init()
        out = bytearray(len(data))
        if encrypting:
            for i, b in enumerate(data):
                out[i] = self._e_char(b)
        else:
            for i, b in enumerate(data):
                out[i] = self._d_char(b)
        return bytes(out)

    def encrypt(self, data: bytes) -> bytes:
        return self._process(data, True, True)

    def decrypt(self, data: bytes) -> bytes:
        return self._process(data, False, True)

    def encryptmore(self, data: bytes) -> bytes:
        return self._process(data, True, False)

    def decryptmore(self, data: bytes) -> bytes:
        return self._process(data, False, False)


def newrotor(key: typing.Union[str, bytes], num_rotors: int = 6) -> RotorCipher:
    return RotorCipher(key, num_rotors=num_rotors)
