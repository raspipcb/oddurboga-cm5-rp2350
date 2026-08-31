"""CM5 <-> RP2350 text protocol: command building and response parsing.

Wire format, per "CM5 RPI Commands in MD format.md":

    request   COMMAND [PARAMETER]
    action    OK
    read      VALUE <data>
    status    STATUS KEY=VAL KEY=VAL ...
    info      INFO KEY=VAL ...
    failure   ERROR <code>

Nothing in this module raises on bad input. Unparseable lines become
KIND_UNKNOWN so a babbling or half-booted controller can never propagate an
exception into the link worker or the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TERMINATOR = "\n"
MAX_LINE_BYTES = 512

KIND_OK = "ok"
KIND_VALUE = "value"
KIND_STATUS = "status"
KIND_INFO = "info"
KIND_ERROR = "error"
KIND_UNKNOWN = "unknown"

_ANSWERED = (KIND_OK, KIND_VALUE, KIND_STATUS, KIND_INFO, KIND_ERROR)

# Ranges the controller documents as validated. Clamping here turns an
# avoidable ERROR INVALID_VALUE round trip into a correct request.
LIMITS = {
    "SET_INLET_OFFSET": (1.0, 5.0),
    "SET_REHEAT_HYST": (1.0, 5.0),
    "SET_TUB_CAL": (-10.0, 10.0),
}

ERROR_CODES = (
    "INVALID_CMD",
    "INVALID_VALUE",
    "SAFETY_LOCK",
    "SENSOR_FAULT",
    "BUSY",
)


@dataclass(frozen=True)
class Response:
    """One parsed reply line."""

    raw: str
    kind: str
    value: str = ""
    fields: dict = field(default_factory=dict)

    @property
    def answered(self) -> bool:
        """True when the controller gave a reply we understand, error included."""
        return self.kind in _ANSWERED

    @property
    def ok(self) -> bool:
        return self.kind in (KIND_OK, KIND_VALUE, KIND_STATUS, KIND_INFO)

    @property
    def error_code(self) -> str:
        return self.value if self.kind == KIND_ERROR else ""

    def number(self, default=None):
        try:
            return float(self.value)
        except (TypeError, ValueError):
            return default


def format_param(param) -> str:
    if isinstance(param, bool):
        return "1" if param else "0"
    if isinstance(param, float):
        return f"{param:.1f}"
    return str(param).strip()


def clamp(command: str, param):
    """Pull a numeric parameter into the controller's documented range."""
    limits = LIMITS.get(str(command).strip().upper())
    if limits is None or isinstance(param, (bool, str)) or param is None:
        return param
    lo, hi = limits
    try:
        return type(param)(min(hi, max(lo, param)))
    except (TypeError, ValueError):
        return param


def build_command(command, param=None) -> str:
    cmd = str(command or "").strip().upper()
    if param is None or param == "":
        return cmd
    return f"{cmd} {format_param(clamp(cmd, param))}"


def parse_fields(text: str) -> dict:
    """Parse `KEY=VAL` tokens, ignoring anything malformed."""
    out = {}
    for token in (text or "").split():
        if "=" not in token:
            continue
        key, _, value = token.partition("=")
        key = key.strip().upper()
        if key:
            out[key] = value.strip()
    return out


def parse_response(line) -> Response:
    """Classify one reply line. Never raises, whatever it is handed."""
    try:
        if line is None:
            raw = ""
        elif isinstance(line, (bytes, bytearray)):
            raw = bytes(line).decode("ascii", "replace").strip()
        else:
            raw = str(line).strip()
    except Exception:
        return Response(raw="", kind=KIND_UNKNOWN)

    if not raw:
        return Response(raw="", kind=KIND_UNKNOWN)

    head, _, rest = raw.partition(" ")
    keyword = head.strip().upper()
    rest = rest.strip()

    if keyword == "OK":
        return Response(raw, KIND_OK)
    if keyword == "VALUE":
        return Response(raw, KIND_VALUE, value=rest)
    if keyword == "ERROR":
        return Response(raw, KIND_ERROR, value=(rest.upper() or "UNKNOWN"))
    if keyword == "STATUS":
        return Response(raw, KIND_STATUS, fields=parse_fields(rest))
    if keyword == "INFO":
        return Response(raw, KIND_INFO, fields=parse_fields(rest))
    return Response(raw, KIND_UNKNOWN)


def parse_number(text, default=None):
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return default
