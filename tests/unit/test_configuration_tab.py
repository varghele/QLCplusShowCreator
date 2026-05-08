"""
ConfigurationTab — universe-mapping cell visuals.

The tab originally used ``setBackground(Qt.GlobalColor.white)`` for
enabled cells and ``setBackground(Qt.GlobalColor.lightGray)`` for
disabled cells. In dark mode that turned the table into a checker-
board of glaring white cells, and the disabled cells looked *brighter*
than the enabled ones — so when the user loaded a config with ArtNet
universes (where Multicast / Port are protocol-disabled by design),
those cells looked normal but mysteriously refused input. The user
read it as "broken".

These tests pin the theme-neutral approach: backgrounds are left to
the theme, disabled cells get a dim foreground brush, and Qt's
flag-based disabled state still blocks input.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _make_config_with_protocol(protocol: str):
    """Configuration with one universe wired for the given protocol."""
    from config.models import Configuration, Universe

    if protocol == "ArtNet":
        params = {"ip": "255.255.255.255", "subnet": "0", "universe": "1"}
    elif protocol == "E1.31":
        params = {
            "multicast": "true", "ip": "239.255.0.1",
            "port": "5568", "universe": "1",
        }
    elif protocol == "DMX USB":
        params = {"device": ""}
    else:
        params = {}

    cfg = Configuration()
    cfg.universes = {1: Universe(
        id=1, name="Universe 1",
        output={"plugin": protocol, "parameters": params, "line": "0"},
    )}
    return cfg


def _make_tab(qapp, protocol: str):
    from gui.theme_manager import ThemeManager
    from gui.tabs.configuration_tab import ConfigurationTab

    ThemeManager().apply(qapp, "dark")
    cfg = _make_config_with_protocol(protocol)
    # Patch device enumeration so the test doesn't depend on real USB.
    with patch(
        "gui.tabs.configuration_tab.get_device_display_names",
        return_value=["No Device"],
    ):
        tab = ConfigurationTab(cfg, parent=None)
    return tab


def test_artnet_row_disables_multicast_and_port_without_white_background(qapp):
    """Loading an ArtNet config (the conf_v8 case) must NOT leave any
    cell with the hardcoded white/lightGray background that the
    pre-fix code was painting. Both colours render badly against the
    dark theme — white is blinding, lightGray is brighter than the
    enabled neighbours so it reads the wrong way round.
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor
    from gui.tabs.configuration_tab import ConfigurationTab

    tab = _make_tab(qapp, "ArtNet")
    try:
        # Enabled-for-ArtNet columns: IP, Subnet, Universe.
        # Disabled-for-ArtNet columns: Multicast (cell widget), Port,
        # DMX Device (cell widget).
        white = QColor(Qt.GlobalColor.white)
        light_gray = QColor(Qt.GlobalColor.lightGray)

        for col in (
            ConfigurationTab.COL_IP_ADDRESS,
            ConfigurationTab.COL_PORT,
            ConfigurationTab.COL_SUBNET,
            ConfigurationTab.COL_ARTNET_UNIVERSE,
        ):
            item = tab.universe_list.item(0, col)
            if item is None:
                continue
            bg = item.background().color()
            assert bg != white, (
                f"col {col} kept the hardcoded white background — "
                "dark mode still broken."
            )
            assert bg != light_gray, (
                f"col {col} kept the hardcoded lightGray background — "
                "disabled cells still look brighter than enabled in dark mode."
            )

        # Port is disabled-for-ArtNet — flags must still block input
        # (this part of the contract was correct before; we just need
        # to verify the visual fix didn't accidentally re-enable it).
        port_item = tab.universe_list.item(0, ConfigurationTab.COL_PORT)
        assert port_item is not None
        assert not bool(port_item.flags() & Qt.ItemFlag.ItemIsEditable)
        assert not bool(port_item.flags() & Qt.ItemFlag.ItemIsEnabled)
    finally:
        tab.deleteLater()


def test_artnet_row_disabled_multicast_widget_is_disabled(qapp):
    """ArtNet doesn't use the multicast checkbox — the cell widget
    container must be disabled so Qt renders the child checkbox in
    its dim, unclickable state. This was always correct *behaviourally*
    but the user couldn't tell visually before the dark-mode fix
    because the surrounding cells looked equally white."""
    from PyQt6 import QtWidgets
    from gui.tabs.configuration_tab import ConfigurationTab

    tab = _make_tab(qapp, "ArtNet")
    try:
        widget = tab.universe_list.cellWidget(0, ConfigurationTab.COL_MULTICAST)
        assert widget is not None
        assert not widget.isEnabled(), (
            "Multicast cell widget must be disabled for ArtNet — "
            "the user can't click it because the protocol doesn't use it."
        )
        checkbox = widget.findChild(QtWidgets.QCheckBox)
        assert checkbox is not None
        # Disabled propagates from container to child.
        assert not checkbox.isEnabled()
    finally:
        tab.deleteLater()


def test_disabled_cell_gets_dim_foreground(qapp):
    """The fix replaces the hardcoded background with a dim
    foreground brush. The exact RGB is internal but the brush must be
    set (not the default invalid brush) so the cell visibly reads as
    'dimmed' in both themes."""
    from gui.tabs.configuration_tab import ConfigurationTab, _DISABLED_FG

    tab = _make_tab(qapp, "ArtNet")
    try:
        # Port is disabled-for-ArtNet → should have the dim brush.
        port_item = tab.universe_list.item(0, ConfigurationTab.COL_PORT)
        assert port_item is not None
        assert port_item.foreground().color() == _DISABLED_FG.color()
    finally:
        tab.deleteLater()


def test_e131_row_keeps_multicast_and_port_editable(qapp):
    """The E1.31 protocol uses both Multicast and Port. The cells must
    be enabled/clickable AND lack the hardcoded white background.
    Pins the regression-free case: the dark-mode fix shouldn't have
    accidentally disabled cells that should stay live."""
    from PyQt6.QtCore import Qt
    from PyQt6 import QtWidgets
    from PyQt6.QtGui import QColor
    from gui.tabs.configuration_tab import ConfigurationTab

    tab = _make_tab(qapp, "E1.31")
    try:
        port_item = tab.universe_list.item(0, ConfigurationTab.COL_PORT)
        assert port_item is not None
        assert bool(port_item.flags() & Qt.ItemFlag.ItemIsEnabled)
        assert bool(port_item.flags() & Qt.ItemFlag.ItemIsEditable)
        assert port_item.background().color() != QColor(Qt.GlobalColor.white)

        widget = tab.universe_list.cellWidget(0, ConfigurationTab.COL_MULTICAST)
        assert widget is not None
        assert widget.isEnabled()
        checkbox = widget.findChild(QtWidgets.QCheckBox)
        assert checkbox is not None
        assert checkbox.isEnabled()
    finally:
        tab.deleteLater()
