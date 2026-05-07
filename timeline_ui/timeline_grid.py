"""
TimelineGrid — unified timeline layout for the Shows and Structure tabs.

Replaces the legacy trio of ``MasterTimelineContainer`` + ``AudioLaneWidget`` +
a separate scrollable lanes container, each with its own horizontal scrollbar
that had to be cross-wired to stay in sync.

Layout::

    ┌──────────────────── TimelineGrid ────────────────────┐
    │ ┌── headers ──┐ │ ┌──── shared horizontal scroll ──┐ │
    │ │ master hdr  │ │ │ master ruler                   │ │
    │ │ audio hdr   │ │ │ audio waveform timeline        │ │
    │ │ lane 1 hdr  │ │ │ lane 1 stripe                  │ │
    │ │ lane 2 hdr  │ │ │ lane 2 stripe                  │ │
    │ └─────────────┘ │ └────────────────────────────────┘ │
    │                 │ shared horizontal scrollbar        │
    └──────────────────────────────────────────────────────┘

Headers and stripes share one outer vertical scrollarea, so they always scroll
together. Stripes are wrapped in their own horizontal scrollarea so all rows
share a single horizontal scrollbar.

The grid does NOT own the lane widgets — it just hosts the (header, stripe)
pieces each lane hands over via ``detach_pieces()``. Callers keep references
to the lane widgets so signals and methods on them keep working.
"""

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QScrollArea, QFrame,
)


_HEADER_COLUMN_WIDTH = 320  # Must match LightLaneWidget / AudioLaneWidget header widths.


class TimelineGrid(QWidget):
    """Unified scrollable grid for master + audio + light-lane timelines.

    The grid keeps headers (left) and stripes (right) row-aligned by stacking
    them in parallel ``QVBoxLayout``s with matching row heights, and shares a
    single horizontal scrollbar across every stripe. The outer container
    scrolls vertically as a unit when there are too many lanes to fit.
    """

    # Re-emitted from whichever stripe drives them. Match the legacy signals
    # so the surrounding tab code doesn't need to change shape.
    playhead_moved = pyqtSignal(float)
    zoom_changed = pyqtSignal(float)
    audio_file_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # The wrapper widgets we hand a row's pieces to. We hold references so
        # remove_light_lane can find and tear them down.
        self._lane_rows: List[dict] = []  # entries: {"lane", "header", "stripe"}
        self._master_container = None
        self._audio_lane = None
        self._setup_ui()

    # ── UI scaffolding ────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Left header column — fixed width, vertically scrolled in lockstep
        # with the right column via the synced vertical scrollbars below.
        self.headers_scroll = QScrollArea()
        self.headers_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.headers_scroll.setWidgetResizable(True)
        self.headers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.headers_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.headers_scroll.setFixedWidth(_HEADER_COLUMN_WIDTH)

        self._headers_inner = QWidget()
        self._headers_layout = QVBoxLayout(self._headers_inner)
        self._headers_layout.setContentsMargins(0, 0, 0, 0)
        self._headers_layout.setSpacing(2)
        self._headers_layout.addStretch()
        self.headers_scroll.setWidget(self._headers_inner)

        # Right stripe column — horizontally scrolled (shared by every row)
        # and vertically scrolled by the outer container.
        self.stripes_scroll = QScrollArea()
        self.stripes_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.stripes_scroll.setWidgetResizable(False)
        self.stripes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.stripes_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._stripes_inner = QWidget()
        self._stripes_layout = QVBoxLayout(self._stripes_inner)
        self._stripes_layout.setContentsMargins(0, 0, 0, 0)
        self._stripes_layout.setSpacing(2)
        self._stripes_layout.addStretch()
        self.stripes_scroll.setWidget(self._stripes_inner)

        # Sync the headers' vertical scroll to the stripes' vertical scroll so
        # the columns scroll together. The headers scroll's own scrollbar is
        # hidden — it's a passive follower.
        self.stripes_scroll.verticalScrollBar().valueChanged.connect(
            self.headers_scroll.verticalScrollBar().setValue
        )

        outer.addWidget(self.headers_scroll)
        outer.addWidget(self.stripes_scroll, 1)

    def _insert_row(self, header: QWidget, stripe: QWidget) -> None:
        """Insert a (header, stripe) pair just before the trailing stretch."""
        # Both layouts have a trailing stretch; insert before it.
        self._headers_layout.insertWidget(self._headers_layout.count() - 1, header)
        self._stripes_layout.insertWidget(self._stripes_layout.count() - 1, stripe)

    def _remove_row(self, header: QWidget, stripe: QWidget) -> None:
        for layout, widget in ((self._headers_layout, header),
                               (self._stripes_layout, stripe)):
            layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()

    # ── Public API ────────────────────────────────────────────────────

    def set_master(self, master_container) -> None:
        """Embed the master timeline as the first row.

        Args:
            master_container: A ``MasterTimelineContainer`` instance whose
                ``detach_pieces()`` will be called.
        """
        if self._master_container is not None:
            return  # Already set; ignore.
        self._master_container = master_container
        header, stripe = master_container.detach_pieces()
        # Master ruler likes to be a bit shorter than light lanes.
        master_row_height = max(stripe.minimumHeight(), 60)
        header.setMinimumHeight(master_row_height)
        header.setMaximumHeight(master_row_height)
        stripe.setMinimumHeight(master_row_height)
        stripe.setMaximumHeight(master_row_height)
        self._insert_row(header, stripe)

        master_container.timeline_widget.playhead_moved.connect(self.playhead_moved.emit)
        master_container.timeline_widget.zoom_changed.connect(self.zoom_changed.emit)

    def set_audio_lane(self, audio_lane) -> None:
        """Embed the audio lane as the second row."""
        if self._audio_lane is not None:
            return
        self._audio_lane = audio_lane
        header, stripe = audio_lane.detach_pieces()
        # Reuse the audio lane's minimum height; clamp matching height across.
        row_height = stripe.minimumHeight() or 100
        header.setMinimumHeight(row_height)
        header.setMaximumHeight(row_height)
        stripe.setMinimumHeight(row_height)
        stripe.setMaximumHeight(row_height)
        self._insert_row(header, stripe)

        audio_lane.audio_file_changed.connect(self.audio_file_changed.emit)
        # Note: playhead_moved and zoom_changed on AudioLaneWidget are already
        # routed via its internal signal forwarding in setup_ui — we re-emit
        # them at the grid level so callers only have one source of truth.
        audio_lane.playhead_moved.connect(self.playhead_moved.emit)
        audio_lane.zoom_changed.connect(self.zoom_changed.emit)

    def add_light_lane(self, lane_widget) -> None:
        """Embed a light lane as a new row below the existing ones."""
        header, stripe = lane_widget.detach_pieces()
        row_height = stripe.minimumHeight() or 80
        header.setMinimumHeight(row_height)
        header.setMaximumHeight(row_height)
        # Stripes already self-size from LightLaneWidget's setMinimum/Maximum
        # height pair; mirror it so headers stay aligned.
        self._insert_row(header, stripe)
        self._lane_rows.append({"lane": lane_widget, "header": header, "stripe": stripe})

        lane_widget.playhead_moved.connect(self.playhead_moved.emit)
        lane_widget.zoom_changed.connect(self.zoom_changed.emit)

    def remove_light_lane(self, lane_widget) -> None:
        """Find the row owned by ``lane_widget`` and tear it down."""
        for entry in list(self._lane_rows):
            if entry["lane"] is lane_widget:
                self._remove_row(entry["header"], entry["stripe"])
                self._lane_rows.remove(entry)
                return

    def light_lanes(self) -> list:
        """Return the lane-widget references in row order."""
        return [entry["lane"] for entry in self._lane_rows]

    # ── Pass-through helpers used by the surrounding tab code ─────────

    def set_song_structure(self, song_structure) -> None:
        if self._master_container is not None:
            self._master_container.timeline_widget.set_song_structure(song_structure)
        if self._audio_lane is not None:
            self._audio_lane.set_song_structure(song_structure)
        for entry in self._lane_rows:
            tw = entry["lane"].timeline_widget
            if hasattr(tw, "set_song_structure"):
                tw.set_song_structure(song_structure)

    def set_playhead_position(self, position: float) -> None:
        if self._master_container is not None:
            self._master_container.set_playhead_position(position)
        if self._audio_lane is not None and hasattr(self._audio_lane, "set_playhead_position"):
            self._audio_lane.set_playhead_position(position)
        for entry in self._lane_rows:
            tw = entry["lane"].timeline_widget
            if hasattr(tw, "set_playhead_position"):
                tw.set_playhead_position(position)

    def set_zoom_factor(self, zoom_factor: float) -> None:
        if self._master_container is not None:
            self._master_container.set_zoom_factor(zoom_factor)
        if self._audio_lane is not None and hasattr(self._audio_lane, "set_zoom_factor"):
            self._audio_lane.set_zoom_factor(zoom_factor)
        for entry in self._lane_rows:
            tw = entry["lane"].timeline_widget
            tw.zoom_factor = zoom_factor
            if hasattr(tw, "update_timeline_width"):
                tw.update_timeline_width()
            tw.update()

    def horizontal_scroll_value(self) -> int:
        return self.stripes_scroll.horizontalScrollBar().value()

    def set_horizontal_scroll_value(self, value: int) -> None:
        self.stripes_scroll.horizontalScrollBar().setValue(value)
