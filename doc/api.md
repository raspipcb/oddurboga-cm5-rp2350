# CM5 ↔ RP2350 Command API

## Contents

- [Overview](#overview)
- [Message Format](#message-format)
- [Commands](#commands)
- [Error Responses](#error-responses)
- [Local Safety and Control](#local-safety-and-control)
- [Responsibility Boundary](#responsibility-boundary)
- [Command Summary](#command-summary)

## Overview

This document defines the command interface between the Raspberry Pi CM5
and the RP2350 controller in the hot-tub control system.

The CM5 handles the user interface, cloud/mobile communication, MQTT,
weather information, and high-level requests. The RP2350 handles
real-time hardware control, temperature measurements, water mixing,
physical outputs, sequencing, and local safety protection.

The interface is functional rather than hardware-specific. The CM5 sends
high-level commands such as `STOP_FLOW` or `SET_DRAIN CLOSE`; it does
not control relay numbers, GPIOs, ADC channels, or PID outputs directly.

## Message Format

### Request

```text
COMMAND [PARAMETER]
```

### Successful Action

```text
OK
```

### Successful Read

```text
VALUE <data>
```

### Error

```text
ERROR <code>
```

## Commands

### SET_TARGET_TEMP

Sets the desired hot-tub water temperature. The RP2350 uses this value
as the main temperature target and performs the required local control.

**Syntax**

```text
SET_TARGET_TEMP <temperature>
```

**Parameter**

-   `temperature` — Target temperature in °C.

**Example**

```text
SET_TARGET_TEMP 39.0
```

**Response**

```text
OK
```

### GET_TARGET_TEMP

Returns the currently configured hot-tub target temperature.

**Syntax**

```text
GET_TARGET_TEMP
```

**Example Response**

```text
VALUE 39.0
```

### GET_TUB_TEMP

Returns the calibrated **Temp 2** measurement (tub / overflow path).

**Syntax**

```text
GET_TUB_TEMP
```

**Example Response**

```text
VALUE 38.6
```

### GET_INLET_TEMP

Returns **Temp 1**, the inlet / control-side temperature (mix side on the
manifold, ADS1115 CH0 via 4–20 mA).

**Syntax**

```text
GET_INLET_TEMP
```

**Example Response**

```text
VALUE 42.0
```

### SET_INLET_OFFSET

Sets the heat-loss compensation used to calculate the required inlet
temperature. Allowed range: 1–5 °C.

**Syntax**

```text
SET_INLET_OFFSET <offset>
```

**Parameter**

-   `offset` — Inlet heat-loss compensation in °C, from 1 to 5.

**Example**

```text
SET_INLET_OFFSET 3.0
```

If the tub target is 39 °C and the inlet offset is 3 °C, the RP2350
controls the inlet toward approximately 42 °C.

**Response**

```text
OK
```

### SET_REHEAT_HYST

Sets how far the tub temperature may fall below its target before
automatic reheating/filling resumes. Allowed range: 1–5 °C.

**Syntax**

```text
SET_REHEAT_HYST <hysteresis>
```

**Example**

```text
SET_REHEAT_HYST 2.0
```

**Response**

```text
OK
```

### SET_TUB_CAL

Sets the installation calibration correction for **Temp 2** (tub). Allowed
adjustment range: -10 °C to +10 °C.

**Syntax**

```text
SET_TUB_CAL <correction>
```

**Example**

```text
SET_TUB_CAL 2.0
```

**Response**

```text
OK
```

### SET_MODE

Selects the main system operating mode.

-   `AUTO` — Enables normal automatic filling, mixing, and temperature
    maintenance.
-   `OFF` — Stops normal automatic control while local safety
    monitoring remains active.
-   `COLD` — Enables cold-tub operation and the extended
    low-temperature operating range.

**Syntax**

```text
SET_MODE <AUTO|OFF|COLD>
```

**Examples**

```text
SET_MODE AUTO
SET_MODE OFF
SET_MODE COLD
```

**Response**

```text
OK
```

### START_FLOW

Requests inlet flow to start or resume. The RP2350 performs the hardware
operation and may inhibit the request if a local safety condition is
active.

**Syntax**

```text
START_FLOW
```

**Response**

```text
OK
```

### STOP_FLOW

Stops inlet flow without requesting the tub to drain.

**Syntax**

```text
STOP_FLOW
```

**Response**

```text
OK
```

### SET_DRAIN

Requests drain operation. The RP2350 handles the physical valve
sequencing internally.

**Syntax**

```text
SET_DRAIN <OPEN|CLOSE>
```

**Examples**

```text
SET_DRAIN OPEN
SET_DRAIN CLOSE
```

When closing during frost conditions, the RP2350 applies the required
thaw/water-flow sequence before completing drain closure.

**Response**

```text
OK
```

### SET_FROST_DELAY

Sets the water-flow/thaw delay used before drain closure when frost
protection is active.

**Syntax**

```text
SET_FROST_DELAY <delay>
```

**Example**

```text
SET_FROST_DELAY 120
```

**Response**

```text
OK
```

### SET_HEAT_CABLE

Controls the heat-cable operating mode.

-   `AUTO` — Allows the heat cable to follow higher-level
    frost/weather control.
-   `ON` — Manually requests heat-cable operation.
-   `OFF` — Manually disables the heat cable.

**Syntax**

```text
SET_HEAT_CABLE <AUTO|ON|OFF>
```

**Example**

```text
SET_HEAT_CABLE AUTO
```

**Response**

```text
OK
```

### SET_AUX

Controls the reserved auxiliary function without exposing its physical
relay assignment.

**Syntax**

```text
SET_AUX <ON|OFF>
```

**Examples**

```text
SET_AUX ON
SET_AUX OFF
```

**Response**

```text
OK
```

### SET_FROST_ACTIVE

Provides the RP2350 with the current higher-level frost condition
determined by CM5/cloud weather logic.

-   `0` — Normal conditions.
-   `1` — Frost protection required.

**Syntax**

```text
SET_FROST_ACTIVE <0|1>
```

**Example**

```text
SET_FROST_ACTIVE 1
```

**Response**

```text
OK
```

### GET_STATUS

Returns the main system information in one response. This is the primary
status command and avoids separate GET commands for every internal
subsystem.

**Syntax**

```text
GET_STATUS
```

**Suggested Response**

```text
STATUS MODE=AUTO TARGET=39.0 TUB=38.4 INLET=42.0 OUTDOOR=7.0 FLOW=ON DRAIN=CLOSED MIX=HEATING HEAT_CABLE=OFF AUX=OFF SAFETY=OK FAULT=NONE ETA_MIN=12 FILL_S=180 PHASE=REGULATE
```

Field meanings relative to the physical installation:

| Field | Sensor / actuator | Physical meaning |
|-------|-------------------|------------------|
| `TUB` | **Temp 2** (ADS CH1) | Tub / overflow water temperature (calibrated) |
| `INLET` | **Temp 1** (ADS CH0) | Inlet / control-side mix temperature |
| `OUTDOOR` | **Temp 3** (ADS CH2) | Outdoor ambient (optional) |
| `FLOW` | Flow valve relay | Mixed-water feed into the tub |
| `DRAIN` | Drain valve relay | Bottom drain toward sewer |
| `MIX` | Mixing valve relays | `PRECOOL` / `HEATING` / `COOLING` / `HOLD` / `IDLE` / `RECOVER` |
| `HEAT_CABLE` | Heat-cable relay | Trace heat on the mixed-water feed pipe |
| `ETA_MIN` | Fill learner | Estimated minutes until tub ready (0 when idle) |
| `FILL_S` | Fill learner | Seconds since current fill started |
| `PHASE` | Sequencer | `IDLE` / `PRECOOL` / `FLOW` / `REGULATE` / `RECOVER` |
| `SAFETY` | Latch | `OK` or `LOCKED` (needs `RECOVER`) |

The CM5 can use this response for regular UI/status updates.

### GET_FAULT

Returns the currently active fault. If no fault is active, the RP2350
returns `NONE`.

**Syntax**

```text
GET_FAULT
```

**Example Responses**

```text
VALUE NONE
VALUE TEMP1_FAULT
VALUE TEMP2_FAULT
VALUE INLET_OVERTEMP
```

### CLEAR_FAULT

Requests clearing of a latched **soft** fault. The RP2350 clears the fault only
when the underlying fault or unsafe condition has disappeared.

Hard safety locks (`SAFETY=LOCKED` from overtemp or valve timeout) are **not**
cleared by this command — use `RECOVER`.

**Syntax**

```text
CLEAR_FAULT
```

**Response**

```text
OK
```

### RECOVER

Hard safety unlock (emulates a physical reset button). Sequence:

1. Stop inlet flow immediately.
2. Drive the mixing valve toward cold for 40 seconds.
3. If sensors are back inside the safe band, clear `SAFETY=LOCKED` and resume
   normal control; otherwise remain locked.

The CM5 should show a confirmation UI (“inlet temperature too high — cool down
and reset”) and send `RECOVER` when the operator confirms.

**Syntax**

```text
RECOVER
```

**Response**

```text
OK
```

### GET_SYSTEM_INFO

Returns basic RP2350 firmware and controller information for diagnostics
and software compatibility checks.

**Syntax**

```text
GET_SYSTEM_INFO
```

**Suggested Response**

```text
INFO FW=1.0.0 STATE=READY
```

### PING

Checks communication between the CM5 and RP2350.

**Syntax**

```text
PING
```

**Response**

```text
OK
```

## Error Responses

| Error                 | Description                                                            |
|-----------------------|------------------------------------------------------------------------|
| `ERROR INVALID_CMD`   | Unknown command.                                                       |
| `ERROR INVALID_VALUE` | Invalid parameter or value outside its allowed range.                  |
| `ERROR SAFETY_LOCK`   | Requested operation is blocked by an active safety condition.          |
| `ERROR SENSOR_FAULT`  | A required sensor is unavailable or invalid.                           |
| `ERROR BUSY`          | RP2350 is completing a sequence that prevents the requested operation. |

## Local Safety and Control

Safety and real-time control do not depend on continuous CM5 commands.
The RP2350 remains responsible for these functions locally.

Hard rules enforced in firmware (`firmware/`):

| Condition | Action |
|-----------|--------|
| Any valve relay continuously on for **120 s** | That drive forced OFF; `SAFETY=LOCKED`, `FAULT=VALVE_TIMEOUT`; wait for `RECOVER` |
| **Temp 1** (inlet) ≥ **49.9 °C** | Flow relay OFF; `SAFETY=LOCKED`, `FAULT=INLET_OVERTEMP` |
| **Temp 2** (tub) ≥ **49.0 °C** | Flow relay OFF **and** drain OPEN; `SAFETY=LOCKED`, `FAULT=TUB_OVERTEMP` |
| Temp 1 or Temp 2 outside **−20…80 °C** | No valve activation; `FAULT=SENSOR_FAULT` |

`RECOVER` runs the mixer toward cold for 40 s, then clears the lock only if
temperatures are healthy again. A physical reset button may call the same path.

Fill soft-start (not a CM5 concern): before opening flow, the mixer is driven
cold for 30 s; after flow opens, inlet is regulated to
`target + inlet_offset` (with learned fill-drop compensation).

Hot/cold mixing, sensor reading, fill-stop/reheat behavior, drain
sequencing, and physical output timing also remain internal RP2350
functions.

### RP2350 vs CM5 (co-work board mode)

With the main-board **I2C jumper on MCU-I2C1**, only the RP2350 talks to the
MCP23017 (relays) and ADS1115 (temperatures). The CM5 must use UART commands
exclusively — never open those I2C devices from Linux while this jumper is set.

## Responsibility Boundary

### CM5

-   HMI
-   Mobile/cloud communication
-   MQTT
-   User/account functions
-   Weather lookup and higher-level frost information
-   Sending configuration and user requests to RP2350
-   Displaying RP2350 status and faults

### RP2350

-   Reading Temp 1, Temp 2, and Temp 3
-   Applying Temp 2 (tub) calibration
-   Real-time inlet-temperature control
-   Hot/cold 3-way mixing control
-   Physical valve and relay operation (MCP23017)
-   ADS1115 / 4–20 mA temperature acquisition
-   Fill-stop and reheat logic
-   Drain sequencing
-   Local frost-related sequencing
-   Immediate local safety protection

## Command Summary

| Command            | Parameter / Example | Description                                                       |
|--------------------|---------------------|-------------------------------------------------------------------|
| `SET_TARGET_TEMP`  | `39.0`              | Set the desired hot-tub water temperature.                        |
| `GET_TARGET_TEMP`  | —                   | Read the active target temperature.                               |
| `GET_TUB_TEMP`     | —                   | Read calibrated Temp 2 / tub water temperature.                   |
| `GET_INLET_TEMP`   | —                   | Read Temp 1 / inlet (control-side) temperature.                   |
| `SET_INLET_OFFSET` | `3.0`               | Configure the 1–5 °C inlet heat-loss compensation.                |
| `SET_REHEAT_HYST`  | `2.0`               | Configure the 1–5 °C automatic reheat hysteresis.                 |
| `SET_TUB_CAL`      | `2.0`               | Configure the -10 °C to +10 °C Temp 2 (tub) calibration.          |
| `SET_MODE`         | `AUTO / OFF / COLD` | Select the main system operating mode.                            |
| `START_FLOW`       | —                   | Start/resume controlled inlet flow.                               |
| `STOP_FLOW`        | —                   | Stop inlet flow without draining the tub.                         |
| `SET_DRAIN`        | `OPEN / CLOSE`      | Request drain-valve operation and required sequencing.            |
| `SET_FROST_DELAY`  | `120`               | Configure the frost-condition drain-closing delay.                |
| `SET_HEAT_CABLE`   | `AUTO / ON / OFF`   | Select automatic or manual heat-cable control.                    |
| `SET_AUX`          | `ON / OFF`          | Control the reserved auxiliary function.                          |
| `SET_FROST_ACTIVE` | `0 / 1`             | Supply the current CM5/cloud frost condition to RP2350.           |
| `GET_STATUS`       | —                   | Read temperatures and important operating states in one response. |
| `GET_FAULT`        | —                   | Read the currently active fault or `NONE`.                        |
| `CLEAR_FAULT`       | —                   | Clear a soft fault after its cause is removed.                    |
| `RECOVER`           | —                   | Hard unlock: 40 s cold mix, then clear `SAFETY=LOCKED` if safe.   |
| `GET_SYSTEM_INFO`   | —                   | Read firmware version and controller readiness.                   |
| `PING`             | —                   | Check CM5 ↔ RP2350 communication; response is `OK`.               |
