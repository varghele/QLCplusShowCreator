"""
GroupRowDelegate — keeps per-row group tints visible when a row is selected.

Qt's default QStyledItemDelegate fills selected cells with the palette's
``Highlight`` brush (whatever ``selection-background-color`` resolves to),
which fully covers any tint applied via ``QTableWidgetItem.setBackground``.
Worse, Qt's QSS rendering pipeline doesn't honor ``rgba(...)`` alpha on
``selection-background-color`` — it paints the selection opaque against
the table base, not blended against the cell background.

This delegate paints the cell as if it weren't selected so the
``BackgroundRole`` tint survives. The selection indicator itself (a
continuous outline around the entire row) is drawn at the table level by
``RowOutlineTableWidget`` so it spans cells that host widgets via
``setCellWidget`` (where delegate ``paint()`` is never invoked).
"""

from PyQt6.QtCore import QModelIndex
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem


class GroupRowDelegate(QStyledItemDelegate):
    """Item delegate that suppresses Qt's default selection fill so the
    cell's :class:`Qt.ItemDataRole.BackgroundRole` tint stays visible.
    The selection outline is painted by ``RowOutlineTableWidget``."""

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        opt = QStyleOptionViewItem(option)
        if opt.state & QStyle.StateFlag.State_Selected:
            opt.state &= ~QStyle.StateFlag.State_Selected
        super().paint(painter, opt, index)
