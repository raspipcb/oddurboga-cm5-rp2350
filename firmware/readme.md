# MicroPython firmware — RP2350 plant controller

## Role in the product

| Chip | Owns |
|------|------|
| **Raspberry Pi CM5** | Linux, PyQt HMI, weather/cloud, UART host (`/dev/serial0`) |
| **RP2350** | MCP23017 valve relays, ADS1115 temperature ADC, local safety & sequencing |

The main-board **I2C jumper** is set to **MCU-I2C1** (RP2350) so the expander and ADC are not on the CM5 bus. UART is always cross-connected: `CM_UART0` ↔ `MCU_UART0`.

Command set: [`doc/api.md`](../doc/api.md). Hardware notes: [`hardware/readme.md`](../hardware/readme.md). Bring-up findings: [`doc/oddurboga-bringup-report-1.pdf`](../doc/oddurboga-bringup-report-1.pdf).

## Plant map (system diagram)

| Kind | Name | Hardware |
|------|------|----------|
| Valve | Hot water | **Relay 0** |
| Valve | Cold water | **Relay 1** |
| Valve | Drain | **Relay 2** (on = OPEN to sewer) |
| — | Relays 3–5 | Unused |
| Temp1 | Inlet / control side | ADS1115 CH0 → API `INLET` |
| Temp2 | Tub wall | ADS1115 CH1 → API `TUB` (+ `SET_TUB_CAL`) |
| Temp3 | Outdoor (optional) | ADS1115 CH2 → API `OUTDOOR` |

`START_FLOW` / `STOP_FLOW` are logical: inlet water is admitted by opening hot and/or cold. Soft-start opens **cold first** for 30 s, then bang-bang regulates.

Diagrams: [`doc/diagrams.md`](../doc/diagrams.md).

## Behaviour highlights

- Soft-start: `START_FLOW` → `OK` immediately; locally open **cold 30 s**, then hot/cold regulate
- Fill detect: Temp2 rise ≥ **5 °C / 10 s** → learn fill time → `ETA_MIN`
- Valve force-off: any relay on **> 120 s** → `SAFETY=LOCKED` / `VALVE_TIMEOUT`
- Temp1 ≥ **49.9 °C** → close hot+cold, lock (`INLET_OVERTEMP`)
- Temp2 ≥ **49.0 °C** → close hot+cold + drain OPEN (`TUB_OVERTEMP`)
- `RECOVER` / onboard button: **`OK` immediately**, then **40 s** cold locally, then unlock if safe

## Layout

```text
firmware/
  main.py          # UART + control loop
  config.py        # addresses, relay bits, timings
  board.py         # MCP23017 + ADS1115 facade
  mcp23017.py      # IO expander driver
  ads1115.py       # ADC + 4–20 mA → °C
  actuators.py     # timed relays
  sensors.py       # Temp1/2/3
  mix_valve.py     # hot/cold Relay 0/1 with interlock
  fill.py safety.py control.py protocol.py store.py hw.py
  tests/           # host suite (no board required)
```

## Flash

1. Confirm I2C jumper = RP2350 and UART cross-link.
2. Adjust `config.py` GPIO / relay-bit map if your PCB routing differs.
3. Calibrate `LOOP_T_AT_*` after measuring a known bath temperature.
4. Copy `*.py` to the device. `boot.py` starts `main.py` automatically after reset.

```bash
python firmware/tests/test_firmware.py
```
