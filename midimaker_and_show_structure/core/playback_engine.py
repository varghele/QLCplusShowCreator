from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from typing import List
from .lane import Lane, AudioLane, MidiLane


class PlaybackEngine(QObject):
    """Manages playback across all lanes with playhead synchronization"""

    position_changed = pyqtSignal(float)  # Emits current playback position in seconds
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_halted = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_position = 0.0  # Current playback position in seconds
        self.is_playing = False
        self.bpm = 120.0
        self.snap_to_grid = True
        self.pixels_per_beat = 60

        # Timer for playback updates (60 FPS for smooth playhead movement)
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_playback)
        self.playback_timer.setInterval(16)  # ~60 FPS (16ms)

        self.lanes: List[Lane] = []
        self.audio_synchronizer = None  # Set externally from main_window
        self.midi_output_engine = None  # Set externally from main_window

        # Track MIDI blocks that have been triggered
        self._triggered_midi_blocks = set()  # Blocks that have started
        self._ended_midi_blocks = set()  # Blocks that have ended

    def set_song_structure(self, song_structure):
        """Set song structure for BPM-aware playback"""
        self.song_structure = song_structure

    def set_lanes(self, lanes: List[Lane]):
        """Set the lanes to be controlled by this engine"""
        self.lanes = lanes

        # Update audio lanes in synchronizer
        if self.audio_synchronizer:
            audio_lanes = [lane for lane in lanes if isinstance(lane, AudioLane)]
            self.audio_synchronizer.update_lanes(audio_lanes)

    def set_bpm(self, bpm: float):
        """Set the BPM for playback calculations"""
        self.bpm = bpm

    def set_snap_to_grid(self, snap: bool):
        """Enable/disable snap to grid for playhead"""
        self.snap_to_grid = snap

    def play(self):
        """Start playback from current position"""
        if not self.is_playing:
            self.is_playing = True
            self.playback_timer.start()
            self.playback_started.emit()

            # Start audio playback
            if self.audio_synchronizer:
                self.audio_synchronizer.on_play_requested(self.current_position)

    def halt(self):
        """Pause playback at current position"""
        if self.is_playing:
            self.is_playing = False
            self.playback_timer.stop()
            self.playback_halted.emit()

            # Pause audio playback
            if self.audio_synchronizer:
                self.audio_synchronizer.on_pause_requested()

    def stop(self):
        """Stop playback and reset to beginning"""
        self.is_playing = False
        self.playback_timer.stop()

        # Stop audio playback first
        if self.audio_synchronizer:
            self.audio_synchronizer.on_stop_requested()

        # Reset MIDI state
        if self.midi_output_engine:
            self.midi_output_engine.reset_playback()

        # Clear MIDI tracking
        self._triggered_midi_blocks.clear()
        self._ended_midi_blocks.clear()

        self.set_position(0.0)
        self.playback_stopped.emit()

    def set_position(self, position: float):
        """Set playback position (in seconds)

        Note: Snapping to grid is handled by the master timeline widget,
        so we don't need to snap here. The position passed in is already
        snapped if snap_to_grid is enabled in the UI.
        """
        self.current_position = max(0.0, position)
        self.position_changed.emit(self.current_position)

        # Seek audio to new position
        if self.audio_synchronizer:
            self.audio_synchronizer.on_seek_requested(self.current_position)

        # Reset MIDI state when seeking
        if self.midi_output_engine:
            self.midi_output_engine.reset_playback()

        # Clear MIDI tracking when seeking
        self._triggered_midi_blocks.clear()
        self._ended_midi_blocks.clear()

    def update_playback(self):
        """Update playback position with dynamic BPM"""
        if self.is_playing:
            # Get current BPM from song structure
            if hasattr(self, 'song_structure') and self.song_structure:
                current_bpm = self.song_structure.get_bpm_at_time(self.current_position)
                # Adjust advancement based on current BPM
                bpm_factor = current_bpm / 120.0  # Normalize to 120 BPM
                advancement = 0.016 * bpm_factor
            else:
                advancement = 0.016

            self.current_position += advancement
            self.position_changed.emit(self.current_position)

            self.process_lane_events()

    def process_lane_events(self):
        """Process events for all lanes at current position"""
        # Check if any lanes are soloed
        any_solo = any(lane.solo for lane in self.lanes)

        for lane in self.lanes:
            # Skip lane if solo mode is active and this lane is not soloed
            if any_solo and not lane.solo:
                continue

            if isinstance(lane, MidiLane):
                self.process_midi_lane(lane)
            elif isinstance(lane, AudioLane):
                self.process_audio_lane(lane)

    def process_midi_lane(self, lane: MidiLane):
        """Process MIDI events for a lane at current position"""
        if lane.muted:
            return

        if not self.midi_output_engine or not self.midi_output_engine.is_initialized():
            return

        for block in lane.midi_blocks:
            block_id = id(block)
            block_end_time = block.start_time + block.duration

            # Check if block should start
            if block.start_time <= self.current_position < block_end_time:
                # Trigger block start if not already triggered
                if block_id not in self._triggered_midi_blocks:
                    self.midi_output_engine.process_block_start(block, lane.midi_channel)
                    self._triggered_midi_blocks.add(block_id)

            # Check if block should end (for NOTE_ON blocks)
            if self.current_position >= block_end_time:
                # Trigger block end if not already ended
                if block_id not in self._ended_midi_blocks:
                    self.midi_output_engine.process_block_end(block, lane.midi_channel)
                    self._ended_midi_blocks.add(block_id)

    def process_audio_lane(self, lane: AudioLane):
        """Process audio playback for a lane at current position"""
        # Audio playback is handled continuously by the audio_synchronizer
        # in a separate thread. This method is called each frame for consistency
        # but doesn't need to do anything - the audio engine handles it all.
        pass
