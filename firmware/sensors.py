"""Temperature probes via ADS1115 ← RCV420 ← PT1000 sensor boards.

  Temp1 = inlet / control-side (ADS CH0)  → API field INLET
  Temp2 = tub wall (ADS CH1)             → API field TUB
           (overflow is a separate outlet — not this sensor)
  Temp3 = outdoor optional (ADS CH2)     → API field OUTDOOR
"""

from __future__ import annotations

import config


class Sensors:
    def __init__(self, board):
        self._board = board
        self.tub_c = 20.0
        self.inlet_c = 20.0
        self.outdoor_c = 10.0
        self.tub_ok = True
        self.inlet_ok = True
        self.outdoor_ok = True
        self.tub_cal_c = 0.0

    def set_mock(self, tub=None, inlet=None, outdoor=None):
        self._board.set_mock_temps(temp1=inlet, temp2=tub, temp3=outdoor)

    def update(self):
        raw_inlet = self._board.read_temp_c(config.ADS_CH_TEMP1)
        raw_tub = self._board.read_temp_c(config.ADS_CH_TEMP2)
        raw_out = self._board.read_temp_c(config.ADS_CH_TEMP3)

        self.inlet_ok = config.SENSOR_MIN_C <= raw_inlet <= config.SENSOR_MAX_C
        self.tub_ok = config.SENSOR_MIN_C <= raw_tub <= config.SENSOR_MAX_C
        self.outdoor_ok = config.SENSOR_MIN_C <= raw_out <= config.SENSOR_MAX_C

        self.inlet_c = raw_inlet
        self.tub_c = raw_tub + float(self.tub_cal_c)
        self.outdoor_c = raw_out

    def any_fault(self):
        # Outdoor is optional; tub + inlet are required for control/safety.
        return not (self.tub_ok and self.inlet_ok)
