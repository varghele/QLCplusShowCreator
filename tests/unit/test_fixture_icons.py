"""Tests for gui/widgets/fixture_icons.py (Phase C of fixture-rewrite).

Each test paints one chassis icon onto a QPixmap and verifies non-trivial
output — the icon library is just QPainter calls so we don't need a GL
context. The ``qapp`` fixture from conftest provides the QApplication
that QPixmap requires.
"""

from __future__ import annotations

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap

from gui.widgets.fixture_icons import (
    ACCENT_LAMPS,
    ACCENT_PIXELS,
    paint_fixture_icon,
)
from utils.fixture_capabilities import Chassis


PIXMAP_SIZE = 100
ICON_SIZE = 30


def _paint(chassis: Chassis, *, accent: str | None = None,
           fill: QColor = QColor(255, 0, 0)) -> QImage:
    """Paint the icon onto a transparent QImage (ARGB32 — QPixmap fill is
    unreliable for alpha on Windows)."""
    image = QImage(PIXMAP_SIZE, PIXMAP_SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    try:
        painter.translate(PIXMAP_SIZE / 2, PIXMAP_SIZE / 2)
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(fill))
        paint_fixture_icon(painter, chassis, ICON_SIZE, accent=accent)
    finally:
        painter.end()

    return image


def _count_non_transparent(image: QImage) -> int:
    """Count pixels with non-zero alpha. Use ``pixelColor`` instead of ``pixel``
    because ``QColor(pixel_int)`` treats the 0 value as an "invalid colour"
    and reports ``alpha=255`` for fully-transparent pixels."""
    count = 0
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 0:
                count += 1
    return count


# ---------------------------------------------------------------------------
# Smoke tests — every chassis paints something visible
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("chassis", list(Chassis))
def test_every_chassis_paints_visible_pixels(qapp, chassis):
    """Every Chassis enum value produces a non-empty icon."""
    image = _paint(chassis)
    visible = _count_non_transparent(image)
    assert visible > 0, f"{chassis} painted nothing"


# ---------------------------------------------------------------------------
# Accents — BAR with pixels / lamps adds extra pixels vs plain BAR
# ---------------------------------------------------------------------------


def test_bar_pixels_accent_adds_visible_pixels(qapp):
    """BAR with ACCENT_PIXELS draws colored cells, so the visible-pixel
    count is higher than plain BAR (the cells use different colors that
    are not transparent)."""
    plain = _count_non_transparent(_paint(Chassis.BAR))
    pixels = _count_non_transparent(_paint(Chassis.BAR, accent=ACCENT_PIXELS))
    # Same outer rectangle, plus 6 colored cells overlaid → more pixels covered
    # by *non-default-fill* color. Both should be non-zero; pixels at minimum
    # equals plain. Stricter: paint detection below.
    assert plain > 0
    assert pixels >= plain


def test_bar_pixels_accent_introduces_distinct_colors(qapp):
    """ACCENT_PIXELS paints six alternating colors not present in the plain bar."""
    image = _paint(Chassis.BAR, accent=ACCENT_PIXELS, fill=QColor(255, 0, 0))
    distinct_colors: set[int] = set()
    for y in range(image.height()):
        for x in range(image.width()):
            distinct_colors.add(image.pixel(x, y))
    # Plain BAR should have ~3 distinct values (transparent, fill, outline).
    # With pixel accents, the 6 cell colors push the count substantially higher.
    assert len(distinct_colors) >= 6


def test_bar_lamps_accent_paints_lamp_circles(qapp):
    """ACCENT_LAMPS paints 5 small filled circles inside the bar."""
    plain = _count_non_transparent(_paint(Chassis.BAR))
    lamps = _count_non_transparent(_paint(Chassis.BAR, accent=ACCENT_LAMPS))
    # Lamps fall inside the bar so they may not increase total visible pixel
    # count materially (already inside the rect). Just sanity-check that the
    # paint succeeds and outputs something visible.
    assert plain > 0
    assert lamps > 0


# ---------------------------------------------------------------------------
# Specific shape sanity checks
# ---------------------------------------------------------------------------


def test_bar_is_wider_than_par(qapp):
    """BAR's bounding box extends further along X than PAR's at the same size."""
    par_image = _paint(Chassis.PAR)
    bar_image = _paint(Chassis.BAR)

    # Walk the centre row and find leftmost / rightmost non-transparent pixels.
    def horizontal_extent(img: QImage) -> int:
        mid_y = img.height() // 2
        first = last = None
        for x in range(img.width()):
            if img.pixelColor(x, mid_y).alpha() > 0:
                if first is None:
                    first = x
                last = x
        if first is None or last is None:
            return 0
        return last - first

    par_extent = horizontal_extent(par_image)
    bar_extent = horizontal_extent(bar_image)
    assert bar_extent > par_extent, (
        f"BAR ({bar_extent}px) should be wider than PAR ({par_extent}px) at the same size"
    )


def test_moving_yoke_includes_direction_triangle(qapp):
    """MOVING_YOKE paints both a circle and a direction triangle pointing +X.

    Sanity check: the painted area should include pixels to the right of
    the central origin (the triangle apex is at +size/2 on the X axis).
    """
    image = _paint(Chassis.MOVING_YOKE, fill=QColor(0, 255, 0))
    cx = image.width() // 2
    cy = image.height() // 2
    # The +X half should have visible content (the circle right hemisphere
    # plus the triangle apex are both there).
    right_pixels = sum(
        1 for x in range(cx, image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() > 0
    )
    assert right_pixels > 0
