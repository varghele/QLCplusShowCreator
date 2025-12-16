# gui/tabs/shows_tab.py
# Timeline-based show management tab

import os
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QLabel, QSlider, QScrollArea, QWidget, QFrame,
                             QSplitter, QSizePolicy, QInputDialog, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from config.models import Configuration, Show, ShowPart, TimelineData, LightBlock
from timeline.song_structure import SongStructure
from timeline.light_lane import LightLane
from timeline_ui import (MasterTimelineContainer, LightLaneWidget, AudioLaneWidget)
from .base_tab import BaseTab

# Try to import audio components - may not be available
try:
    from audio.audio_file import AudioFile
    from audio.audio_engine import AudioEngine
    from audio.audio_mixer import AudioMixer
    from audio.playback_synchronizer import PlaybackSynchronizer
    from audio.device_manager import DeviceManager
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class ShowsTab(BaseTab):
    """Timeline-based show management tab.

    Provides a visual timeline interface for managing show structure,
    audio tracks, and light effect lanes with full playback support.
    """

    def __init__(self, config: Configuration, parent=None):
        """Initialize shows tab.

        Args:
            config: Shared Configuration object
            parent: Parent widget (typically MainWindow)
        """
        # Initialize state before super().__init__
        self.song_structure = None
        self.lane_widgets = []
        self.current_show_name = ""
        self.is_playing = False
        self.playhead_position = 0.0

        # Audio components (lazy init)
        self.audio_engine = None
        self.audio_mixer = None
        self.playback_sync = None
        self.device_manager = None

        # Playback timer
        self.playback_timer = QTimer()
        self.playback_timer.setInterval(16)  # ~60 FPS
        self.playback_timer.timeout.connect(self._update_playback)

        super().__init__(config, parent)

    def setup_ui(self):
        """Set up the timeline-based UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Top toolbar
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)

        # Master timeline
        self.master_timeline = MasterTimelineContainer()
        main_layout.addWidget(self.master_timeline)

        # Audio lane
        self.audio_lane = AudioLaneWidget()
        main_layout.addWidget(self.audio_lane)

        # Light lanes scroll area
        self.lanes_scroll = QScrollArea()
        self.lanes_scroll.setWidgetResizable(True)
        self.lanes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lanes_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.lanes_scroll.setMinimumHeight(200)

        # Container for light lanes
        self.lanes_container = QWidget()
        self.lanes_layout = QVBoxLayout(self.lanes_container)
        self.lanes_layout.setContentsMargins(0, 0, 0, 0)
        self.lanes_layout.setSpacing(4)
        self.lanes_layout.addStretch()  # Push lanes to top

        self.lanes_scroll.setWidget(self.lanes_container)
        main_layout.addWidget(self.lanes_scroll, 1)  # Takes remaining space

        # Bottom playback controls
        playback_bar = self._create_playback_controls()
        main_layout.addLayout(playback_bar)

    def _create_toolbar(self):
        """Create the top toolbar with show selection and lane controls."""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Show selection
        show_label = QLabel("Show:")
        show_label.setStyleSheet("font-weight: bold;")
        toolbar.addWidget(show_label)

        self.show_combo = QComboBox()
        self.show_combo.setMinimumWidth(150)
        toolbar.addWidget(self.show_combo)

        # New show button
        self.new_show_btn = QPushButton("+ New")
        self.new_show_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #AB47BC;
            }
        """)
        toolbar.addWidget(self.new_show_btn)

        toolbar.addSpacing(20)

        # Add lane button
        self.add_lane_btn = QPushButton("+ Add Light Lane")
        self.add_lane_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        toolbar.addWidget(self.add_lane_btn)

        toolbar.addSpacing(20)

        # Zoom control
        zoom_label = QLabel("Zoom:")
        toolbar.addWidget(zoom_label)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 500)  # 0.1x to 5.0x
        self.zoom_slider.setValue(100)  # 1.0x default
        self.zoom_slider.setFixedWidth(120)
        toolbar.addWidget(self.zoom_slider)

        self.zoom_label = QLabel("1.0x")
        self.zoom_label.setFixedWidth(40)
        toolbar.addWidget(self.zoom_label)

        toolbar.addStretch()

        # Save button
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #42A5F5;
            }
        """)
        toolbar.addWidget(self.save_btn)

        return toolbar

    def _create_playback_controls(self):
        """Create bottom playback control bar."""
        controls = QHBoxLayout()
        controls.setSpacing(10)

        # Playback buttons
        self.play_btn = QPushButton("Play")
        self.play_btn.setFixedWidth(70)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        controls.addWidget(self.play_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #EF5350;
            }
        """)
        controls.addWidget(self.stop_btn)

        controls.addSpacing(20)

        # Time display
        self.time_label = QLabel("00:00.00")
        self.time_label.setStyleSheet("""
            font-family: monospace;
            font-size: 16px;
            font-weight: bold;
            padding: 4px 8px;
            background-color: #333;
            color: #0f0;
            border-radius: 4px;
        """)
        self.time_label.setFixedWidth(100)
        controls.addWidget(self.time_label)

        controls.addSpacing(10)

        # Position slider
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.setValue(0)
        controls.addWidget(self.position_slider, 1)

        # Total time display
        self.total_time_label = QLabel("/ 00:00")
        self.total_time_label.setStyleSheet("font-family: monospace; color: #666;")
        controls.addWidget(self.total_time_label)

        return controls

    def connect_signals(self):
        """Connect widget signals to handlers."""
        # Toolbar
        self.show_combo.currentTextChanged.connect(self._on_show_changed)
        self.new_show_btn.clicked.connect(self._create_new_show)
        self.add_lane_btn.clicked.connect(self._add_new_lane)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        self.save_btn.clicked.connect(self.save_to_config)

        # Playback controls
        self.play_btn.clicked.connect(self._toggle_playback)
        self.stop_btn.clicked.connect(self._stop_playback)
        self.position_slider.sliderPressed.connect(self._on_position_slider_pressed)
        self.position_slider.sliderReleased.connect(self._on_position_slider_released)
        self.position_slider.valueChanged.connect(self._on_position_slider_changed)

        # Master timeline sync
        self.master_timeline.scroll_position_changed.connect(self._sync_scroll)
        self.master_timeline.playhead_moved.connect(self._on_playhead_moved)
        self.master_timeline.zoom_changed.connect(self._on_external_zoom_changed)

        # Audio lane sync
        self.audio_lane.scroll_position_changed.connect(self._sync_scroll)
        self.audio_lane.zoom_changed.connect(self._on_external_zoom_changed)
        self.audio_lane.playhead_moved.connect(self._on_playhead_moved)

    def update_from_config(self):
        """Refresh timeline from configuration."""
        # Update show combo
        current = self.show_combo.currentText()
        self.show_combo.blockSignals(True)
        self.show_combo.clear()
        self.show_combo.addItems(sorted(self.config.shows.keys()))
        if current and current in self.config.shows:
            self.show_combo.setCurrentText(current)
        elif self.config.shows:
            self.show_combo.setCurrentIndex(0)
        self.show_combo.blockSignals(False)

        # Load current show
        self._load_show(self.show_combo.currentText())

    def _on_show_changed(self, show_name: str):
        """Handle show selection change."""
        # Save current show before switching
        if self.current_show_name:
            self.save_to_config()

        self._load_show(show_name)

    def _load_show(self, show_name: str):
        """Load show into timeline."""
        # Stop playback
        self._stop_playback()

        if not show_name or show_name not in self.config.shows:
            self._clear_timeline()
            return

        self.current_show_name = show_name
        show = self.config.shows[show_name]

        # Convert old effects if no timeline data
        if show.timeline_data is None and show.effects:
            self._convert_effects_to_timeline(show)

        # Build song structure from show parts
        self.song_structure = SongStructure()
        self.song_structure.load_from_show_parts(show.parts)

        # Set song structure on all timelines
        self.master_timeline.timeline_widget.set_song_structure(self.song_structure)
        self.audio_lane.set_song_structure(self.song_structure)

        # Update total time display
        total_duration = self.song_structure.get_total_duration() if self.song_structure else 0
        self.total_time_label.setText(f"/ {self._format_time(total_duration)}")

        # Clear and rebuild light lanes
        self._clear_light_lanes()

        if show.timeline_data:
            # Load audio file
            if show.timeline_data.audio_file_path:
                self.audio_lane.load_audio_file(show.timeline_data.audio_file_path)

            # Create lane widgets
            for lane_data in show.timeline_data.lanes:
                runtime_lane = LightLane.from_data_model(lane_data)
                self._add_lane_widget(runtime_lane)

    def _clear_timeline(self):
        """Clear all timeline data."""
        self.current_show_name = ""
        self.song_structure = None
        self._clear_light_lanes()
        self.master_timeline.timeline_widget.set_song_structure(None)
        self.audio_lane.set_song_structure(None)

    def _clear_light_lanes(self):
        """Remove all light lane widgets."""
        for lane_widget in self.lane_widgets:
            lane_widget.remove_requested.disconnect()
            lane_widget.scroll_position_changed.disconnect()
            lane_widget.zoom_changed.disconnect()
            lane_widget.playhead_moved.disconnect()
            self.lanes_layout.removeWidget(lane_widget)
            lane_widget.deleteLater()
        self.lane_widgets.clear()

    def _add_lane_widget(self, lane: LightLane):
        """Add a lane widget for the given lane data."""
        # Get fixture groups from config
        fixture_groups = list(self.config.groups.keys())

        lane_widget = LightLaneWidget(lane, fixture_groups, self)
        lane_widget.set_song_structure(self.song_structure)
        lane_widget.set_zoom_factor(self.zoom_slider.value() / 100.0)

        # Connect signals
        lane_widget.remove_requested.connect(self._remove_lane_widget)
        lane_widget.scroll_position_changed.connect(self._sync_scroll)
        lane_widget.zoom_changed.connect(self._on_external_zoom_changed)
        lane_widget.playhead_moved.connect(self._on_playhead_moved)

        # Insert before the stretch
        self.lanes_layout.insertWidget(len(self.lane_widgets), lane_widget)
        self.lane_widgets.append(lane_widget)

    def _add_new_lane(self):
        """Add a new empty light lane."""
        if not self.current_show_name:
            QMessageBox.warning(
                self,
                "No Show Selected",
                "Please select or create a show first before adding lanes.",
                QMessageBox.StandardButton.Ok
            )
            return

        # Create new lane with default name
        lane_num = len(self.lane_widgets) + 1
        fixture_groups = list(self.config.groups.keys())
        default_group = fixture_groups[0] if fixture_groups else ""

        lane = LightLane(f"Lane {lane_num}", default_group)
        self._add_lane_widget(lane)

    def _create_new_show(self):
        """Create a new show with a dialog."""
        name, ok = QInputDialog.getText(
            self,
            "Create New Show",
            "Enter show name:",
            text="New Show"
        )

        if ok and name:
            # Check if name already exists
            if name in self.config.shows:
                QMessageBox.warning(
                    self,
                    "Name Exists",
                    f"A show named '{name}' already exists. Please choose a different name.",
                    QMessageBox.StandardButton.Ok
                )
                return

            # Create new show with default part
            new_show = Show(
                name=name,
                parts=[
                    ShowPart(
                        name="Intro",
                        color="#4CAF50",
                        signature="4/4",
                        bpm=120.0,
                        num_bars=8,
                        transition="instant"
                    )
                ],
                effects=[],
                timeline_data=TimelineData()
            )

            # Add to config
            self.config.shows[name] = new_show

            # Update combo and select new show
            self.show_combo.blockSignals(True)
            self.show_combo.addItem(name)
            self.show_combo.setCurrentText(name)
            self.show_combo.blockSignals(False)

            # Load the new show
            self._load_show(name)

    def _remove_lane_widget(self, lane_widget: LightLaneWidget):
        """Remove a lane widget."""
        if lane_widget in self.lane_widgets:
            lane_widget.remove_requested.disconnect()
            lane_widget.scroll_position_changed.disconnect()
            lane_widget.zoom_changed.disconnect()
            lane_widget.playhead_moved.disconnect()
            self.lanes_layout.removeWidget(lane_widget)
            self.lane_widgets.remove(lane_widget)
            lane_widget.deleteLater()

    def _convert_effects_to_timeline(self, show: Show):
        """Convert old ShowEffect data to LightBlock timeline format."""
        if show.timeline_data is None:
            show.timeline_data = TimelineData()

        # Need song structure for timing
        song_structure = SongStructure()
        song_structure.load_from_show_parts(show.parts)

        # Create lane per fixture group
        groups_with_effects = set(e.fixture_group for e in show.effects if e.effect)
        for group_name in groups_with_effects:
            from config.models import LightLane as LightLaneModel
            lane = LightLaneModel(name=group_name, fixture_group=group_name)

            for effect in show.effects:
                if effect.fixture_group != group_name or not effect.effect:
                    continue

                # Find show part to get timing
                part = next((p for p in song_structure.parts if p.name == effect.show_part), None)
                if part:
                    block = LightBlock(
                        start_time=part.start_time,
                        duration=part.duration,
                        effect_name=effect.effect,
                        parameters={
                            'speed': effect.speed,
                            'color': effect.color,
                            'intensity': effect.intensity,
                            'spot': effect.spot
                        }
                    )
                    lane.light_blocks.append(block)

            if lane.light_blocks:
                show.timeline_data.lanes.append(lane)

    def save_to_config(self):
        """Save timeline state to configuration."""
        if not self.current_show_name or self.current_show_name not in self.config.shows:
            return

        show = self.config.shows[self.current_show_name]

        # Ensure timeline_data exists
        if show.timeline_data is None:
            show.timeline_data = TimelineData()

        # Save audio file path
        show.timeline_data.audio_file_path = self.audio_lane.get_audio_file_path()

        # Save lanes from widgets
        show.timeline_data.lanes = []
        for lane_widget in self.lane_widgets:
            lane_data = lane_widget.lane.to_data_model()
            show.timeline_data.lanes.append(lane_data)

    # === Scroll/Zoom Synchronization ===

    def _sync_scroll(self, position: int):
        """Synchronize scroll position across all lanes."""
        sender = self.sender()

        # Sync master timeline
        if sender != self.master_timeline:
            self.master_timeline.sync_scroll_position(position)

        # Sync audio lane
        if sender != self.audio_lane:
            self.audio_lane.sync_scroll_position(position)

        # Sync all light lanes
        for lane in self.lane_widgets:
            if sender != lane:
                lane.sync_scroll_position(position)

    def _on_zoom_changed(self, value: int):
        """Handle zoom slider change."""
        zoom_factor = value / 100.0
        self.zoom_label.setText(f"{zoom_factor:.1f}x")
        self._apply_zoom(zoom_factor)

    def _on_external_zoom_changed(self, zoom_factor: float):
        """Handle zoom change from a timeline widget."""
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(zoom_factor * 100))
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f"{zoom_factor:.1f}x")
        self._apply_zoom(zoom_factor)

    def _apply_zoom(self, zoom_factor: float):
        """Apply zoom factor to all timeline widgets."""
        self.master_timeline.set_zoom_factor(zoom_factor)
        self.audio_lane.set_zoom_factor(zoom_factor)
        for lane in self.lane_widgets:
            lane.set_zoom_factor(zoom_factor)

    # === Playhead and Playback ===

    def _on_playhead_moved(self, position: float):
        """Handle playhead position change from timeline click."""
        self.playhead_position = position
        self._update_playhead_display(position)

        # Update all timelines
        self.master_timeline.set_playhead_position(position)
        self.audio_lane.set_playhead_position(position)
        for lane in self.lane_widgets:
            lane.set_playhead_position(position)

    def _update_playhead_display(self, position: float):
        """Update time display and position slider."""
        self.time_label.setText(self._format_time(position))

        if self.song_structure:
            total = self.song_structure.get_total_duration()
            if total > 0:
                slider_pos = int((position / total) * 1000)
                self.position_slider.blockSignals(True)
                self.position_slider.setValue(slider_pos)
                self.position_slider.blockSignals(False)

    def _format_time(self, seconds: float) -> str:
        """Format time as MM:SS.ss"""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:05.2f}"

    def _on_position_slider_pressed(self):
        """Handle position slider press - pause updates during drag."""
        self._slider_dragging = True

    def _on_position_slider_released(self):
        """Handle position slider release - seek to position."""
        self._slider_dragging = False
        if self.song_structure:
            total = self.song_structure.get_total_duration()
            position = (self.position_slider.value() / 1000.0) * total
            self._seek_to(position)

    def _on_position_slider_changed(self, value: int):
        """Handle position slider value change during drag."""
        if hasattr(self, '_slider_dragging') and self._slider_dragging:
            if self.song_structure:
                total = self.song_structure.get_total_duration()
                position = (value / 1000.0) * total
                self.time_label.setText(self._format_time(position))

    def _toggle_playback(self):
        """Toggle play/pause."""
        if self.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        """Start playback."""
        if not self.song_structure:
            return

        self.is_playing = True
        self.play_btn.setText("Pause")

        # Initialize audio if available
        if AUDIO_AVAILABLE and self.audio_lane.get_audio_file():
            self._init_audio_engine()
            if self.playback_sync:
                self.playback_sync.on_play_requested(self.playhead_position)

        self.playback_timer.start()

    def _pause_playback(self):
        """Pause playback."""
        self.is_playing = False
        self.play_btn.setText("Play")
        self.playback_timer.stop()

        if self.playback_sync:
            self.playback_sync.on_pause_requested()

    def _stop_playback(self):
        """Stop playback and reset position."""
        self.is_playing = False
        self.play_btn.setText("Play")
        self.playback_timer.stop()

        if self.playback_sync:
            self.playback_sync.on_stop_requested()

        self._seek_to(0.0)

    def _seek_to(self, position: float):
        """Seek to a specific position."""
        self.playhead_position = position
        self._on_playhead_moved(position)

        if self.playback_sync:
            self.playback_sync.on_seek_requested(position)

    def _update_playback(self):
        """Called by timer during playback to update position."""
        if not self.is_playing or not self.song_structure:
            return

        # Get position from audio if available, otherwise use timer
        if self.playback_sync:
            position = self.playback_sync.get_accurate_position()
        else:
            # Fallback: increment by timer interval
            position = self.playhead_position + 0.016  # 16ms

        total = self.song_structure.get_total_duration()
        if position >= total:
            self._stop_playback()
            return

        self.playhead_position = position
        self._update_playhead_display(position)

        # Update all timeline playheads
        self.master_timeline.set_playhead_position(position)
        self.audio_lane.set_playhead_position(position)
        for lane in self.lane_widgets:
            lane.set_playhead_position(position)

    def _init_audio_engine(self):
        """Initialize audio engine on first use."""
        if not AUDIO_AVAILABLE:
            return

        if self.audio_engine is None:
            try:
                self.device_manager = DeviceManager()
                self.audio_engine = AudioEngine()
                self.audio_mixer = AudioMixer()

                # Apply stored audio settings if available
                device_index = None
                if hasattr(self, 'audio_settings') and self.audio_settings:
                    device_index = self.audio_settings.get('device_index')
                    sample_rate = self.audio_settings.get('sample_rate', 44100)
                    buffer_size = self.audio_settings.get('buffer_size', 1024)
                    self.audio_engine.sample_rate = sample_rate
                    self.audio_engine.buffer_size = buffer_size

                # Initialize audio engine with device
                self.audio_engine.initialize(device_index=device_index)

                self.playback_sync = PlaybackSynchronizer(
                    self.audio_engine, self.audio_mixer
                )

                # Load audio file into mixer
                audio_file = self.audio_lane.get_audio_file()
                if audio_file:
                    self.audio_mixer.add_lane("audio", audio_file, 1.0)

                # Connect volume/mute
                self.audio_lane.volume_slider.valueChanged.connect(
                    lambda v: self.audio_mixer.update_lane_volume("audio", v / 100.0) if self.audio_mixer else None
                )
                self.audio_lane.mute_button.toggled.connect(
                    lambda m: self.audio_mixer.set_mute_state("audio", m) if self.audio_mixer else None
                )

            except Exception as e:
                print(f"Failed to initialize audio engine: {e}")
                self.audio_engine = None
                self.playback_sync = None

    def apply_audio_settings(self, settings: dict):
        """Apply audio settings from settings dialog.

        Args:
            settings: Dict with device_index, sample_rate, buffer_size
        """
        self.audio_settings = settings

        # If audio engine exists, reinitialize with new settings
        if self.audio_engine:
            was_playing = self.is_playing
            if was_playing:
                self._pause_playback()

            # Cleanup and reinitialize
            try:
                self.audio_engine.cleanup()
            except Exception:
                pass

            self.audio_engine = None
            self.playback_sync = None

            # Reinitialize with new settings
            self._init_audio_engine()

            if was_playing:
                self._start_playback()

    def cleanup(self):
        """Clean up audio resources."""
        self._stop_playback()

        if self.audio_engine:
            try:
                self.audio_engine.shutdown()
            except Exception:
                pass
            self.audio_engine = None
            self.audio_mixer = None
            self.playback_sync = None

        self.audio_lane.cleanup()

    def on_tab_deactivated(self):
        """Called when leaving the tab."""
        self._pause_playback()
        self.save_to_config()
