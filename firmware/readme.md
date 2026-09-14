# MicroPython firmware — RP2350 plant controller

## Role in the product

| Chip | Owns |
|------|------|
| **Raspberry Pi CM5** | Linux, PyQt HMI, weather/cloud, UART host (`/dev/ttyAMA0`) |
| **RP2350** | MCP23017 valve relays, ADS1115 temperature ADC, local safety & sequencing |

The main-board **I2C jumper** is set to **MCU-I2C1** (RP2350) so the expander and ADC are not on the CM5 bus. UART is always cross-connected: `CM_UART0` ↔ `MCU_UART0`.

Command set: [`doc/api.md`](../doc/api.md). Hardware notes: [`hardware/readme.md`](../hardware/readme.md). Bring-up findings: [`doc/oddurboga-bringup-report-1.pdf`](../doc/oddurboga-bringup-report-1.pdf).

## Plant map (system diagram)

| Kind | Name | Hardware |
|------|------|----------|
| Valve | Flow (inlet shutoff) | **Relay 0** |
| Valve | Hot water (mixer) | **Relay 1** |
| Valve | Cold water (mixer) | **Relay 2** |
| Valve | Drain | **Relay 3** (on = OPEN to sewer) |
| Output | Heat cable | **Relay 4** (AUTO: outdoor &lt; 5 °C) |
| Output | Aux (shower / cold-tub) | **Relay 5** (timed 3–10 min) |
| Temp1 | Inlet / control side | ADS1115 CH0 → API `INLET` |
| Temp2 | Tub wall | ADS1115 CH1 → API `TUB` (+ `SET_TUB_CAL`) |
| Temp3 | Outdoor (optional) | ADS1115 CH2 → API `OUTDOOR` |

`START_FLOW` opens **Relay 0** (flow), soft-starts on **Relay 2** (cold) for 30 s, then regulates **Relay 1/2** (hot/cold). `STOP_FLOW` closes flow and mixer.

Diagrams: [`doc/diagrams.md`](../doc/diagrams.md).

## Behaviour highlights

- Soft-start: `START_FLOW` → `OK` immediately; locally open **flow + cold 30 s**, then hot/cold regulate
- Fill detect: Temp2 rise ≥ **5 °C / 10 s** → learn fill time → `ETA_MIN`
- Valve force-off: any relay on **> 120 s** → `SAFETY=LOCKED` / `VALVE_TIMEOUT` (safety watchdog, not run-time limit)
- Temp1 ≥ **49.9 °C** → close flow + hot + cold, lock (`INLET_OVERTEMP`)
- Temp2 ≥ **49.0 °C** → close flow + hot + cold + drain OPEN (`TUB_OVERTEMP`)
- Heat cable AUTO: Relay 4 on when outdoor Temp3 &lt; **5 °C**
- Aux: `SET_AUX ON` energizes Relay 5 for `SET_AUX_DURATION` seconds (180–600)
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
  mix_valve.py     # hot/cold Relay 1/2 with interlock
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
