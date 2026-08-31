"""Serial link to the RP2350 controller over CM_UART0.

Rules this module is built around:

* The UI thread never touches the port and never waits on it. Callers use
  ``send()``, which returns immediately, and react to the ``call_finished``
  signal.
* Every request carries a deadline. A silent controller produces a timeout
  result, not a stalled screen.
* Any exception - open, read, write, decode - is logged, the port is dropped
  and reopened, and the worker loop continues. The loop body cannot escape.
* The request queue is bounded and coalescing, so dragging a slider or a dead
  link can never grow memory without limit.
* When no port is configured the link runs against a built-in simulator so the
  UI is fully usable on a desktop.

Wiring, per the board schematic: CM5 UART0 (GPIO14/15) is cross-connected to
the RP2350 UART0. On Raspberry Pi OS that is /dev/serial0.
"""

from __future__ import annotations

import sys
import threading
import time
from collections import deque
from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal

from api_log import FAIL, RX, STRAY, TX, log
from protocol import (
    KIND_ERROR, KIND_INFO, KIND_STATUS, MAX_LINE_BYTES, TERMINATOR, Response,
    build_command, parse_response,
)

DEFAULT_PORT_LINUX = "/dev/serial0"
DEFAULT_BAUD = 115200
DEFAULT_TIMEOUT = 1.0
QUEUE_LIMIT = 32
MAX_STRAY_LINES = 20
RECONNECT_MIN = 1.0
RECONNECT_MAX = 5.0
UNHEALTHY_AFTER = 3
IDLE_POLL = 0.2

ERR_TIMEOUT = "TIMEOUT"
ERR_OFFLINE = "OFFLINE"
ERR_IO = "IO_ERROR"
ERR_PROTOCOL = "PROTOCOL"
ERR_DROPPED = "DROPPED"


class LinkError(Exception):
    """Raised internally to force a reconnect. Never escapes the worker."""

    def __init__(self, message, code: str = ERR_IO):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------- transports


class MockTransport:
    """Stand-in controller so the UI runs without hardware attached."""

    name = "simulated"

    def __init__(self, latency: float = 0.01):
        self._latency = latency
        self._pending: deque[str] = deque()
        self._open = False
        self._state = {
            "MODE": "AUTO",
            "TARGET": 39.0,
            "TUB": 37.4,
            "INLET": 41.2,
            "FLOW": "OFF",
            "DRAIN": "CLOSED",
            "MIX": "IDLE",
            "HEAT_CABLE": "OFF",
            "AUX": "OFF",
            "SAFETY": "OK",
            "FAULT": "NONE",
            "INLET_OFFSET": 3.0,
            "REHEAT_HYST": 2.0,
            "TUB_CAL": 0.0,
        }

    def open(self):
        self._open = True

    def close(self):
        self._open = False
        self._pending.clear()

    def reset_input(self):
        self._pending.clear()

    def write_line(self, line: str):
        if not self._open:
            raise LinkError("simulator closed")
        self._pending.append(self._respond(line))

    def read_line(self, timeout: float):
        deadline = time.monotonic() + max(0.0, timeout)
        while not self._pending:
            if time.monotonic() >= deadline:
                return ""
            time.sleep(min(self._latency, 0.01))
        return self._pending.popleft()

    def _drift(self):
        """Nudge the tub toward target so the UI shows something alive."""
        target = float(self._state["TARGET"])
        tub = float(self._state["TUB"])
        if self._state["FLOW"] == "ON":
            tub += 0.1 if tub < target else -0.02
        else:
            tub -= 0.01
        self._state["TUB"] = round(max(0.0, min(60.0, tub)), 1)
        self._state["INLET"] = round(target + float(self._state["INLET_OFFSET"]), 1)

    def _respond(self, line: str) -> str:
        self._drift()
        cmd, _, param = line.strip().partition(" ")
        cmd = cmd.upper()
        param = param.strip()

        setters = {
            "SET_TARGET_TEMP": "TARGET",
            "SET_INLET_OFFSET": "INLET_OFFSET",
            "SET_REHEAT_HYST": "REHEAT_HYST",
            "SET_TUB_CAL": "TUB_CAL",
        }
        if cmd in setters:
            try:
                self._state[setters[cmd]] = float(param)
            except ValueError:
                return "ERROR INVALID_VALUE"
            return "OK"

        if cmd == "SET_MODE":
            if param.upper() not in ("AUTO", "OFF", "COLD"):
                return "ERROR INVALID_VALUE"
            self._state["MODE"] = param.upper()
            return "OK"
        if cmd == "START_FLOW":
            self._state["FLOW"] = "ON"
            self._state["MIX"] = "HEATING"
            return "OK"
        if cmd == "STOP_FLOW":
            self._state["FLOW"] = "OFF"
            self._state["MIX"] = "IDLE"
            return "OK"
        if cmd == "SET_DRAIN":
            if param.upper() not in ("OPEN", "CLOSE"):
                return "ERROR INVALID_VALUE"
            self._state["DRAIN"] = "OPEN" if param.upper() == "OPEN" else "CLOSED"
            return "OK"
        if cmd in ("SET_HEAT_CABLE", "SET_AUX", "SET_FROST_ACTIVE", "SET_FROST_DELAY"):
            key = {"SET_HEAT_CABLE": "HEAT_CABLE", "SET_AUX": "AUX"}.get(cmd)
            if key:
                self._state[key] = param.upper()
            return "OK"
        if cmd == "CLEAR_FAULT":
            self._state["FAULT"] = "NONE"
            return "OK"

        if cmd == "GET_TARGET_TEMP":
            return f"VALUE {float(self._state['TARGET']):.1f}"
        if cmd == "GET_TUB_TEMP":
            return f"VALUE {float(self._state['TUB']):.1f}"
        if cmd == "GET_INLET_TEMP":
            return f"VALUE {float(self._state['INLET']):.1f}"
        if cmd == "GET_FAULT":
            return f"VALUE {self._state['FAULT']}"
        if cmd == "GET_SYSTEM_INFO":
            return "INFO FW=1.0.0-sim STATE=READY"
        if cmd == "PING":
            return "OK"
        if cmd == "GET_STATUS":
            keys = (
                "MODE", "TARGET", "TUB", "INLET", "FLOW", "DRAIN", "MIX",
                "HEAT_CABLE", "AUX", "SAFETY", "FAULT",
            )
            body = " ".join(f"{k}={self._state[k]}" for k in keys)
            return f"STATUS {body}"
        return "ERROR INVALID_CMD"


class SerialTransport:
    """pyserial-backed transport for the real controller."""

    def __init__(self, port: str, baud: int = DEFAULT_BAUD):
        self.port = port
        self.baud = baud
        self.name = f"{port}@{baud}"
        self._serial = None

    def open(self):
        try:
            import serial
        except ImportError as exc:
            raise LinkError(f"pyserial not installed: {exc}") from exc
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.2,
                write_timeout=1.0,
            )
        except Exception as exc:
            raise LinkError(f"cannot open {self.port}: {exc}") from exc

    def close(self):
        port, self._serial = self._serial, None
        if port is None:
            return
        try:
            port.close()
        except Exception as exc:
            log.debug("ignoring error while closing %s: %s", self.port, exc)

    def reset_input(self):
        if self._serial is None:
            return
        try:
            self._serial.reset_input_buffer()
        except Exception as exc:
            raise LinkError(f"flush failed: {exc}") from exc

    def write_line(self, line: str):
        if self._serial is None:
            raise LinkError("port not open")
        try:
            self._serial.write((line + TERMINATOR).encode("ascii", "replace"))
            self._serial.flush()
        except Exception as exc:
            raise LinkError(f"write failed: {exc}") from exc

    def read_line(self, timeout: float) -> str:
        if self._serial is None:
            raise LinkError("port not open")
        try:
            self._serial.timeout = max(0.01, min(timeout, 1.0))
            raw = self._serial.readline()
        except Exception as exc:
            raise LinkError(f"read failed: {exc}") from exc
        if not raw:
            return ""
        return raw[:MAX_LINE_BYTES].decode("ascii", "replace").strip()


# ------------------------------------------------------------------- calls


@dataclass
class Call:
    command: str
    param: object = None
    label_key: str = ""
    coalesce_key: str = ""
    timeout: float = DEFAULT_TIMEOUT
    silent: bool = False
    line: str = ""

    def render(self) -> str:
        self.line = build_command(self.command, self.param)
        return self.line


@dataclass
class Result:
    call: Call
    response: Response | None = None
    error: str = ""
    elapsed_ms: int = 0

    @property
    def ok(self) -> bool:
        return not self.error and self.response is not None and self.response.ok

    @property
    def code(self) -> str:
        """Machine-readable failure code, or "" on success."""
        if self.error:
            return self.error
        if self.response is not None and self.response.kind == KIND_ERROR:
            return self.response.error_code
        return ""


class _CallQueue:
    """Bounded FIFO where a coalesce key means "latest value wins"."""

    def __init__(self, limit: int = QUEUE_LIMIT):
        self._limit = limit
        self._items: deque[Call] = deque()
        self._cond = threading.Condition()

    def push(self, call: Call) -> Call | None:
        """Queue a call. Returns any call it displaced or dropped."""
        with self._cond:
            if call.coalesce_key:
                for i, queued in enumerate(self._items):
                    if queued.coalesce_key == call.coalesce_key:
                        self._items[i] = call
                        self._cond.notify()
                        return queued
            dropped = None
            if len(self._items) >= self._limit:
                dropped = self._items.popleft()
            self._items.append(call)
            self._cond.notify()
            return dropped

    def pop(self, timeout: float) -> Call | None:
        with self._cond:
            if not self._items:
                self._cond.wait(timeout)
            if not self._items:
                return None
            return self._items.popleft()

    def drain(self) -> list[Call]:
        with self._cond:
            items = list(self._items)
            self._items.clear()
            return items

    def wake(self):
        with self._cond:
            self._cond.notify_all()

    def __len__(self):
        with self._cond:
            return len(self._items)


# -------------------------------------------------------------------- link


class DeviceLink(QObject):
    """Thread-safe, non-blocking façade over the controller serial link."""

    connection_changed = pyqtSignal(bool, str)
    call_started = pyqtSignal(object)
    call_finished = pyqtSignal(object)
    status_updated = pyqtSignal(object)
    info_updated = pyqtSignal(object)

    def __init__(self, port: str | None = None, baud: int = DEFAULT_BAUD,
                 mock: bool = False, parent=None):
        super().__init__(parent)
        self._queue = _CallQueue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._connected = False
        self._mock = mock or not port
        self._transport = MockTransport() if self._mock else SerialTransport(port, baud)
        self.description = self._transport.name

    # ---- lifecycle

    def start(self):
        if self._thread is not None:
            return
        log.info("link starting on %s", self.description)
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="device-link", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0):
        """Ask the worker to finish. Bounded wait so app exit cannot hang."""
        thread, self._thread = self._thread, None
        self._stop.set()
        self._queue.wake()
        if thread is not None:
            thread.join(timeout)
            if thread.is_alive():
                log.warning("link thread still running after %.1fs", timeout)
        log.info("link stopped")

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def simulated(self) -> bool:
        return self._mock

    # ---- request submission (UI thread, never blocks)

    def send(self, command, param=None, label_key="", coalesce=None,
             silent=False, timeout=DEFAULT_TIMEOUT) -> Call:
        call = Call(
            command=command,
            param=param,
            label_key=label_key,
            coalesce_key=(command if coalesce is None else (coalesce or "")),
            timeout=timeout,
            silent=silent,
        )
        call.render()
        displaced = self._queue.push(call)
        if displaced is not None and displaced.coalesce_key != call.coalesce_key:
            log.warning("%s queue full, dropped %s", FAIL, displaced.line)
            self._finish(Result(displaced, error=ERR_DROPPED))
        return call

    # ---- worker

    def _run(self):
        backoff = RECONNECT_MIN
        opened = False
        failures = 0
        inflight: Call | None = None
        while not self._stop.is_set():
            try:
                if not opened:
                    self._transport.open()
                    opened = True
                    failures = 0
                    backoff = RECONNECT_MIN
                    self._set_connected(True, self.description)

                call = self._queue.pop(IDLE_POLL)
                if call is None:
                    continue

                inflight = call
                result = self._exchange(call)
                inflight = None
                if result.error in (ERR_TIMEOUT, ERR_IO, ERR_PROTOCOL):
                    failures += 1
                else:
                    failures = 0
                self._finish(result)

                if failures >= UNHEALTHY_AFTER:
                    log.warning(
                        "%s %d consecutive failures, cycling %s",
                        FAIL, failures, self.description,
                    )
                    raise LinkError("link unhealthy")

            except Exception as exc:
                # Includes LinkError plus anything unforeseen: the loop must live.
                if opened:
                    log.warning("%s link fault: %s", FAIL, exc)
                else:
                    log.debug("%s link unavailable: %s", FAIL, exc)
                # A request that tripped the fault still owes its caller an
                # answer, or the UI would show no outcome for that tap.
                if inflight is not None:
                    self._finish(Result(inflight, error=getattr(exc, "code", ERR_IO)))
                    inflight = None
                self._safe_close()
                opened = False
                failures = 0
                self._set_connected(False, str(exc))
                self._fail_queued(ERR_OFFLINE)
                if self._stop.wait(backoff):
                    break
                backoff = min(RECONNECT_MAX, backoff * 2)

        self._safe_close()
        self._set_connected(False, "stopped")

    def _exchange(self, call: Call) -> Result:
        started = time.monotonic()

        def elapsed_ms():
            return int((time.monotonic() - started) * 1000)

        try:
            # Drop anything still buffered so a late reply to a previous,
            # already-timed-out request is never mistaken for this one.
            self._transport.reset_input()
            log.info("%s %s", TX, call.line)
            self._transport.write_line(call.line)
        except Exception as exc:
            log.warning("%s %s send failed: %s", FAIL, call.line, exc)
            raise LinkError(f"send failed: {exc}", ERR_IO) from exc

        strays = 0
        while True:
            remaining = call.timeout - (time.monotonic() - started)
            if remaining <= 0:
                log.warning("%s %s timeout after %d ms", FAIL, call.line, elapsed_ms())
                return Result(call, error=ERR_TIMEOUT, elapsed_ms=elapsed_ms())

            line = self._transport.read_line(remaining)
            if not line:
                time.sleep(0.001)
                continue

            response = parse_response(line)
            if response.answered:
                log.info("%s %s (%d ms)", RX, response.raw, elapsed_ms())
                self._publish(response)
                return Result(call, response=response, elapsed_ms=elapsed_ms())

            strays += 1
            log.debug("%s %s", STRAY, line[:120])
            if strays >= MAX_STRAY_LINES:
                raise LinkError(
                    f"{strays} unparseable lines from controller", ERR_PROTOCOL
                )

    def _publish(self, response: Response):
        if response.kind == KIND_STATUS and response.fields:
            self.status_updated.emit(dict(response.fields))
        elif response.kind == KIND_INFO and response.fields:
            self.info_updated.emit(dict(response.fields))

    def _finish(self, result: Result):
        self.call_finished.emit(result)

    def _fail_queued(self, error: str):
        for call in self._queue.drain():
            log.warning("%s %s not sent (%s)", FAIL, call.line, error)
            self._finish(Result(call, error=error))

    def _safe_close(self):
        try:
            self._transport.close()
        except Exception as exc:
            log.debug("ignoring close error: %s", exc)

    def _set_connected(self, connected: bool, detail: str):
        if connected == self._connected:
            return
        self._connected = connected
        log.info("link %s (%s)", "up" if connected else "down", detail)
        self.connection_changed.emit(connected, detail)


def default_port() -> str | None:
    """Best guess for CM_UART0 on the host we're running on."""
    if sys.platform.startswith("linux"):
        return DEFAULT_PORT_LINUX
    return None
