"""Local safety latch: overtemp + valve timeout → HARD lock until RECOVER."""

from __future__ import annotations

import config


class Safety:
    OK = "OK"
    LOCKED = "LOCKED"

    def __init__(self):
        self.state = self.OK
        self.fault = "NONE"
        self.lock_reason = ""
        self.allow_outputs = True

    def trip(self, fault, reason=""):
        self.state = self.LOCKED
        self.fault = fault
        self.lock_reason = reason or fault
        self.allow_outputs = False

    def clear_if_safe(self, sensors, actuators):
        """RECOVER may clear the latch only when sensors are healthy again."""
        if sensors.any_fault():
            return False
        if sensors.inlet_c >= config.INLET_CUTOFF_C:
            return False
        if sensors.tub_c >= config.TUB_CUTOFF_C:
            return False
        actuators.clear_force()
        self.state = self.OK
        self.fault = "NONE"
        self.lock_reason = ""
        self.allow_outputs = True
        return True

    def evaluate(self, sensors, actuators):
        """Run every control tick. Returns action hints for the controller."""
        actions = {
            "kill_flow": False,
            "open_drain": False,
            "tripped": False,
        }

        # Sensor sanity: refuse to energize valves.
        if sensors.any_fault():
            self.trip("SENSOR_FAULT", "sensor out of range")
            actions["kill_flow"] = True
            actions["tripped"] = True
            return actions

        # Inlet / Temp1 overtemp → flow OFF.
        if sensors.inlet_c >= config.INLET_CUTOFF_C:
            self.trip("INLET_OVERTEMP", "temp1/inlet >= %.1f" % config.INLET_CUTOFF_C)
            actions["kill_flow"] = True
            actions["tripped"] = True

        # Tub / Temp2 overtemp → flow OFF + drain OPEN.
        if sensors.tub_c >= config.TUB_CUTOFF_C:
            self.trip("TUB_OVERTEMP", "temp2/tub >= %.1f" % config.TUB_CUTOFF_C)
            actions["kill_flow"] = True
            actions["open_drain"] = True
            actions["tripped"] = True

        # Per-valve 120 s force-off.
        tripped = actuators.tick()
        if tripped:
            self.trip("VALVE_TIMEOUT", "timeout:" + ",".join(tripped))
            actions["kill_flow"] = True
            actions["tripped"] = True

        if self.state == self.LOCKED:
            self.allow_outputs = False
        return actions
