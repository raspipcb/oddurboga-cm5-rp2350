"""Fill detection via Temp2 (tub wall), ETA, and inlet-drop learning.

When Temp2 rises ≥ FILL_RISE_C within FILL_RISE_WINDOW_S after inlet flow
starts, water has reached the tub-wall probe. Overflow is a separate outlet.
"""

from __future__ import annotations

import config
from hw import ticks_diff, ticks_ms


class FillTracker:
    def __init__(self, store):
        self.store = store
        self.active = False
        self.reached_top = False
        self._start_ms = 0
        self._window_start_ms = 0
        self._window_start_tub = 0.0
        self._start_inlet = 0.0
        self.elapsed_s = 0.0
        self.eta_s = store.avg_fill_s()

    def start(self, tub_c, inlet_c):
        self.active = True
        self.reached_top = False
        self._start_ms = ticks_ms()
        self._window_start_ms = self._start_ms
        self._window_start_tub = float(tub_c)
        self._start_inlet = float(inlet_c)
        self.elapsed_s = 0.0
        self.eta_s = self.store.avg_fill_s()

    def stop(self, record=False, tub_c=0.0):
        if self.active and record and not self.reached_top:
            self.elapsed_s = ticks_diff(ticks_ms(), self._start_ms) / 1000.0
        if record and self.elapsed_s > 0:
            self.store.record_fill(self.elapsed_s, self._start_inlet, tub_c)
        self.active = False

    def update(self, tub_c):
        if not self.active or self.reached_top:
            if self.active:
                elapsed = ticks_diff(ticks_ms(), self._start_ms) / 1000.0
                self.eta_s = max(0.0, self.store.avg_fill_s() - elapsed)
            return False

        now = ticks_ms()
        elapsed = ticks_diff(now, self._start_ms) / 1000.0
        self.elapsed_s = elapsed
        self.eta_s = max(0.0, self.store.avg_fill_s() - elapsed)

        window = ticks_diff(now, self._window_start_ms) / 1000.0
        rise = float(tub_c) - self._window_start_tub
        if window >= config.FILL_RISE_WINDOW_S:
            if rise >= config.FILL_RISE_C:
                self.reached_top = True
                self.elapsed_s = elapsed
                self.store.record_fill(self.elapsed_s, self._start_inlet, tub_c)
                self.eta_s = 0.0
                return True
            self._window_start_ms = now
            self._window_start_tub = float(tub_c)
        return False

    def eta_min(self):
        return int(round(self.eta_s / 60.0))
