"""2D icon library for fixtures, keyed off :class:`Chassis`.

One icon per chassis value. Used by ``FixtureItem.paint`` (Stage tab) and
optionally by anywhere else that needs a tiny representative glyph
(group-color picker preview, fixture browser, etc.).

Conventions:
- Icons are drawn centered at the painter's local origin ``(0, 0)``.
- ``size`` is the nominal width of the bounding box; the BAR variants
  extend to ``2 * size`` along X to read as elongated.
- The painter's existing brush + pen drive the body fill + outline.
  Helpers that need accent colors (PIXELBAR cells, SUNSTRIP lamps,
  MOVING_YOKE direction triangle) save/restore the painter state.
- :func:`paint_fixture_icon` accepts an optional ``accent`` kwarg so a
  plain ``Chassis.BAR`` can render with the legacy "pixels" or "lamps"
  ornament when the caller knows the fixture has per-cell control.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen

from utils.fixture_capabilities import Chassis


# Accent values understood by paint_fixture_icon.
ACCENT_PIXELS = 'pixels'   # colored cells inside a BAR (PIXELBAR / pixel matrix)
ACCENT_LAMPS = 'lamps'     # white lamp circles inside a BAR (SUNSTRIP)


def paint_fixture_icon(
    painter: QPainter,
    chassis: Chassis,
    size: float,
    *,
    accent: Optional[str] = None,
) -> None:
    """Paint the chassis icon centered at the painter's origin.

    Args:
        painter: Active QPainter. Brush + pen are the body fill + outline.
        chassis: Which icon to paint.
        size: Nominal size in painter units (existing FixtureItem uses 30px).
        accent: Optional accent for BAR — ``"pixels"`` (colored cells) or
            ``"lamps"`` (white lamp circles). Other chassis ignore it.
    """
    if chassis is Chassis.PAR:
        _paint_par_icon(painter, size)
    elif chassis is Chassis.BAR:
        _paint_bar_icon(painter, size, accent=accent)
    elif chassis is Chassis.PANEL:
        _paint_panel_icon(painter, size)
    elif chassis is Chassis.MOVING_YOKE:
        _paint_moving_yoke_icon(painter, size)
    elif chassis is Chassis.SCANNER:
        _paint_scanner_icon(painter, size)
    elif chassis is Chassis.EFFECT:
        _paint_effect_icon(painter, size)
    elif chassis is Chassis.PARTICLE:
        _paint_particle_icon(painter, size)
    elif chassis is Chassis.LASER:
        _paint_laser_icon(painter, size)
    else:
        _paint_other_icon(painter, size)


# ---------------------------------------------------------------------------
# Static / non-moving fixtures
# ---------------------------------------------------------------------------


def _paint_par_icon(painter: QPainter, size: float) -> None:
    """PAR — circle. Existing FixtureItem PAR visual."""
    painter.drawEllipse(QRectF(-size / 2, -size / 2, size, size))


def _paint_bar_icon(
    painter: QPainter,
    size: float,
    *,
    accent: Optional[str] = None,
) -> None:
    """BAR — elongated rectangle (2:1 aspect by way of size×2 width).

    Optional accent draws cell squares (``"pixels"``) or lamp circles
    (``"lamps"``) inside the bar, mirroring the legacy PIXELBAR/SUNSTRIP
    visuals. The caller is expected to opt into accent only when the
    underlying fixture actually has per-cell DMX or per-cell dimmer.
    """
    bar_height = size / 3
    bar_width = size * 2
    painter.drawRect(QRectF(-size, -bar_height / 2, bar_width, bar_height))

    if accent == ACCENT_PIXELS:
        _draw_pixel_accents(painter, size, bar_width)
    elif accent == ACCENT_LAMPS:
        _draw_lamp_accents(painter, size, bar_width)


def _draw_pixel_accents(painter: QPainter, size: float, bar_width: float) -> None:
    """Six alternating-color squares inside a BAR — PIXELBAR cue."""
    painter.save()
    segment_count = 6
    spacing = (bar_width * 0.85) / segment_count
    start_x = -size * 0.85 + spacing / 2
    seg_size = spacing * 0.7
    colors = [
        QColor(255, 100, 100),
        QColor(100, 255, 100),
        QColor(100, 100, 255),
        QColor(255, 255, 100),
        QColor(255, 100, 255),
        QColor(100, 255, 255),
    ]
    for i in range(segment_count):
        x = start_x + i * spacing - seg_size / 2
        painter.setBrush(QBrush(colors[i % len(colors)]))
        painter.drawRect(QRectF(x, -seg_size / 2, seg_size, seg_size))
    painter.restore()


def _draw_lamp_accents(painter: QPainter, size: float, bar_width: float) -> None:
    """Five small circles inside a BAR — SUNSTRIP cue."""
    painter.save()
    bulb_count = 5
    spacing = (bar_width * 0.85) / bulb_count
    start_x = -size * 0.85 + spacing / 2
    bulb_radius = 3.0
    for i in range(bulb_count):
        x = start_x + i * spacing
        painter.drawEllipse(QRectF(x - bulb_radius, -bulb_radius, bulb_radius * 2, bulb_radius * 2))
    painter.restore()


def _paint_panel_icon(painter: QPainter, size: float) -> None:
    """PANEL — square (LED matrix / video panel)."""
    painter.drawRect(QRectF(-size / 2, -size / 2, size, size))


# ---------------------------------------------------------------------------
# Moving fixtures
# ---------------------------------------------------------------------------


def _paint_moving_yoke_icon(painter: QPainter, size: float) -> None:
    """Moving head — circle + direction triangle. Mirrors legacy MH visual."""
    painter.drawEllipse(QRectF(-size / 2, -size / 2, size, size))
    triangle = [
        QPointF(size / 2, 0),
        QPointF(0, -size / 4),
        QPointF(0, size / 4),
    ]
    painter.drawPolygon(triangle)


def _paint_scanner_icon(painter: QPainter, size: float) -> None:
    """Scanner — square with a small protruding mirror cue on +X."""
    half = size / 2
    painter.drawRect(QRectF(-half, -half, size, size))
    # Mirror cue: small triangle on the +X edge
    painter.save()
    mirror_w = size * 0.18
    triangle = [
        QPointF(half, -mirror_w / 2),
        QPointF(half + mirror_w, 0),
        QPointF(half, mirror_w / 2),
    ]
    painter.drawPolygon(triangle)
    painter.restore()


# ---------------------------------------------------------------------------
# Effect / particle / laser / other
# ---------------------------------------------------------------------------


def _paint_effect_icon(painter: QPainter, size: float) -> None:
    """Effect — hexagon (centipede / derby / sweeper variants)."""
    half = size / 2
    h = half * 0.866  # cos(30°) ≈ 0.866
    hexagon = [
        QPointF(half, 0),
        QPointF(half / 2, -h),
        QPointF(-half / 2, -h),
        QPointF(-half, 0),
        QPointF(-half / 2, h),
        QPointF(half / 2, h),
    ]
    painter.drawPolygon(hexagon)


def _paint_particle_icon(painter: QPainter, size: float) -> None:
    """Particle — three overlapping circles forming a cloud silhouette."""
    r = size * 0.32
    centers = [
        QPointF(-size * 0.22, size * 0.05),
        QPointF(0.0, -size * 0.10),
        QPointF(size * 0.22, size * 0.05),
    ]
    for c in centers:
        painter.drawEllipse(QRectF(c.x() - r, c.y() - r, r * 2, r * 2))


def _paint_laser_icon(painter: QPainter, size: float) -> None:
    """Laser — triangle pointing +X."""
    half = size / 2
    triangle = [
        QPointF(half, 0),
        QPointF(-half * 0.6, -half),
        QPointF(-half * 0.6, half),
    ]
    painter.drawPolygon(triangle)


def _paint_other_icon(painter: QPainter, size: float) -> None:
    """Unknown / dimmer pack / fan — square with a "?" glyph."""
    half = size / 2
    painter.drawRect(QRectF(-half, -half, size, size))
    painter.save()
    pen = painter.pen()
    text_pen = QPen(QColor(220, 220, 220))
    text_pen.setWidthF(max(1.0, pen.widthF()))
    painter.setPen(text_pen)
    font = painter.font()
    font.setPointSizeF(max(8.0, size * 0.5))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(
        QRectF(-half, -half, size, size),
        int(Qt.AlignmentFlag.AlignCenter),
        '?',
    )
    painter.restore()
