# tests/unit/test_light_block_widget.py
"""Unit tests for the slip-rejection, hit-test buffer, and right-click marquee
helpers added to LightBlockWidget."""

import pytest
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtWidgets import QWidget

from config.models import (
    LightBlock, DimmerBlock, ColourBlock, MovementBlock, SpecialBlock,
    FixtureGroupCapabilities,
)
from timeline_ui.light_block_widget import LightBlockWidget


# Real Qt widgets need a real Qt parent and a real QApplication (the qapp
# fixture in conftest.py covers the latter). The timeline / lane interfaces
# the widget reads from are simple enough to stub out — we don't need to
# spin up TimelineWidget or LightLaneWidget for these unit tests.

_PIXELS_PER_SECOND = 100.0


class _StubTimeline:
    """Minimal subset of TimelineWidget that LightBlockWidget needs."""
    pixels_per_second = _PIXELS_PER_SECOND

    def time_to_pixel(self, t: float) -> float:
        return t * self.pixels_per_second

    def pixel_to_time(self, px: float) -> float:
        return px / self.pixels_per_second

    def height(self) -> int:
        return 200

    def find_nearest_beat_time(self, t: float) -> float:
        return t


class _StubLane:
    """Minimal subset of LightLaneWidget. All four sublanes enabled so the
    hit/marquee logic can be exercised across every block type."""
    sublane_height = 50
    capabilities = FixtureGroupCapabilities(
        has_dimmer=True, has_colour=True, has_movement=True, has_special=True,
    )

    _ROWS = {"dimmer": 0, "colour": 1, "movement": 2, "special": 3}

    def get_sublane_index(self, sublane_type: str) -> int:
        return self._ROWS[sublane_type]


@pytest.fixture
def stub_block():
    """A LightBlock at 0–10 s with no sublane content."""
    return LightBlock(start_time=0.0, end_time=10.0, effect_name="test.effect")


@pytest.fixture
def widget(qapp, stub_block):
    """A LightBlockWidget hooked up to stubs and a real QWidget parent.

    Yield (rather than return) so the local `parent` reference stays alive
    for the duration of the test — otherwise Python GC takes the parent and
    the C++ child gets destroyed mid-test.
    """
    parent = QWidget()
    timeline = _StubTimeline()
    lane = _StubLane()
    w = LightBlockWidget(stub_block, timeline, lane, parent=parent)
    yield w
    parent.deleteLater()


# ── Part A: tiny-block rejection on creation ──────────────────────────────

class TestSublaneCreationMinDuration:

    def test_rejects_below_threshold(self, widget, stub_block):
        widget._create_sublane_block("dimmer", 1.0, 1.0 + 0.01)  # 10 ms
        assert stub_block.dimmer_blocks == []

    def test_rejects_zero_duration(self, widget, stub_block):
        widget._create_sublane_block("dimmer", 1.0, 1.0)
        assert stub_block.dimmer_blocks == []

    def test_accepts_at_threshold(self, widget, stub_block):
        widget._create_sublane_block("dimmer", 1.0, 1.0 + LightBlockWidget.MIN_SUBLANE_BLOCK_DURATION)
        assert len(stub_block.dimmer_blocks) == 1

    def test_accepts_normal_duration(self, widget, stub_block):
        widget._create_sublane_block("colour", 2.0, 4.0)
        assert len(stub_block.colour_blocks) == 1
        assert stub_block.colour_blocks[0].start_time == 2.0
        assert stub_block.colour_blocks[0].end_time == 4.0

    def test_threshold_applies_to_all_sublane_types(self, widget, stub_block):
        for sublane_type in ("dimmer", "colour", "movement", "special"):
            widget._create_sublane_block(sublane_type, 0.0, 0.01)
        assert stub_block.dimmer_blocks == []
        assert stub_block.colour_blocks == []
        assert stub_block.movement_blocks == []
        assert stub_block.special_blocks == []


# ── Part B: hit-test buffer for already-existing tiny blocks ─────────────

class TestSublaneHitTestBuffer:

    def test_strict_hit_inside_block(self, widget, stub_block):
        # A 1-second dimmer block starting at the envelope start.
        # In widget-local x: 0..100 px (start=0, end=1s, ppx=100).
        stub_block.dimmer_blocks.append(DimmerBlock(start_time=0.0, end_time=1.0, intensity=200.0))
        sublane_y = _StubLane.sublane_height // 2  # row 0 mid-height
        sublane_type, hit = widget._get_sublane_block_at_pos(QPoint(50, sublane_y))
        assert sublane_type == "dimmer"
        assert hit is stub_block.dimmer_blocks[0]

    def test_hit_inside_buffer_zone(self, widget, stub_block):
        # Tiny 1px-wide block at 1.0 s. The hit-test buffer (3 px) should
        # let a click 2 px to the right of the block still register.
        stub_block.dimmer_blocks.append(
            DimmerBlock(start_time=1.0, end_time=1.0 + 0.01, intensity=200.0)
        )
        # Block occupies x ≈ [100, 101]. Click at x=103 → within +3 px buffer.
        sublane_y = _StubLane.sublane_height // 2
        sublane_type, hit = widget._get_sublane_block_at_pos(QPoint(103, sublane_y))
        assert sublane_type == "dimmer"
        assert hit is stub_block.dimmer_blocks[0]

    def test_miss_outside_buffer(self, widget, stub_block):
        # Same tiny block, click 10 px to the right → outside the 3 px buffer.
        stub_block.dimmer_blocks.append(
            DimmerBlock(start_time=1.0, end_time=1.0 + 0.01, intensity=200.0)
        )
        sublane_y = _StubLane.sublane_height // 2
        sublane_type, hit = widget._get_sublane_block_at_pos(QPoint(115, sublane_y))
        assert sublane_type is None
        assert hit is None

    def test_strict_match_preferred_over_buffer(self, widget, stub_block):
        # Two blocks close together: clicking strictly inside one shouldn't
        # be drawn into the buffered zone of the other.
        stub_block.dimmer_blocks.append(DimmerBlock(start_time=0.0, end_time=1.0, intensity=255.0))
        stub_block.dimmer_blocks.append(DimmerBlock(start_time=1.05, end_time=2.0, intensity=128.0))
        sublane_y = _StubLane.sublane_height // 2
        # x=50 is strictly inside the first block (0..100 px).
        sublane_type, hit = widget._get_sublane_block_at_pos(QPoint(50, sublane_y))
        assert hit is stub_block.dimmer_blocks[0]


# ── Part D: marquee geometry helpers ──────────────────────────────────────

class TestSublaneMarqueeRect:

    def test_normalises_top_left_to_bottom_right(self, widget):
        widget._sublane_marquee_start = QPoint(10, 10)
        widget._sublane_marquee_current = QPoint(60, 80)
        rect = widget._compute_sublane_marquee_rect()
        assert rect == QRect(10, 10, 50, 70)

    def test_normalises_bottom_right_to_top_left(self, widget):
        # Reversed-direction drag — rect should still be normalised positive.
        widget._sublane_marquee_start = QPoint(60, 80)
        widget._sublane_marquee_current = QPoint(10, 10)
        rect = widget._compute_sublane_marquee_rect()
        assert rect == QRect(10, 10, 50, 70)


class TestSublaneBlocksInRect:

    def test_finds_block_inside_rect(self, widget, stub_block):
        # Dimmer block 0..2s at row 0, y in [0..50]. Rect 50..150 px x 0..50 y.
        stub_block.dimmer_blocks.append(DimmerBlock(start_time=0.0, end_time=2.0, intensity=255.0))
        rect = QRect(50, 0, 100, 50)
        hits = widget._sublane_blocks_in_rect(rect)
        assert len(hits) == 1
        assert hits[0] == ("dimmer", stub_block.dimmer_blocks[0])

    def test_excludes_block_outside_rect_horizontally(self, widget, stub_block):
        stub_block.dimmer_blocks.append(DimmerBlock(start_time=0.0, end_time=1.0, intensity=255.0))
        # Block ends at x=100; rect starts at x=200 → no horizontal overlap.
        rect = QRect(200, 0, 100, 50)
        assert widget._sublane_blocks_in_rect(rect) == []

    def test_excludes_block_outside_rect_vertically(self, widget, stub_block):
        # Dimmer is row 0 (y in [0..50]). Rect at y in [100..150] → row 2.
        stub_block.dimmer_blocks.append(DimmerBlock(start_time=0.0, end_time=2.0, intensity=255.0))
        rect = QRect(0, 100, 200, 50)
        hits = widget._sublane_blocks_in_rect(rect)
        # No movement blocks added, so no hits.
        assert hits == []

    def test_finds_blocks_across_multiple_sublane_types(self, widget, stub_block):
        # One block per sublane type, all 0..2s.
        stub_block.dimmer_blocks.append(DimmerBlock(start_time=0.0, end_time=2.0, intensity=255.0))
        stub_block.colour_blocks.append(ColourBlock(start_time=0.0, end_time=2.0, red=255.0))
        stub_block.movement_blocks.append(MovementBlock(start_time=0.0, end_time=2.0, pan=0.0, tilt=0.0))
        stub_block.special_blocks.append(SpecialBlock(start_time=0.0, end_time=2.0))
        # Marquee covers all four rows (y 0..200) and the time range.
        rect = QRect(0, 0, 300, 200)
        hits = widget._sublane_blocks_in_rect(rect)
        types = sorted(t for t, _ in hits)
        assert types == ["colour", "dimmer", "movement", "special"]

    def test_partial_horizontal_overlap_counts(self, widget, stub_block):
        # Block 1..2s = x in [100..200]. Rect 150..400 → partial overlap, hit.
        stub_block.dimmer_blocks.append(DimmerBlock(start_time=1.0, end_time=2.0, intensity=255.0))
        rect = QRect(150, 0, 250, 50)
        assert len(widget._sublane_blocks_in_rect(rect)) == 1


class TestBulkDeleteSublaneBlocks:

    def test_deletes_each_block(self, widget, stub_block):
        b1 = DimmerBlock(start_time=0.0, end_time=1.0, intensity=255.0)
        b2 = DimmerBlock(start_time=2.0, end_time=3.0, intensity=128.0)
        c1 = ColourBlock(start_time=0.5, end_time=1.5, red=255.0)
        stub_block.dimmer_blocks.extend([b1, b2])
        stub_block.colour_blocks.append(c1)

        widget._bulk_delete_sublane_blocks([
            ("dimmer", b1), ("dimmer", b2), ("colour", c1)
        ])

        assert stub_block.dimmer_blocks == []
        assert stub_block.colour_blocks == []
