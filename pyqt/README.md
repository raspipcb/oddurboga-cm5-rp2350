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

