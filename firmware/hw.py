"""Low-level time/UART helpers + I2C open for RP2350 or host mock."""

try:
    from machine import I2C, Pin, UART  # type: ignore
    import time as _time

    ON_DEVICE = True
except ImportError:
    I2C = Pin = UART = None  # type: ignore
    import time as _time

    ON_DEVICE = False


def ticks_ms():
    if ON_DEVICE:
        return _time.ticks_ms()  # type: ignore[attr-defined]
    return int(_time.monotonic() * 1000)


def ticks_diff(a, b):
    if ON_DEVICE:
        return _time.ticks_diff(a, b)  # type: ignore[attr-defined]
    return a - b


def sleep_ms(ms):
    if ON_DEVICE:
        _time.sleep_ms(ms)  # type: ignore[attr-defined]
    else:
        _time.sleep(ms / 1000.0)


class DigitalIn:
    def __init__(self, pin_no, pull_up=True, mock=None):
        self.pin_no = pin_no
        self._mock = mock
        if pin_no is None:
            self._pin = None
            return
        if ON_DEVICE and mock is None:
            pull = Pin.PULL_UP if pull_up else None
            self._pin = Pin(pin_no, Pin.IN, pull)
        else:
            self._pin = None
            if mock is not None and pin_no not in mock:
                mock[pin_no] = 1

    def raw(self):
        if self.pin_no is None:
            return 1
        if self._pin is not None:
            return self._pin.value()
        if self._mock is not None:
            return int(self._mock.get(self.pin_no, 1))
        return 1

    def pressed(self):
        return self.pin_no is not None and self.raw() == 0


class UartPort:
    def __init__(self, uart_id, baud, tx, rx, mock_lines=None):
        self._buf = bytearray()
        self._mock_rx = mock_lines if mock_lines is not None else []
        self._mock_tx = []
        if ON_DEVICE and mock_lines is None:
            # Large RX buffer so CM5 bursts cannot overrun the FIFO while we
            # service I2C in the control tick.
            self._uart = UART(
                uart_id, baudrate=baud, tx=Pin(tx), rx=Pin(rx), rxbuf=512,
            )
        else:
            self._uart = None

    def write_line(self, text):
        line = text if text.endswith("\n") else text + "\n"
        if self._uart is not None:
            self._uart.write(line.encode("ascii", "ignore"))
        else:
            self._mock_tx.append(line.rstrip("\n"))

    def read_lines(self):
        lines = []
        if self._uart is not None:
            n = self._uart.any()
            if n:
                self._buf.extend(self._uart.read(n) or b"")
        else:
            while self._mock_rx:
                self._buf.extend((self._mock_rx.pop(0) + "\n").encode("ascii"))
        while True:
            end = -1
            for sep in (0x0A, 0x0D):
                try:
                    end = self._buf.index(sep)
                    break
                except ValueError:
                    continue
            if end < 0:
                break
            raw = bytes(self._buf[:end])
            del self._buf[: end + 1]
            # Swallow a paired CRLF or LFCR.
            while self._buf[:1] in (b"\r", b"\n"):
                del self._buf[:1]
            try:
                line = raw.decode("ascii", "ignore").strip()
            except Exception:
                continue
            if line:
                lines.append(line)
        return lines


def open_i2c(mock=False):
    """Return machine.I2C or None when mocking on host."""
    if mock or not ON_DEVICE:
        return None
    import config
    return I2C(
        config.I2C_ID,
        scl=Pin(config.I2C_SCL_PIN),
        sda=Pin(config.I2C_SDA_PIN),
        freq=config.I2C_FREQ_HZ,
    )
