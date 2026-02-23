# tests/unit/test_selection_manager.py
"""Unit tests for timeline_ui/selection_manager.py - multi-selection state."""

import pytest
from unittest.mock import MagicMock
from timeline_ui.selection_manager import SelectionManager


@pytest.fixture
def qapp():
    """Create a QApplication instance for the test."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def manager(qapp):
    return SelectionManager()


def _mock_block(name="block"):
    """Create a mock LightBlockWidget."""
    block = MagicMock()
    block.set_multi_selected = MagicMock()
    block.__hash__ = MagicMock(return_value=id(block))
    block.__eq__ = MagicMock(side_effect=lambda other: block is other)
    return block


class TestSelectDeselect:

    def test_select_single(self, manager):
        block = _mock_block()
        manager.select(block)
        assert manager.is_selected(block) is True
        assert manager.get_selection_count() == 1
        block.set_multi_selected.assert_called_with(True)

    def test_select_replaces_previous(self, manager):
        b1 = _mock_block()
        b2 = _mock_block()
        manager.select(b1)
        manager.select(b2)  # extend=False: replaces
        assert manager.is_selected(b1) is False
        assert manager.is_selected(b2) is True
        assert manager.get_selection_count() == 1

    def test_select_extend(self, manager):
        b1 = _mock_block()
        b2 = _mock_block()
        manager.select(b1)
        manager.select(b2, extend=True)
        assert manager.is_selected(b1) is True
        assert manager.is_selected(b2) is True
        assert manager.get_selection_count() == 2

    def test_deselect(self, manager):
        block = _mock_block()
        manager.select(block)
        manager.deselect(block)
        assert manager.is_selected(block) is False
        assert manager.get_selection_count() == 0


class TestSelectMultiple:

    def test_select_multiple(self, manager):
        blocks = [_mock_block() for _ in range(3)]
        manager.select_multiple(blocks)
        for b in blocks:
            assert manager.is_selected(b) is True
        assert manager.get_selection_count() == 3

    def test_select_multiple_extend(self, manager):
        b1 = _mock_block()
        manager.select(b1)
        new_blocks = [_mock_block() for _ in range(2)]
        manager.select_multiple(new_blocks, extend=True)
        assert manager.get_selection_count() == 3


class TestToggleClear:

    def test_toggle_selects(self, manager):
        block = _mock_block()
        manager.toggle_selection(block)
        assert manager.is_selected(block) is True

    def test_toggle_deselects(self, manager):
        block = _mock_block()
        manager.select(block)
        manager.toggle_selection(block)
        assert manager.is_selected(block) is False

    def test_clear_selection(self, manager):
        blocks = [_mock_block() for _ in range(3)]
        manager.select_multiple(blocks)
        manager.clear_selection()
        assert manager.get_selection_count() == 0
        assert manager.has_selection() is False

    def test_clear_empty_no_signal(self, manager):
        """Clearing an empty selection should not emit signal."""
        signal_spy = MagicMock()
        manager.selection_changed.connect(signal_spy)
        manager.clear_selection()
        signal_spy.assert_not_called()


class TestRemoveBlock:

    def test_remove_from_selection(self, manager):
        block = _mock_block()
        manager.select(block)
        manager.remove_block(block)
        assert manager.is_selected(block) is False

    def test_remove_not_selected(self, manager):
        block = _mock_block()
        manager.remove_block(block)  # Should not raise


class TestSignals:

    def test_selection_changed_emitted(self, manager):
        signal_spy = MagicMock()
        manager.selection_changed.connect(signal_spy)
        block = _mock_block()
        manager.select(block)
        signal_spy.assert_called_once()

    def test_get_selected_blocks(self, manager):
        b1 = _mock_block()
        b2 = _mock_block()
        manager.select_multiple([b1, b2])
        selected = manager.get_selected_blocks()
        assert len(selected) == 2
        assert b1 in selected
        assert b2 in selected


class TestHasSelection:

    def test_empty(self, manager):
        assert manager.has_selection() is False

    def test_with_selection(self, manager):
        manager.select(_mock_block())
        assert manager.has_selection() is True