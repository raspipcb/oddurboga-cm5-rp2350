# IPSs - PyQt5 Hardware UI

Touchscreen UI for the IPS hot-tub controller, built with Python + PyQt5.  
Target hardware: Raspberry Pi + 800×480 or 1024×600 capacitive touch display.

## Display sizes

The UI scales for **800×480** (default) and **1024×600**:

```bash
./scripts/run.sh                      # 800×480 window
./scripts/run.sh --size 1024x600      # larger layout
./scripts/run.sh --fullscreen         # auto-detect from screen geometry
./scripts/run.sh --fullscreen --size 800x480
```

On Pi with a 1024×600 panel, use `./scripts/run.sh --fullscreen` - it picks the matching preset automatically.

## Screens


| Screen                | File                     | Description                                                 |
| --------------------- | ------------------------ | ----------------------------------------------------------- |
| Home (Heim)           | `src/home_screen.py`     | Action buttons, weather forecast, temperature control       |
| Settings (Stillingar) | `src/settings_screen.py` | Threshold sliders, sensor readings, device info, WiFi reset |




## Project structure

```
pyqt/
  scripts/
    setup-dev.sh
    setup-pi.sh
    run.sh
  src/
    main.py
    theme.py
    ui_common.py
    home_screen.py
    settings_screen.py
    assets/logo.png
  requirements.txt
```



## Quick start



### Desktop development

```bash
cd hardware-ui/pyqt
./scripts/setup-dev.sh
./scripts/run.sh
```



### Raspberry Pi

```bash
cd hardware-ui/pyqt
./scripts/setup-pi.sh
./scripts/run.sh --fullscreen
```

On Raspberry Pi OS with a desktop session, PyQt5 uses the normal X11/Wayland display - no framebuffer drivers needed.

### Autostart on boot

Add to `~/.config/autostart/husvit.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=IPS
Exec=/home/pi/housesit/hardware-ui/pyqt/scripts/run.sh --fullscreen
X-GNOME-Autostart-enabled=true
```



## Language

Default language is **English**. Switch to Icelandic on the Settings screen under **Language**.

The choice is saved to `config.json` in the project root and restored on next launch.

Supported languages: `en`, `is`

## Controller link (CM_UART0 -> RP2350)

The UI talks to the RP2350 over the cross-connected UART using the command set in
[`CM5 RPI Commands in MD format.md`](../CM5%20RPI%20Commands%20in%20MD%20format.md).

```bash
./scripts/run.sh --port /dev/serial0    # explicit port
./scripts/run.sh --baud 115200          # link speed
./scripts/run.sh --mock                 # built-in controller simulator
./scripts/run.sh --poll 2.0             # GET_STATUS interval, seconds
```

`IPS_PORT` and `IPS_BAUD` work as environment variables too. With no port given,
Linux defaults to `/dev/serial0`; if that device is absent (or on Windows/macOS)
the UI runs against the simulator so development needs no hardware.

### Transport assumptions

The API document defines syntax but not framing, so the client uses these
defaults. **Firmware must match them:**

| Setting | Value |
| ------- | ----- |
| Baud | 115200, 8N1, no flow control |
| Request terminator | `\n` (`\r\n` also accepted on replies) |
| Encoding | ASCII |
| Response timeout | 1.0 s per request |
| Model | One request, one reply line; no unsolicited traffic expected |

Unsolicited or unparseable lines are logged and discarded. After 20 of them in a
single exchange, or 3 consecutive failed requests, the link cycles the port.

### Modules

| File | Role |
| ---- | ---- |
| `src/protocol.py` | Command building and tolerant reply parsing (no I/O) |
| `src/device_link.py` | Worker thread, timeouts, reconnect, request queue, simulator |
| `src/toast.py` | On-screen result notifications |
| `src/api_log.py` | Rotating API log at `pyqt/logs/api.log` |

Every request and reply is logged with elapsed time:

```text
-> SET_TARGET_TEMP 39.0
<- OK (12 ms)
!! GET_STATUS timeout after 1000 ms
```

### UI to command mapping

The four home tiles are independent toggles. The background shows whether the
feature is on, the title says what the next tap will do, and the state is
reconciled from `GET_STATUS` - not from the last tap - so the screen follows the
controller even if something else changes it. The flow tile also swaps its glyph
with the title: a play triangle while stopped, a stop square while running.

| Tile | Tap while off | Tap while on | On when |
| ---- | ------------- | ------------ | ------- |
| Turn on / Turn off | `SET_MODE AUTO` | `SET_MODE OFF` | `MODE != OFF` |
| Start / Stop | `START_FLOW` | `STOP_FLOW` | `FLOW = ON` |
| Drain / Close drain | `SET_DRAIN OPEN` | `SET_DRAIN CLOSE` | `DRAIN = OPEN` |
| Cold / Auto | `SET_MODE COLD` | `SET_MODE AUTO` | `MODE = COLD` |

`Turn on` and `Cold` both drive `MODE`, so in cold mode both tiles read as on.
A command the controller refuses (for example `SAFETY_LOCK`) reverts its tile.

| Other control | Command |
| ------------- | ------- |
| Set-temperature slider | `SET_TARGET_TEMP` (debounced 350 ms) |
| Turn-on threshold | `SET_REHEAT_HYST` (1-5 °C) |
| Extra heat | `SET_INLET_OFFSET` (1-5 °C) |
| Status poll | `GET_STATUS` -> temperatures, tile states |

Run the test suites with:

```bash
.venv/bin/python tests/test_device_link.py    # link robustness
.venv/bin/python tests/test_home_actions.py   # action tile behaviour
```

## Application state

`APP_STATE` in `main.py` is passed to both screens. Replace static values with live sensor/MQTT reads:

```python
APP_STATE = {
    "current_temp": read_ds18b20(),
    "set_temp": mqtt_client.get("set"),
    "wifi_status": get_wifi_rssi(),
}
```



### Wiring up actions


| Signal                      | Where                | What to connect              |
| --------------------------- | -------------------- | ---------------------------- |
| `TempCard.temp_changed`     | `home_screen.py`     | Publish target temp via MQTT |
| `TempCard.mode_changed`     | `home_screen.py`     | Switch pump mode             |
| `SettingsScreen.wifi_reset` | `settings_screen.py` | Clear WiFi credentials       |




## Display config (Waveshare 7")

Add to `/boot/config.txt`:

```
max_usb_current=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 800 480 60 6 0 0 0
hdmi_drive=1
```

