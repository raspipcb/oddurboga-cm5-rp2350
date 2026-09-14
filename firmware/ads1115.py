"""ADS1115 16-bit ADC @ 0x49 — three 4–20 mA temperature channels."""

import config

# Pointer / config bits.
_REG_CONV = 0x00
_REG_CFG = 0x01

# MUX single-ended AIN0..AIN3 vs GND.
_MUX_SINGLE = (0x4000, 0x5000, 0x6000, 0x7000)
# PGA: 0=±6.144 1=±4.096 2=±2.048 …
_PGA = {0: 0x0000, 1: 0x0200, 2: 0x0400, 3: 0x0600}
_PGA_FS = {0: 6.144, 1: 4.096, 2: 2.048, 3: 1.024}

_OS_SINGLE = 0x8000
_MODE_SINGLE = 0x0100
_DR_128 = 0x0080  # 128 SPS


class ADS1115:
    def __init__(self, i2c, addr=0x49, mock_volts=None):
        self._i2c = i2c
        self._addr = addr
        self._mock = mock_volts  # dict channel→volts
        self._pga = config.ADS_PGA

    def read_volts(self, channel):
        channel = int(channel)
        if self._mock is not None:
            return float(self._mock.get(channel, 0.0))
        cfg = (
            _OS_SINGLE
            | _MUX_SINGLE[channel]
            | _PGA.get(self._pga, 0x0200)
            | _MODE_SINGLE
            | _DR_128
            | 0x0003  # disable comparator
        )
        self._i2c.writeto_mem(self._addr, _REG_CFG, bytes((cfg >> 8, cfg & 0xFF)))
        # 128 SPS ≈ 8 ms; wait a bit longer.
        try:
            from hw import sleep_ms
            sleep_ms(10)
        except Exception:
            pass
        raw = self._i2c.readfrom_mem(self._addr, _REG_CONV, 2)
        value = (raw[0] << 8) | raw[1]
        if value & 0x8000:
            value -= 1 << 16
        fs = _PGA_FS.get(self._pga, 4.096)
        return value * fs / 32768.0

    def read_celsius(self, channel):
        """Map RCV420 voltage (4–20 mA loop) to °C."""
        volts = self.read_volts(channel)
        v0 = config.LOOP_V_AT_4MA
        v1 = config.LOOP_V_AT_20MA
        t0 = config.LOOP_T_AT_4MA_C
        t1 = config.LOOP_T_AT_20MA_C
        if v1 <= v0:
            return t0
        frac = (volts - v0) / (v1 - v0)
        return t0 + frac * (t1 - t0)
