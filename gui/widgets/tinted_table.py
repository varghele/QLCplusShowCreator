"""
TintedTableWidget — QTableWidget that paints a translucent tint over
specific rows so categorical groupings (e.g. per-fixture-group rows in
the Fixtures tab) read at a glance without forcing widget cells to
fight the active theme.

Why a subclass instead of ``QTableWidgetItem.setBackground``:
``QAbstractItemView::setCellWidget`` makes the widget replace the cell's
display entirely — the item's painted background is skipped for cells
that host a widget. So per-cell ``setBackground`` only ever colors the
text-only cells, leaving widget cells untinted. Painting in ``drawRow``
after ``super().drawRow`` paints over both kinds of cells uniformly,
and because the tint uses alpha, theme-styled cell widgets (transparent
backgrounds via the global ``QTableView QSpinBox/QComboBox`` rule)
remain readable on top of the tinted row.
"""

from typing import Dict, Optional

from PyQt6.QtCore import QModelIndex, QRect
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QStyleOptionViewItem, QTableWidget, QWidget


class TintedTableWidget(QTableWidget):
    """QTableWidget with an opt-in per-row translucent overlay."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._row_tints: Dict[int, QColor] = {}

    def set_row_tint(self, row: int, color: QColor) -> None:
        """Tint ``row`` with ``color``. Alpha on the colour controls how
        much the underlying cells / text show through (~140 reads as a
        clear hue while keeping text legible)."""
        self._row_tints[row] = QColor(color)
        self.viewport().update()

    def clear_row_tint(self, row: int) -> None:
        if row in self._row_tints:
            del self._row_tints[row]
            self.viewport().update()

    def clear_all_row_tints(self) -> None:
        if self._row_tints:
            self._row_tints.clear()
            self.viewport().update()

    def drawRow(
        self,
        painter: QPainter,
        options: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        # Paint the cell content first…
        super().drawRow(painter, options, index)

        # …then overlay the row tint (with alpha) so the same hue covers
        # widget cells and text cells uniformly. Cell widgets paint into
        # the viewport in a separate cycle; with the global
        # ``QTableView QSpinBox/QComboBox { background-color: transparent }``
        # rule, the painted tint reads through them too.
        tint = self._row_tints.get(index.row())
        if tint is None:
            return

        # Stretch the tint to the full visible width of the viewport so
        # row coloring reads as a stripe even past the last column.
        rect = QRect(0, options.rect.y(),
                     self.viewport().width(), options.rect.height())
        painter.save()
        painter.fillRect(rect, tint)
        painter.restore()
