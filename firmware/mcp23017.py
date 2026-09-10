"""MCP23017 16-bit I/O expander @ 0x20 — drives the six plant relays."""

from __future__ import annotations

# Register map (IOCON.BANK = 0).
_IODIRA = 0x00
_IODIRB = 0x01
_GPIOA = 0x12
_GPIOB = 0x13
_OLATA = 0x14
_OLATB = 0x15


class MCP23017:
    def __init__(self, i2c, addr=0x20, mock_bits=None):
        self._i2c = i2c
        self._addr = addr
        self._olat = 0  # 16-bit shadow (bit0=GPA0)
        self._mock = mock_bits  # dict bit→0/1 when i2c is None
        if i2c is not None:
            # All pins outputs, start low.
            self._write(_IODIRA, b"\x00\x00")
            self._write(_OLATA, b"\x00\x00")

    def _write(self, reg, data):
        self._i2c.writeto_mem(self._addr, reg, data)

    def set_bit(self, bit, on):
        bit = int(bit)
        if bit < 0 or bit > 15:
            raise ValueError("bit")
        if on:
            self._olat |= 1 << bit
        else:
            self._olat &= ~(1 << bit)
        if self._mock is not None:
            self._mock[bit] = 1 if on else 0
            return
        lo = self._olat & 0xFF
        hi = (self._olat >> 8) & 0xFF
        self._write(_OLATA, bytes((lo, hi)))

    def get_bit(self, bit):
        if self._mock is not None:
            return bool(self._mock.get(int(bit), 0))
        return bool(self._olat & (1 << int(bit)))

    def all_off(self):
        self._olat = 0
        if self._mock is not None:
            for k in list(self._mock.keys()):
                self._mock[k] = 0
            return
        self._write(_OLATA, b"\x00\x00")
