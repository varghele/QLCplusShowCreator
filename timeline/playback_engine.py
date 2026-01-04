# timeline/playback_engine.py
# Adapted from midimaker_and_show_structure/core/playback_engine.py
# Simplified for light show playback (removed MIDI/audio specific code)

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from typing import List, Optional, Set
from .song_structure import SongStructure
from .light_lane import LightLane


class PlaybackEngine(QObject):
    """Manages playback timeline for light shows.

    Handles playhead position, BPM-aware timing, and coordinates
    with UI components for synchronized display.
    """

    # Signals
    position_changed = pyqtSignal(float)  # Current playback position in seconds
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_halted = pyqtSignal()
    block_triggered = pyqtSignal(object, object)  # (lane, block) when block starts
    block_ended = pyqtSignal(object, object)  # (lane, block) when block ends

    def __init__(self):
        super().__init__()
        self.current_position = 0.0  # Current playback position in seconds
        self.is_playing = False
        self.bpm = 120.0
        self.snap_to_grid = True

        # Timer for playback updates (60 FPS for smooth playhead movement)
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_playback)
        self.playback_timer.setInterval(16)  # ~60 FPS (16ms)

        self.lanes: List[LightLane] = []
        self.song_structure: Optional[SongStructure] = None

        # Track light blocks that have been triggered
        self._triggered_blocks: Set[int] = set()  # Blocks that have started (by id)
        self._ended_blocks: Set[int] = set()  # Blocks that have ended (by id)

    def set_song_structure(self, song_structure: SongStructure):
        """Set song structure for BPM-aware playback.

        Args:
            song_structure: SongStructure instance with timing information
        """
        self.song_structure = song_structure

    def set_lanes(self, lanes: List[LightLane]):
        """Set the lanes to be controlled by this engine.

        Args:
            lanes: List of LightLane objects
        """
        self.lanes = lanes

    def set_bpm(self, bpm: float):
        """Set the default BPM for playback calculations.

        Args:
            bpm: Beats per minute
        """
        self.bpm = bpm

    def set_snap_to_grid(self, snap: bool):
        """Enable/disable snap to grid for playhead.

        Args:
            snap: Whether to snap to grid
        """
        self.snap_to_grid = snap

    def play(self):
        """Start playback from current position."""
        if not self.is_playing:
            self.is_playing = True
            self.playback_timer.start()
            self.playback_started.emit()

    def halt(self):
        """Pause playback at current position."""
        if self.is_playing:
            self.is_playing = False
            self.playback_timer.stop()
            self.playback_halted.emit()

    def stop(self):
        """Stop playback and reset to beginning."""
        self.is_playing = False
        self.playback_timer.stop()

        # Clear block tracking
        self._triggered_blocks.clear()
        self._ended_blocks.clear()

        self.set_position(0.0)
        self.playback_stopped.emit()

    def set_position(self, position: float):
        """Set playback position.

        Args:
            position: Position in seconds (will be clamped to >= 0)
        """
        self.current_position = max(0.0, position)
        self.position_changed.emit(self.current_position)

        # Clear block tracking when seeking
        self._triggered_blocks.clear()
        self._ended_blocks.clear()

    def update_playback(self):
        """Update playback position with dynamic BPM.

        Called by timer at ~60 FPS.
        """
        if self.is_playing:
            # Get current BPM from song structure
            if self.song_structure:
                current_bpm = self.song_structure.get_bpm_at_time(self.current_position)
                # Adjust advancement based on current BPM
                # Normalize to 120 BPM (standard reference)
                bpm_factor = current_bpm / 120.0
                advancement = 0.016 * bpm_factor
            else:
                advancement = 0.016

            self.current_position += advancement
            self.position_changed.emit(self.current_position)

            self.process_lane_events()

    def process_lane_events(self):
        """Process events for all lanes at current position."""
        # Check if any lanes are soloed
        any_solo = any(lane.solo for lane in self.lanes)

        for lane in self.lanes:
            # Skip muted lanes
            if lane.muted:
                continue

            # Skip lane if solo mode is active and this lane is not soloed
            if any_solo and not lane.solo:
                continue

            self.process_light_lane(lane)

    def process_light_lane(self, lane: LightLane):
        """Process light blocks for a lane at current position.

        Emits signals when blocks start or end.

        Args:
            lane: LightLane to process
        """
        for block in lane.light_blocks:
            block_id = id(block)
            block_end_time = block.start_time + block.duration

            # Check if block should start
            if block.start_time <= self.current_position < block_end_time:
                # Trigger block start if not already triggered
                if block_id not in self._triggered_blocks:
                    self.block_triggered.emit(lane, block)
                    self._triggered_blocks.add(block_id)

            # Check if block should end
            if self.current_position >= block_end_time:
                # Trigger block end if not already ended
                if block_id not in self._ended_blocks:
                    self.block_ended.emit(lane, block)
                    self._ended_blocks.add(block_id)

    def get_current_bpm(self) -> float:
        """Get the current BPM at playhead position.

        Returns:
            Current BPM (from song structure or default)
        """
        if self.song_structure:
            return self.song_structure.get_bpm_at_time(self.current_position)
        return self.bpm

    def get_total_duration(self) -> float:
        """Get the total duration of the timeline.

        Returns:
            Duration in seconds (from song structure or default)
        """
        if self.song_structure:
            return self.song_structure.get_total_duration()
        return 300.0  # Default 5 minutes if no structure
