"""Plant I/O facade: MCP23017 relays + ADS1115 temperatures.

In CM5+RP2350 co-work mode the I2C jumper puts both chips on MCU-I2C1.
Host tests pass mock dicts and never open the bus.
"""

from __future__ import annotations

import config
from ads1115 import ADS1115
from hw import DigitalIn, open_i2c
from mcp23017 import MCP23017


class Board:
    def __init__(self, mock=False, mock_temps_c=None):
        self.mock = mock or open_i2c(mock=True) is None and not _on_device()
        i2c = None if mock else open_i2c(mock=False)
        if i2c is None:
            self.mock = True

        self._relay_bits = {}
        self.expander = MCP23017(
            i2c, config.MCP23017_ADDR,
            mock_bits=self._relay_bits if self.mock else None,
        )

        volts = None
        if self.mock:
            temps = mock_temps_c or {"temp1": 25.0, "temp2": 35.0, "temp3": 7.0}
            volts = {
                config.ADS_CH_TEMP1: _c_to_v(temps.get("temp1", temps.get("inlet", 25.0))),
                config.ADS_CH_TEMP2: _c_to_v(temps.get("temp2", temps.get("tub", 35.0))),
                config.ADS_CH_TEMP3: _c_to_v(temps.get("temp3", temps.get("outdoor", 7.0))),
            }
        self.adc = ADS1115(i2c, config.ADS1115_ADDR, mock_volts=volts)
        self._mock_temps = mock_temps_c or {}

        self.recover_btn = DigitalIn(
            config.PIN_RECOVER_BTN,
            mock=self._relay_bits if self.mock else None,
        )

        # Power the 24 V sensor loops once at boot.
        self.expander.set_bit(config.BIT_SENSOR_24V_EN, True)

    def set_relay(self, bit, on):
        self.expander.set_bit(bit, on)

    def relay(self, bit):
        return self.expander.get_bit(bit)

    def read_temp_c(self, channel):
        if self.mock and self._mock_temps:
            # Prefer live mock overrides keyed by channel role.
            key = {0: "temp1", 1: "temp2", 2: "temp3"}.get(channel)
            alt = {0: "inlet", 1: "tub", 2: "outdoor"}.get(channel)
            if key in self._mock_temps:
                return float(self._mock_temps[key])
            if alt in self._mock_temps:
                return float(self._mock_temps[alt])
        return self.adc.read_celsius(channel)

    def set_mock_temps(self, temp1=None, temp2=None, temp3=None, **legacy):
        if temp1 is None and "inlet" in legacy:
            temp1 = legacy["inlet"]
        if temp2 is None and "tub" in legacy:
            temp2 = legacy["tub"]
        if temp3 is None and "outdoor" in legacy:
            temp3 = legacy["outdoor"]
        if temp1 is not None:
            self._mock_temps["temp1"] = float(temp1)
            self.adc._mock[config.ADS_CH_TEMP1] = _c_to_v(temp1)
        if temp2 is not None:
            self._mock_temps["temp2"] = float(temp2)
            self.adc._mock[config.ADS_CH_TEMP2] = _c_to_v(temp2)
        if temp3 is not None:
            self._mock_temps["temp3"] = float(temp3)
            self.adc._mock[config.ADS_CH_TEMP3] = _c_to_v(temp3)


def _c_to_v(celsius):
    t0, t1 = config.LOOP_T_AT_4MA_C, config.LOOP_T_AT_20MA_C
    v0, v1 = config.LOOP_V_AT_4MA, config.LOOP_V_AT_20MA
    frac = (float(celsius) - t0) / (t1 - t0) if t1 != t0 else 0.0
    return v0 + frac * (v1 - v0)


def _on_device():
    from hw import ON_DEVICE
    return ON_DEVICE
