# timeline_ui/selection_manager.py
# Central coordinator for multi-selection state across all lanes

from typing import Set, List, TYPE_CHECKING
from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from .light_block_widget import LightBlockWidget


class SelectionManager(QObject):
    """Manages multi-selection state for LightBlockWidget instances across lanes.

    Provides a central point for tracking which blocks are selected,
    and emits signals when selection changes for UI updates.
    """

    # Emitted when selection changes (for UI updates)
    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_blocks: Set['LightBlockWidget'] = set()

    def select(self, block: 'LightBlockWidget', extend: bool = False) -> None:
        """Select a block.

        Args:
            block: LightBlockWidget to select
            extend: If True, add to existing selection (Shift+click behavior).
                   If False, replace existing selection.
        """
        if not extend:
            # Clear existing selection first
            self._clear_selection_internal()

        if block not in self._selected_blocks:
            self._selected_blocks.add(block)
            block.set_multi_selected(True)

        self.selection_changed.emit()

    def select_multiple(self, blocks: List['LightBlockWidget'], extend: bool = False) -> None:
        """Select multiple blocks at once.

        Args:
            blocks: List of LightBlockWidget instances to select
            extend: If True, add to existing selection.
                   If False, replace existing selection.
        """
        if not extend:
            self._clear_selection_internal()

        for block in blocks:
            if block not in self._selected_blocks:
                self._selected_blocks.add(block)
                block.set_multi_selected(True)

        self.selection_changed.emit()

    def deselect(self, block: 'LightBlockWidget') -> None:
        """Deselect a specific block.

        Args:
            block: LightBlockWidget to deselect
        """
        if block in self._selected_blocks:
            self._selected_blocks.discard(block)
            block.set_multi_selected(False)
            self.selection_changed.emit()

    def toggle_selection(self, block: 'LightBlockWidget') -> None:
        """Toggle selection state of a block.

        Args:
            block: LightBlockWidget to toggle
        """
        if block in self._selected_blocks:
            self.deselect(block)
        else:
            self.select(block, extend=True)

    def clear_selection(self) -> None:
        """Deselect all blocks."""
        if self._selected_blocks:
            self._clear_selection_internal()
            self.selection_changed.emit()

    def _clear_selection_internal(self) -> None:
        """Internal method to clear selection without emitting signal."""
        for block in self._selected_blocks:
            block.set_multi_selected(False)
        self._selected_blocks.clear()

    def is_selected(self, block: 'LightBlockWidget') -> bool:
        """Check if a block is selected.

        Args:
            block: LightBlockWidget to check

        Returns:
            True if block is selected
        """
        return block in self._selected_blocks

    def get_selected_blocks(self) -> List['LightBlockWidget']:
        """Get list of currently selected blocks.

        Returns:
            List of selected LightBlockWidget instances
        """
        return list(self._selected_blocks)

    def get_selection_count(self) -> int:
        """Get number of selected blocks.

        Returns:
            Number of selected blocks
        """
        return len(self._selected_blocks)

    def has_selection(self) -> bool:
        """Check if any blocks are selected.

        Returns:
            True if at least one block is selected
        """
        return len(self._selected_blocks) > 0

    def remove_block(self, block: 'LightBlockWidget') -> None:
        """Remove a block from selection tracking (called when block is deleted).

        Args:
            block: LightBlockWidget being removed
        """
        self._selected_blocks.discard(block)
