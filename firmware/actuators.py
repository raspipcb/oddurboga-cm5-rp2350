"""Timed relay drives — flow, hot, cold, drain, heat cable, aux."""

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
    """Relay0=flow, 1=hot, 2=cold, 3=drain, 4=heat cable, 5=aux."""

    def __init__(self, board):
        self.flow = TimedRelay(board, config.BIT_FLOW, "flow")
        self.hot = TimedRelay(board, config.BIT_HOT, "hot")
        self.cold = TimedRelay(board, config.BIT_COLD, "cold")
        self.drain = TimedRelay(board, config.BIT_DRAIN, "drain")
        self.heat_cable = TimedRelay(board, config.BIT_HEAT_CABLE, "heat_cable")
        self.aux = TimedRelay(board, config.BIT_AUX, "aux")
        # Names used by MixValve.
        self.mix_hot = self.hot
        self.mix_cold = self.cold
        self._timed = (
            self.flow, self.hot, self.cold, self.drain,
            self.heat_cable, self.aux,
        )

    def mixing_open(self):
        """True when hot or cold mixing valve is energized."""
        return self.hot.active or self.cold.active

    def close_mixer(self, allow=True):
        self.hot.request(False, allow=allow)
        self.cold.request(False, allow=allow)

    def close_inlet_path(self, allow=True):
        """Close flow shutoff and both mixing valves."""
        self.flow.request(False, allow=allow)
        self.close_mixer(allow=allow)

    # Back-compat alias used by mix_valve / older call sites.
    def close_inlet(self, allow=True):
        self.close_mixer(allow=allow)

    def inlet_open(self):
        """Flow relay on (water may pass to the mixer)."""
        return self.flow.active

    def tick(self):
        tripped = []
        for out in self._timed:
            if out.tick():
                tripped.append(out.name)
        return tripped

    def all_off(self):
        for out in self._timed:
            out.request(False)

    def clear_force(self):
        for out in self._timed:
            out.clear_force()

    def any_forced(self):
        return any(o.forced_off for o in self._timed)
