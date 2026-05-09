"""Unit tests for the master-timeline grid subdivision feature.

Covers:
- ``MasterTimelineContainer`` exposes a subdivision combobox whose entries
  match the documented choices (1 / 1/2 / 1/4) and pushes new values into
  the underlying ``MasterTimelineWidget`` + emits ``subdivision_changed``.
- ``TimelineGrid`` fans the master subdivision out to the audio lane and
  every light lane (including ones added *after* the user picked a fine
  setting).
- ``TimelineWidget.find_nearest_beat_time`` honours the lane's
  ``grid_subdivision`` so block placement / drag snap to the same grid the
  user sees.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _make_song_structure():
    from config.models import ShowPart
    from timeline.song_structure import SongStructure

    parts = [ShowPart(name="A", color="#FFF", signature="4/4",
                      bpm=120.0, num_bars=4, transition="instant")]
    ss = SongStructure()
    ss.load_from_show_parts(parts)
    return ss


def test_master_combobox_lists_documented_subdivisions(qapp):
    from timeline_ui.master_timeline_widget import (
        MasterTimelineContainer, SUBDIVISION_CHOICES,
    )

    container = MasterTimelineContainer()
    try:
        values = [container.subdivision_combo.itemData(i)
                  for i in range(container.subdivision_combo.count())]
        assert values == [v for _label, v in SUBDIVISION_CHOICES]
        assert values == [1, 2, 4]
    finally:
        container.deleteLater()


def test_master_combobox_pushes_into_timeline_and_emits_signal(qapp):
    from timeline_ui.master_timeline_widget import MasterTimelineContainer

    container = MasterTimelineContainer()
    received = []
    container.subdivision_changed.connect(received.append)
    try:
        # Default state: subdivision==1.
        assert container.timeline_widget.grid_subdivision == 1

        # User picks 1/2-beat.
        container.subdivision_combo.setCurrentIndex(1)
        assert container.timeline_widget.grid_subdivision == 2
        assert received == [2]

        # User picks 1/4-beat.
        container.subdivision_combo.setCurrentIndex(2)
        assert container.timeline_widget.grid_subdivision == 4
        assert received == [2, 4]
    finally:
        container.deleteLater()


def test_set_grid_subdivision_updates_combobox_silently(qapp):
    """Programmatic set should sync the combobox without re-emitting."""
    from timeline_ui.master_timeline_widget import MasterTimelineContainer

    container = MasterTimelineContainer()
    received = []
    container.subdivision_changed.connect(received.append)
    try:
        container.set_grid_subdivision(4)
        assert container.timeline_widget.grid_subdivision == 4
        assert container.subdivision_combo.currentData() == 4
        # No signal — programmatic sync mustn't trigger a feedback loop with
        # whoever is calling set_grid_subdivision.
        assert received == []
    finally:
        container.deleteLater()


def test_timeline_grid_fans_subdivision_to_audio_and_lanes(qapp):
    from timeline.light_lane import LightLane
    from timeline_ui import (
        AudioLaneWidget, LightLaneWidget, MasterTimelineContainer, TimelineGrid,
    )

    grid = TimelineGrid()
    master = MasterTimelineContainer()
    audio = AudioLaneWidget()
    grid.set_master(master)
    grid.set_audio_lane(audio)

    lane_model = LightLane(name="L1", fixture_targets=["TestGroup"])
    lane = LightLaneWidget(lane_model, ["TestGroup"])
    grid.add_light_lane(lane)

    try:
        grid.set_grid_subdivision(2)
        assert master.timeline_widget.grid_subdivision == 2
        assert audio.timeline_widget.grid_subdivision == 2
        assert lane.timeline_widget.grid_subdivision == 2

        # Master combobox change must fan out automatically.
        master.subdivision_combo.setCurrentIndex(2)  # 1/4-beat
        assert audio.timeline_widget.grid_subdivision == 4
        assert lane.timeline_widget.grid_subdivision == 4
    finally:
        grid.deleteLater()
        master.deleteLater()
        audio.deleteLater()
        lane.deleteLater()


def test_late_added_light_lane_inherits_current_subdivision(qapp):
    """If the user picks 1/4-beat then adds a new lane, the new lane must
    inherit the current subdivision instead of starting at 1.
    """
    from timeline.light_lane import LightLane
    from timeline_ui import (
        LightLaneWidget, MasterTimelineContainer, TimelineGrid,
    )

    grid = TimelineGrid()
    master = MasterTimelineContainer()
    grid.set_master(master)

    # Master is already at 1/4-beat when the new lane joins.
    master.set_grid_subdivision(4)

    lane_model = LightLane(name="L1", fixture_targets=["TestGroup"])
    lane = LightLaneWidget(lane_model, ["TestGroup"])
    grid.add_light_lane(lane)

    try:
        assert lane.timeline_widget.grid_subdivision == 4
    finally:
        grid.deleteLater()
        master.deleteLater()
        lane.deleteLater()


def test_find_nearest_beat_time_uses_lane_subdivision(qapp):
    """``TimelineWidget.find_nearest_beat_time`` is what every drag/drop /
    paste / playhead-set goes through. It must reflect the lane's current
    ``grid_subdivision`` so the snap matches the visible grid.
    """
    from timeline_ui.timeline_widget import TimelineWidget

    tw = TimelineWidget()
    tw.set_song_structure(_make_song_structure())
    try:
        # 120 BPM, beat=0.5s. 0.27 → on-beat 0.5 at subdivision=1.
        tw.set_grid_subdivision(1)
        assert abs(tw.find_nearest_beat_time(0.27) - 0.5) < 1e-6

        # Same target → half-beat 0.25 at subdivision=2.
        tw.set_grid_subdivision(2)
        assert abs(tw.find_nearest_beat_time(0.27) - 0.25) < 1e-6

        # And quarter-beat 0.25 at subdivision=4 (target 0.27 rounds down).
        tw.set_grid_subdivision(4)
        assert abs(tw.find_nearest_beat_time(0.27) - 0.25) < 1e-6

        # 0.13 → 0.125 at quarter-beat (the sixteenth-note grid line).
        assert abs(tw.find_nearest_beat_time(0.13) - 0.125) < 1e-6
    finally:
        tw.deleteLater()


def test_find_nearest_beat_time_fallback_path_uses_subdivision(qapp):
    """No song structure loaded → falls back to bare-BPM snap; subdivision
    must apply there too so the empty-state behaves consistently.
    """
    from timeline_ui.timeline_widget import TimelineWidget

    tw = TimelineWidget()  # No set_song_structure call.
    try:
        # 120 BPM default → 0.5s/beat. At subdivision=2, 0.27 → 0.25.
        tw.set_grid_subdivision(2)
        assert abs(tw.find_nearest_beat_time(0.27) - 0.25) < 1e-6
    finally:
        tw.deleteLater()


def test_master_snap_checkbox_fans_out_to_lanes(qapp):
    """The master Snap checkbox pairs with the Grid combobox in the header.
    Toggling it must fan out to every lane's timeline + per-lane checkbox so
    the visible state in lane controls stays consistent.
    """
    from timeline.light_lane import LightLane
    from timeline_ui import (
        LightLaneWidget, MasterTimelineContainer, TimelineGrid,
    )

    grid = TimelineGrid()
    master = MasterTimelineContainer()
    grid.set_master(master)

    lane_model = LightLane(name="L1", fixture_targets=["TestGroup"])
    lane = LightLaneWidget(lane_model, ["TestGroup"])
    grid.add_light_lane(lane)

    try:
        # Default: snap is on everywhere.
        assert master.snap_checkbox.isChecked() is True
        assert master.timeline_widget.snap_to_grid is True
        assert lane.timeline_widget.snap_to_grid is True
        assert lane.snap_checkbox.isChecked() is True

        # User unticks the master snap.
        master.snap_checkbox.setChecked(False)
        assert master.timeline_widget.snap_to_grid is False
        assert lane.timeline_widget.snap_to_grid is False
        # Per-lane checkbox should mirror the master so the visible state
        # in lane controls doesn't lie about whether snap is active.
        assert lane.snap_checkbox.isChecked() is False
    finally:
        grid.deleteLater()
        master.deleteLater()
        lane.deleteLater()


def test_master_header_uses_two_row_layout_after_detach(qapp):
    """detach_pieces must produce a header that's a 2-row stack so the
    Snap + Grid controls don't get pushed off-screen by the info widget
    inside the 320 px header column.

    Pin the QVBoxLayout shape so future refactors don't quietly revert
    to a single-row layout (which is what caused the controls to be
    invisible in the first place).
    """
    from PyQt6.QtWidgets import QVBoxLayout
    from timeline_ui.master_timeline_widget import MasterTimelineContainer

    master = MasterTimelineContainer()
    try:
        header, _stripe = master.detach_pieces()
        layout = header.layout()
        assert isinstance(layout, QVBoxLayout), \
            "Master header must be a QVBoxLayout (controls row + info row)"
        # Two children: a controls QHBoxLayout and the info_widget directly.
        assert layout.count() == 2

        # The Snap and Grid controls must live inside this header — earlier
        # bug was that detach_pieces left them orphaned in the original
        # top_row_layout that nothing rendered.
        assert master.snap_checkbox.parent() is header
        assert master.subdivision_combo.parent() is header
        assert master.subdivision_label.parent() is header
        assert master.info_widget.parent() is header
    finally:
        master.deleteLater()
