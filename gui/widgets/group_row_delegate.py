"""
GroupRowDelegate — keeps per-row group tints visible when a row is selected.

Qt's default QStyledItemDelegate fills selected cells with the palette's
``Highlight`` brush (whatever ``selection-background-color`` resolves to),
which fully covers any tint applied via ``QTableWidgetItem.setBackground``.
Worse, Qt's QSS rendering pipeline doesn't honor ``rgba(...)`` alpha on
``selection-background-color`` — it paints the selection opaque against
the table base, not blended against the cell background.

This delegate paints the cell as if it weren't selected (so the
``BackgroundRole`` brush survives) and then overlays a thin border to
indicate selection — same function, no obscured row tint.
"""

from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem


# Selection border style — matches the theme's accent blue at full alpha
# so the indicator reads cleanly on top of any group color.
_SELECTION_BORDER_COLOR = QColor("#2196F3")
_SELECTION_BORDER_WIDTH = 2


class GroupRowDelegate(QStyledItemDelegate):
    """Item delegate that draws selection as a thin border, leaving the
    cell's :class:`Qt.ItemDataRole.BackgroundRole` tint visible underneath."""

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        # Copy the option so we can locally modify state without affecting
        # the rest of the view's paint pipeline.
        opt = QStyleOptionViewItem(option)
        is_selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        # Strip the Selected state for the default paint so Qt doesn't draw
        # the opaque selection fill that would hide the row tint.
        if is_selected:
            opt.state &= ~QStyle.StateFlag.State_Selected

        super().paint(painter, opt, index)

        if is_selected:
            painter.save()
            pen = QPen(_SELECTION_BORDER_COLOR, _SELECTION_BORDER_WIDTH)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Inset by half the pen width so the border sits cleanly inside
            # the cell rect rather than getting clipped on the outer edge.
            inset = _SELECTION_BORDER_WIDTH // 2
            painter.drawRect(option.rect.adjusted(inset, inset, -inset - 1, -inset - 1))
            painter.restore()
