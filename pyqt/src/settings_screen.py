"""Settings screen — thresholds, sensors, device info."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from i18n import tr
import theme
from settings_store import save_persisted
from theme import GAP, MARGIN, s
from ui_common import (
    Card, FieldLabel, HeaderBar, InfoRow, LabeledSlider, LanguageSwitch, MetricCard, NavBar,
    PrimaryButton, SectionTitle,
)


class SettingsScreen(QWidget):
    navigate_home = pyqtSignal()
    wifi_reset = pyqtSignal()

    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = state or {}
        self.setStyleSheet(f"background: {theme.C_BG};")
        self._build()

    def _build(self):
        if self.layout():
            QWidget().setLayout(self.layout())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.header = HeaderBar()
        root.addWidget(self.header)

        content = QHBoxLayout()
        content.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        content.setSpacing(GAP)
        content.addLayout(self._left(), 1)
        content.addLayout(self._right(), 1)
        root.addLayout(content, 1)

        self.nav = NavBar(active="settings")
        self.nav.home_clicked.connect(self.navigate_home.emit)
        root.addWidget(self.nav)
        self.retranslate()

    def _left(self):
        col = QVBoxLayout()
        col.setSpacing(GAP)

        temp_card = Card()
        temp_body = temp_card.body()
        self.temp_section = SectionTitle("")
        temp_body.addWidget(self.temp_section)

        self.threshold = LabeledSlider(-10, 30, self.state.get("threshold", 0), large_value=True)
        self.threshold.value_changed.connect(self._on_threshold)
        temp_body.addWidget(self.threshold)

        self.extra = LabeledSlider(0, 20, self.state.get("extra_heat", 3), large_value=True)
        self.extra.value_changed.connect(self._on_extra_heat)
        temp_body.addWidget(self.extra)
        col.addWidget(temp_card)

        sensors_card = Card()
        sensors_body = sensors_card.body()
        self.sensors_section = SectionTitle("")
        sensors_body.addWidget(self.sensors_section)
        self.pot_card = MetricCard("", f"{self.state.get('pot_temp', -0.0):.1f} °C")
        self.control_card = MetricCard("", f"{self.state.get('control_val', 0):.1f} °C")
        sensors_body.addWidget(self.pot_card)
        sensors_body.addWidget(self.control_card)
        col.addWidget(sensors_card)

        col.addStretch()
        return col

    def _right(self):
        col = QVBoxLayout()
        col.setSpacing(GAP)

        about_card = Card()
        about_body = about_card.body()
        self.about_section = SectionTitle("")
        about_body.addWidget(self.about_section)
        device = self.state.get("device_name", "—")
        max_len = s(28)
        device_text = device if len(device) < max_len else device[: max_len - 1] + "…"
        self.software_row = InfoRow("", self.state.get("software_ver", "Version 3"))
        self.wifi_row = InfoRow("", self.state.get("wifi_status", tr("status.connected")), accent=True)
        self.device_row = InfoRow("", device_text, divider=False)
        about_body.addWidget(self.software_row)
        about_body.addWidget(self.wifi_row)
        about_body.addWidget(self.device_row)
        col.addWidget(about_card)

        prefs_card = Card()
        prefs_body = prefs_card.body()
        lang_row = QHBoxLayout()
        lang_row.setSpacing(s(8))
        self.lang_section = FieldLabel("")
        self.lang_switch = LanguageSwitch()
        lang_row.addWidget(self.lang_section, 0, Qt.AlignVCenter)
        lang_row.addStretch(1)
        lang_row.addWidget(self.lang_switch, 0, Qt.AlignRight | Qt.AlignVCenter)
        prefs_body.addLayout(lang_row)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {theme.C_BORDER}; border: none;")
        self.prefs_divider = divider
        prefs_body.addWidget(divider)

        net_row = QHBoxLayout()
        net_row.setSpacing(s(8))
        self.forget_lbl = FieldLabel("")
        self.reset_btn = PrimaryButton("", danger=True, compact=True, icon="wifi")
        self.reset_btn.clicked.connect(self.wifi_reset.emit)
        net_row.addWidget(self.forget_lbl, 0, Qt.AlignVCenter)
        net_row.addStretch(1)
        net_row.addWidget(self.reset_btn, 0, Qt.AlignRight | Qt.AlignVCenter)
        prefs_body.addLayout(net_row)
        col.addWidget(prefs_card)

        col.addStretch()
        return col

    def retranslate(self):
        self.temp_section.setText(tr("settings.temp_settings"))
        self.threshold.set_label(tr("settings.threshold"))
        self.extra.set_label(tr("settings.extra_heat"))
        self.sensors_section.setText(tr("settings.sensors"))
        self.pot_card.label.setText(tr("settings.sensor_pot"))
        self.control_card.label.setText(tr("settings.sensor_control"))

        self.about_section.setText(tr("settings.about"))
        self.software_row.left.setText(tr("settings.software"))
        self.wifi_row.left.setText(tr("settings.wifi"))
        self.device_row.left.setText(tr("settings.device"))

        self.lang_section.setText(tr("settings.language"))
        self.forget_lbl.setText(tr("settings.forget_wifi"))
        self.reset_btn.setText(tr("settings.reset"))

        self.nav.retranslate()

    def _on_threshold(self, value):
        self.state["threshold"] = value
        save_persisted(threshold=value)

    def _on_extra_heat(self, value):
        self.state["extra_heat"] = value
        save_persisted(extra_heat=value)

    def restyle(self):
        self.setStyleSheet(f"background: {theme.C_BG};")
        self.header.restyle()
        self.prefs_divider.setStyleSheet(f"background: {theme.C_BORDER}; border: none;")
        self.temp_section.restyle()
        self.sensors_section.restyle()
        self.about_section.restyle()
        self.lang_section.restyle()
        self.forget_lbl.restyle()
        self.threshold.restyle()
        self.extra.restyle()
        self.pot_card.restyle()
        self.control_card.restyle()
        self.software_row.restyle()
        self.wifi_row.restyle()
        self.device_row.restyle()
        self.reset_btn.restyle()
        self.lang_switch.restyle()
        for card in self.findChildren(Card):
            card.restyle()
        self.nav.restyle()
