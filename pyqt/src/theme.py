"""Design tokens, screen metrics, themes, and global Qt styles."""

from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal

from settings_store import read_config, write_config

DEFAULT_THEME = "light"

LIGHT = {
    "C_BG": "#E8EEF4",
    "C_SURFACE": "#FFFFFF",
    "C_TILE": "#F4F7FA",
    "C_BORDER": "#D1DCE8",
    "C_BORDER_FOCUS": "#B8C8D8",
    "C_TEXT": "#1E3050",
    "C_TEXT_MUTED": "#6B7C8F",
    "C_TEXT_LIGHT": "#8A9AAB",
    "C_ACCENT": "#0284C7",
    "C_ACCENT_HOVER": "#0369A1",
    "C_ACCENT_SOFT": "#E0F2FE",
    "C_ACCENT_TEXT": "#0369A1",
    "C_PRESS_CYAN": "#67E8F9",
    "C_SUCCESS": "#059669",
    "C_SUCCESS_SOFT": "#ECFDF5",
    "C_WARNING": "#D97706",
    "C_WARNING_SOFT": "#FFFBEB",
    "C_DANGER": "#DC2626",
    "C_DANGER_SOFT": "#FEF2F2",
    "C_ORANGE": "#EA580C",
    "C_ORANGE_SOFT": "#FFF7ED",
    "C_ICON_BG": "#1A3050",
}

DARK = {
    "C_BG": "#0F172A",
    "C_SURFACE": "#1E293B",
    "C_TILE": "#334155",
    "C_BORDER": "#475569",
    "C_BORDER_FOCUS": "#64748B",
    "C_TEXT": "#F1F5F9",
    "C_TEXT_MUTED": "#94A3B8",
    "C_TEXT_LIGHT": "#64748B",
    "C_ACCENT": "#38BDF8",
    "C_ACCENT_HOVER": "#0EA5E9",
    "C_ACCENT_SOFT": "#0C4A6E",
    "C_ACCENT_TEXT": "#7DD3FC",
    "C_PRESS_CYAN": "#22D3EE",
    "C_SUCCESS": "#34D399",
    "C_SUCCESS_SOFT": "#064E3B",
    "C_WARNING": "#FBBF24",
    "C_WARNING_SOFT": "#78350F",
    "C_DANGER": "#F87171",
    "C_DANGER_SOFT": "#7F1D1D",
    "C_ORANGE": "#FB923C",
    "C_ORANGE_SOFT": "#7C2D12",
    "C_ICON_BG": "#0F2744",
}

PALETTES = {"light": LIGHT, "dark": DARK}

BASE_W, BASE_H = 800, 480
PRESETS = {
    "800x480": (800, 480),
    "1024x600": (1024, 600),
}

FONT_FAMILY = '"Segoe UI", "SF Pro Text", "Roboto", "Liberation Sans", sans-serif'

# Populated by configure_screen()
W, H = BASE_W, BASE_H
MARGIN = 12
GAP = 10
GAP_SM = 6
RADIUS = 12
RADIUS_SM = 10
HDR_H = 54
NAV_H = 58
CONTENT_H = H - HDR_H - NAV_H
SCALE = 1.0
HOME_LEFT_STRETCH = 11
HOME_RIGHT_STRETCH = 10
HOME_WEATHER_STRETCH = 6
HOME_TEMP_STRETCH = 4
TOUCH_MIN = 44
MODE_BTN_H = 40
ACTION_MIN_H = 140
TEMP_VALUE_PT = 26
WEATHER_ICON_SZ = 34
CARD_PAD_X = 14
CARD_PAD_Y = 12
CARD_GAP = 10

# Color tokens - updated by apply_palette()
C_BG = LIGHT["C_BG"]
C_SURFACE = LIGHT["C_SURFACE"]
C_TILE = LIGHT["C_TILE"]
C_BORDER = LIGHT["C_BORDER"]
C_BORDER_FOCUS = LIGHT["C_BORDER_FOCUS"]
C_TEXT = LIGHT["C_TEXT"]
C_TEXT_MUTED = LIGHT["C_TEXT_MUTED"]
C_TEXT_LIGHT = LIGHT["C_TEXT_LIGHT"]
C_ACCENT = LIGHT["C_ACCENT"]
C_ACCENT_HOVER = LIGHT["C_ACCENT_HOVER"]
C_ACCENT_SOFT = LIGHT["C_ACCENT_SOFT"]
C_ACCENT_TEXT = LIGHT["C_ACCENT_TEXT"]
C_PRESS_CYAN = LIGHT["C_PRESS_CYAN"]
C_SUCCESS = LIGHT["C_SUCCESS"]
C_SUCCESS_SOFT = LIGHT["C_SUCCESS_SOFT"]
C_WARNING = LIGHT["C_WARNING"]
C_WARNING_SOFT = LIGHT["C_WARNING_SOFT"]
C_DANGER = LIGHT["C_DANGER"]
C_DANGER_SOFT = LIGHT["C_DANGER_SOFT"]
C_ORANGE = LIGHT["C_ORANGE"]
C_ORANGE_SOFT = LIGHT["C_ORANGE_SOFT"]
C_ICON_BG = LIGHT["C_ICON_BG"]

# Typography roles
C_GROUP = C_TEXT
C_LABEL = C_TEXT_MUTED
C_VALUE = C_TEXT
C_VALUE_MUTED = C_TEXT_LIGHT


def _sync_typography_roles() -> None:
    global C_GROUP, C_LABEL, C_VALUE, C_VALUE_MUTED
    C_GROUP = C_TEXT
    C_LABEL = C_TEXT_MUTED
    C_VALUE = C_TEXT
    C_VALUE_MUTED = C_TEXT_LIGHT


def apply_palette(name: str) -> None:
    """Switch module-level color tokens to *name* (light or dark)."""
    palette = PALETTES.get(name, PALETTES[DEFAULT_THEME])
    g = globals()
    for key, value in palette.items():
        g[key] = value
    _sync_typography_roles()


def load_theme() -> str:
    name = read_config().get("theme", DEFAULT_THEME)
    if name in PALETTES:
        return name
    return DEFAULT_THEME


def save_theme(name: str) -> None:
    write_config({"theme": name})


class Theme(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._name = load_theme()
        apply_palette(self._name)

    @property
    def name(self) -> str:
        return self._name

    def set_theme(self, name: str) -> None:
        if name not in PALETTES or name == self._name:
            return
        self._name = name
        apply_palette(name)
        save_theme(name)
        self.theme_changed.emit(name)


theme = Theme()


def s(n: float) -> int:
    """Scale a base-800×480 pixel value to the current screen."""
    return max(1, round(n * SCALE))


def fs(n: float) -> str:
    return f"font-size: {s(n)}px;"


def transparent_bg() -> str:
    return "background: transparent;"


def group_title_style() -> str:
    return f"color: {C_GROUP}; {fs(11)} font-weight: 700; letter-spacing: 0.4px; {transparent_bg()}"


def field_label_style() -> str:
    return f"color: {C_LABEL}; {fs(12)} font-weight: 500; {transparent_bg()}"


def value_style(accent: bool = False, large: bool = False) -> str:
    color = C_ACCENT if accent else C_VALUE
    size = 20 if large else 13
    weight = 700 if large else 600
    return f"color: {color}; {fs(size)} font-weight: {weight}; {transparent_bg()}"


def configure_screen(width: int, height: int) -> None:
    """Apply layout metrics for 800×480 or 1024×600 (or any supported size)."""
    global W, H, MARGIN, GAP, GAP_SM, RADIUS, RADIUS_SM, HDR_H, NAV_H, CONTENT_H
    global SCALE, HOME_LEFT_STRETCH, HOME_RIGHT_STRETCH, HOME_WEATHER_STRETCH, HOME_TEMP_STRETCH
    global TOUCH_MIN, MODE_BTN_H, ACTION_MIN_H, TEMP_VALUE_PT, WEATHER_ICON_SZ
    global CARD_PAD_X, CARD_PAD_Y, CARD_GAP

    W = width
    H = height

    if width >= 1024 and height >= 600:
        # Extra pixels become layout space - don't scale widgets up 1.25×
        SCALE = 1.0
        MARGIN = 14
        GAP = 12
        GAP_SM = 8
        HDR_H = 56
        NAV_H = 62
        TOUCH_MIN = 44
        MODE_BTN_H = 36
        ACTION_MIN_H = 128
        TEMP_VALUE_PT = 24
        WEATHER_ICON_SZ = 32
        CARD_PAD_X = 14
        CARD_PAD_Y = 10
        CARD_GAP = 8
        HOME_LEFT_STRETCH = 11
        HOME_RIGHT_STRETCH = 10
        HOME_WEATHER_STRETCH = 5
        HOME_TEMP_STRETCH = 5
    else:
        SCALE = min(width / BASE_W, height / BASE_H)
        MARGIN = s(12)
        GAP = s(10)
        GAP_SM = s(6)
        HDR_H = s(54)
        NAV_H = s(58)
        TOUCH_MIN = s(44)
        MODE_BTN_H = s(40)
        ACTION_MIN_H = s(140)
        TEMP_VALUE_PT = s(26)
        WEATHER_ICON_SZ = s(34)
        CARD_PAD_X = s(14)
        CARD_PAD_Y = s(12)
        CARD_GAP = s(10)
        HOME_LEFT_STRETCH = 11
        HOME_RIGHT_STRETCH = 10
        HOME_WEATHER_STRETCH = 6
        HOME_TEMP_STRETCH = 4

    RADIUS = s(12)
    RADIUS_SM = s(10)
    CONTENT_H = H - HDR_H - NAV_H


def parse_size(text: str) -> tuple[int, int]:
    key = text.lower().replace(" ", "")
    if key in PRESETS:
        return PRESETS[key]
    if "x" in key:
        w, h = key.split("x", 1)
        return int(w), int(h)
    raise ValueError(f"Unknown size '{text}'. Use 800x480 or 1024x600.")


def app_stylesheet() -> str:
    groove = s(8)
    handle = s(22)
    margin = s(8)
    radius = handle // 2
    return f"""
    * {{
        font-family: {FONT_FAMILY};
    }}
    QWidget {{
        color: {C_TEXT};
        background: transparent;
    }}
    QMainWindow, QStackedWidget {{
        background-color: {C_BG};
    }}
    QLabel {{
        background: transparent;
    }}
    QSlider {{
        background: transparent;
    }}
    QPushButton {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QPushButton:flat {{
        border: none;
    }}
    QPushButton#navTab {{
        background: transparent;
        border: none;
        border-top: none;
        outline: none;
        margin: 0;
        padding: 0;
    }}
    QPushButton#navTab:pressed, QPushButton#navTab:hover, QPushButton#navTab:focus {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QSlider::groove:horizontal {{
        height: {groove}px;
        border-radius: {groove // 2}px;
        background: transparent;
        border: 1px solid {C_BORDER};
    }}
    QSlider::handle:horizontal {{
        width: {handle}px;
        height: {handle}px;
        margin: -{margin}px 0;
        border-radius: {radius}px;
        background: {C_SURFACE};
        border: 2px solid {C_ACCENT};
    }}
    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {C_ACCENT}, stop:1 #F87171);
        border-radius: {groove // 2}px;
    }}
    QSlider::add-page:horizontal {{
        background: transparent;
        border: none;
    }}
    QSlider#tempSlider {{
        background: {C_SURFACE};
    }}
    QWidget#tempSliderRow {{
        background: {C_SURFACE};
    }}
    QFrame#tempPanel {{
        background: {C_SURFACE};
    }}
    QSlider#tempSlider::groove:horizontal {{
        background: {C_SURFACE};
        border: 1px solid {C_BORDER};
    }}
    QSlider#tempSlider::add-page:horizontal {{
        background: {C_SURFACE};
        border: none;
    }}
    QSlider#tempSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {C_ACCENT}, stop:1 #F87171);
        border-radius: {groove // 2}px;
    }}
    """


def card_style(object_name: str = "card") -> str:
    return f"""
        QFrame#{object_name} {{
            background: {C_SURFACE};
            border: 1px solid {C_BORDER};
            border-radius: {RADIUS}px;
        }}
    """
