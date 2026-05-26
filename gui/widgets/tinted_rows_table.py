"""
TintedRowsTableWidget — QTableWidget with proper per-row tinting.

The trick: every editor passed to :meth:`setCellWidget` is silently
wrapped in a thin :class:`CellWrapper` container with small layout
margins. The wrapper's background paints the row's tint; the editor
inside stays solidly theme-styled. So the visual reads as "the row is
colored with theme-styled inputs sitting on top" — which is impossible
with bare ``setCellWidget`` because Qt makes the widget *replace* the
cell display, hiding any item background underneath it.

``cellWidget(row, col)`` returns the original editor (not the wrapper)
so callers don't have to know about the wrapping. Existing code paths
in fixtures_tab that look up spinboxes / comboboxes by ``cellWidget``
keep working unchanged.

Text-only cells (no widget) are tinted via ``QTableWidgetItem.setBackground``
in the same call to :meth:`set_row_tint`, so the whole row reads as a
single colored band.
"""

from typing import Dict, Optional

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QHBoxLayout, QTableWidget, QTableWidgetItem, QWidget,
)


# Wrapper layout margins — the visible "tint frame" thickness around
# each editor. Small enough that the editor is still clearly the
# dominant element of the cell, large enough that the row tint reads
# as a colored band rather than a hairline border.
_WRAPPER_MARGIN_H = 3
_WRAPPER_MARGIN_V = 2


class CellWrapper(QWidget):
    """Internal wrapper hosting a single editor + a tint background.

    Public so the QSS selector ``CellWrapper { ... }`` matches it. The
    selector scopes the per-instance stylesheet to the wrapper itself
    so the inner editor inherits the global theme rules unmodified.
    """

    def __init__(self, inner: QWidget, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            _WRAPPER_MARGIN_H, _WRAPPER_MARGIN_V,
            _WRAPPER_MARGIN_H, _WRAPPER_MARGIN_V,
        )
        layout.addWidget(inner)
        self._inner = inner

    def inner(self) -> QWidget:
        return self._inner


class TintedRowsTableWidget(QTableWidget):
    """``QTableWidget`` whose rows can be tinted across both widget and
    text cells uniformly."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # row index → tint color (alpha respected). Re-applied to any new
        # cell widget added to a row that already carries a tint.
        self._row_tints: Dict[int, QColor] = {}

    # ── Transparent override of widget access ────────────────────────

    def setCellWidget(self, row: int, column: int, widget: QWidget) -> None:
        """Wrap ``widget`` in a :class:`CellWrapper` and put it in the cell.
        If the row is already tinted, the new wrapper picks up the same
        tint immediately."""
        wrapper = CellWrapper(widget)
        tint = self._row_tints.get(row)
        if tint is not None:
            self._apply_tint_to_wrapper(wrapper, tint)
        super().setCellWidget(row, column, wrapper)

    def cellWidget(self, row: int, column: int) -> Optional[QWidget]:
        """Return the inner editor (not the wrapper) so callers see the
        widget they originally passed to :meth:`setCellWidget`."""
        wrapper = super().cellWidget(row, column)
        if isinstance(wrapper, CellWrapper):
            return wrapper.inner()
        return wrapper

    # ── Public tinting API ───────────────────────────────────────────

    def set_row_tint(self, row: int, color: QColor) -> None:
        """Tint row ``row`` with ``color`` (alpha respected). Wraps every
        widget cell with the tint and sets matching item backgrounds on
        text cells, so the row reads as a single colored band."""
        self._row_tints[row] = QColor(color)
        for col in range(self.columnCount()):
            wrapper = super().cellWidget(row, col)
            if isinstance(wrapper, CellWrapper):
                self._apply_tint_to_wrapper(wrapper, color)
            item = self.item(row, col)
            if item is None:
                item = QTableWidgetItem("")
                self.setItem(row, col, item)
            item.setBackground(QColor(color))

    def clear_row_tint(self, row: int) -> None:
        """Remove the tint on ``row``. Wrappers and items return to
        theme defaults."""
        self._row_tints.pop(row, None)
        empty_brush = QBrush()
        for col in range(self.columnCount()):
            wrapper = super().cellWidget(row, col)
            if isinstance(wrapper, CellWrapper):
                wrapper.setStyleSheet("")
            item = self.item(row, col)
            if item is not None:
                item.setBackground(empty_brush)

    def clear_all_row_tints(self) -> None:
        """Drop every registered tint."""
        for row in list(self._row_tints.keys()):
            self.clear_row_tint(row)

    # ── Internals ────────────────────────────────────────────────────

    @staticmethod
    def _apply_tint_to_wrapper(wrapper: CellWrapper, color: QColor) -> None:
        # Class-scoped selector so the rule only paints the wrapper
        # itself — not its descendants. Without the selector,
        # setStyleSheet would cascade into the inner editor and override
        # the theme's panel background on it.
        wrapper.setStyleSheet(
            f"CellWrapper {{ background-color: rgba("
            f"{color.red()}, {color.green()}, "
            f"{color.blue()}, {color.alpha()}); }}"
        )
