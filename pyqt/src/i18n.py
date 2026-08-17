"""Lightweight translations - English default, Icelandic optional."""

from PyQt5.QtCore import QObject, pyqtSignal

from settings_store import read_config, write_config

DEFAULT_LANGUAGE = "en"

TRANSLATIONS = {
    "en": {
        "nav.home": "Home",
        "nav.settings": "Settings",
        "status.connected": "Connected",
        "home.temp.title": "Temperature in tub",
        "home.temp.current": "Current",
        "home.temp.target": "Set temperature",
        "home.mode.steady": "Continuous",
        "home.mode.medium": "Medium",
        "home.mode.low": "Low flow",
        "home.weather.title": "Weather forecast",
        "home.weather.subtitle": "Smoke Bay",
        "home.weather.mon": "Mon",
        "home.weather.tue": "Tue",
        "home.weather.wed": "Wed",
        "home.weather.thu": "Thu",
        "home.action.turn_on.title": "Turn on",
        "home.action.turn_on.sub": "the hot tub",
        "home.action.stop.title": "Stop",
        "home.action.stop.sub": "flow in tub",
        "home.action.drain.title": "Drain",
        "home.action.drain.sub": "the hot tub",
        "home.action.cold.title": "Cold",
        "home.action.cold.sub": "injection (soon)",
        "settings.temp_settings": "Temperature settings",
        "settings.threshold": "Turn-on threshold",
        "settings.extra_heat": "Extra heat",
        "settings.sensors": "Temperature sensors",
        "settings.sensor_pot": "Tub",
        "settings.sensor_control": "Controller",
        "settings.about": "About device",
        "settings.software": "Software",
        "settings.wifi": "WiFi",
        "settings.device": "Device",
        "settings.network": "Network",
        "settings.forget_wifi": "Forget WiFi",
        "settings.reset": "Reset",
        "settings.language": "Language",
        "settings.language.en": "EN",
        "settings.language.is": "IS",
    },
    "is": {
        "nav.home": "Heim",
        "nav.settings": "Stillingar",
        "status.connected": "Tengdur",
        "home.temp.title": "Hiti í potti",
        "home.temp.current": "Núverandi",
        "home.temp.target": "Stillt hitastig",
        "home.mode.steady": "Síflæði",
        "home.mode.medium": "Miðlungs",
        "home.mode.low": "Lágt flæði",
        "home.weather.title": "Veðurspá næstu daga",
        "home.weather.subtitle": "Reykjavík",
        "home.weather.mon": "Mán",
        "home.weather.tue": "Þri",
        "home.weather.wed": "Mið",
        "home.weather.thu": "Fim",
        "home.action.turn_on.title": "Kveikja",
        "home.action.turn_on.sub": "á heita pottinum",
        "home.action.stop.title": "Stoppa",
        "home.action.stop.sub": "flæði í potti",
        "home.action.drain.title": "Tæma",
        "home.action.drain.sub": "heita pottinn",
        "home.action.cold.title": "Köld",
        "home.action.cold.sub": "innspýting (kemur)",
        "settings.temp_settings": "Hitastillingar",
        "settings.threshold": "Kveikjumörk",
        "settings.extra_heat": "Aukahiti",
        "settings.sensors": "Hitaskynjarar",
        "settings.sensor_pot": "Pottinn",
        "settings.sensor_control": "Stýring",
        "settings.about": "Um tækið",
        "settings.software": "Hugbúnaður",
        "settings.wifi": "WiFi",
        "settings.device": "Tæki",
        "settings.network": "Nettenging",
        "settings.forget_wifi": "Gleyma WiFi",
        "settings.reset": "Reset",
        "settings.language": "Tungumál",
        "settings.language.en": "EN",
        "settings.language.is": "IS",
    },
}


def load_language():
    lang = read_config().get("language", DEFAULT_LANGUAGE)
    if lang in TRANSLATIONS:
        return lang
    return DEFAULT_LANGUAGE


def save_language(code):
    write_config({"language": code})


class I18n(QObject):
    language_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._lang = load_language()

    @property
    def language(self):
        return self._lang

    def tr(self, key):
        table = TRANSLATIONS.get(self._lang, TRANSLATIONS[DEFAULT_LANGUAGE])
        return table.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))

    def set_language(self, code):
        if code not in TRANSLATIONS or code == self._lang:
            return
        self._lang = code
        save_language(code)
        self.language_changed.emit(code)


i18n = I18n()


def tr(key):
    return i18n.tr(key)
