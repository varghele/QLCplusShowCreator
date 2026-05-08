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
