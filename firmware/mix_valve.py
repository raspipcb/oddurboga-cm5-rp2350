"""Hot / cold inlet valves (Relay 0 / Relay 1) with open-loop mix estimate.

Interlock: hot and cold are never energized together. Full travel ≈ 60 s.
"""

from __future__ import annotations

import config
from hw import ticks_diff, ticks_ms


class MixValve:
    def __init__(self, actuators):
        self._act = actuators
        self.position = 0.5  # 0=full cold, 1=full hot
        self._dir = 0
        self._last_ms = ticks_ms()
        self.phase = "IDLE"

    def stop(self, allow=True):
        self._update_position()
        self._dir = 0
        self._act.close_inlet(allow=allow)

    def drive_cold(self, allow=True):
        self._update_position()
        self._dir = -1
        self._act.hot.request(False, allow=allow)
        self._act.cold.request(True, allow=allow)

    def drive_hot(self, allow=True):
        self._update_position()
        self._dir = 1
        self._act.cold.request(False, allow=allow)
        self._act.hot.request(True, allow=allow)

    def _update_position(self):
        now = ticks_ms()
        dt = ticks_diff(now, self._last_ms) / 1000.0
        self._last_ms = now
        if self._dir == 0 or dt <= 0:
            return
        delta = dt / config.MIX_FULL_STROKE_S
        self.position = max(0.0, min(1.0, self.position + self._dir * delta))
        if (self._dir < 0 and self.position <= 0.0) or (self._dir > 0 and self.position >= 1.0):
            self._dir = 0
            self._act.close_inlet()

    def tick(self):
        self._update_position()

    def regulate_toward(self, inlet_c, setpoint_c, allow=True, band=0.4):
        self._update_position()
        err = float(setpoint_c) - float(inlet_c)
        if err > band:
            self.drive_hot(allow=allow)
            return "HEATING"
        if err < -band:
            self.drive_cold(allow=allow)
            return "COOLING"
        self.stop(allow=allow)
        return "HOLD"

    def status_token(self):
        if self.phase == "PRECOOL":
            return "PRECOOL"
        if self.phase == "RECOVER_COLD":
            return "RECOVER"
        if self._dir > 0:
            return "HEATING"
        if self._dir < 0:
            return "COOLING"
        return "IDLE"
