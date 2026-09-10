# Hardware - Oddurboga CM5 IO with RP2350

Schematics (2026-06-30):

- `[SCH_Schematic_MainBoard_2026-06-30.pdf](SCH_Schematic_MainBoard_2026-06-30.pdf)`
- `[SCH_Schematic_SensorBoard_2026-06-30.pdf](SCH_Schematic_SensorBoard_2026-06-30.pdf)`

## Co-work mode (current production setting)

The main board can assign the shared I2C bus to either the CM5 or the RP2350 via jumpers.


| Jumper  | Co-work setting       | Effect                                    |
| ------- | --------------------- | ----------------------------------------- |
| **I2C** | **MCU-I2C1** (RP2350) | MCP23017 + ADS1115 controlled by firmware |
| UART    | CM_UART0 ↔ MCU_UART0  | PyQt ↔ firmware API (always)              |


CM5 runs Linux + the PyQt app and **must not** drive the expander/ADC while the I2C jumper selects the RP2350. The app only uses the serial port (`/dev/serial0`, 115200 8N1).

```text
  PyQt (CM5)  --UART0--  RP2350 firmware
                            |
                     I2C1 --+-- MCP23017 @ 0x20  (6 relays)
                            +-- ADS1115  @ 0x48  (3× 4–20 mA → °C)
```



## Block diagram chips


| Chip                  | Addr / link  | Function                           |
| --------------------- | ------------ | ---------------------------------- |
| RP2350A + 16 MB flash | —            | Plant controller                   |
| CM5                   | —            | HMI / OS                           |
| MCP23017              | `0x20`       | 6× relay outputs + `SENSOR_24V_EN` |
| ADS1115               | `0x48`       | 16-bit ADC, AIN0–2 from RCV420     |
| RCV420 ×3             | —            | 4–20 mA → ~0–2.5 V                 |
| Sensor board (×3)     | 4–20 mA loop | PT1000 + XTR112 (TIPD202-style)    |




## Three valves / three sensors (system diagram)

| # | Plant role | Electrical |
|---|------------|------------|
| Valve | **Hot** water | **Relay 0** |
| Valve | **Cold** water | **Relay 1** |
| Valve | **Drain** to sewer | **Relay 2** (energized = open) |
| — | Relays 3–5 | **Unused** |
| Temp 1 | Inlet / between heat meter & mixer | ADS CH0 → firmware `INLET` |
| Temp 2 | Tub / after overflow | ADS CH1 → firmware `TUB` |
| Temp 3 | Outdoor (optional) | ADS CH2 → firmware `OUTDOOR` |

Architecture Mermaid diagrams: [`doc/diagrams.md`](../doc/diagrams.md).

## Sensor board

Each remote probe board is a linearized **2-wire PT1000 → 2-wire 4–20 mA** transmitter (TI TIPD202 / XTR112). The main board sinks the loops through RCV420 receivers into the ADS1115.