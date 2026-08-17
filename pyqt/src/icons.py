"""UI icons — SVG assets where available, QPainter fallback otherwise."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QPointF, Qt, QRectF
from PyQt5.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtSvg import QSvgRenderer

from theme import s

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "icons"

# Action icons shipped as SVG vector assets
SVG_ICONS = frozenset({
    "power", "pause", "stop", "cold", "down", "drop",
    "home", "settings", "refresh", "plus", "minus", "wifi",
    "sun", "cloud", "rain", "moon",
})


def _color(value: str | QColor) -> QColor:
    return value if isinstance(value, QColor) else QColor(value)


def _color_hex(value: str | QColor) -> str:
    c = _color(value)
    return c.name(QColor.HexRgb)


def _svg_renderer(name: str, fg: str | QColor) -> QSvgRenderer | None:
    svg_name = "cold" if name == "down" else name
    path = ASSETS_DIR / f"{svg_name}.svg"
    if not path.is_file():
        return None
    color = _color_hex(fg)
    data = path.read_text(encoding="utf-8")
    data = data.replace("#FFFFFF", color).replace("#ffffff", color)
    renderer = QSvgRenderer()
    if not renderer.load(data.encode("utf-8")):
        return None
    return renderer


def _svg_pixmap(
    name: str,
    px_size: int,
    fg: str | QColor,
    bg: str | QColor | None,
) -> QPixmap | None:
    renderer = _svg_renderer(name, fg)
    if renderer is None:
        return None

    px = QPixmap(px_size, px_size)
    px.fill(Qt.transparent)

    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)

    if bg is not None:
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_color(bg)))
        p.drawEllipse(0, 0, px_size, px_size)
        glyph = int(px_size * 0.46)
    else:
        glyph = int(px_size * 0.88)

    offset = (px_size - glyph) // 2
    renderer.render(p, QRectF(offset, offset, glyph, glyph))
    p.end()
    return px


def icon_pixmap(
    name: str,
    size: int | None = None,
    fg: str | QColor = "#FFFFFF",
    bg: str | QColor | None = None,
) -> QPixmap:
    """Render a named icon to a pixmap. Optional *bg* draws a filled circle behind it."""
    px_size = size if size is not None else s(52)

    if name in SVG_ICONS:
        svg_px = _svg_pixmap(name, px_size, fg, bg)
        if svg_px is not None:
            return svg_px

    return _painter_pixmap(name, px_size, fg, bg)


def _painter_pixmap(
    name: str,
    px_size: int,
    fg: str | QColor,
    bg: str | QColor | None,
) -> QPixmap:
    fg_c = _color(fg)
    bg_c = _color(bg) if bg is not None else None

    px = QPixmap(px_size, px_size)
    px.fill(Qt.transparent)

    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)

    if bg_c is not None:
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(bg_c))
        p.drawEllipse(0, 0, px_size, px_size)

    pad = px_size * 0.28
    inner = px_size - pad * 2
    cx, cy = px_size / 2, px_size / 2

    pen = QPen(fg_c)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if name == "home":
        p.setBrush(QBrush(fg_c))
        p.setPen(Qt.NoPen)
        body_w = inner * 0.52
        body_h = inner * 0.34
        body_y = cy + inner * 0.04
        p.drawRoundedRect(
            int(cx - body_w / 2), int(body_y),
            int(body_w), int(body_h), 2, 2,
        )
        roof = QPainterPath()
        roof.moveTo(cx - body_w * 0.62, body_y + 2)
        roof.lineTo(cx, cy - inner * 0.32)
        roof.lineTo(cx + body_w * 0.62, body_y + 2)
        roof.closeSubpath()
        p.drawPath(roof)

    elif name == "settings":
        pen.setWidthF(max(2.0, px_size * 0.06))
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(
            int(cx - inner * 0.16), int(cy - inner * 0.16),
            int(inner * 0.32), int(inner * 0.32),
        )
        for angle in range(0, 360, 45):
            p.save()
            p.translate(cx, cy)
            p.rotate(angle)
            p.drawLine(QPointF(inner * 0.2, 0), QPointF(inner * 0.36, 0))
            p.restore()

    elif name == "minus":
        pen.setWidthF(max(2.5, px_size * 0.1))
        p.setPen(pen)
        p.drawLine(QPointF(cx - inner * 0.22, cy), QPointF(cx + inner * 0.22, cy))

    p.end()
    return px
