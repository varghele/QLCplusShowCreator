# tests/unit/test_effect_clipboard.py
"""Unit tests for timeline_ui/effect_clipboard.py - clipboard operations."""

import pytest
from config.models import LightBlock, DimmerBlock, ColourBlock
from timeline_ui.effect_clipboard import (
    copy_effect, paste_effect, clear_clipboard,
    has_clipboard_data, has_multi_clipboard_data,
    _adjust_times, get_multi_clipboard_count,
)


@pytest.fixture(autouse=True)
def _clear_clipboard():
    """Ensure clipboard is empty before/after each test."""
    clear_clipboard()
    yield
    clear_clipboard()


def _make_block(start=0.0, end=4.0, name="test"):
    return LightBlock(
        start_time=start, end_time=end, effect_name=name,
        dimmer_blocks=[DimmerBlock(start_time=start, end_time=end, intensity=200)],
        colour_blocks=[ColourBlock(start_time=start, end_time=end, red=255)],
    )


class TestCopyPasteSingle:

    def test_copy_sets_clipboard(self):
        block = _make_block()
        copy_effect(block)
        assert has_clipboard_data() is True

    def test_paste_creates_new_block(self):
        block = _make_block(start=2.0, end=6.0)
        copy_effect(block)
        pasted = paste_effect(10.0)
        assert pasted is not None
        assert pasted.start_time == 10.0
        assert pasted.end_time == 14.0  # 10 + (6-2)

    def test_paste_preserves_sublanes(self):
        block = _make_block(start=0, end=4)
        copy_effect(block)
        pasted = paste_effect(5.0)
        assert len(pasted.dimmer_blocks) == 1
        assert pasted.dimmer_blocks[0].start_time == 5.0
        assert pasted.dimmer_blocks[0].intensity == 200

    def test_paste_empty_clipboard_returns_none(self):
        assert paste_effect(0.0) is None

    def test_clear_clipboard(self):
        block = _make_block()
        copy_effect(block)
        assert has_clipboard_data() is True
        clear_clipboard()
        assert has_clipboard_data() is False


class TestAdjustTimes:

    def test_positive_offset(self):
        data = {
            "start_time": 2.0,
            "end_time": 6.0,
            "dimmer_blocks": [{"start_time": 2.0, "end_time": 6.0}],
            "colour_blocks": [],
            "movement_blocks": None,
            "special_blocks": None,
        }
        result = _adjust_times(data, 3.0)
        assert result["start_time"] == 5.0
        assert result["end_time"] == 9.0
        assert result["dimmer_blocks"][0]["start_time"] == 5.0

    def test_negative_offset(self):
        data = {
            "start_time": 10.0,
            "end_time": 14.0,
            "dimmer_blocks": [],
            "colour_blocks": [{"start_time": 10.0, "end_time": 14.0}],
            "movement_blocks": None,
            "special_blocks": None,
        }
        result = _adjust_times(data, -5.0)
        assert result["start_time"] == 5.0
        assert result["colour_blocks"][0]["start_time"] == 5.0


class TestMultiClipboard:

    def test_initially_empty(self):
        assert has_multi_clipboard_data() is False
        assert get_multi_clipboard_count() == 0

    def test_single_copy_clears_multi(self):
        block = _make_block()
        copy_effect(block)
        assert has_multi_clipboard_data() is False