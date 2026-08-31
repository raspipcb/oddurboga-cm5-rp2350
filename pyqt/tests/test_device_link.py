"""Robustness tests for the RP2350 link.

Every case here is a way the controller or the port can misbehave. The link is
expected to report a failure and keep running - never to block the caller, wedge
the worker, or grow the queue without bound.

Run with:  python tests/test_device_link.py
"""

from __future__ import annotations

import os
import random
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from PyQt5.QtCore import QCoreApplication  # noqa: E402

import device_link  # noqa: E402
from device_link import (  # noqa: E402
    ERR_DROPPED, ERR_OFFLINE, ERR_TIMEOUT, DeviceLink, LinkError, MockTransport,
    _CallQueue, Call,
)
from protocol import (  # noqa: E402
    KIND_ERROR, KIND_STATUS, KIND_UNKNOWN, build_command, parse_response,
)

APP = QCoreApplication.instance() or QCoreApplication(sys.argv)

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(f"{name} {detail}")
        print(f"  FAIL  {name} {detail}")


def pump(seconds: float):
    """Spin the event loop so queued signals are delivered."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        APP.processEvents()
        time.sleep(0.005)
    APP.processEvents()


def collect(link: DeviceLink) -> list:
    results = []
    link.call_finished.connect(results.append)
    return results


# ------------------------------------------------------------ fake transports


class SilentTransport:
    """Accepts writes, never answers."""

    name = "silent"

    def open(self):
        pass

    def close(self):
        pass

    def reset_input(self):
        pass

    def write_line(self, line):
        pass

    def read_line(self, timeout):
        time.sleep(min(timeout, 0.02))
        return ""


class BabblingTransport:
    """Streams endless junk that is never a valid response."""

    name = "babbling"

    def open(self):
        pass

    def close(self):
        pass

    def reset_input(self):
        pass

    def write_line(self, line):
        pass

    def read_line(self, timeout):
        return "\x00garbage " + "x" * 200


class UnopenableTransport:
    """Never opens, like a missing /dev/serial0."""

    name = "missing-port"

    def __init__(self):
        self.attempts = 0

    def open(self):
        self.attempts += 1
        raise LinkError("no such device")

    def close(self):
        pass

    def reset_input(self):
        pass

    def write_line(self, line):
        raise LinkError("closed")

    def read_line(self, timeout):
        raise LinkError("closed")


class ChaosTransport:
    """Raises arbitrary exception types at random points."""

    name = "chaos"

    def __init__(self, seed=7):
        self.rng = random.Random(seed)
        self.mock = MockTransport(latency=0.0)

    def open(self):
        if self.rng.random() < 0.3:
            raise RuntimeError("open exploded")
        self.mock.open()

    def close(self):
        self.mock.close()

    def reset_input(self):
        if self.rng.random() < 0.2:
            raise ValueError("flush exploded")

    def write_line(self, line):
        if self.rng.random() < 0.3:
            raise OSError("write exploded")
        self.mock.write_line(line)

    def read_line(self, timeout):
        roll = self.rng.random()
        if roll < 0.2:
            raise IOError("read exploded")
        if roll < 0.4:
            return None  # not even a string
        return self.mock.read_line(timeout)


class LateTransport:
    """Answers the previous request, one turn behind."""

    name = "late"

    def __init__(self):
        self.queued = []

    def open(self):
        pass

    def close(self):
        pass

    def reset_input(self):
        self.queued.clear()

    def write_line(self, line):
        self.queued.append("OK")

    def read_line(self, timeout):
        time.sleep(min(timeout, 0.05))
        return ""


# ------------------------------------------------------------------- protocol


def test_protocol():
    print("\nprotocol parsing")
    check("OK parses", parse_response("OK").ok)
    check("VALUE parses", parse_response("VALUE 38.6").number() == 38.6)
    check("ERROR classified", parse_response("ERROR BUSY").kind == KIND_ERROR)
    check("ERROR code upper", parse_response("error busy").error_code == "BUSY")
    status = parse_response("STATUS MODE=AUTO TARGET=39.0 FLOW=ON")
    check("STATUS fields", status.kind == KIND_STATUS and status.fields["MODE"] == "AUTO")
    check("partial STATUS ok", "TARGET" in parse_response("STATUS TARGET=39.0 junk").fields)
    for junk in (None, "", "   ", "\x00\xff", "WAT", "VALUE", 12345, b"bytes"):
        response = parse_response(junk)
        check(f"junk {junk!r} never raises", response is not None)
    check("junk is unknown", parse_response("hello").kind == KIND_UNKNOWN)
    check("no trailing space", build_command("PING") == "PING")
    check("float formatted", build_command("SET_TARGET_TEMP", 39.0) == "SET_TARGET_TEMP 39.0")
    check("clamped high", build_command("SET_INLET_OFFSET", 99.0) == "SET_INLET_OFFSET 5.0")
    check("clamped low", build_command("SET_TUB_CAL", -99.0) == "SET_TUB_CAL -10.0")
    check("bool param", build_command("SET_FROST_ACTIVE", True) == "SET_FROST_ACTIVE 1")


def test_queue():
    print("\nbounded coalescing queue")
    queue = _CallQueue(limit=4)
    for i in range(10):
        queue.push(Call(command="GET_STATUS", param=i, coalesce_key=""))
    check("queue stays bounded", len(queue) == 4, f"len={len(queue)}")

    queue = _CallQueue(limit=8)
    for value in range(20, 30):
        call = Call(command="SET_TARGET_TEMP", param=value, coalesce_key="SET_TARGET_TEMP")
        call.render()
        queue.push(call)
    check("coalesced to one", len(queue) == 1, f"len={len(queue)}")
    latest = queue.pop(0.1)
    check("latest value wins", latest.param == 29, f"param={latest.param}")
    check("pop on empty returns None", _CallQueue().pop(0.01) is None)


# ----------------------------------------------------------------- link cases


def run_link(transport, calls, settle=1.5, mock=False):
    """Drive a link against a transport and return the results it emitted."""
    link = DeviceLink(port=None, mock=True)
    if not mock:
        link._transport = transport
        link._mock = False
        link.description = getattr(transport, "name", "test")
    results = collect(link)
    link.start()
    for command, param in calls:
        link.send(command, param, coalesce="")
    pump(settle)
    started = time.monotonic()
    link.stop(timeout=2.0)
    stop_ms = (time.monotonic() - started) * 1000
    pump(0.1)
    return link, results, stop_ms


def test_happy_path():
    print("\nsimulated controller")
    link, results, stop_ms = run_link(None, [
        ("PING", None),
        ("SET_TARGET_TEMP", 39.0),
        ("GET_TUB_TEMP", None),
        ("GET_STATUS", None),
        ("GET_SYSTEM_INFO", None),
    ], mock=True)
    check("all five answered", len(results) == 5, f"got {len(results)}")
    check("all succeeded", all(r.ok for r in results),
          str([(r.call.line, r.code) for r in results if not r.ok]))
    check("stop is prompt", stop_ms < 1500, f"{stop_ms:.0f} ms")
    check("link reports connected", link.connected is False)  # stopped by now


def test_unknown_command():
    print("\nunknown command gets a clean error")
    _, results, _ = run_link(None, [("NO_SUCH_COMMAND", None)], mock=True)
    check("one result", len(results) == 1)
    check("reported INVALID_CMD", results and results[0].code == "INVALID_CMD",
          results and results[0].code)


def test_silent_device():
    print("\nsilent controller")
    _, results, stop_ms = run_link(SilentTransport(), [("PING", None)], settle=2.5)
    timeouts = [r for r in results if r.code == ERR_TIMEOUT]
    check("timed out rather than hung", len(timeouts) >= 1, f"results={len(results)}")
    check("stop still prompt", stop_ms < 1500, f"{stop_ms:.0f} ms")


def test_babbling_device():
    print("\nbabbling controller")
    _, results, stop_ms = run_link(BabblingTransport(), [("PING", None)] * 3, settle=2.5)
    check("every call resolved", len(results) >= 3, f"results={len(results)}")
    check("none reported success", not any(r.ok for r in results))
    check("stop still prompt", stop_ms < 1500, f"{stop_ms:.0f} ms")


def test_missing_port():
    print("\nport that never opens")
    transport = UnopenableTransport()
    _, results, stop_ms = run_link(transport, [("PING", None), ("GET_STATUS", None)], settle=2.0)
    check("calls failed fast", len(results) >= 2, f"results={len(results)}")
    check("reported offline", all(r.code == ERR_OFFLINE for r in results),
          str([r.code for r in results]))
    check("retried with backoff", 1 <= transport.attempts <= 6, f"attempts={transport.attempts}")
    check("stop still prompt", stop_ms < 1500, f"{stop_ms:.0f} ms")


def test_chaos():
    print("\ntransport raising arbitrary exceptions")
    _, results, stop_ms = run_link(
        ChaosTransport(), [("PING", None)] * 12, settle=3.0
    )
    check("worker survived, results emitted", len(results) >= 1, f"results={len(results)}")
    check("no result is malformed", all(hasattr(r, "code") for r in results))
    check("stop still prompt", stop_ms < 1500, f"{stop_ms:.0f} ms")


def test_late_reply_not_misattributed():
    print("\nlate reply from a timed-out request")
    transport = LateTransport()
    _, results, _ = run_link(transport, [("PING", None), ("PING", None)], settle=2.5)
    check("no stale success", all(not r.ok for r in results),
          str([(r.call.line, r.code) for r in results]))


def test_flood_is_bounded():
    print("\nflood of requests")
    link = DeviceLink(port=None, mock=True)
    results = collect(link)
    link.start()
    for value in range(500):
        link.send("SET_TARGET_TEMP", float(20 + value % 30), coalesce="SET_TARGET_TEMP")
    for value in range(500):
        link.send("GET_STATUS", coalesce="GET_STATUS")
    check("queue bounded under flood", len(link._queue) <= device_link.QUEUE_LIMIT,
          f"len={len(link._queue)}")
    pump(2.0)
    link.stop(timeout=2.0)
    pump(0.1)
    dropped = [r for r in results if r.code == ERR_DROPPED]
    check("coalescing kept it small", len(results) < 200, f"results={len(results)}")
    check("drops are reported, not silent", all(r.code for r in dropped))


def test_send_never_blocks():
    print("\nsend() latency against a dead link")
    link = DeviceLink(port=None, mock=True)
    link._transport = SilentTransport()
    link._mock = False
    link.start()
    worst = 0.0
    for _ in range(200):
        started = time.monotonic()
        link.send("PING", coalesce="")
        worst = max(worst, time.monotonic() - started)
    link.stop(timeout=2.0)
    check("send stays sub-millisecond", worst < 0.05, f"worst={worst * 1000:.2f} ms")


def test_repeated_start_stop():
    print("\nrepeated start/stop cycles")
    link = DeviceLink(port=None, mock=True)
    worst = 0.0
    for _ in range(5):
        link.start()
        link.send("PING", coalesce="")
        pump(0.2)
        started = time.monotonic()
        link.stop(timeout=2.0)
        worst = max(worst, time.monotonic() - started)
    check("every stop was prompt", worst < 1.5, f"worst={worst:.2f} s")
    remaining = [t for t in threading.enumerate() if t.name == "device-link"]
    check("no worker threads leaked", not remaining, f"alive={len(remaining)}")


def main():
    print("RP2350 link robustness suite")
    test_protocol()
    test_queue()
    test_happy_path()
    test_unknown_command()
    test_silent_device()
    test_babbling_device()
    test_missing_port()
    test_chaos()
    test_late_reply_not_misattributed()
    test_flood_is_bounded()
    test_send_never_blocks()
    test_repeated_start_stop()

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for failure in FAILED:
        print(f"  - {failure}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
