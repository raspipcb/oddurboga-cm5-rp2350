"""
HÚSVIT - PyQt5 touchscreen UI for Raspberry Pi.

Supported displays: 800×480, 1024×600

Usage:
  python main.py                        # 800×480 window
  python main.py --size 1024x600        # larger layout
  python main.py --fullscreen           # auto-detect screen size
  python main.py --fullscreen --size 800x480

Controller link (CM_UART0 -> RP2350):
  python main.py --port /dev/serial0    # explicit serial port
  python main.py --baud 115200          # link speed
  python main.py --mock                 # run against the built-in simulator
  python main.py --poll 2.0             # GET_STATUS interval in seconds
"""

import argparse
import os
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget

from api_log import log
from device_link import DEFAULT_BAUD, DeviceLink, default_port
from home_screen import HomeScreen
from i18n import i18n, tr
from settings_screen import SettingsScreen
from settings_store import load_persisted
from theme import (
    H, NAV_H, W, app_stylesheet, configure_screen, parse_size, theme as theme_mgr,
)
from toast import LEVEL_ERROR, LEVEL_INFO, LEVEL_SUCCESS, ToastOverlay

APP_STATE = {
    "current_temp": 0.0,
    "set_temp": 36,
    "threshold": 2,
    "extra_heat": 3,
    "flow_mode": 1,
    "pot_temp": 0.0,
    "control_val": 23.4,
    "software_ver": "Version 3",
    "wifi_status": "Connected -57 dBm",
    "device_name": "Húsvit Linda - 206EF18C5EAC",
}
APP_STATE.update(load_persisted())

DEFAULT_POLL_S = 2.0


def on_pi() -> bool:
    return os.path.exists("/proc/device-tree/model")


def detect_screen_size(fullscreen: bool, size_arg: str | None) -> tuple[int, int]:
    if size_arg:
        return parse_size(size_arg)
    app = QApplication.instance()
    if fullscreen and app:
        screen = app.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            w, h = g.width(), g.height()
            if (w, h) in {(800, 480), (1024, 600)}:
                return w, h
            # Snap to nearest supported preset
            if w >= 1024 and h >= 600:
                return 1024, 600
            return 800, 480
    return 800, 480


def resolve_port(args) -> tuple[str | None, bool]:
    """Decide between a real port and the simulator. Returns (port, mock)."""
    if args.mock:
        return None, True
    if args.port:
        return args.port, False
    guess = default_port()
    if guess and os.path.exists(guess):
        return guess, False
    if guess:
        log.info("%s not present, using simulated controller", guess)
    return None, True


class MainWindow(QMainWindow):
    def __init__(self, fullscreen: bool = False, link: DeviceLink | None = None,
                 poll_s: float = DEFAULT_POLL_S):
        super().__init__()
        self.setWindowTitle("IPS")
        self.setFixedSize(W, H)
        self.link = link

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home = HomeScreen(state=APP_STATE, link=link)
        self.settings = SettingsScreen(state=APP_STATE, link=link)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.settings)

        self.toasts = ToastOverlay(self.stack, bottom_inset=NAV_H)

        self.home.navigate_settings.connect(lambda: self.stack.setCurrentWidget(self.settings))
        self.settings.navigate_home.connect(lambda: self.stack.setCurrentWidget(self.home))
        self.settings.wifi_reset.connect(self._on_wifi_reset)
        i18n.language_changed.connect(self._on_language_changed)
        theme_mgr.theme_changed.connect(self._on_theme_changed)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(max(250, int(poll_s * 1000)))
        self.poll_timer.timeout.connect(self._poll_status)

        if link is not None:
            link.connection_changed.connect(self._on_connection_changed)
            link.call_finished.connect(self._on_call_finished)
            link.status_updated.connect(self._on_status)
            link.info_updated.connect(self._on_info)
            self._apply_link_status()
            self.poll_timer.start()

        if fullscreen or on_pi():
            self.showFullScreen()
        else:
            self.show()

    # ---- link plumbing

    def _poll_status(self):
        if self.link is None:
            return
        # Silent + coalesced: a slow link can never build a backlog of polls.
        self.link.send("GET_STATUS", silent=True, coalesce="GET_STATUS")

    def _apply_link_status(self):
        if self.link is None:
            return
        if not self.link.connected:
            text, ok = tr("status.offline"), False
        elif self.link.simulated:
            text, ok = tr("status.simulated"), True
        else:
            text, ok = tr("status.connected"), True
        for screen in (self.home, self.settings):
            screen.set_link_status(text, ok)

    def _on_connection_changed(self, connected: bool, detail: str):
        self._apply_link_status()
        if connected:
            self.toasts.show_toast(tr("status.connected"), LEVEL_SUCCESS)
            self.link.send("GET_SYSTEM_INFO", label_key="api.system_info", silent=True)
        else:
            self.toasts.show_toast(tr("status.offline"), LEVEL_ERROR)
        log.debug("connection change: %s (%s)", connected, detail)

    def _on_call_finished(self, result):
        self.home.apply_result(result)
        label = tr(result.call.label_key) if result.call.label_key else result.call.command
        if result.ok:
            if not result.call.silent:
                self.toasts.show_toast(f"{label}: {tr('api.sent')}", LEVEL_SUCCESS)
            return
        # Failures surface even for polling, but identical repeats coalesce
        # into a single toast rather than stacking up.
        code = result.code or "UNKNOWN"
        self.toasts.show_toast(f"{label}: {tr('err.' + code)}", LEVEL_ERROR)

    def _on_status(self, fields):
        self.home.apply_status(fields)
        self.settings.apply_status(fields)
        fault = (fields.get("FAULT") or "NONE").upper()
        if fault not in ("NONE", ""):
            self.toasts.show_toast(f"{tr('api.status')}: {fault}", LEVEL_ERROR)

    def _on_info(self, fields):
        self.settings.apply_info(fields)

    # ---- misc

    def _on_wifi_reset(self):
        log.info("WiFi reset requested")
        self.toasts.show_toast(tr("settings.forget_wifi"), LEVEL_INFO)

    def _on_language_changed(self, _lang):
        self.home.retranslate()
        self.settings.retranslate()
        self._apply_link_status()

    def _on_theme_changed(self, _name):
        QApplication.instance().setStyleSheet(app_stylesheet())
        self.home.restyle()
        self.settings.restyle()
        self.toasts.restyle()

    def closeEvent(self, event):
        self.poll_timer.stop()
        if self.link is not None:
            self.link.stop()
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description="HÚSVIT PyQt UI")
    parser.add_argument("--fullscreen", action="store_true",
                        help="Fullscreen (auto-detects display size)")
    parser.add_argument("--size", default=None,
                        help="Screen preset: 800x480 (default) or 1024x600")
    parser.add_argument("--port", default=os.environ.get("IPS_PORT"),
                        help="Serial port for CM_UART0 (default /dev/serial0 on Linux)")
    parser.add_argument("--baud", type=int,
                        default=int(os.environ.get("IPS_BAUD", DEFAULT_BAUD)),
                        help=f"Serial speed (default {DEFAULT_BAUD})")
    parser.add_argument("--mock", action="store_true",
                        help="Use the built-in controller simulator")
    parser.add_argument("--poll", type=float, default=DEFAULT_POLL_S,
                        help=f"GET_STATUS interval in seconds (default {DEFAULT_POLL_S})")
    args = parser.parse_args()

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    width, height = detect_screen_size(args.fullscreen, args.size)
    configure_screen(width, height)
    app.setStyleSheet(app_stylesheet())

    port, mock = resolve_port(args)
    link = DeviceLink(port=port, baud=args.baud, mock=mock)

    win = MainWindow(fullscreen=args.fullscreen, link=link, poll_s=args.poll)
    app.aboutToQuit.connect(link.stop)
    link.start()

    exit_code = app.exec_()
    link.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
