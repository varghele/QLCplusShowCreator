"""
Tests for ``gui.widgets.modern_table.apply_modern_table_style`` — the
shared visual contract every data table in the app goes through.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_helper_left_aligns_header_text(qapp):
    """Headers must be left-aligned so the QSS ``QHeaderView::section
    { padding: 8px 10px; }`` rule reads identically across tables.
    Qt's default is centred, which made FixturesTab (which set
    AlignLeft explicitly) appear to have different padding from
    ConfigurationTab (which used the default). Centralising the
    alignment here means every table the helper touches gets the same
    look without each callsite having to remember to do it."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QTableWidget
    from gui.widgets.modern_table import apply_modern_table_style

    table = QTableWidget(0, 3)
    table.setHorizontalHeaderLabels(["A", "B", "C"])
    try:
        apply_modern_table_style(table)
        align = table.horizontalHeader().defaultAlignment()
        assert align & Qt.AlignmentFlag.AlignLeft, (
            "modern_table helper must left-align header text — "
            "centred headers leave callers chasing 'is the padding "
            "different?' bugs that aren't really about padding."
        )
        assert align & Qt.AlignmentFlag.AlignVCenter
    finally:
        table.deleteLater()


def test_fixtures_and_configuration_tables_share_header_alignment(
    qapp, sample_configuration
):
    """End-to-end pin: the two tables the user originally compared
    must come out with the same header alignment after construction."""
    from gui.theme_manager import ThemeManager
    from gui.tabs.fixtures_tab import FixturesTab
    from gui.tabs.configuration_tab import ConfigurationTab

    ThemeManager().apply(qapp, "dark")

    fixtures = FixturesTab(sample_configuration, parent=None)
    config = ConfigurationTab(sample_configuration, parent=None)
    try:
        f_align = fixtures.table.horizontalHeader().defaultAlignment()
        c_align = config.universe_list.horizontalHeader().defaultAlignment()
        assert f_align == c_align, (
            f"Header alignment mismatch — fixtures={int(f_align)} "
            f"vs configuration={int(c_align)}. Both should go through "
            "apply_modern_table_style and end up identical."
        )
    finally:
        fixtures.deleteLater()
        config.deleteLater()
