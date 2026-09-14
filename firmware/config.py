"""Hardware map for Oddurboga CM5 + RP2350 co-work mode.

Plant valves on Relay 0–5 (MCP23017 GPB0–GPB5):
  Relay 0 = flow (main inlet shutoff)
  Relay 1 = hot water valve
  Relay 2 = cold water valve
  Relay 3 = drain valve
  Relay 4 = heat cable (outdoor frost protection)
  Relay 5 = aux (timed shower / cold-tub)
"""

FW_VERSION = "1.2.0"

# --- UART CM5 ↔ RP2350 (cross-over on PCB) --------------------------------
UART_ID = 0
UART_BAUD = 115200
UART_TX_PIN = 0
UART_RX_PIN = 1

# --- I2C1 on RP2350 (MCU_I2C1_SDA / MCU_I2C1_SCL) -------------------------
# Schematic p.4: GPIO6 = SDA, GPIO7 = SCL (not GPIO2/3).
I2C_ID = 1
I2C_SDA_PIN = 6
I2C_SCL_PIN = 7
I2C_FREQ_HZ = 100_000

MCP23017_ADDR = 0x20
# Schematic p.5: ADDR pin tied to 3V3 → 0x49 (not 0x48).
ADS1115_ADDR = 0x49

# MCP23017: GPA0 = SENSOR_24V_EN; GPB0..GPB5 = RELAY0..RELAY5.
# Driver maps bits 0–7 → port A, 8–15 → port B.
BIT_SENSOR_24V_EN = 0
BIT_RELAY0 = 8   # flow
BIT_RELAY1 = 9   # hot
BIT_RELAY2 = 10  # cold
BIT_RELAY3 = 11  # drain
BIT_RELAY4 = 12  # heat cable
BIT_RELAY5 = 13  # aux

BIT_FLOW = BIT_RELAY0
BIT_HOT = BIT_RELAY1
BIT_COLD = BIT_RELAY2
BIT_DRAIN = BIT_RELAY3
BIT_HEAT_CABLE = BIT_RELAY4
BIT_AUX = BIT_RELAY5

PIN_RECOVER_BTN = 22

ADS_CH_TEMP1 = 0
ADS_CH_TEMP2 = 1
ADS_CH_TEMP3 = 2

ADS_PGA = 1
LOOP_V_AT_4MA = 0.0
LOOP_V_AT_20MA = 2.5
LOOP_T_AT_4MA_C = -20.0
LOOP_T_AT_20MA_C = 100.0

# Hot/cold valves are motorized; full travel cold↔hot ≈ this long.
MIX_FULL_STROKE_S = 60.0
MIX_PRECOOL_S = 30.0           # cold valve open before allowing hot
MIX_RECOVER_COLD_S = 40.0
# Safety: any relay continuously on longer than this → force OFF + SAFETY lock.
VALVE_MAX_ON_S = 120.0

INLET_CUTOFF_C = 49.9
TUB_CUTOFF_C = 49.0
SENSOR_MIN_C = -20.0
SENSOR_MAX_C = 80.0

# Heat cable AUTO: energize when outdoor Temp3 is below this (°C).
HEAT_CABLE_ON_BELOW_C = 5.0

# Aux timed run (shower / cold-tub): user-adjustable 3–10 minutes.
AUX_DURATION_MIN_S = 180.0
AUX_DURATION_MAX_S = 600.0
AUX_DURATION_DEFAULT_S = 300.0

FILL_RISE_C = 5.0              # Temp2 rise ⇒ water reached the tub probe
FILL_RISE_WINDOW_S = 10.0
FILL_ETA_DEFAULT_S = 12 * 60
FILL_HISTORY = 8

DEFAULT_TARGET_C = 39.0
DEFAULT_INLET_OFFSET_C = 3.0
DEFAULT_REHEAT_HYST_C = 2.0
DEFAULT_TUB_CAL_C = 0.0
DEFAULT_FROST_DELAY_S = 120.0

TARGET_MIN_C = 5.0
TARGET_MAX_C = 45.0
COLD_TARGET_MAX_C = 25.0

CONTROL_PERIOD_S = 0.2
SENSOR_SAMPLE_S = 0.5

STORE_PATH = "settings.json"
