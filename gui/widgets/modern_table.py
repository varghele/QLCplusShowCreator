"""
Helper that gives Qt tables a consistent modern look.

The visual styling (colors, padding, header font weight) lives in the active
theme stylesheet under ``QTableView`` / ``QHeaderView`` selectors. This helper
only configures behaviour — alternating rows, no grid, no vertical header,
sensible row height — so every table in the app feels the same regardless of
the calling tab.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QTableView, QTableWidget,
)


_DEFAULT_ROW_HEIGHT = 32
_DEFAULT_HEADER_HEIGHT = 36


def apply_modern_table_style(
    table,
    row_height: int = _DEFAULT_ROW_HEIGHT,
    header_height: int = _DEFAULT_HEADER_HEIGHT,
    select_rows: bool = True,
) -> None:
    """Apply consistent modern-look settings to a QTableView/QTableWidget.

    Args:
        table: The QTableView or QTableWidget to style.
        row_height: Default row height in pixels.
        header_height: Header row height in pixels.
        select_rows: If True, configure row-based selection. Set to False for
                     tables where individual cells should be selectable
                     independently (e.g. universe-mapping editors).
    """
    if not isinstance(table, (QTableView, QTableWidget)):
        return

    table.setShowGrid(False)
    table.setAlternatingRowColors(True)

    vh = table.verticalHeader()
    if vh is not None:
        vh.setVisible(False)
        vh.setDefaultSectionSize(row_height)

    hh = table.horizontalHeader()
    if hh is not None:
        hh.setFixedHeight(header_height)
        hh.setHighlightSections(False)
        # Left-align header labels so the QSS ``QHeaderView::section
        # { padding: 8px 10px; }`` rule reads identically across
        # tables. Qt's default alignment is centred, which made
        # FixturesTab's headers (which set AlignLeft explicitly) read
        # as having different padding from ConfigurationTab's
        # (centred) — same QSS, same pixels, but the text sat in a
        # different position inside the section. Centralising it
        # here means every table in the app gets the same look.
        hh.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

    if select_rows:
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
