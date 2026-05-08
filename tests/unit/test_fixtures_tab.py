"""
FixturesTab — toolbar button visuals.

The +/-/duplicate toolbar buttons originally rendered blank (default
``QPushButton { padding: 6px 14px; }`` ate every pixel of glyph room
on a 31×31 fixed-size button). The first fix used
``density="compact"`` to tighten the padding, which made the glyphs
visible but left the icon buttons reading as a different widget
class from default text buttons in ConfigurationTab's toolbar.

Final contract: NO compact density, fixed width matching
``TOOLBAR_BTN_WIDTH`` (currently 40), height free so the theme's
natural ~36 px wins. Both tabs share the constant so future tweaks
only happen in one place.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_toolbar_buttons_match_default_button_styling(qapp, sample_configuration):
    from gui.theme_manager import ThemeManager
    from gui.tabs.configuration_tab import TOOLBAR_BTN_WIDTH
    from gui.tabs.fixtures_tab import FixturesTab

    ThemeManager().apply(qapp, "dark")
    tab = FixturesTab(sample_configuration, parent=None)
    try:
        # No compact-density: rely on the default
        # ``QPushButton { padding: 6px 14px; }`` rule so the icon
        # buttons render with the same proportions as text buttons.
        assert tab.add_btn.property("density") in (None, "")
        assert tab.remove_btn.property("density") in (None, "")
        assert tab.duplicate_btn.property("density") in (None, "")

        # Sanity: button glyphs are what we think they are.
        assert tab.add_btn.text() == "+"
        assert tab.remove_btn.text() == "-"
        assert tab.duplicate_btn.text() == "⎘"

        # All three icon buttons match the shared icon-button width.
        for btn in (tab.add_btn, tab.remove_btn, tab.duplicate_btn):
            assert btn.minimumWidth() == TOOLBAR_BTN_WIDTH
            assert btn.maximumWidth() == TOOLBAR_BTN_WIDTH
    finally:
        tab.deleteLater()
