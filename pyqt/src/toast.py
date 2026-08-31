"""Transient on-screen notifications for API operations.

The overlay is transparent to mouse and touch events, so a toast can never
swallow a tap meant for a control underneath it. The number of live toasts is
capped and each one dismisses itself on a timer, so a storm of link errors
cannot bury the UI or leak widgets.
"""

from __future__ import annotations

from PyQt5.QtCore import QEvent, QObject, Qt, QTimer
from PyQt5.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

import theme
from theme import GAP_SM, RADIUS_SM, fs, s, transparent_bg

LEVEL_INFO = "info"
LEVEL_SUCCESS = "success"
LEVEL_ERROR = "error"

MAX_VISIBLE = 3
DURATION_MS = {LEVEL_INFO: 2200, LEVEL_SUCCESS: 2200, LEVEL_ERROR: 4000}
FADE_MS = 180
DOT_SZ = 8


class Toast(QFrame):
    """A single message chip."""

    def __init__(self, text: str, level: str = LEVEL_INFO, parent=None):
        super().__init__(parent)
        self.text = text
        self.level = level
        self.setObjectName("toast")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        row = QHBoxLayout(self)
        row.setContentsMargins(s(10), s(7), s(12), s(7))
        row.setSpacing(s(8))

        self.dot = QLabel()
        self.dot.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.dot.setFixedSize(s(DOT_SZ), s(DOT_SZ))
        row.addWidget(self.dot, 0, Qt.AlignVCenter)

        self.text_lbl = QLabel(text)
        self.text_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.text_lbl.setWordWrap(False)
        row.addWidget(self.text_lbl, 1, Qt.AlignVCenter)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)

        self.restyle()

    def set_text(self, text: str):
        self.text = text
        self.text_lbl.setText(text)
        self.adjustSize()

    def _accent(self) -> str:
        if self.level == LEVEL_ERROR:
            return theme.C_DANGER
        if self.level == LEVEL_SUCCESS:
            return theme.C_SUCCESS
        return theme.C_ACCENT

    def restyle(self):
        accent = self._accent()
        self.setStyleSheet(f"""
            QFrame#toast {{
                background: {theme.C_SURFACE};
                border: 1px solid {accent};
                border-radius: {RADIUS_SM}px;
            }}
        """)
        self.text_lbl.setStyleSheet(
            f"color: {theme.C_TEXT}; {fs(12)} font-weight: 600; {transparent_bg()}"
        )
        self.dot.setStyleSheet(
            f"background: {accent}; border: none; border-radius: {s(DOT_SZ) // 2}px;"
        )
        self.adjustSize()

    def fade_out(self, on_done):
        """Dim then hand back to the overlay for removal."""
        steps = 6
        interval = max(1, FADE_MS // steps)
        state = {"i": 0}

        timer = QTimer(self)
        timer.setInterval(interval)

        def tick():
            state["i"] += 1
            self._effect.setOpacity(max(0.0, 1.0 - state["i"] / steps))
            if state["i"] >= steps:
                timer.stop()
                on_done(self)

        timer.timeout.connect(tick)
        timer.start()


class ToastOverlay(QWidget):
    """Stacks toasts in the lower-right corner of its parent."""

    def __init__(self, parent: QWidget, bottom_inset: int = 0):
        super().__init__(parent)
        self._bottom_inset = bottom_inset
        self._toasts: list[Toast] = []
        self._timers: dict[Toast, QTimer] = {}
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setStyleSheet(transparent_bg())
        parent.installEventFilter(self)
        self.setGeometry(parent.rect())
        self.raise_()

    def set_bottom_inset(self, inset: int):
        self._bottom_inset = inset
        self._relayout()

    def eventFilter(self, obj: QObject, event: QEvent):
        if obj is self.parent() and event.type() in (QEvent.Resize, QEvent.Show):
            self.setGeometry(self.parent().rect())
            self.raise_()
            self._relayout()
        return False

    def show_toast(self, text: str, level: str = LEVEL_INFO):
        if not text:
            return
        # Repeat of the newest message: restart its timer instead of stacking.
        if self._toasts:
            newest = self._toasts[-1]
            if newest.text == text and newest.level == level:
                self._arm(newest)
                return

        while len(self._toasts) >= MAX_VISIBLE:
            self._remove(self._toasts[0])

        toast = Toast(text, level, self)
        self._toasts.append(toast)
        toast.show()
        self.raise_()
        self._relayout()
        self._arm(toast)

    def clear(self):
        for toast in list(self._toasts):
            self._remove(toast)

    def restyle(self):
        for toast in self._toasts:
            toast.restyle()
        self._relayout()

    def _arm(self, toast: Toast):
        timer = self._timers.get(toast)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda t=toast: self._expire(t))
            self._timers[toast] = timer
        timer.start(DURATION_MS.get(toast.level, 2200))

    def _expire(self, toast: Toast):
        if toast not in self._toasts:
            return
        toast.fade_out(self._remove)

    def _remove(self, toast: Toast):
        timer = self._timers.pop(toast, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
        if toast in self._toasts:
            self._toasts.remove(toast)
        toast.hide()
        toast.deleteLater()
        self._relayout()

    def _relayout(self):
        margin = s(10)
        y = self.height() - self._bottom_inset - margin
        for toast in reversed(self._toasts):
            toast.adjustSize()
            width = min(toast.sizeHint().width(), max(s(120), self.width() - 2 * margin))
            height = toast.sizeHint().height()
            y -= height
            toast.setGeometry(self.width() - margin - width, y, width, height)
            y -= GAP_SM
