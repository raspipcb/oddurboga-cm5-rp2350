"""Timed relay drives — Relay0=hot, Relay1=cold, Relay2=drain."""

from __future__ import annotations

import config
from hw import ticks_diff, ticks_ms


class TimedRelay:
    def __init__(self, board, bit, name):
        self.name = name
        self._board = board
        self._bit = bit
        self._on_since = None
        self.forced_off = False
        self.active = False

    def request(self, on, allow=True):
        if self.forced_off or not allow:
            on = False
        if on:
            if not self.active:
                self._on_since = ticks_ms()
            self.active = True
            if self._bit is not None:
                self._board.set_relay(self._bit, True)
        else:
            self.active = False
            self._on_since = None
            if self._bit is not None:
                self._board.set_relay(self._bit, False)

    def tick(self):
        if self._bit is None:
            return False
        if not self.active or self._on_since is None:
            return False
        elapsed = ticks_diff(ticks_ms(), self._on_since) / 1000.0
        if elapsed >= config.VALVE_MAX_ON_S:
            self.forced_off = True
            self.request(False)
            return True
        return False

    def clear_force(self):
        self.forced_off = False


class Actuators:
    """Relay0=hot, Relay1=cold, Relay2=drain. Relays 3–5 unused."""

    def __init__(self, board):
        self.hot = TimedRelay(board, config.BIT_HOT, "hot")
        self.cold = TimedRelay(board, config.BIT_COLD, "cold")
        self.drain = TimedRelay(board, config.BIT_DRAIN, "drain")
        self.heat_cable = TimedRelay(board, None, "heat_cable")
        self.aux = TimedRelay(board, None, "aux")
        # Names used by MixValve.
        self.mix_hot = self.hot
        self.mix_cold = self.cold
        self._all = (self.hot, self.cold, self.drain)

    def inlet_open(self):
        """True when either inlet valve is energized (water can flow in)."""
        return self.hot.active or self.cold.active

    def close_inlet(self, allow=True):
        self.hot.request(False, allow=allow)
        self.cold.request(False, allow=allow)

    def tick(self):
        tripped = []
        for out in self._all:
            if out.tick():
                tripped.append(out.name)
        return tripped

    def all_off(self):
        for out in self._all:
            out.request(False)

    def clear_force(self):
        for out in self._all:
            out.clear_force()

    def any_forced(self):
        return any(o.forced_off for o in self._all)
