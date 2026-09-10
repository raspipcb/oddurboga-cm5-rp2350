"""Host-side tests for firmware control / safety (no MicroPython needed).

Run from repo root:
  python firmware/tests/test_firmware.py
or:
  cd firmware && python tests/test_firmware.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config  # noqa: E402
from control import Controller  # noqa: E402
from protocol import Protocol  # noqa: E402


PASSED = []
FAILED = []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print("  PASS  " + name)
    else:
        FAILED.append(name + " " + detail)
        print("  FAIL  " + name + " " + detail)


def make_ctl(**temps):
    path = tempfile.mktemp(suffix=".json")
    mock_io = {}
    mock_temps = {"tub": 35.0, "inlet": 25.0, "outdoor": 7.0}
    mock_temps.update(temps)
    return Controller(mock_io=mock_io, mock_temps=mock_temps, store_path=path)


def pump(ctl, seconds, step=None):
    step = step or config.CONTROL_PERIOD_S
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        ctl.tick()
        time.sleep(step)


def test_protocol_basics():
    print("\nprotocol basics")
    ctl = make_ctl()
    p = Protocol(ctl)
    check("PING", p.handle("PING") == "OK")
    check("unknown", p.handle("NOPE") == "ERROR INVALID_CMD")
    check("set target", p.handle("SET_TARGET_TEMP 40") == "OK")
    check("get target", p.handle("GET_TARGET_TEMP") == "VALUE 40.0")
    check("bad offset", p.handle("SET_INLET_OFFSET 9") == "ERROR INVALID_VALUE")
    check("cal", p.handle("SET_TUB_CAL 1.5") == "OK")
    status = p.handle("GET_STATUS")
    check("status has TUB", "TUB=" in status)
    check("status has SAFETY", "SAFETY=OK" in status)


def test_precool_before_flow():
    print("\nprecool then open flow")
    # Shorten timings for the test.
    old_pre, old_full = config.MIX_PRECOOL_S, config.MIX_FULL_STROKE_S
    config.MIX_PRECOOL_S = 0.4
    config.MIX_FULL_STROKE_S = 1.0
    try:
        ctl = make_ctl(tub=34.0, inlet=22.0)
        check("start accepted", ctl.start_flow() == "OK")
        check("phase precool", ctl.phase == Controller.PHASE_PRECOOL)
        check("cold valve during precool", ctl.actuators.cold.active)
        check("hot valve off during precool", not ctl.actuators.hot.active)
        pump(ctl, 0.55)
        check("reached regulate", ctl.phase == Controller.PHASE_REGULATE, ctl.phase)
        check("flow wanted after precool", ctl.flow_wanted)
    finally:
        config.MIX_PRECOOL_S, config.MIX_FULL_STROKE_S = old_pre, old_full


def test_inlet_overtemp_kills_flow():
    print("\ninlet overtemp safety")
    ctl = make_ctl(tub=38.0, inlet=50.0)
    ctl.start_flow()
    # Force into regulate with flow wanted.
    ctl.phase = Controller.PHASE_REGULATE
    ctl.flow_wanted = True
    ctl.actuators.hot.request(True)
    ctl.tick()
    check("safety locked", ctl.safety.state == "LOCKED")
    check("fault inlet", ctl.safety.fault == "INLET_OVERTEMP")
    check("inlet valves closed", not ctl.actuators.inlet_open())
    p = Protocol(ctl)
    check("start blocked", p.handle("START_FLOW") == "ERROR SAFETY_LOCK")
    check("clear_fault blocked", p.handle("CLEAR_FAULT") == "ERROR SAFETY_LOCK")


def test_tub_overtemp_opens_drain():
    print("\ntub overtemp opens drain")
    ctl = make_ctl(tub=49.5, inlet=40.0)
    ctl.flow_wanted = True
    ctl.actuators.hot.request(True)
    ctl.tick()
    check("fault tub", ctl.safety.fault == "TUB_OVERTEMP")
    check("inlet valves closed", not ctl.actuators.inlet_open())
    check("drain requested open", ctl.drain_wanted == "OPEN")
    check("drain coil on", ctl.actuators.drain.active)


def test_valve_timeout():
    print("\nvalve 120s force-off")
    old = config.VALVE_MAX_ON_S
    config.VALVE_MAX_ON_S = 0.3
    try:
        ctl = make_ctl(tub=39.0, inlet=25.0)  # at target so AUTO won't reheat
        ctl.set_mode("OFF")
        ctl.actuators.hot.request(True)
        pump(ctl, 0.5)
        check("hot forced off", not ctl.actuators.hot.active)
        check("force latch set", ctl.actuators.hot.forced_off)
        check("timeout fault", ctl.safety.fault == "VALVE_TIMEOUT", ctl.safety.fault)
        check("locked", ctl.safety.state == "LOCKED", ctl.safety.state)
    finally:
        config.VALVE_MAX_ON_S = old


def test_recover_cools_then_unlocks():
    print("\nRECOVER cools mixer and unlocks")
    old = config.MIX_RECOVER_COLD_S
    config.MIX_RECOVER_COLD_S = 0.4
    try:
        ctl = make_ctl(tub=38.0, inlet=40.0)
        ctl.safety.trip("INLET_OVERTEMP", "test")
        ctl.actuators.hot.forced_off = True
        p = Protocol(ctl)
        check("recover ok", p.handle("RECOVER") == "OK")
        check("recover phase", ctl.phase == Controller.PHASE_RECOVER)
        check("cold valve on", ctl.actuators.cold.active)
        ctl.sensors.set_mock(inlet=30.0, tub=38.0)
        pump(ctl, 0.6)
        check("unlocked", ctl.safety.state == "OK", ctl.safety.state)
        check("fault cleared", ctl.safety.fault == "NONE")
        check("idle after recover", ctl.phase == Controller.PHASE_IDLE)
    finally:
        config.MIX_RECOVER_COLD_S = old


def test_fill_detection_and_eta():
    print("\nfill rise detection")
    old_w = config.FILL_RISE_WINDOW_S
    config.FILL_RISE_WINDOW_S = 0.3
    try:
        ctl = make_ctl(tub=30.0, inlet=42.0)
        ctl.fill.start(30.0, 42.0)
        check("eta seeded", ctl.fill.eta_min() >= 0)
        time.sleep(0.15)
        ctl.sensors.set_mock(tub=33.0)
        ctl.sensors.update()
        ctl.fill.update(ctl.sensors.tub_c)
        check("not yet top", not ctl.fill.reached_top)
        time.sleep(0.2)
        ctl.sensors.set_mock(tub=36.5)  # +6.5 from window start if window slid...
        # Restart clean window for a clear >5°C rise.
        ctl.fill.start(30.0, 42.0)
        time.sleep(0.35)
        hit = ctl.fill.update(36.0)
        check("reached top", hit and ctl.fill.reached_top)
        check("fill recorded", len(ctl.store.fill_times) >= 1)
    finally:
        config.FILL_RISE_WINDOW_S = old_w


def test_calibration_applied():
    print("\ntub calibration")
    ctl = make_ctl(tub=38.0)
    ctl.set_tub_cal(2.0)
    ctl.sensors.set_mock(tub=38.0)
    ctl.sensors.update()
    check("cal added", abs(ctl.sensors.tub_c - 40.0) < 0.05, str(ctl.sensors.tub_c))


def main():
    print("firmware control suite")
    test_protocol_basics()
    test_precool_before_flow()
    test_inlet_overtemp_kills_flow()
    test_tub_overtemp_opens_drain()
    test_valve_timeout()
    test_recover_cools_then_unlocks()
    test_fill_detection_and_eta()
    test_calibration_applied()
    print("\n%d passed, %d failed" % (len(PASSED), len(FAILED)))
    for f in FAILED:
        print("  - " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
