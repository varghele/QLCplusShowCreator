"""
Smoke test for ``LiveTab`` — the QMainWindow → tab refactor from
UI_MODERNIZATION_PLAN step 9.

We don't drive the audio engine here (that pulls in real audio devices
and sounddevice / portaudio threads). The test just makes sure the tab
can be constructed offscreen, exposes the expected widgets, and
implements the BaseTab lifecycle hooks the MainWindow's tab bar relies
on.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_live_tab_constructs(qapp, sample_configuration):
    from gui.theme_manager import ThemeManager
    from gui.tabs import LiveTab

    ThemeManager().apply(qapp, "dark")

    tab = LiveTab(sample_configuration, parent=None)
    try:
        # Core widgets must exist for the rest of the tab to be useful.
        assert tab._start_btn is not None
        assert tab._stop_btn is not None
        assert tab._bpm_spinbox is not None
        assert tab._status_phase is not None

        # Stop button is disabled at rest; START is enabled.
        assert tab._start_btn.isEnabled()
        assert not tab._stop_btn.isEnabled()

        # Phase label drives off the `phase` dynamic property — start
        # state must match the QSS rule for "stopped" so colour is
        # right out of the box.
        assert tab._status_phase.property("phase") == "stopped"

        # BaseTab lifecycle hooks are present and don't blow up when
        # called without an active engine.
        tab.on_tab_activated()
        tab.on_tab_deactivated()
        # Lazy fixture-defs load fired during the first activation.
        assert tab._fixtures_loaded is True

        # Cleanup is idempotent and safe to call without a started engine.
        tab.cleanup()
        tab.cleanup()
    finally:
        tab.deleteLater()


def test_live_tab_phase_property_drives_theme(qapp, sample_configuration):
    """``_set_phase`` flips the dynamic property and re-polishes so the
    QSS ``QLabel#LiveStatusPhase[phase="..."]`` rule re-evaluates."""
    from gui.theme_manager import ThemeManager
    from gui.tabs import LiveTab

    ThemeManager().apply(qapp, "dark")
    tab = LiveTab(sample_configuration, parent=None)
    try:
        tab._set_phase("running")
        assert tab._status_phase.property("phase") == "running"
        tab._set_phase("fill")
        assert tab._status_phase.property("phase") == "fill"
        tab._set_phase("stopped")
        assert tab._status_phase.property("phase") == "stopped"
    finally:
        tab.cleanup()
        tab.deleteLater()


def test_group_panels_rebuild_when_config_groups_change(qapp):
    """Submasters + riff-constraint panels must rebuild when the user
    loads a config file *after* MainWindow has constructed the tab.

    Reproduces the original bug: tab built with empty config.groups,
    then config populates → submasters stayed empty because setup_ui
    only ran once with the original (empty) group set.
    """
    from PyQt6.QtWidgets import QApplication
    from config.models import (Configuration, Fixture, FixtureGroup,
                               FixtureMode, Universe)
    from gui.theme_manager import ThemeManager
    from gui.tabs import LiveTab

    ThemeManager().apply(qapp, "dark")

    # Empty config at construction — no groups → submasters has 0 sliders.
    config = Configuration(fixtures=[], groups={}, universes={})
    tab = LiveTab(config, parent=None)
    try:
        assert list(tab._submasters._sliders.keys()) == []
        assert tab._current_groups_fingerprint == frozenset()

        # Config grows after construction.
        f = Fixture(
            universe=1, address=1, manufacturer="M", model="X",
            name="A1", group="Lights", current_mode="m",
            available_modes=[FixtureMode(name="m", channels=4)],
            type="PAR",
        )
        config.fixtures.append(f)
        config.groups["Lights"] = FixtureGroup(name="Lights", fixtures=[f])
        config.universes[1] = Universe(id=1, name="U1", output={})

        # Activating the tab should rebuild the group panels.
        tab.on_tab_activated()
        QApplication.processEvents()

        assert list(tab._submasters._sliders.keys()) == ["Lights"]
        assert tab._current_groups_fingerprint == frozenset({"Lights"})
    finally:
        tab.cleanup()
        tab.deleteLater()


def test_universe_table_layout(qapp, sample_configuration):
    """Universe-mapping table must stretch its columns and hide the
    vertical header so it fits in the 220-px right panel without
    clipping."""
    from PyQt6.QtWidgets import QHeaderView
    from gui.theme_manager import ThemeManager
    from gui.tabs import LiveTab

    ThemeManager().apply(qapp, "dark")
    tab = LiveTab(sample_configuration, parent=None)
    try:
        # Short header labels — anything longer gets clipped at 100 px.
        labels = [tab._universe_table.horizontalHeaderItem(c).text()
                  for c in range(tab._universe_table.columnCount())]
        assert labels == ["Config", "ArtNet"]

        # Stretch resize mode on every column.
        h_header = tab._universe_table.horizontalHeader()
        for c in range(tab._universe_table.columnCount()):
            assert (h_header.sectionResizeMode(c)
                    == QHeaderView.ResizeMode.Stretch)

        # Vertical header (row numbers) hidden.
        assert not tab._universe_table.verticalHeader().isVisible()

        # 120-px fixed height (≈ header + 3 rows).
        assert tab._universe_table.minimumHeight() == 120
        assert tab._universe_table.maximumHeight() == 120
    finally:
        tab.cleanup()
        tab.deleteLater()


def test_engine_does_not_auto_fill():
    """The engine grooves continuously; ``is_fill`` is only set by
    ``force_fill`` and clears on the next bar boundary. Catches a
    regression to the old groove+fill auto-cycling."""
    import time
    from config.models import Configuration
    from live.engine import LiveShowEngine

    engine = LiveShowEngine(Configuration(), fixture_definitions={})
    engine.set_bpm(240.0)  # 1 bar = 1 second
    engine.start()
    try:
        # Tick across several bar boundaries — should never auto-flip
        # is_fill on its own.
        t0 = time.monotonic()
        for elapsed in (0.2, 1.2, 2.2, 3.2, 4.2, 5.2):
            engine.tick(t0 + elapsed)
            assert engine.is_fill is False, (
                f"Engine auto-flipped is_fill at t={elapsed}s — auto-fill "
                "should be gone after the groove-only refactor."
            )

        # set_groove_bars should be gone (groove length is fixed).
        assert not hasattr(engine, "set_groove_bars")
        # cycle_bars property exists with the fixed default.
        assert engine.cycle_bars == 4
    finally:
        engine.stop()
