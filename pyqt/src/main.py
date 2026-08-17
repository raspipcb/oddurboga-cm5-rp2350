"""
HÚSVIT - PyQt5 touchscreen UI for Raspberry Pi.

Supported displays: 800×480, 1024×600

Usage:
  python main.py                        # 800×480 window
  python main.py --size 1024x600        # larger layout
  python main.py --fullscreen           # auto-detect screen size
  python main.py --fullscreen --size 800x480
"""

import argparse
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget

from home_screen import HomeScreen
from i18n import i18n
from settings_screen import SettingsScreen
from settings_store import load_persisted, save_persisted
from theme import H, W, app_stylesheet, configure_screen, parse_size, theme as theme_mgr

APP_STATE = {
    "current_temp": 0.0,
    "set_temp": 36,
    "threshold": 0,
    "extra_heat": 3,
    "flow_mode": 1,
    "pot_temp": 0.0,
    "control_val": 23.4,
    "software_ver": "Version 3",
    "wifi_status": "Connected -57 dBm",
    "device_name": "Húsvit Linda - 206EF18C5EAC",
}
APP_STATE.update(load_persisted())


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


class MainWindow(QMainWindow):
    def __init__(self, fullscreen: bool = False):
        super().__init__()
        self.setWindowTitle("IPS")
        self.setFixedSize(W, H)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home = HomeScreen(state=APP_STATE)
        self.settings = SettingsScreen(state=APP_STATE)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.settings)

        self.home.navigate_settings.connect(lambda: self.stack.setCurrentWidget(self.settings))
        self.settings.navigate_home.connect(lambda: self.stack.setCurrentWidget(self.home))
        self.settings.wifi_reset.connect(self._on_wifi_reset)
        i18n.language_changed.connect(self._on_language_changed)
        theme_mgr.theme_changed.connect(self._on_theme_changed)

        if fullscreen or on_pi():
            self.showFullScreen()
        else:
            self.show()

    def _on_wifi_reset(self):
        print("WiFi reset requested")

    def _on_language_changed(self, _lang):
        self.home.retranslate()
        self.settings.retranslate()

    def _on_theme_changed(self, _name):
        QApplication.instance().setStyleSheet(app_stylesheet())
        self.home.restyle()
        self.settings.restyle()


def main():
    parser = argparse.ArgumentParser(description="HÚSVIT PyQt UI")
    parser.add_argument("--fullscreen", action="store_true", help="Fullscreen (auto-detects display size)")
    parser.add_argument(
        "--size",
        default=None,
        help="Screen preset: 800x480 (default) or 1024x600",
    )
    args = parser.parse_args()

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    width, height = detect_screen_size(args.fullscreen, args.size)
    configure_screen(width, height)
    app.setStyleSheet(app_stylesheet())

    win = MainWindow(fullscreen=args.fullscreen)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
