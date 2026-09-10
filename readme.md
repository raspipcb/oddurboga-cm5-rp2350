# oddurboga-cm5-rp2350

Smart hot-tub control: Raspberry Pi CM5 HMI + RP2350 plant controller (co-work mode).

| Path | Role |
|------|------|
| [`pyqt/`](pyqt/) | Touch UI (PyQt5) — UART client only |
| [`firmware/`](firmware/) | MicroPython on RP2350 — MCP23017 relays + ADS1115 temps |
| [`hardware/`](hardware/) | Schematics + co-work jumper notes |
| [`doc/`](doc/) | API, user guide, [architecture diagrams](doc/diagrams.md), system PNGs |

With the I2C jumper on **MCU-I2C1**, the RP2350 owns all three valves and three
temperature loops. The CM5 sends high-level commands (`START_FLOW`, …) over UART.
