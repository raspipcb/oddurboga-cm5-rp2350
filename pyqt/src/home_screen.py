"""Home screen - temperature control and quick actions."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QSizePolicy,
    QVBoxLayout, QWidget,
)

from i18n import tr
from icons import icon_pixmap
import theme
from settings_store import save_persisted
from theme import (
    GAP, GAP_SM, HOME_LEFT_STRETCH, HOME_RIGHT_STRETCH, HOME_TEMP_STRETCH,
    HOME_WEATHER_STRETCH, MARGIN, ACTION_MIN_H, TEMP_VALUE_PT, WEATHER_ICON_SZ,
    RADIUS_SM, TOUCH_MIN, card_style, field_label_style, group_title_style, transparent_bg,
    value_style, fs, s,
)
from ui_common import Card, FieldLabel, HeaderBar, NavBar, SegmentedControl, StepButton

class ActionButton(QFrame):
    clicked = pyqtSignal()

    def __init__(self, title_key, subtitle_key, icon, active=False, parent=None):
        super().__init__(parent)
        self._title_key = title_key
        self._subtitle_key = subtitle_key
        self._icon = icon
        self._active = active
        self._pressed = False
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(ACTION_MIN_H)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(s(12), s(12), s(12), s(12))
        layout.setSpacing(s(2))
        layout.setAlignment(Qt.AlignCenter)

        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_lbl, 0, Qt.AlignHCenter)

        self.title_lbl = QLabel()
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setFont(QFont("", s(15), QFont.DemiBold))
        self.sub_lbl = QLabel()
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        self.sub_lbl.setWordWrap(True)
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.sub_lbl)
        self.retranslate()
        self._apply_tile_style()

    def _update_icon(self):
        icon_size = s(52)
        self.icon_lbl.setPixmap(
            icon_pixmap(self._icon, icon_size, fg="#FFFFFF", bg=theme.C_ICON_BG)
        )

    def _apply_tile_style(self):
        if self._pressed:
            bg = theme.C_PRESS_CYAN
        else:
            bg = theme.C_SURFACE
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: none;
                border-radius: {RADIUS_SM}px;
            }}
        """)

    def retranslate(self):
        self.title_lbl.setText(tr(self._title_key))
        self.sub_lbl.setText(tr(self._subtitle_key))
        self._update_icon()
        self.title_lbl.setStyleSheet(
            f"color: {theme.C_TEXT if not self._active else theme.C_ACCENT_TEXT}; {fs(15)} font-weight: 600; {transparent_bg()}"
        )
        self.sub_lbl.setStyleSheet(
            f"color: {theme.C_TEXT_MUTED if not self._active else theme.C_ACCENT_TEXT}; {fs(11)} {transparent_bg()}"
        )
        self._apply_tile_style()

    def mousePressEvent(self, event):
        self._pressed = True
        self._apply_tile_style()
        self.clicked.emit()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self._apply_tile_style()
        super().mouseReleaseEvent(event)

    def restyle(self):
        self.retranslate()


class TempPanel(Card):
    temp_changed = pyqtSignal(int)
    mode_changed = pyqtSignal(int)

    def __init__(self, current=-0.0, target=36, flow_mode=1, parent=None):
        super().__init__(parent)
        self.set_card_name("tempPanel")
        layout = self.body()
        layout.setSpacing(s(8))

        self.title = QLabel()
        self.title.setStyleSheet(group_title_style())
        layout.addWidget(self.title)

        temps = QHBoxLayout()
        temps.setSpacing(s(16))

        cur_box = QVBoxLayout()
        cur_box.setSpacing(s(4))
        self.current_lbl = QLabel()
        self.current_lbl.setStyleSheet(field_label_style())
        cur_box.addWidget(self.current_lbl)
        self.cur_val = QLabel(f"{current:.1f} °C")
        self.cur_val.setFont(QFont("", TEMP_VALUE_PT, QFont.Light))
        self.cur_val.setStyleSheet(value_style(large=True))
        cur_box.addWidget(self.cur_val)
        temps.addLayout(cur_box)
        temps.addStretch()

        tgt_box = QVBoxLayout()
        tgt_box.setSpacing(s(4))
        tgt_box.setAlignment(Qt.AlignRight)
        self.target_lbl = QLabel()
        self.target_lbl.setAlignment(Qt.AlignRight)
        self.target_lbl.setStyleSheet(field_label_style())
        tgt_box.addWidget(self.target_lbl)
        self.target_val = QLabel(f"{target} °C")
        self.target_val.setAlignment(Qt.AlignRight)
        self.target_val.setFont(QFont("", TEMP_VALUE_PT, QFont.DemiBold))
        self.target_val.setStyleSheet(value_style(accent=True, large=True))
        tgt_box.addWidget(self.target_val)
        temps.addLayout(tgt_box)
        layout.addLayout(temps)

        controls = QHBoxLayout()
        controls.setSpacing(s(10))
        controls.setContentsMargins(0, 0, 0, 0)
        minus = StepButton(icon="minus")
        minus.clicked.connect(lambda: self._step(-1))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setObjectName("tempSlider")
        self.slider.setFixedHeight(s(32))
        self.slider.setRange(20, 50)
        self.slider.setValue(target)
        self.slider.valueChanged.connect(self._on_slider)
        plus = StepButton(icon="plus")
        plus.clicked.connect(lambda: self._step(1))
        self.minus_btn = minus
        self.plus_btn = plus
        controls.addWidget(minus)
        controls.addWidget(self.slider, 1)
        controls.addWidget(plus)

        controls_wrap = QWidget()
        controls_wrap.setObjectName("tempSliderRow")
        controls_wrap.setAutoFillBackground(True)
        controls_wrap.setStyleSheet(f"background-color: {theme.C_SURFACE};")
        controls_wrap.setLayout(controls)
        self.controls_wrap = controls_wrap
        layout.addWidget(controls_wrap)

        self.modes = SegmentedControl([], selected=flow_mode)
        self.modes.changed.connect(self.mode_changed.emit)
        layout.addWidget(self.modes)
        self.retranslate()

    def retranslate(self):
        self.title.setText(tr("home.temp.title"))
        self.current_lbl.setText(tr("home.temp.current"))
        self.target_lbl.setText(tr("home.temp.target"))
        self.modes.set_labels([
            tr("home.mode.steady"),
            tr("home.mode.medium"),
            tr("home.mode.low"),
        ])

    def _step(self, delta):
        self.slider.setValue(max(20, min(50, self.slider.value() + delta)))

    def _on_slider(self, value):
        self.target_val.setText(f"{value}°C")
        self.temp_changed.emit(value)

    def restyle(self):
        super().restyle()
        self.title.setStyleSheet(group_title_style())
        self.current_lbl.setStyleSheet(field_label_style())
        self.target_lbl.setStyleSheet(field_label_style())
        self.cur_val.setStyleSheet(value_style(large=True))
        self.target_val.setStyleSheet(value_style(accent=True, large=True))
        self.controls_wrap.setStyleSheet(f"background-color: {theme.C_SURFACE};")
        self.minus_btn.restyle()
        self.plus_btn.restyle()
        self.modes.restyle()
        self.retranslate()


class WeatherStrip(Card):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_card_name("weatherCard")
        self.setStyleSheet(
            card_style("weatherCard")
            + f" QFrame#weatherCard QLabel, QFrame#weatherCard QWidget {{ {transparent_bg()} }}"
        )
        layout = self.body()
        layout.setSpacing(s(8))

        header = QHBoxLayout()
        header.setSpacing(s(8))
        left = QVBoxLayout()
        left.setSpacing(s(2))
        self.title = QLabel()
        self.title.setStyleSheet(group_title_style())
        self.subtitle = QLabel()
        self.subtitle.setStyleSheet(field_label_style())
        left.addWidget(self.title)
        left.addWidget(self.subtitle)
        header.addLayout(left, 1)
        header.addStretch()

        self.refresh_btn = QPushButton()
        self.refresh_btn.setFixedSize(TOUCH_MIN, TOUCH_MIN)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: {TOUCH_MIN // 2}px;
            }}
            QPushButton:pressed {{
                opacity: 0.55;
            }}
        """)
        self._set_refresh_icon()
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        self.row = QHBoxLayout()
        self.row.setSpacing(GAP_SM)
        self.day_labels = []
        self.icon_labels = []
        self.temp_labels = []
        self.note_labels = []
        self._forecast = [
            ("sun", "9°", "> 3m/s", "orange"),
            ("cloud", "8°", "^ 4m/s", "accent"),
            ("rain", "8°", "^ 3m/s", "accent"),
            ("rain", "9°", "v 5m/s", "accent"),
        ]
        icon_sz = WEATHER_ICON_SZ
        self._icon_sz = icon_sz
        for weather_icon, temp, note, color_key in self._forecast:
            cell = QVBoxLayout()
            cell.setContentsMargins(0, 0, 0, 0)
            cell.setSpacing(s(4))
            day = QLabel()
            day.setAlignment(Qt.AlignCenter)
            day.setStyleSheet(field_label_style())
            ico = QLabel()
            ico.setAlignment(Qt.AlignCenter)
            ico.setFixedSize(icon_sz, icon_sz)
            ico.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            ico.setAutoFillBackground(False)
            ico.setStyleSheet(transparent_bg())
            ico.setPixmap(icon_pixmap(weather_icon, icon_sz, fg=self._forecast_color(color_key)))
            t = QLabel(temp)
            t.setAlignment(Qt.AlignCenter)
            t.setStyleSheet(value_style())
            n = QLabel(note)
            n.setAlignment(Qt.AlignCenter)
            n.setStyleSheet(f"color: {theme.C_TEXT_LIGHT}; {fs(10)} {transparent_bg()}")
            cell.addWidget(day, 0, Qt.AlignHCenter)
            cell.addWidget(ico, 0, Qt.AlignHCenter)
            cell.addWidget(t, 0, Qt.AlignHCenter)
            cell.addWidget(n, 0, Qt.AlignHCenter)
            self.day_labels.append(day)
            self.icon_labels.append(ico)
            self.temp_labels.append(t)
            self.note_labels.append(n)
            self.row.addLayout(cell, 1)
        layout.addLayout(self.row)
        self.retranslate()

    def _set_refresh_icon(self):
        icon_sz = s(22)
        pix = icon_pixmap("refresh", icon_sz, fg=theme.C_ACCENT)
        self.refresh_btn.setIcon(QIcon(pix))
        self.refresh_btn.setIconSize(pix.size())

    def retranslate(self):
        self.title.setText(tr("home.weather.title"))
        self.subtitle.setText(tr("home.weather.subtitle"))
        for lbl, key in zip(self.day_labels, [
            "home.weather.mon", "home.weather.tue", "home.weather.wed", "home.weather.thu",
        ]):
            lbl.setText(tr(key))

    @staticmethod
    def _forecast_color(key: str) -> str:
        return theme.C_ORANGE if key == "orange" else theme.C_ACCENT

    def restyle(self):
        super().restyle()
        self.setStyleSheet(
            card_style("weatherCard")
            + f" QFrame#weatherCard QLabel, QFrame#weatherCard QWidget {{ {transparent_bg()} }}"
        )
        self.title.setStyleSheet(group_title_style())
        self.subtitle.setStyleSheet(field_label_style())
        for lbl in self.day_labels:
            lbl.setStyleSheet(field_label_style())
        for ico, (weather_icon, _, _, color_key) in zip(self.icon_labels, self._forecast):
            ico.setPixmap(
                icon_pixmap(weather_icon, self._icon_sz, fg=self._forecast_color(color_key))
            )
        for t in self.temp_labels:
            t.setStyleSheet(value_style())
        for n in self.note_labels:
            n.setStyleSheet(f"color: {theme.C_TEXT_LIGHT}; {fs(10)} {transparent_bg()}")
        self._set_refresh_icon()
        self.retranslate()


class HomeScreen(QWidget):
    navigate_settings = pyqtSignal()

    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = state or {}
        self.setStyleSheet(f"background: {theme.C_BG};")
        self._action_buttons = []
        self._build()

    def _build(self):
        if self.layout():
            QWidget().setLayout(self.layout())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        status = self.state.get("wifi_status", tr("status.connected"))
        self.header = HeaderBar(status_text=status[:16])
        root.addWidget(self.header)

        content = QHBoxLayout()
        content.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        content.setSpacing(GAP)

        # Left: 2×2 action grid (matches hardware mockup)
        actions = QGridLayout()
        actions.setSpacing(GAP)
        actions.setRowStretch(0, 1)
        actions.setRowStretch(1, 1)
        actions.setColumnStretch(0, 1)
        actions.setColumnStretch(1, 1)
        self._action_buttons = []
        for i, (title_key, sub_key, icon, active) in enumerate([
            ("home.action.turn_on.title", "home.action.turn_on.sub", "power", False),
            ("home.action.stop.title", "home.action.stop.sub", "stop", False),
            ("home.action.drain.title", "home.action.drain.sub", "drop", True),
            ("home.action.cold.title", "home.action.cold.sub", "cold", False),
        ]):
            btn = ActionButton(title_key, sub_key, icon, active=active)
            self._action_buttons.append(btn)
            actions.addWidget(btn, i // 2, i % 2)
        action_wrap = QWidget()
        action_wrap.setStyleSheet("background: transparent;")
        action_wrap.setLayout(actions)
        content.addWidget(action_wrap, HOME_LEFT_STRETCH)

        # Right: weather (top) + temperature (bottom)
        right = QVBoxLayout()
        right.setSpacing(GAP)
        self.weather = WeatherStrip()
        self.temp = TempPanel(
            current=self.state.get("current_temp", -0.0),
            target=self.state.get("set_temp", 36),
            flow_mode=self.state.get("flow_mode", 1),
        )
        self.temp.temp_changed.connect(self._on_set_temp)
        self.temp.mode_changed.connect(self._on_flow_mode)
        right.addWidget(self.weather, HOME_WEATHER_STRETCH)
        right.addWidget(self.temp, HOME_TEMP_STRETCH)
        content.addLayout(right, HOME_RIGHT_STRETCH)

        root.addLayout(content, 1)

        self.nav = NavBar(active="home")
        self.nav.settings_clicked.connect(self.navigate_settings.emit)
        root.addWidget(self.nav)
        self.retranslate()

    def retranslate(self):
        self.header.set_status(self.state.get("wifi_status", tr("status.connected"))[:16])
        self.temp.retranslate()
        self.weather.retranslate()
        for btn in self._action_buttons:
            btn.retranslate()
        self.nav.retranslate()

    def _on_set_temp(self, value):
        self.state["set_temp"] = value
        save_persisted(set_temp=value)

    def _on_flow_mode(self, mode):
        self.state["flow_mode"] = mode
        save_persisted(flow_mode=mode)

    def restyle(self):
        self.setStyleSheet(f"background: {theme.C_BG};")
        self.header.restyle()
        self.weather.restyle()
        self.temp.restyle()
        for btn in self._action_buttons:
            btn.restyle()
        self.nav.restyle()
