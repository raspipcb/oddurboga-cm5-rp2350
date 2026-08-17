"""Reusable UI components."""

from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QSizePolicy, QVBoxLayout, QWidget,
)

from i18n import i18n, tr
from icons import icon_pixmap
import theme
from theme import (
    GAP_SM, HDR_H, NAV_H, RADIUS_SM, TOUCH_MIN, CARD_GAP, CARD_PAD_X, CARD_PAD_Y,
    MODE_BTN_H, card_style, field_label_style,
    group_title_style, theme as theme_mgr, transparent_bg, value_style, fs, s,
)

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS / "logo.png"


class ThemeSwitch(QWidget):
    """Light / dark theme toggle using sun and moon icons."""

    _ICON_SZ = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setStyleSheet(transparent_bg())
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(s(4))
        btn_sz = s(32)
        self.light_btn = QPushButton()
        self.dark_btn = QPushButton()
        for btn in (self.light_btn, self.dark_btn):
            btn.setFixedSize(btn_sz, btn_sz)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFlat(True)
        self.light_btn.clicked.connect(lambda: self._select("light"))
        self.dark_btn.clicked.connect(lambda: self._select("dark"))
        layout.addWidget(self.light_btn)
        layout.addWidget(self.dark_btn)

        self._select(theme_mgr.name)
        theme_mgr.theme_changed.connect(lambda _: self._select(theme_mgr.name))

    def _select(self, name: str):
        icon_sz = s(self._ICON_SZ)
        for btn, mode, icon_name in (
            (self.light_btn, "light", "sun"),
            (self.dark_btn, "dark", "moon"),
        ):
            active = mode == name
            color = theme.C_ACCENT if active else theme.C_TEXT_MUTED
            pix = icon_pixmap(icon_name, icon_sz, fg=color)
            btn.setIcon(QIcon(pix))
            btn.setIconSize(pix.size())
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: {RADIUS_SM}px;
                    padding: 0;
                }}
                QPushButton:pressed {{
                    background: {theme.C_ACCENT_SOFT};
                }}
            """)
        if name != theme_mgr.name:
            theme_mgr.set_theme(name)

    def restyle(self):
        self._select(theme_mgr.name)


class HeaderBar(QFrame):
    def __init__(self, status_text=None, status_ok=True, parent=None):
        super().__init__(parent)
        self._status_ok = status_ok
        self._status_message = status_text or tr("status.connected")
        self.setFixedHeight(HDR_H)
        self._apply_frame_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(s(14), 0, s(14), 0)
        layout.setSpacing(s(10))

        if LOGO_PATH.is_file():
            self.logo = QLabel()
            logo_sz = s(40)
            self.logo.setPixmap(
                QPixmap(str(LOGO_PATH)).scaled(logo_sz, logo_sz, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            layout.addWidget(self.logo)

        layout.addStretch()

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(s(8), s(8))
        self.status_text = QLabel()

        self.status = QFrame()
        self.status.setObjectName("statusPill")
        pill_layout = QHBoxLayout(self.status)
        pill_layout.setContentsMargins(s(10), s(5), s(12), s(5))
        pill_layout.setSpacing(s(6))
        pill_layout.addWidget(self.status_dot, 0, Qt.AlignVCenter)
        pill_layout.addWidget(self.status_text, 0, Qt.AlignVCenter)
        layout.addWidget(self.status)

        self.theme_switch = ThemeSwitch()
        layout.addWidget(self.theme_switch)

        self.set_status(self._status_message, status_ok)

    def _apply_frame_style(self):
        self.setStyleSheet(f"QFrame {{ background: {theme.C_SURFACE}; border-bottom: 1px solid {theme.C_BORDER}; }}")

    def restyle(self):
        self._apply_frame_style()
        self.set_status(self._status_message, self._status_ok)
        self.theme_switch.restyle()

    def set_status(self, text, ok=None):
        self._status_message = text
        if ok is None:
            lower = text.lower()
            ok = any(k in lower for k in ("connect", "tengd", "tengdur"))
        self._status_ok = ok
        self.status_text.setText(text)
        dot_color = theme.C_SUCCESS if ok else theme.C_DANGER
        self.status_dot.setStyleSheet(f"""
            background: {dot_color};
            border: none;
            border-radius: {s(4)}px;
        """)
        self.status_text.setStyleSheet(
            f"color: {theme.C_TEXT if ok else theme.C_DANGER}; {fs(11)} font-weight: 600; {transparent_bg()}"
        )
        self.status.setStyleSheet(f"""
            QFrame#statusPill {{
                background: transparent;
                border: none;
            }}
        """)


class NavTab(QPushButton):
    """Nav item with icon and label side by side, centred in the tab."""

    _ICON_SZ = 28
    _FONT_SZ = 14

    def __init__(self, label, icon_name, active=False, parent=None):
        super().__init__(parent)
        self.setObjectName("navTab")
        self._icon_name = icon_name
        self._label_text = label
        self._active = active
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(TOUCH_MIN)
        self.setFlat(True)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_StyledBackground, True)

        row = QHBoxLayout(self)
        row.setContentsMargins(s(16), s(6), s(16), s(6))
        row.setSpacing(s(8))
        row.addStretch(1)
        self._icon = QLabel()
        self._icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._icon.setStyleSheet(f"border: none; {transparent_bg()}")
        self._text = QLabel(label)
        self._text.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._text.setStyleSheet(f"border: none; {transparent_bg()}")
        row.addWidget(self._icon, 0, Qt.AlignVCenter)
        row.addWidget(self._text, 0, Qt.AlignVCenter)
        row.addStretch(1)
        self._apply_style(active)

    def set_active(self, active: bool):
        self._active = active
        self._apply_style(active)

    def set_label(self, label: str):
        self._label_text = label
        self._text.setText(label)
        self._apply_style(self._active)

    def _apply_style(self, active: bool):
        color = theme.C_ACCENT if active else theme.C_TEXT_MUTED
        text_color = theme.C_ACCENT_TEXT if active else theme.C_TEXT_MUTED
        icon_sz = s(self._ICON_SZ)
        self._icon.setPixmap(icon_pixmap(self._icon_name, icon_sz, fg=color))
        self._text.setStyleSheet(
            f"color: {text_color}; {fs(self._FONT_SZ)} font-weight: {'600' if active else '500'}; "
            f"border: none; {transparent_bg()}"
        )
        self.setStyleSheet(f"""
            QPushButton#navTab {{
                background: transparent;
                border: none;
                border-top: none;
                border-bottom: none;
                outline: none;
                margin: 0;
                padding: 0;
            }}
            QPushButton#navTab:pressed, QPushButton#navTab:hover, QPushButton#navTab:focus {{
                background: transparent;
                border: none;
                outline: none;
            }}
        """)


class NavBar(QFrame):
    home_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()

    def __init__(self, active="home", parent=None):
        super().__init__(parent)
        self._active = active
        self.setFixedHeight(NAV_H)
        self.setStyleSheet(f"QFrame {{ background: {theme.C_SURFACE}; border-top: 1px solid {theme.C_BORDER}; }}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(s(12), s(8), s(12), s(8))
        layout.setSpacing(s(10))

        self.home_btn = NavTab(tr("nav.home"), "home", active == "home")
        self.settings_btn = NavTab(tr("nav.settings"), "settings", active == "settings")
        self.home_btn.clicked.connect(self.home_clicked.emit)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.home_btn, 1)
        layout.addWidget(self.settings_btn, 1)

        i18n.language_changed.connect(self.retranslate)
        theme_mgr.theme_changed.connect(lambda _: self.restyle())

    def retranslate(self, _lang=None):
        self.home_btn.set_label(tr("nav.home"))
        self.settings_btn.set_label(tr("nav.settings"))
        self.home_btn.set_active(self._active == "home")
        self.settings_btn.set_active(self._active == "settings")

    def restyle(self):
        self.setStyleSheet(f"QFrame {{ background: {theme.C_SURFACE}; border-top: 1px solid {theme.C_BORDER}; }}")
        self.home_btn.set_active(self._active == "home")
        self.settings_btn.set_active(self._active == "settings")


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self._card_name = "card"
        self.setStyleSheet(card_style(self._card_name))
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(CARD_PAD_X, CARD_PAD_Y, CARD_PAD_X, CARD_PAD_Y)
        self._layout.setSpacing(CARD_GAP)

    def set_card_name(self, name: str):
        self._card_name = name
        self.setObjectName(name)

    def body(self):
        return self._layout

    def restyle(self):
        self.setStyleSheet(card_style(self._card_name))


class SectionTitle(QLabel):
    """Card / section group header."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.restyle()

    def restyle(self):
        self.setStyleSheet(group_title_style())


class FieldLabel(QLabel):
    """Individual setting or row label."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.restyle()

    def restyle(self):
        self.setStyleSheet(field_label_style())


class MetricCard(QFrame):
    def __init__(self, label, value, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ {transparent_bg()} border: none; }}")
        self.setFixedHeight(s(40))
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(s(8))
        self.label = QLabel(label)
        self.label.setStyleSheet(field_label_style())
        self.value = QLabel(value)
        self.value.setFont(QFont("", s(18), QFont.DemiBold))
        self.value.setStyleSheet(value_style(large=True))
        self.value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.label)
        row.addStretch()
        row.addWidget(self.value)

    def set_value(self, value):
        self.value.setText(value)

    def restyle(self):
        self.label.setStyleSheet(field_label_style())
        self.value.setStyleSheet(value_style(large=True))


class InfoRow(QFrame):
    """Key/value row for use inside a grouped settings card (no outer border)."""

    def __init__(self, label, value, accent=False, divider=True, parent=None):
        super().__init__(parent)
        self._accent = accent
        self._divider = divider
        self.setFixedHeight(s(40))
        self._apply_frame_style()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.left = QLabel(label)
        self.left.setStyleSheet(field_label_style())
        self.right = QLabel(value)
        self.right.setStyleSheet(value_style(accent=accent))
        self.right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.left)
        row.addStretch()
        row.addWidget(self.right)

    def _apply_frame_style(self):
        border = f"border-bottom: 1px solid {theme.C_BORDER};" if self._divider else ""
        self.setStyleSheet(f"QFrame {{ background: transparent; {border} }}")

    def set_value(self, value):
        self.right.setText(value)

    def restyle(self):
        self._apply_frame_style()
        self.left.setStyleSheet(field_label_style())
        self.right.setStyleSheet(value_style(accent=self._accent))


class SettingRow(QFrame):
    def __init__(self, label, value, value_color=theme.C_TEXT, parent=None):
        super().__init__(parent)
        self.setFixedHeight(s(48))
        self.setObjectName("card")
        self.setStyleSheet(card_style())
        row = QHBoxLayout(self)
        row.setContentsMargins(s(14), 0, s(14), 0)
        self.left = QLabel(label)
        self.left.setStyleSheet(f"color: {theme.C_TEXT}; {fs(13)}")
        self.right = QLabel(value)
        self.right.setStyleSheet(f"color: {value_color}; {fs(13)} font-weight: 500;")
        self.right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.left)
        row.addStretch()
        row.addWidget(self.right)

    def set_value(self, value):
        self.right.setText(value)


class StepButton(QPushButton):
    _ICON_SZ = 28

    def __init__(self, text=None, icon=None, parent=None):
        super().__init__(parent)
        self._icon_name = icon
        sz = max(TOUCH_MIN, s(44))
        self.setFixedSize(sz, sz)
        self.setCursor(Qt.PointingHandCursor)
        if icon:
            self._apply_icon()
        elif text:
            self.setText(text)
        self.restyle()

    def _apply_icon(self):
        icon_sz = s(self._ICON_SZ)
        pix = icon_pixmap(self._icon_name, icon_sz, fg=theme.C_ACCENT)
        self.setIcon(QIcon(pix))
        self.setIconSize(pix.size())

    def restyle(self):
        if self._icon_name:
            self._apply_icon()
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {theme.C_ACCENT};
                border: none;
                {fs(22)}
                font-weight: 600;
            }}
            QPushButton:pressed {{
                background: transparent;
                opacity: 0.55;
            }}
        """)


class SegmentedControl(QWidget):
    changed = pyqtSignal(int)

    def __init__(self, labels, selected=0, parent=None):
        super().__init__(parent)
        self.setStyleSheet(transparent_bg())
        self._buttons = []
        self._selected = selected
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GAP_SM)
        for i, label in enumerate(labels):
            btn = QPushButton(label)
            btn.setMinimumHeight(MODE_BTN_H)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._select(idx))
            self._buttons.append(btn)
            layout.addWidget(btn, 1)
        self._select(selected)

    def set_labels(self, labels, selected=None):
        if selected is None:
            selected = self._selected
        for btn, label in zip(self._buttons, labels):
            btn.setText(label)
        self._select(selected)

    def _select(self, index):
        self._selected = index
        for i, btn in enumerate(self._buttons):
            if i == index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {theme.C_ACCENT};
                        border: none;
                        border-radius: {RADIUS_SM}px;
                        {fs(12)}
                        font-weight: 600;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {theme.C_TEXT_MUTED};
                        border: none;
                        border-radius: {RADIUS_SM}px;
                        {fs(12)}
                        font-weight: 500;
                    }}
                    QPushButton:pressed {{
                        color: {theme.C_ACCENT};
                    }}
                """)
        self.changed.emit(index)

    def restyle(self):
        self._select(self._selected)


class LabeledSlider(QWidget):
    value_changed = pyqtSignal(int)

    def __init__(self, lo, hi, value, label="", suffix="°C", large_value=False, parent=None):
        super().__init__(parent)
        self._large_value = large_value
        self.setStyleSheet(transparent_bg())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(s(6))

        header = QHBoxLayout()
        header.setSpacing(s(8))
        self.field_lbl = QLabel(label)
        self.field_lbl.setStyleSheet(field_label_style())
        header.addWidget(self.field_lbl)
        header.addStretch()
        self.value_lbl = QLabel(f"{value}{suffix}")
        self.value_lbl.setStyleSheet(value_style(accent=True, large=self._large_value))
        self.value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.value_lbl)
        layout.addLayout(header)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setFixedHeight(s(32))
        self.slider.setRange(lo, hi)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(self._on_change)
        layout.addWidget(self.slider)
        self._suffix = suffix

    def set_label(self, text: str):
        self.field_lbl.setText(text)

    def _on_change(self, value):
        self.value_lbl.setText(f"{value}{self._suffix}")
        self.value_changed.emit(value)

    def restyle(self):
        self.field_lbl.setStyleSheet(field_label_style())
        self.value_lbl.setStyleSheet(value_style(accent=True, large=self._large_value))


class PrimaryButton(QPushButton):
    def __init__(self, text, danger=False, compact=False, icon=None, parent=None):
        super().__init__(text, parent)
        self._danger = danger
        self._compact = compact
        self._icon_name = icon
        self.setMinimumHeight(s(36) if compact else TOUCH_MIN)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.restyle()

    def restyle(self):
        bg = theme.C_DANGER if self._danger else theme.C_ACCENT
        pad_x = s(12) if self._compact else s(18)
        if self._icon_name:
            icon_sz = s(14 if self._compact else 16)
            pix = icon_pixmap(self._icon_name, icon_sz, fg="#FFFFFF")
            self.setIcon(QIcon(pix))
            self.setIconSize(pix.size())
            pad_x = s(10) if self._compact else s(14)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: white;
                border: none;
                border-radius: {RADIUS_SM}px;
                {fs(12 if self._compact else 13)}
                font-weight: 600;
                padding: 0 {pad_x}px;
            }}
            QPushButton:pressed {{ opacity: 0.9; }}
        """)


class LanguageSwitch(QWidget):
    changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setStyleSheet(transparent_bg())
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GAP_SM)

        self.en_btn = QPushButton(tr("settings.language.en"))
        self.is_btn = QPushButton(tr("settings.language.is"))
        for btn in (self.en_btn, self.is_btn):
            btn.setMinimumHeight(s(36))
            btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            btn.setCursor(Qt.PointingHandCursor)
        for code, btn in (("en", self.en_btn), ("is", self.is_btn)):
            btn.clicked.connect(lambda _, c=code: self._select(c))
        layout.addWidget(self.en_btn)
        layout.addWidget(self.is_btn)
        self._select(i18n.language)
        i18n.language_changed.connect(lambda _: self._select(i18n.language))
        theme_mgr.theme_changed.connect(lambda _: self.restyle())

    def _select(self, code):
        pad = f"padding: {s(4)}px {s(10)}px;"
        for btn, lang in ((self.en_btn, "en"), (self.is_btn, "is")):
            active = lang == code
            if active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {theme.C_ACCENT};
                        border: none;
                        border-radius: {RADIUS_SM}px;
                        {fs(12)}
                        font-weight: 600;
                        {pad}
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {theme.C_TEXT_MUTED};
                        border: none;
                        border-radius: {RADIUS_SM}px;
                        {fs(12)}
                        font-weight: 500;
                        {pad}
                    }}
                    QPushButton:pressed {{
                        color: {theme.C_ACCENT};
                    }}
                """)
        if code != i18n.language:
            i18n.set_language(code)
        self.changed.emit(code)

    def restyle(self):
        self._select(i18n.language)
