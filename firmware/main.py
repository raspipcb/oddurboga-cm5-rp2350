"""RP2350 hot-tub controller entry point (MicroPython).

Architecture (co-work mode):
  CM5  — Linux + PyQt, UART host (/dev/serial0)
  RP2350 — owns MCP23017 relays + ADS1115 temps over I2C1, UART slave

Boot:
  1. Board() enables SENSOR_24V and talks to expander/ADC
  2. Controller + Protocol
  3. Loop: UART commands + control tick
"""

from __future__ import annotations

import config
from control import Controller
from hw import ON_DEVICE, UartPort, sleep_ms
from protocol import Protocol


def main(mock=False):
    ctl = Controller(mock=mock, mock_temps={
        "inlet": 25.0, "tub": 36.0, "outdoor": 7.0,
    } if mock else None)
    proto = Protocol(ctl)
    uart = UartPort(
        config.UART_ID, config.UART_BAUD, config.UART_TX_PIN, config.UART_RX_PIN,
        mock_lines=[] if mock else None,
    )
    uart.write_line("INFO FW=%s STATE=READY" % config.FW_VERSION)

    period_ms = int(config.CONTROL_PERIOD_S * 1000)
    while True:
        for line in uart.read_lines():
            reply = proto.handle(line)
            if reply:
                uart.write_line(reply)
        ctl.tick()
        sleep_ms(period_ms)


if __name__ == "__main__":
    main(mock=not ON_DEVICE)
