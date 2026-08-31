"""Behaviour tests for the four home-screen action tiles.

Each tile is an independent two-state toggle: the background shows whether the
feature is on, the title says what the next tap will do, and the state is
reconciled from GET_STATUS rather than from the last tap.

Run with:  python tests/test_home_actions.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from PyQt5.QtCore import QPoint, Qt  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from theme import app_stylesheet, configure_screen  # noqa: E402

APP = QApplication.instance() or QApplication(sys.argv)
APP.setStyle("Fusion")
configure_screen(800, 480)
APP.setStyleSheet(app_stylesheet())

from device_link import DeviceLink  # noqa: E402
from home_screen import HomeScreen  # noqa: E402

PASSED = []
FAILED = []

AUTO_IDLE = {"MODE": "AUTO", "FLOW": "OFF", "DRAIN": "CLOSED"}


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(f"{name} {detail}")
        print(f"  FAIL  {name} {detail}")


def pump(seconds=0.05):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        APP.processEvents()
        time.sleep(0.005)
    APP.processEvents()


class RecordingLink:
    """Captures what the screen would send, without touching a port."""

    def __init__(self):
        self.sent = []

    def send(self, command, param=None, **kwargs):
        self.sent.append((command, param))

    def last(self):
        return self.sent[-1] if self.sent else None


def build_screen():
    link = RecordingLink()
    screen = HomeScreen(state={}, link=link)
    screen.resize(800, 480)
    screen.show()
    QTest.qWaitForWindowExposed(screen)
    pump(0.1)
    return screen, link


def tile(screen, key):
    for button in screen._action_buttons:
        if button.spec.key == key:
            return button
    raise AssertionError(f"no tile {key}")


def tap(button):
    QTest.mouseClick(
        button, Qt.LeftButton, Qt.NoModifier,
        QPoint(button.width() // 2, button.height() // 2),
    )
    pump(0.05)


def test_toggle_sends_both_directions():
    print("\neach tile sends both of its values")
    screen, link = build_screen()
    screen.apply_status(dict(AUTO_IDLE))
    pump(0.05)

    expectations = {
        "mode": (("SET_MODE", "OFF"), ("SET_MODE", "AUTO")),
        "flow": (("START_FLOW", None), ("STOP_FLOW", None)),
        "drain": (("SET_DRAIN", "OPEN"), ("SET_DRAIN", "CLOSE")),
        "cold": (("SET_MODE", "COLD"), ("SET_MODE", "AUTO")),
    }
    for key, (first, second) in expectations.items():
        button = tile(screen, key)
        tap(button)
        check(f"{key} first tap -> {first[0]} {first[1] or ''}".strip(),
              link.last() == first, f"got {link.last()}")
        tap(button)
        check(f"{key} second tap -> {second[0]} {second[1] or ''}".strip(),
              link.last() == second, f"got {link.last()}")
    screen.close()


def test_title_flips_with_state():
    print("\ntitle says what the next tap does")
    screen, _ = build_screen()

    screen.apply_status({"MODE": "OFF", "FLOW": "OFF", "DRAIN": "CLOSED"})
    pump(0.05)
    check("mode off shows 'Turn on'", tile(screen, "mode").title_lbl.text() == "Turn on",
          tile(screen, "mode").title_lbl.text())
    check("flow off shows 'Start'", tile(screen, "flow").title_lbl.text() == "Start",
          tile(screen, "flow").title_lbl.text())
    check("drain closed shows 'Drain'", tile(screen, "drain").title_lbl.text() == "Drain",
          tile(screen, "drain").title_lbl.text())

    screen.apply_status({"MODE": "COLD", "FLOW": "ON", "DRAIN": "OPEN"})
    pump(0.05)
    check("mode on shows 'Turn off'", tile(screen, "mode").title_lbl.text() == "Turn off",
          tile(screen, "mode").title_lbl.text())
    check("flow on shows 'Stop'", tile(screen, "flow").title_lbl.text() == "Stop",
          tile(screen, "flow").title_lbl.text())
    check("drain open shows 'Close drain'",
          tile(screen, "drain").title_lbl.text() == "Close drain",
          tile(screen, "drain").title_lbl.text())
    check("cold on shows 'Auto'", tile(screen, "cold").title_lbl.text() == "Auto",
          tile(screen, "cold").title_lbl.text())
    screen.close()


def test_icon_flips_with_state():
    print("\nflow icon matches the next tap")
    screen, _ = build_screen()

    screen.apply_status({"MODE": "AUTO", "FLOW": "OFF", "DRAIN": "CLOSED"})
    pump(0.05)
    flow = tile(screen, "flow")
    check("flow off uses the play icon", flow.face().icon == "play", flow.face().icon)
    play_img = flow.icon_lbl.pixmap().toImage()

    screen.apply_status({"MODE": "AUTO", "FLOW": "ON", "DRAIN": "CLOSED"})
    pump(0.05)
    check("flow on uses the stop icon", flow.face().icon == "stop", flow.face().icon)
    stop_img = flow.icon_lbl.pixmap().toImage()
    check("the two icons render differently", play_img != stop_img)

    for key in ("mode", "drain", "cold"):
        button = tile(screen, key)
        check(f"{key} keeps one icon in both states",
              not button.spec.off.icon and not button.spec.on.icon)
    screen.close()


def test_tiles_are_independent():
    print("\ntiles no longer exclude each other")
    screen, _ = build_screen()
    screen.apply_status({"MODE": "AUTO", "FLOW": "ON", "DRAIN": "OPEN"})
    pump(0.05)
    check("mode, flow and drain all engaged",
          tile(screen, "mode").isChecked()
          and tile(screen, "flow").isChecked()
          and tile(screen, "drain").isChecked())
    check("cold stays off in AUTO", not tile(screen, "cold").isChecked())

    # Tapping one tile must not disturb the others.
    before = [b.isChecked() for b in screen._action_buttons]
    tap(tile(screen, "drain"))
    after = [b.isChecked() for b in screen._action_buttons]
    changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    check("one tap changes exactly one tile", changed == [2], f"changed={changed}")
    screen.close()


def test_status_drives_state():
    print("\ncontroller status wins over the last tap")
    screen, _ = build_screen()
    screen.apply_status(dict(AUTO_IDLE))
    pump(0.05)
    tap(tile(screen, "flow"))
    check("optimistically engaged", tile(screen, "flow").isChecked())
    # Controller says flow never started.
    screen.apply_status(dict(AUTO_IDLE))
    pump(0.05)
    check("status corrected the tile", not tile(screen, "flow").isChecked())

    check("cold reflects MODE=COLD",
          screen._engaged("cold", {"MODE": "COLD"}) is True)
    check("unknown status leaves tile alone", screen._engaged("flow", {}) is None)
    screen.close()


def test_refused_command_reverts():
    print("\na refused command puts the tile back")
    screen, _ = build_screen()
    screen.apply_status(dict(AUTO_IDLE))
    pump(0.05)

    drain = tile(screen, "drain")
    tap(drain)
    check("tile engaged on tap", drain.isChecked())

    class Refused:
        ok = False
        code = "SAFETY_LOCK"

    screen.apply_result(Refused())
    pump(0.05)
    check("reverted after refusal", not drain.isChecked())
    check("title back to 'Drain'", drain.title_lbl.text() == "Drain",
          drain.title_lbl.text())
    screen.close()


def test_language_switch_keeps_state():
    print("\nlanguage switch keeps toggle state")
    from i18n import i18n

    screen, _ = build_screen()
    screen.apply_status({"MODE": "AUTO", "FLOW": "ON", "DRAIN": "OPEN"})
    pump(0.05)
    before = [b.isChecked() for b in screen._action_buttons]

    i18n.set_language("is")
    screen.retranslate()
    pump(0.05)
    after = [b.isChecked() for b in screen._action_buttons]
    check("states survive retranslate", before == after, f"{before} -> {after}")
    check("flow title translated", tile(screen, "flow").title_lbl.text() == "Stoppa",
          tile(screen, "flow").title_lbl.text())
    i18n.set_language("en")
    screen.retranslate()
    pump(0.05)
    check("back to English", tile(screen, "flow").title_lbl.text() == "Stop",
          tile(screen, "flow").title_lbl.text())
    screen.close()


def test_no_link_does_not_crash():
    print("\ntapping with no link attached")
    screen = HomeScreen(state={}, link=None)
    screen.resize(800, 480)
    screen.show()
    QTest.qWaitForWindowExposed(screen)
    pump(0.05)
    for button in screen._action_buttons:
        tap(button)
    check("tiles still toggle without a link",
          any(b.isChecked() for b in screen._action_buttons))
    screen.close()


def main():
    print("home action tile suite")
    test_toggle_sends_both_directions()
    test_title_flips_with_state()
    test_icon_flips_with_state()
    test_tiles_are_independent()
    test_status_drives_state()
    test_refused_command_reverts()
    test_language_switch_keeps_state()
    test_no_link_does_not_crash()

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for failure in FAILED:
        print(f"  - {failure}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
