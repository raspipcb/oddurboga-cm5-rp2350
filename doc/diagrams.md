# System architecture diagrams

Mermaid diagrams for GitHub rendering. Symbols follow common automation /
P&ID-style naming where Mermaid allows (valves, sensors, controllers).

Relay assignment (production):

| Relay | Valve |
|-------|--------|
| **0** | Hot water valve |
| **1** | Cold water valve |
| **2** | Drain valve |
| 3–5 | Unused |

Inlet “flow” is logical (`START_FLOW` / `STOP_FLOW`): water enters when the
hot and/or cold valve is open. There is no separate flow relay.

---

## 1. Water system (P&ID-style)

```mermaid
flowchart LR
  subgraph SUPPLY["District heating"]
    HOT["Hot water IN"]
    COLD["Cold water IN"]
  end

  T1(["TE Temp1<br/>inlet / mix"])
  VH{{"XV-HOT<br/>hot water valve<br/>Relay 0"}}
  VC{{"XV-COLD<br/>cold water valve<br/>Relay 1"}}
  MIX["Mixing manifold"]
  HC["Heating cable<br/>on feed pipe"]
  TUB[("Hot tub")]
  T2(["TE Temp2<br/>tub wall"])
  OF["Overflow<br/>to sewer"]
  DRAIN{{"XV-DRAIN<br/>drain valve<br/>Relay 2"}}
  SEWER["To sewer"]
  T3(["TE Temp3<br/>outdoor optional"])

  HOT --> VH --> MIX
  COLD --> VC --> MIX
  MIX --> T1 --> HC --> TUB
  TUB --- T2
  TUB --> OF --> SEWER
  TUB --> DRAIN --> SEWER
  T3 -.->|"ambient"| TUB
```

**Legend:** `TE` = temperature element · `XV` = valve · cylinder = vessel/tub

Temp2 is a tub-wall probe. Overflow is a separate outlet to sewer — not the Temp2 location.

---

## 2. Electrical system (plant ↔ main board ↔ CM5 / RP2350)

```mermaid
flowchart TB
  subgraph PLANT["Field devices"]
    direction LR
    V0["XV-HOT<br/>Relay 0"]
    V1["XV-COLD<br/>Relay 1"]
    V2["XV-DRAIN<br/>Relay 2"]
    S1["Temp1 PT1000<br/>4–20 mA"]
    S2["Temp2 PT1000<br/>tub wall"]
    S3["Temp3 PT1000<br/>4–20 mA"]
  end

  subgraph MAIN["Main board — Oddurboga CM5 IO + RP2350"]
    direction TB
    subgraph CM5BOX["Raspberry Pi CM5"]
      PYQT["PyQt app<br/>Linux HMI"]
      UART_CM["UART0<br/>/dev/serial0<br/>GPIO14/15"]
      PYQT <--> UART_CM
    end

    subgraph RPBOX["RP2350 firmware"]
      FW["control / safety / protocol"]
      UART_MCU["UART0<br/>MCU_UART0"]
      I2C["I2C1<br/>MCU-I2C1<br/>jumper selected"]
      FW <--> UART_MCU
      FW <--> I2C
    end

    MCP["MCP23017 @ 0x20<br/>IO expander<br/>RELAY0..2 used<br/>RELAY3..5 unused"]
    ADS["ADS1115 @ 0x48<br/>16-bit ADC"]
    RCV["RCV420 ×3<br/>4–20 mA → 0–2.5 V"]

    I2C --> MCP
    I2C --> ADS
    RCV --> ADS
  end

  UART_CM <-.->|"cross-over UART<br/>115200 8N1"| UART_MCU

  MCP -->|"Relay 0"| V0
  MCP -->|"Relay 1"| V1
  MCP -->|"Relay 2"| V2
  S1 --> RCV
  S2 --> RCV
  S3 --> RCV
```

**Co-work mode:** I2C jumper → **MCU-I2C1** (RP2350 owns expander + ADC). CM5 uses UART only.

---

## 3. PyQt app algorithm

```mermaid
flowchart TD
  START([App start]) --> ARGS[Parse --port / --baud / --mock / --poll]
  ARGS --> LINK[Create DeviceLink<br/>serial worker thread]
  LINK --> UI[MainWindow<br/>Home + Settings + Toasts]
  UI --> POLL[QTimer: GET_STATUS / GET_SYSTEM_INFO]

  subgraph UI_LOOP["UI thread — never blocks on serial"]
    HOME[HomeScreen tiles / temp slider]
    SET[SettingsScreen sliders / sensors]
    TOAST[ToastOverlay]
    HOME -->|send command| Q
    SET -->|send command| Q
    POLL -->|send| Q
  end

  Q[DeviceLink.send<br/>coalescing queue] --> W

  subgraph WORKER["Background link worker"]
    W[Write line to UART]
    W --> R[Read reply with timeout]
    R -->|OK / VALUE / STATUS / ERROR| SIG[Signals to UI]
    R -->|timeout / I/O error| RE[Reconnect with backoff]
  end

  SIG --> APPLY[apply_status / apply_result<br/>update tiles, temps, toasts]
  APPLY --> UI_LOOP

  CLOSE([closeEvent]) --> STOP[link.stop]
```

**Mapping (home tiles → UART):**

| Tile | Off → On | On → Off |
|------|----------|----------|
| Power | `SET_MODE AUTO` | `SET_MODE OFF` |
| Flow | `START_FLOW` | `STOP_FLOW` |
| Drain | `SET_DRAIN OPEN` | `SET_DRAIN CLOSE` |
| Cold | `SET_MODE COLD` | `SET_MODE AUTO` |

---

## 4. RP2350 firmware algorithm

```mermaid
flowchart TD
  BOOT([main boot]) --> BOARD[Board: enable SENSOR_24V<br/>init MCP23017 + ADS1115]
  BOARD --> LOOP

  subgraph LOOP["Main loop ~200 ms"]
    direction TB
    RX[Read UART lines] --> PROTO[Protocol.handle]
    PROTO -->|reply| TX[Write UART line]
    PROTO --> CTL[Controller.tick]
    RX --> CTL
  end

  subgraph TICK["Controller.tick"]
    SEN[Read Temp1/2/3 via ADS1115] --> SAF[Safety.evaluate]
    SAF -->|INLET≥49.9| K1[Close hot+cold + LOCK]
    SAF -->|TUB≥49.0| K2[Close hot+cold + Drain OPEN + LOCK]
    SAF -->|relay on >120s| K3[Force that relay OFF + LOCK]
    SAF --> PHASE

    subgraph PHASE["Sequencer"]
      Idle[IDLE] -->|START_FLOW / auto reheat| Pre[PRECOOL<br/>Relay1 cold 30s]
      Pre --> Reg[REGULATE<br/>Relay0/1 bang-bang<br/>to inlet setpoint]
      Reg -->|tub rise ≥5°C/10s| Fill[Fill learned / ETA]
      Reg -->|tub ≥ target| Idle2[Close hot+cold → IDLE]
      Idle -->|STOP_FLOW| Idle
      LOCK[SAFETY LOCKED] -->|RECOVER| Rec[RECOVER<br/>Relay1 cold 40s]
      Rec -->|temps OK| Idle
    end
  end

  CTL --> TICK
```

**Soft-start note:** `START_FLOW` opens **Relay 1 (cold)** for 30 s first, then bang-bang regulates with Relay 0 (hot) / Relay 1 (cold). Hot and cold are never on together.

---

## 5. End-to-end data path (summary)

```mermaid
sequenceDiagram
  participant UI as PyQt on CM5
  participant UART as CM_UART0 ↔ MCU_UART0
  participant FW as RP2350 firmware
  participant MCP as MCP23017
  participant ADS as ADS1115
  participant V as Relays 0/1/2
  participant T as Temp1/2/3

  UI->>UART: START_FLOW
  UART->>FW: START_FLOW
  FW->>MCP: Relay1 cold ON (precool)
  Note over FW: after 30 s
  FW->>MCP: Relay0/1 regulate mix
  FW->>ADS: read CH0/CH1/CH2
  ADS->>T: 4–20 mA loops
  FW->>UART: STATUS TUB=… INLET=… FLOW=ON …
  UART->>UI: update tiles / temps
```
