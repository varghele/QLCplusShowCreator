# timeline_ui/audio_lane_widget.py
# Audio lane widget for displaying waveform and audio controls on the timeline

import os
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QPushButton, QSlider, QFrame, QScrollArea,
                             QFileDialog, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from .timeline_widget import TimelineWidget

# Try to import audio components - may not be available in all installations
try:
    from audio.audio_file import AudioFile
    from audio.audio_waveform_widget import AudioWaveformWidget
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    AudioFile = None
    AudioWaveformWidget = None


class AudioTimelineWidget(TimelineWidget):
    """Timeline widget with embedded waveform display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.waveform_widget = None
        self.audio_file = None

        if AUDIO_AVAILABLE:
            self.waveform_widget = AudioWaveformWidget(self)
            self.waveform_widget.setStyleSheet("background: transparent;")

    def resizeEvent(self, event):
        """Handle resize to update waveform widget size."""
        super().resizeEvent(event)
        if self.waveform_widget:
            self.waveform_widget.setGeometry(0, 0, self.width(), self.height())

    def set_zoom_factor(self, zoom_factor: float):
        """Set zoom factor and update waveform."""
        super().set_zoom_factor(zoom_factor)
        if self.waveform_widget:
            self.waveform_widget.set_zoom_factor(zoom_factor)

    def load_audio(self, audio_file):
        """Load audio file for waveform display."""
        self.audio_file = audio_file
        if self.waveform_widget and audio_file:
            self.waveform_widget.load_audio_file(audio_file)

    def paintEvent(self, event):
        """Draw timeline with waveform overlay."""
        # Draw base timeline (grid, playhead)
        super().paintEvent(event)
        # Waveform widget draws itself as a child

    def cleanup(self):
        """Clean up resources."""
        if self.waveform_widget:
            self.waveform_widget.cleanup()


class AudioLaneWidget(QFrame):
    """Widget for displaying and controlling the audio lane.

    Shows lane controls on the left (file path, load button, volume, mute)
    and a scrollable timeline with waveform on the right.
    """

    scroll_position_changed = pyqtSignal(int)  # Emits horizontal scroll position
    zoom_changed = pyqtSignal(float)  # Emits zoom factor
    playhead_moved = pyqtSignal(float)  # Emits playhead position
    audio_file_changed = pyqtSignal(str)  # Emits new audio file path

    def __init__(self, parent=None):
        """Create a new audio lane widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.audio_file = None
        self.audio_file_path = ""

        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setMinimumHeight(100)
        self.setMaximumHeight(140)
        self.setStyleSheet("""
            AudioLaneWidget {
                background-color: #1a2a3a;
                border: 1px solid #3d5a7a;
                border-radius: 4px;
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Lane controls section (left side)
        controls_widget = self.create_controls_widget()
        main_layout.addWidget(controls_widget)

        # Timeline section (right side) - scrollable
        self.timeline_scroll = QScrollArea()
        self.timeline_widget = AudioTimelineWidget()
        self.timeline_widget.zoom_changed.connect(self.zoom_changed.emit)
        self.timeline_widget.zoom_changed.connect(self.on_timeline_zoom_changed)
        self.timeline_widget.playhead_moved.connect(self.playhead_moved.emit)

        self.timeline_scroll.setWidget(self.timeline_widget)
        self.timeline_scroll.setWidgetResizable(False)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Connect scroll events
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(
            self.scroll_position_changed.emit)
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(
            self._on_scroll_changed)

        main_layout.addWidget(self.timeline_scroll, 1)

    def create_controls_widget(self):
        """Create the lane controls section."""
        widget = QWidget()
        widget.setFixedWidth(320)
        widget.setStyleSheet("background-color: #1a2a3a;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        # Row 1: Audio label
        title_layout = QHBoxLayout()
        title_label = QLabel("Audio Track")
        title_label.setStyleSheet("color: #7eb8ff; font-weight: bold; font-size: 13px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Row 2: File path and load button
        file_layout = QHBoxLayout()

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("No audio file loaded")
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2d3d4d;
                color: #aabbcc;
                border: 1px solid #3d5a7a;
                border-radius: 3px;
                padding: 3px 5px;
                font-size: 10px;
            }
        """)
        file_layout.addWidget(self.file_path_edit, 1)

        self.load_button = QPushButton("Load")
        self.load_button.setFixedWidth(50)
        self.load_button.clicked.connect(self._on_load_clicked)
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #4a6a8a;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #5a7a9a;
            }
        """)
        file_layout.addWidget(self.load_button)

        layout.addLayout(file_layout)

        # Row 3: Volume and mute controls
        controls_layout = QHBoxLayout()

        # Mute button
        self.mute_button = QPushButton("M")
        self.mute_button.setFixedSize(30, 25)
        self.mute_button.setCheckable(True)
        self.mute_button.toggled.connect(self._on_mute_toggled)
        self.mute_button.setStyleSheet("""
            QPushButton {
                background-color: #3d5a7a;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4d6a8a;
            }
            QPushButton:checked {
                background-color: #d32f2f;
            }
        """)
        controls_layout.addWidget(self.mute_button)

        # Volume icon
        vol_label = QLabel("Vol:")
        vol_label.setStyleSheet("color: #aabbcc; font-size: 11px;")
        controls_layout.addWidget(vol_label)

        # Volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #2d3d4d;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #7eb8ff;
                width: 12px;
                margin: -3px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #4a6a8a;
                border-radius: 3px;
            }
        """)
        controls_layout.addWidget(self.volume_slider)

        # Volume percentage label
        self.volume_label = QLabel("100%")
        self.volume_label.setFixedWidth(35)
        self.volume_label.setStyleSheet("color: #aabbcc; font-size: 10px;")
        controls_layout.addWidget(self.volume_label)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        return widget

    def _on_load_clicked(self):
        """Handle load button click - open file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*)"
        )
        if file_path:
            self.load_audio_file(file_path)

    def load_audio_file(self, file_path: str):
        """Load an audio file and display its waveform.

        Args:
            file_path: Path to the audio file
        """
        if not AUDIO_AVAILABLE:
            self.file_path_edit.setText("Audio support not available")
            return

        if not os.path.exists(file_path):
            self.file_path_edit.setText(f"File not found: {file_path}")
            return

        self.audio_file_path = file_path
        self.file_path_edit.setText(os.path.basename(file_path))
        self.file_path_edit.setToolTip(file_path)

        # Load audio file
        try:
            self.audio_file = AudioFile()
            self.audio_file.load(file_path)
            self.timeline_widget.load_audio(self.audio_file)
            self.audio_file_changed.emit(file_path)
        except Exception as e:
            self.file_path_edit.setText(f"Error: {str(e)}")
            self.audio_file = None

    def clear_audio(self):
        """Clear the current audio file and reset the display."""
        self.audio_file = None
        self.audio_file_path = ""
        self.file_path_edit.setText("")
        self.file_path_edit.setPlaceholderText("No audio file loaded")
        self.file_path_edit.setToolTip("")
        # Clear waveform from timeline
        if hasattr(self.timeline_widget, 'load_audio'):
            self.timeline_widget.load_audio(None)

    def get_audio_file_path(self) -> str:
        """Get the current audio file path."""
        return self.audio_file_path

    def get_audio_file(self):
        """Get the loaded AudioFile object."""
        return self.audio_file

    def _on_volume_changed(self, value: int):
        """Handle volume slider change."""
        self.volume_label.setText(f"{value}%")
        # Volume control will be connected to audio engine by parent

    def _on_mute_toggled(self, checked: bool):
        """Handle mute button toggle."""
        if checked:
            self.mute_button.setStyleSheet("""
                QPushButton {
                    background-color: #d32f2f;
                    color: white;
                    font-weight: bold;
                    border: none;
                    border-radius: 3px;
                }
            """)
        else:
            self.mute_button.setStyleSheet("""
                QPushButton {
                    background-color: #3d5a7a;
                    color: white;
                    font-weight: bold;
                    border: none;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #4d6a8a;
                }
            """)
        # Mute state will be connected to audio engine by parent

    def is_muted(self) -> bool:
        """Check if audio is muted."""
        return self.mute_button.isChecked()

    def get_volume(self) -> float:
        """Get current volume as 0.0-1.0."""
        return self.volume_slider.value() / 100.0

    def _on_scroll_changed(self, position: int):
        """Handle scroll position change - update waveform offset."""
        if self.timeline_widget.waveform_widget:
            self.timeline_widget.waveform_widget.set_scroll_offset(position)

    def on_timeline_zoom_changed(self, zoom_factor: float):
        """Handle timeline zoom changes."""
        if self.timeline_widget.waveform_widget:
            self.timeline_widget.waveform_widget.set_zoom_factor(zoom_factor)

    def set_song_structure(self, song_structure):
        """Set song structure for this lane's timeline."""
        self.timeline_widget.set_song_structure(song_structure)

    def set_playhead_position(self, position: float):
        """Set playhead position for this lane's timeline."""
        self.timeline_widget.set_playhead_position(position)

    def set_zoom_factor(self, zoom_factor: float):
        """Set zoom factor for this lane's timeline."""
        self.timeline_widget.set_zoom_factor(zoom_factor)
        if self.timeline_widget.waveform_widget:
            self.timeline_widget.waveform_widget.set_zoom_factor(zoom_factor)

    def sync_scroll_position(self, position: int):
        """Sync scroll position with master timeline."""
        self.timeline_scroll.horizontalScrollBar().setValue(position)

    def cleanup(self):
        """Clean up audio resources."""
        self.timeline_widget.cleanup()
