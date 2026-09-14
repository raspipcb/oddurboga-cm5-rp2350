"""Main plant controller: sequencing, setpoints, drain, recover."""

import config
from actuators import Actuators
from board import Board
from fill import FillTracker
from hw import ticks_diff, ticks_ms
from mix_valve import MixValve
from safety import Safety
from sensors import Sensors
from store import Store


class Controller:
    # High-level flow / mix phases.
    PHASE_IDLE = "IDLE"
    PHASE_PRECOOL = "PRECOOL"
    PHASE_FLOW = "FLOW"
    PHASE_REGULATE = "REGULATE"
    PHASE_RECOVER = "RECOVER"

    def __init__(self, mock_io=None, mock_temps=None, store_path=None, mock=None):
        # mock_io kept for test API compatibility; prefer mock=True.
        use_mock = True if mock is None else bool(mock)
        if mock_io is not None:
            use_mock = True
        temps = mock_temps or {}
        # Accept either role keys (tub/inlet) or TempN keys.
        board_temps = {
            "temp1": temps.get("temp1", temps.get("inlet", 25.0)),
            "temp2": temps.get("temp2", temps.get("tub", 35.0)),
            "temp3": temps.get("temp3", temps.get("outdoor", 7.0)),
        }
        self.board = Board(mock=use_mock, mock_temps_c=board_temps)
        self.store = Store(store_path)
        self.sensors = Sensors(self.board)
        self.sensors.tub_cal_c = self.store.tub_cal_c
        self.actuators = Actuators(self.board)
        self.mix = MixValve(self.actuators)
        self.safety = Safety()
        self.fill = FillTracker(self.store)
        self.recover_btn = self.board.recover_btn

        self.phase = self.PHASE_IDLE
        self.flow_wanted = False
        self.drain_wanted = "CLOSED"  # OPEN | CLOSED
        self.aux_on = False
        self._aux_until_ms = None
        self._phase_started_ms = ticks_ms()
        self._post_top_trim = False
        self.busy = False

    # --- configuration ----------------------------------------------------
    def set_target(self, value):
        lo = config.TARGET_MIN_C
        hi = config.COLD_TARGET_MAX_C if self.store.mode == "COLD" else config.TARGET_MAX_C
        if value < lo or value > hi:
            return False
        self.store.target_c = float(value)
        self.store.save()
        return True

    def set_inlet_offset(self, value):
        if value < 1.0 or value > 5.0:
            return False
        self.store.inlet_offset_c = float(value)
        self.store.save()
        return True

    def set_reheat_hyst(self, value):
        if value < 1.0 or value > 5.0:
            return False
        self.store.reheat_hyst_c = float(value)
        self.store.save()
        return True

    def set_tub_cal(self, value):
        if value < -10.0 or value > 10.0:
            return False
        self.store.tub_cal_c = float(value)
        self.sensors.tub_cal_c = float(value)
        self.store.save()
        return True

    def set_mode(self, mode):
        mode = mode.upper()
        if mode not in ("AUTO", "OFF", "COLD"):
            return False
        self.store.mode = mode
        self.store.save()
        if mode == "OFF":
            self.stop_flow()
        return True

    def set_frost_delay(self, value):
        if value < 0 or value > 3600:
            return False
        self.store.frost_delay_s = float(value)
        self.store.save()
        return True

    def set_frost_active(self, value):
        self.store.frost_active = 1 if int(value) else 0
        self.store.save()
        return True

    def set_heat_cable(self, mode):
        mode = mode.upper()
        if mode not in ("AUTO", "ON", "OFF"):
            return False
        self.store.heat_cable = mode
        self.store.save()
        return True

    def set_aux_duration(self, seconds):
        lo = config.AUX_DURATION_MIN_S
        hi = config.AUX_DURATION_MAX_S
        if seconds < lo or seconds > hi:
            return False
        self.store.aux_duration_s = float(seconds)
        self.store.save()
        return True

    def set_aux(self, on):
        on = bool(on)
        self.aux_on = on
        if on:
            duration_ms = int(self.store.aux_duration_s * 1000)
            self._aux_until_ms = ticks_ms() + duration_ms
        else:
            self._aux_until_ms = None
            self.actuators.aux.request(False)
        return True

    # --- operator requests ------------------------------------------------
    def start_flow(self):
        if self.safety.state != Safety.OK:
            return "SAFETY_LOCK"
        if self.store.mode == "OFF":
            return "BUSY"
        if self.sensors.any_fault():
            return "SENSOR_FAULT"
        self.flow_wanted = True
        if self.phase == self.PHASE_IDLE:
            self._enter(self.PHASE_PRECOOL)
            self.mix.phase = "PRECOOL"
            self.actuators.flow.request(True, allow=self.safety.allow_outputs)
            self.mix.drive_cold(allow=self.safety.allow_outputs)
        return "OK"

    def stop_flow(self):
        self.flow_wanted = False
        self.fill.stop(record=False)
        self._enter(self.PHASE_IDLE)
        allow = self.safety.allow_outputs
        self.actuators.close_inlet_path(allow=allow)
        self.mix.stop(allow=allow)
        self.mix.phase = "IDLE"
        self.busy = False
        self._post_top_trim = False
        return "OK"

    def set_drain(self, state):
        state = state.upper()
        if state not in ("OPEN", "CLOSE", "CLOSED"):
            return "INVALID_VALUE"
        if state == "CLOSE":
            state = "CLOSED"
        if self.safety.state != Safety.OK and state == "CLOSED":
            # Allow OPEN during tub overtemp (safety itself opens drain).
            if self.safety.fault != "TUB_OVERTEMP":
                return "SAFETY_LOCK"
        self.drain_wanted = "OPEN" if state == "OPEN" else "CLOSED"
        return "OK"

    def recover(self):
        """HARD_RESET emulation: cool mixer, then clear latch if safe."""
        self.flow_wanted = False
        self.actuators.close_inlet_path(allow=True)
        self.actuators.clear_force()
        self.safety.allow_outputs = True
        self._enter(self.PHASE_RECOVER)
        self.mix.phase = "RECOVER_COLD"
        self.mix.drive_cold(allow=True)
        self.busy = True
        return "OK"

    def clear_fault(self):
        """Soft clear only when not hard-locked."""
        if self.safety.state == Safety.LOCKED:
            return "SAFETY_LOCK"
        self.safety.fault = "NONE"
        return "OK"

    # --- status -----------------------------------------------------------
    def status_fields(self):
        flow = "ON" if self.actuators.flow.active else "OFF"
        drain = "OPEN" if self.actuators.drain.active or self.drain_wanted == "OPEN" else "CLOSED"
        heat = self.store.heat_cable
        if heat == "AUTO":
            heat = "ON" if self.actuators.heat_cable.active else "OFF"
        fields = {
            "MODE": self.store.mode,
            "TARGET": "%.1f" % self.store.target_c,
            "TUB": "%.1f" % self.sensors.tub_c,
            "INLET": "%.1f" % self.sensors.inlet_c,
            "OUTDOOR": "%.1f" % self.sensors.outdoor_c,
            "FLOW": flow,
            "DRAIN": drain,
            "MIX": self.mix.status_token(),
            "HEAT_CABLE": heat,
            "AUX": "ON" if self.actuators.aux.active else "OFF",
            "SAFETY": self.safety.state,
            "FAULT": self.safety.fault,
            "ETA_MIN": str(self.fill.eta_min() if self.fill.active else 0),
            "FILL_S": "%.0f" % self.fill.elapsed_s,
            "PHASE": self.phase,
            "AUX_S": str(int(max(0, self._aux_remaining_s()))),
        }
        return fields

    def _aux_remaining_s(self):
        if not self.aux_on or self._aux_until_ms is None:
            return 0
        return ticks_diff(self._aux_until_ms, ticks_ms()) / 1000.0

    # --- main tick --------------------------------------------------------
    def tick(self):
        self.sensors.update()
        actions = self.safety.evaluate(self.sensors, self.actuators)

        if self.recover_btn.pressed() and self.safety.state == Safety.LOCKED:
            self.recover()

        if actions["kill_flow"]:
            self.flow_wanted = False
            self.actuators.close_inlet_path(allow=False)
            self.fill.stop(record=False)
            if self.phase != self.PHASE_RECOVER:
                self.phase = self.PHASE_IDLE
                self.mix.stop(allow=False)
                self.busy = False

        if actions["open_drain"]:
            self.drain_wanted = "OPEN"

        allow = self.safety.allow_outputs and self.safety.state == Safety.OK
        if self.phase == self.PHASE_RECOVER:
            allow = True  # recover cold drive is permitted while unlocking

        self._tick_drain(allow or actions["open_drain"])
        self._tick_heat_cable(allow)
        self._tick_aux(allow)

        if self.phase == self.PHASE_PRECOOL:
            self._tick_precool(allow)
        elif self.phase == self.PHASE_FLOW:
            self._tick_open_flow(allow)
        elif self.phase == self.PHASE_REGULATE:
            self._tick_regulate(allow)
        elif self.phase == self.PHASE_RECOVER:
            self._tick_recover()
        else:
            self.mix.tick()
            if self.flow_wanted and self.store.mode != "OFF" and allow:
                self._enter(self.PHASE_PRECOOL)
            elif self.store.mode == "AUTO" and allow:
                self._tick_auto_reheat(allow)

        self.mix.tick()

    def _enter(self, phase):
        self.phase = phase
        self._phase_started_ms = ticks_ms()

    def _elapsed(self):
        return ticks_diff(ticks_ms(), self._phase_started_ms) / 1000.0

    def _tick_precool(self, allow):
        """Open flow shutoff + cold valve for MIX_PRECOOL_S before hot."""
        self.busy = True
        self.mix.phase = "PRECOOL"
        self.actuators.flow.request(True, allow=allow)
        self.mix.drive_cold(allow=allow)
        if self._elapsed() >= config.MIX_PRECOOL_S:
            self._enter(self.PHASE_FLOW)
            self._tick_open_flow(allow)

    def _tick_open_flow(self, allow):
        self.actuators.flow.request(True, allow=allow)
        self.fill.start(self.sensors.tub_c, self.sensors.inlet_c)
        self._post_top_trim = False
        self._enter(self.PHASE_REGULATE)

    def _tick_regulate(self, allow):
        if not self.flow_wanted:
            self.stop_flow()
            return
        self.busy = True
        self.actuators.flow.request(True, allow=allow)
        self.mix.phase = "REGULATE"
        setpoint = self.store.effective_inlet_setpoint()
        if self.fill.update(self.sensors.tub_c):
            self._post_top_trim = True
        if self._post_top_trim:
            setpoint = self.store.target_c + min(self.store.inlet_offset_c, 1.0)
        self.mix.regulate_toward(self.sensors.inlet_c, setpoint, allow=allow)

        if self.fill.reached_top and self.sensors.tub_c >= self.store.target_c:
            self.fill.stop(record=True, tub_c=self.sensors.tub_c)
            self.stop_flow()

    def _tick_recover(self):
        self.busy = True
        self.mix.phase = "RECOVER_COLD"
        self.actuators.flow.request(False, allow=True)
        self.mix.drive_cold(allow=True)
        if self._elapsed() >= config.MIX_RECOVER_COLD_S:
            cleared = self.safety.clear_if_safe(self.sensors, self.actuators)
            self.mix.stop(allow=True)
            self.mix.phase = "IDLE"
            self._enter(self.PHASE_IDLE)
            self.busy = False
            if not cleared:
                self.safety.trip(self.safety.fault or "SAFETY_LOCK", "recover incomplete")

    def _tick_auto_reheat(self, allow):
        if self.store.mode != "AUTO":
            return
        if self.sensors.tub_c <= self.store.target_c - self.store.reheat_hyst_c:
            self.flow_wanted = True
            self._enter(self.PHASE_PRECOOL)

    def _tick_drain(self, allow):
        self.actuators.drain.request(self.drain_wanted == "OPEN", allow=allow)

    def _tick_heat_cable(self, allow):
        mode = self.store.heat_cable
        on = False
        if mode == "ON":
            on = True
        elif mode == "AUTO":
            on = self.sensors.outdoor_c < config.HEAT_CABLE_ON_BELOW_C
        self.actuators.heat_cable.request(on, allow=allow)

    def _tick_aux(self, allow):
        if self.aux_on and self._aux_until_ms is not None:
            if ticks_diff(ticks_ms(), self._aux_until_ms) >= 0:
                self.aux_on = False
                self._aux_until_ms = None
                self.actuators.aux.request(False, allow=allow)
                return
        self.actuators.aux.request(self.aux_on, allow=allow)
