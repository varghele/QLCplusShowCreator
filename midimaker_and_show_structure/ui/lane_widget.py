from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QPushButton, QCheckBox, QSpinBox, QLineEdit,
                             QFrame, QFileDialog, QMessageBox, QComboBox,
                             QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPalette, QPainter, QPen, QColor, QWheelEvent
from core.lane import Lane, AudioLane, MidiLane
from .midi_block_widget import MidiBlockWidget
from .audio_waveform_widget import AudioWaveformWidget
from audio.audio_file import AudioFile
from styles import theme_manager


class TimelineWidget(QWidget):
    """Custom timeline widget with grid drawing and snap functionality"""

    zoom_changed = pyqtSignal(float)  # New signal for zoom changes
    playhead_moved = pyqtSignal(float)  # Signal for playhead position changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bpm = 120.0
        self.zoom_factor = 1.0
        self.base_pixels_per_second = 60  # Time-based: 60 pixels per second
        self.pixels_per_second = self.base_pixels_per_second
        self.snap_to_grid = True
        self.playhead_position = 0.0  # Position in seconds
        self.dragging_playhead = False  # Track if we're dragging the playhead
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.song_structure = None

        self.setMinimumHeight(60)
        self.update_timeline_width()
        self.setStyleSheet("background-color: #f8f8f8; border: 1px solid #ddd;")

    def update_timeline_width(self):
        """Update timeline width based on zoom level and song structure"""
        self.pixels_per_second = self.base_pixels_per_second * self.zoom_factor

        # Check if we have song structure to calculate width
        if (hasattr(self, 'song_structure') and self.song_structure and
                hasattr(self.song_structure, 'parts') and self.song_structure.parts):
            try:
                total_duration = self.song_structure.get_total_duration()
                new_width = max(2000, int(total_duration * self.pixels_per_second) + 100)
            except (AttributeError, ZeroDivisionError, TypeError):
                new_width = max(2000, int(60 * self.pixels_per_second))  # Default 60 seconds
        else:
            new_width = max(2000, int(60 * self.pixels_per_second))  # Default 60 seconds

        self.setMinimumWidth(new_width)

    def draw_grid(self, painter, width, height):
        """Draw grid with song structure awareness"""
        if (hasattr(self, 'song_structure') and self.song_structure and
            hasattr(self.song_structure, 'parts') and self.song_structure.parts):
            try:
                # Draw song structure-aware grid
                self.draw_song_structure_grid(painter, width, height)
            except Exception as e:
                print(f"Error drawing song structure grid: {e}")
                # Fall back to basic grid
                self.draw_basic_grid(painter, width, height)
        else:
            # Draw basic grid
            self.draw_basic_grid(painter, width, height)

    def draw_song_structure_grid(self, painter, width, height):
        """Draw grid based on song structure using time_to_pixel for consistency"""
        beat_pen = QPen(QColor("#cccccc"), 1)
        bar_pen = QPen(QColor("#999999"), 2)
        part_pen = QPen(QColor("#666666"), 3)  # Thicker line for part boundaries

        num_parts = len(self.song_structure.parts)
        for part_idx, part in enumerate(self.song_structure.parts):
            beats_per_bar = int(part.get_beats_per_bar())
            total_beats_in_part = int(part.get_total_beats())
            seconds_per_beat = 60.0 / part.bpm

            # Draw part boundary
            start_x = round(self.time_to_pixel(part.start_time))
            if 0 <= start_x <= width:
                painter.setPen(part_pen)
                painter.drawLine(start_x, 0, start_x, height)

            # For all parts except the last, skip the final beat
            # (it will be drawn as beat 0 of the next part to avoid
            # floating-point boundary issues)
            is_last_part = (part_idx == num_parts - 1)
            max_beat = total_beats_in_part if is_last_part else total_beats_in_part - 1

            # Draw beat lines within this part
            for beat_index in range(max_beat + 1):
                # Calculate time for this beat within the part
                beat_time = part.start_time + (beat_index * seconds_per_beat)
                beat_x = round(self.time_to_pixel(beat_time))

                if 0 <= beat_x <= width:
                    # Use bar pen for bar boundaries, beat pen for beats
                    painter.setPen(bar_pen if beat_index % beats_per_bar == 0 else beat_pen)
                    painter.drawLine(beat_x, 0, beat_x, height)

    def draw_basic_grid(self, painter, width, height):
        """Draw basic grid without song structure (time-based)"""
        beat_pen = QPen(QColor("#cccccc"), 1)
        bar_pen = QPen(QColor("#999999"), 2)

        # Use default BPM for basic grid
        seconds_per_beat = 60.0 / self.bpm
        beat_count = 0
        beat_time = 0.0
        max_time = width / self.pixels_per_second

        while beat_time <= max_time:
            x = round(self.time_to_pixel(beat_time))
            if beat_count % 4 == 0:
                painter.setPen(bar_pen)
            else:
                painter.setPen(beat_pen)

            painter.drawLine(x, 0, x, height)
            beat_count += 1
            beat_time = beat_count * seconds_per_beat

    def time_to_pixel(self, time: float) -> float:
        """Convert time in seconds to pixel position (time-based layout)"""
        return time * self.pixels_per_second

    def pixel_to_time(self, pixel: float) -> float:
        """Convert pixel position to time in seconds (time-based layout)"""
        return pixel / self.pixels_per_second

    def find_nearest_beat_time(self, target_time: float) -> float:
        """Find the nearest beat position using song structure if available"""
        if not (hasattr(self, 'song_structure') and self.song_structure and
                hasattr(self.song_structure, 'parts') and self.song_structure.parts):
            # Fallback to simple beat snapping with default BPM
            beat_duration = 60.0 / self.bpm
            nearest_beat = round(target_time / beat_duration)
            return nearest_beat * beat_duration

        # Find which part contains the target time
        target_part = None
        target_part_index = -1

        for i, part in enumerate(self.song_structure.parts):
            if part.start_time <= target_time < part.start_time + part.duration:
                target_part = part
                target_part_index = i
                break

        # If beyond all parts, use the last part
        if not target_part and self.song_structure.parts:
            target_part = self.song_structure.parts[-1]
            target_part_index = len(self.song_structure.parts) - 1

        if not target_part:
            return target_time

        # Calculate candidate beat times
        candidates = []
        seconds_per_beat = 60.0 / target_part.bpm
        total_beats_in_part = int(target_part.get_total_beats())

        # Calculate which beat we're closest to within the part
        time_in_part = target_time - target_part.start_time
        beat_in_part_float = time_in_part / seconds_per_beat

        floor_beat = int(beat_in_part_float)
        ceil_beat = floor_beat + 1

        # Add floor and ceil beats from current part
        for beat in [floor_beat, ceil_beat]:
            if 0 <= beat <= total_beats_in_part:
                candidate_time = target_part.start_time + (beat * seconds_per_beat)
                candidates.append(candidate_time)

        # Always include part start time
        candidates.append(target_part.start_time)

        # Include the last beat of this part
        last_beat_time = target_part.start_time + (total_beats_in_part * seconds_per_beat)
        candidates.append(last_beat_time)

        # Check adjacent parts for boundary beats
        if target_part_index > 0:
            prev_part = self.song_structure.parts[target_part_index - 1]
            prev_seconds_per_beat = 60.0 / prev_part.bpm
            prev_total_beats = int(prev_part.get_total_beats())
            prev_last_beat = prev_part.start_time + (prev_total_beats * prev_seconds_per_beat)
            candidates.append(prev_last_beat)

        if target_part_index < len(self.song_structure.parts) - 1:
            next_part = self.song_structure.parts[target_part_index + 1]
            candidates.append(next_part.start_time)

        # Remove duplicates and find closest
        candidates = list(set(candidates))

        if not candidates:
            return target_time

        # Find the closest candidate
        closest_time = min(candidates, key=lambda t: abs(t - target_time))

        return closest_time

    def draw_playhead(self, painter, width, height):
        """Draw playhead at time position"""
        playhead_x = round(self.time_to_pixel(self.playhead_position))

        if 0 <= playhead_x <= width:
            playhead_pen = QPen(QColor("#FF4444"), 2)
            painter.setPen(playhead_pen)
            painter.drawLine(playhead_x, 0, playhead_x, height)

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel events for zooming"""
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Shift + wheel = zoom
            delta = event.angleDelta().y()
            zoom_in = delta > 0

            # Get mouse position for zoom center
            mouse_x = event.position().x()

            # Calculate time position at mouse cursor before zoom (song structure aware)
            time_at_mouse = self.pixel_to_time(mouse_x)

            # Apply zoom
            old_zoom = self.zoom_factor
            if zoom_in:
                self.zoom_factor = min(self.max_zoom, self.zoom_factor * 1.2)
            else:
                self.zoom_factor = max(self.min_zoom, self.zoom_factor / 1.2)

            if self.zoom_factor != old_zoom:
                self.update_timeline_width()
                self.zoom_changed.emit(self.zoom_factor)

                # Maintain mouse position after zoom (song structure aware)
                new_mouse_x = self.time_to_pixel(time_at_mouse)
                scroll_offset = new_mouse_x - mouse_x

                # Notify parent scroll area to adjust position
                if hasattr(self.parent(), 'horizontalScrollBar'):
                    current_scroll = self.parent().horizontalScrollBar().value()
                    self.parent().horizontalScrollBar().setValue(int(current_scroll + scroll_offset))

                self.update()

            event.accept()
        else:
            # Normal wheel = scroll horizontally
            super().wheelEvent(event)

    def set_zoom_factor(self, zoom_factor: float):
        """Set zoom factor externally"""
        self.zoom_factor = zoom_factor
        self.update_timeline_width()
        self.update()

    def set_song_structure(self, song_structure):
        """Set song structure for this timeline"""
        self.song_structure = song_structure
        self.update_timeline_width()
        self.update()

    def set_bpm(self, bpm):
        """Set BPM for grid calculations"""
        self.bpm = bpm
        self.update()

    def get_current_bpm(self) -> float:
        """Get BPM at current playhead position"""
        if (hasattr(self, 'song_structure') and self.song_structure and
                hasattr(self.song_structure, 'get_bmp_at_time')):
            try:
                return self.song_structure.get_bpm_at_time(self.playhead_position)
            except (AttributeError, TypeError):
                pass
        return self.bpm

    def set_pixels_per_second(self, pixels):
        """Set zoom level (pixels per second)"""
        self.pixels_per_second = pixels
        self.update()

    def set_snap_to_grid(self, snap):
        """Enable/disable snap to grid"""
        self.snap_to_grid = snap

    def set_playhead_position(self, position: float):
        """Set playhead position and update display"""
        self.playhead_position = position
        self.update()

    def mousePressEvent(self, event):
        """Handle mouse press for playhead dragging"""
        from PyQt6.QtCore import Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_playhead = True
            self.update_playhead_from_mouse(event.pos().x())

    def mouseMoveEvent(self, event):
        """Handle mouse move for playhead dragging"""
        from PyQt6.QtCore import Qt
        if self.dragging_playhead:
            self.update_playhead_from_mouse(event.pos().x())

    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop playhead dragging"""
        from PyQt6.QtCore import Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_playhead = False

    def update_playhead_from_mouse(self, x_pos: int):
        """Update playhead position based on mouse position"""
        # Convert pixel position to time
        time_position = self.pixel_to_time(x_pos)

        # Apply snap to grid if enabled
        if self.snap_to_grid:
            time_position = self.find_nearest_beat_time(time_position)

        time_position = max(0.0, time_position)
        self.playhead_position = time_position
        self.playhead_moved.emit(time_position)
        self.update()

    def draw_song_structure_background(self, painter, width, height):
        """Draw song structure parts as subtle colored backgrounds"""
        if not (hasattr(self, 'song_structure') and self.song_structure and
                hasattr(self.song_structure, 'parts') and self.song_structure.parts):
            return

        try:
            for part in self.song_structure.parts:
                start_x = self.time_to_pixel(part.start_time)
                end_x = self.time_to_pixel(part.start_time + part.duration)

                if end_x < 0 or start_x > width:
                    continue

                # Draw colored background with lower alpha for subtle effect
                color = QColor(part.color)
                color.setAlpha(40)  # More subtle than master timeline (which uses 100)
                painter.fillRect(int(start_x), 0, int(end_x - start_x), height, color)

        except Exception as e:
            print(f"Error drawing song structure background in lane: {e}")

    def paintEvent(self, event):
        """Draw the timeline - can be extended by subclasses"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw song structure backgrounds first (subtle colors)
        self.draw_song_structure_background(painter, width, height)

        # Draw grid (can be overridden)
        self.draw_grid(painter, width, height)

        # Draw playhead (can be overridden)
        self.draw_playhead(painter, width, height)


class LaneWidget(QFrame):
    remove_requested = pyqtSignal(object)
    scroll_position_changed = pyqtSignal(int)  # Emits horizontal scroll position
    zoom_changed = pyqtSignal(float)  # Signal for zoom changes
    playhead_moved = pyqtSignal(float)  # Signal for playhead position changes

    def __init__(self, lane: Lane, parent=None):
        super().__init__(parent)
        self.lane = lane
        self.midi_block_widgets = []
        self.main_window = parent
        self.waveform_widget = None  # For audio lanes

        # Apply widget style
        self.setStyleSheet(theme_manager.get_lane_widget_style())

        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)

        self.setup_ui()
        self.setup_drag_drop()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)

        # Lane controls section (left side)
        controls_widget = QWidget()
        controls_widget.setFixedWidth(320)  # Increased width for better spacing
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setSpacing(4)  # Add spacing between rows

        # Lane name and type (first row)
        name_layout = QHBoxLayout()
        self.name_edit = QLineEdit(self.lane.name)
        self.name_edit.textChanged.connect(self.on_name_changed)

        self.remove_button = QPushButton("×")
        self.remove_button.setFixedSize(25, 25)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))

        name_label = QLabel("Name:")
        name_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        name_layout.addWidget(self.remove_button)

        # Apply styles to input fields
        self.name_edit.setStyleSheet(theme_manager.get_line_edit_style())
        # Style the remove button
        self.remove_button.setStyleSheet(theme_manager.get_remove_button_style())

        controls_layout.addLayout(name_layout)

        # Lane-specific controls (second row)
        lane_specific_layout = QHBoxLayout()

        if isinstance(self.lane, MidiLane):
            self.setup_midi_controls(lane_specific_layout)
        elif isinstance(self.lane, AudioLane):
            self.setup_audio_controls(lane_specific_layout)

        controls_layout.addLayout(lane_specific_layout)

        # Mute, Solo, and Snap controls (third row)
        control_buttons_layout = QHBoxLayout()

        # Mute and Solo buttons
        self.mute_button = QPushButton("M")
        self.solo_button = QPushButton("S")

        # Make buttons smaller and more compact
        self.mute_button.setFixedSize(30, 25)
        self.solo_button.setFixedSize(30, 25)

        # Style the buttons
        self.mute_button.setCheckable(True)
        self.solo_button.setCheckable(True)

        self.mute_button.setChecked(self.lane.muted)
        self.solo_button.setChecked(self.lane.solo)

        # Set initial styles
        self.update_mute_button_style()
        self.update_solo_button_style()

        self.mute_button.toggled.connect(self.on_mute_toggled)
        self.solo_button.toggled.connect(self.on_solo_toggled)

        control_buttons_layout.addWidget(self.mute_button)
        control_buttons_layout.addWidget(self.solo_button)

        # Add snap to grid control for MIDI lanes
        if isinstance(self.lane, MidiLane):
            # Add some spacing between buttons and checkbox
            control_buttons_layout.addSpacing(10)

            self.snap_checkbox = QCheckBox("Snap")
            self.snap_checkbox.setChecked(True)
            self.snap_checkbox.setStyleSheet("color: white; font-size: 12px;")
            self.snap_checkbox.toggled.connect(self.on_snap_toggled)
            control_buttons_layout.addWidget(self.snap_checkbox)

        control_buttons_layout.addStretch()  # Push everything to the left

        controls_layout.addLayout(control_buttons_layout)

        main_layout.addWidget(controls_widget)

        # Timeline section (right side) - scrollable
        self.timeline_scroll = QScrollArea()
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.zoom_changed.connect(self.zoom_changed.emit)  # Connect zoom signal
        self.timeline_widget.zoom_changed.connect(self.on_timeline_zoom_changed)  # Update MIDI blocks on zoom
        self.timeline_widget.playhead_moved.connect(self.playhead_moved.emit)  # Forward playhead changes
        #self.timeline_widget.setMinimumWidth(2000)  # Wide timeline

        if isinstance(self.lane, MidiLane):
            self.setup_midi_timeline()
        elif isinstance(self.lane, AudioLane):
            self.setup_audio_timeline()

        self.timeline_scroll.setWidget(self.timeline_widget)
        self.timeline_scroll.setWidgetResizable(False)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Connect scroll events
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(
            self.scroll_position_changed.emit)

        main_layout.addWidget(self.timeline_scroll, 1)

    def set_song_structure(self, song_structure):
        """Set song structure for this lane's timeline"""
        self.timeline_widget.set_song_structure(song_structure)

    def setup_midi_controls(self, layout):
        # First row: Channel selection and name
        channel_row = QHBoxLayout()

        # MIDI Channel selection with label
        ch_label = QLabel("Ch:")
        ch_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px; min-width: 25px;")
        channel_row.addWidget(ch_label)

        self.channel_spinbox = QSpinBox()
        self.channel_spinbox.setRange(1, 16)
        self.channel_spinbox.setValue(self.lane.midi_channel)
        self.channel_spinbox.setFixedWidth(50)
        self.channel_spinbox.valueChanged.connect(self.on_channel_changed)
        self.channel_spinbox.setStyleSheet(theme_manager.get_spinbox_style())
        channel_row.addWidget(self.channel_spinbox)

        # Channel name with more space
        self.channel_name_edit = QLineEdit(self.lane.channel_name)
        self.channel_name_edit.setPlaceholderText("Channel Name")
        self.channel_name_edit.textChanged.connect(self.on_channel_name_changed)
        self.channel_name_edit.setStyleSheet(theme_manager.get_line_edit_style())
        channel_row.addWidget(self.channel_name_edit, 1)  # Give it stretch factor

        layout.addLayout(channel_row)

        # Second row: Add Block button (full width)
        button_row = QHBoxLayout()
        self.add_block_button = QPushButton("Add Block")
        self.add_block_button.clicked.connect(self.add_midi_block)
        self.add_block_button.setStyleSheet(theme_manager.get_action_button_style())
        button_row.addWidget(self.add_block_button)
        button_row.addStretch()  # Push button to the left

        layout.addLayout(button_row)


    def setup_audio_controls(self, layout):
        # Load audio file button
        self.load_audio_button = QPushButton("Load Audio")
        self.load_audio_button.clicked.connect(self.load_audio_file)
        self.load_audio_button.setStyleSheet(theme_manager.get_action_button_style())
        layout.addWidget(self.load_audio_button)

        # Volume control with readable label
        vol_label = QLabel("Vol:")
        vol_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px; margin-left: 10px;")
        layout.addWidget(vol_label)

        self.volume_spinbox = QSpinBox()
        self.volume_spinbox.setRange(0, 100)
        self.volume_spinbox.setValue(int(self.lane.volume * 100))
        self.volume_spinbox.setFixedWidth(60)
        self.volume_spinbox.valueChanged.connect(self.on_volume_changed)
        self.volume_spinbox.setStyleSheet(theme_manager.get_spinbox_style())
        layout.addWidget(self.volume_spinbox)

        layout.addStretch()  # Push controls to the left

    def set_playhead_position(self, position: float):
        """Set playhead position for this lane's timeline"""
        self.timeline_widget.set_playhead_position(position)

    def set_zoom_factor(self, zoom_factor: float):
        """Set zoom factor for this lane's timeline"""
        self.timeline_widget.set_zoom_factor(zoom_factor)

        # Update MIDI block positions
        for block_widget in self.midi_block_widgets:
            if hasattr(block_widget, 'set_grid_size'):
                block_widget.set_grid_size(self.timeline_widget.pixels_per_second)
            if hasattr(block_widget, 'update_position'):
                block_widget.update_position()

        # Update waveform widget zoom
        if self.waveform_widget:
            self.waveform_widget.set_zoom_factor(zoom_factor)

    def sync_scroll_position(self, position: int):
        """Sync scroll position with master timeline"""
        self.timeline_scroll.horizontalScrollBar().setValue(position)

        # Update waveform widget scroll offset
        if self.waveform_widget:
            self.waveform_widget.set_scroll_offset(position)

    def setup_midi_timeline(self):
        # Create MIDI block widgets for existing blocks
        for block in self.lane.midi_blocks:
            self.create_midi_block_widget(block)

    def setup_audio_timeline(self):
        # Create waveform widget for audio visualization
        self.waveform_widget = AudioWaveformWidget(self.timeline_widget)
        self.waveform_widget.setGeometry(0, 0, self.timeline_widget.width(), self.timeline_widget.height())
        self.waveform_widget.pixels_per_second = self.timeline_widget.pixels_per_second
        self.waveform_widget.zoom_factor = self.timeline_widget.zoom_factor
        self.waveform_widget.show()

        # Load audio file if available
        if self.lane.audio_file_path:
            self.load_audio_into_waveform(self.lane.audio_file_path)
        else:
            # Show placeholder text on waveform widget
            placeholder_label = QLabel("Drag audio file here", self.waveform_widget)
            placeholder_label.setStyleSheet("color: #888; font-style: italic; font-size: 14px;")
            placeholder_label.setGeometry(10, 10, 300, 30)

    def load_audio_into_waveform(self, file_path: str):
        """Load audio file into waveform widget"""
        try:
            # Create AudioFile and load
            audio_file = AudioFile(target_sample_rate=44100)
            if audio_file.load(file_path):
                # Pass to waveform widget
                if self.waveform_widget:
                    self.waveform_widget.load_audio_file(audio_file)
            else:
                QMessageBox.warning(self, "Error", f"Failed to load audio file: {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading audio file: {str(e)}")

    def setup_drag_drop(self):
        if isinstance(self.lane, AudioLane):
            self.setAcceptDrops(True)

    def update_bpm(self, bpm):
        """Update BPM for grid calculations"""
        self.timeline_widget.set_bpm(bpm)
        for block_widget in self.midi_block_widgets:
            if hasattr(block_widget, 'update_position'):
                block_widget.update_position()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if isinstance(self.lane, AudioLane) and event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
                event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if isinstance(self.lane, AudioLane) and event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            self.lane.set_audio_file(file_path)
            self.refresh_audio_timeline()

            # Update audio synchronizer with new audio file
            if self.main_window:
                self.main_window.playback_engine.set_lanes(self.main_window.project.lanes)

            event.acceptProposedAction()

    def create_midi_block_widget(self, block):
        block_widget = MidiBlockWidget(block, self.timeline_widget)
        block_widget.remove_requested.connect(self.remove_midi_block_widget)
        block_widget.position_changed.connect(self.on_block_position_changed)
        block_widget.duration_changed.connect(self.on_block_duration_changed)

        # Set grid properties
        block_widget.set_grid_size(self.timeline_widget.pixels_per_second)
        block_widget.set_snap_to_grid(self.timeline_widget.snap_to_grid)

        self.midi_block_widgets.append(block_widget)
        block_widget.show()

    def add_midi_block(self):
        if isinstance(self.lane, MidiLane):
            # Add block at current playhead position
            start_time = self.timeline_widget.playhead_position
            block = self.lane.add_midi_block(start_time, 1.0)
            self.create_midi_block_widget(block)

    def remove_midi_block_widget(self, block_widget):
        self.lane.remove_midi_block(block_widget.block)
        self.midi_block_widgets.remove(block_widget)
        block_widget.deleteLater()

    def on_block_position_changed(self, block_widget, new_start_time):
        """Handle when a MIDI block is moved"""
        # The block's start_time is already updated in the widget
        # We could add additional logic here if needed
        pass

    def on_block_duration_changed(self, block_widget, new_duration):
        """Handle when a MIDI block is resized"""
        # The block's duration is already updated in the widget
        # We could add additional logic here if needed (e.g., collision detection)
        pass

    def on_timeline_zoom_changed(self, zoom_factor):
        """Handle timeline zoom changes - update all MIDI block positions and sizes"""
        new_pixels_per_second = self.timeline_widget.pixels_per_second

        # Update all MIDI blocks to reflect new zoom level
        for block_widget in self.midi_block_widgets:
            block_widget.set_grid_size(new_pixels_per_second)

    def load_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Audio File", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg)")

        if file_path:
            self.lane.set_audio_file(file_path)
            self.refresh_audio_timeline()

            # Update audio synchronizer with new audio file
            if self.main_window:
                self.main_window.playback_engine.set_lanes(self.main_window.project.lanes)

    def refresh_audio_timeline(self):
        # Clear existing waveform widget
        if self.waveform_widget:
            self.waveform_widget.cleanup()
            self.waveform_widget.deleteLater()
            self.waveform_widget = None

        # Clear any remaining labels
        for child in self.timeline_widget.findChildren(QLabel):
            child.deleteLater()

        # Re-setup timeline
        self.setup_audio_timeline()

    # Event handlers
    def on_name_changed(self, text):
        self.lane.name = text

    def on_mute_toggled(self, checked):
        self.lane.muted = checked
        self.update_mute_button_style()

        # Update audio mixer mute state if this is an audio lane
        if isinstance(self.lane, AudioLane) and hasattr(self.main_window, 'audio_synchronizer'):
            self.main_window.audio_synchronizer.update_lane_mute(id(self.lane), checked)

    def on_solo_toggled(self, checked):
        self.lane.solo = checked
        self.update_solo_button_style()

        # Update audio mixer solo state if this is an audio lane
        if isinstance(self.lane, AudioLane) and hasattr(self.main_window, 'audio_synchronizer'):
            self.main_window.audio_synchronizer.update_lane_solo(id(self.lane), checked)

    def on_channel_changed(self, value):
        if isinstance(self.lane, MidiLane):
            self.lane.set_midi_channel(value, self.channel_name_edit.text())

    def on_channel_name_changed(self, text):
        if isinstance(self.lane, MidiLane):
            self.lane.channel_name = text

    def on_volume_changed(self, value):
        if isinstance(self.lane, AudioLane):
            self.lane.volume = value / 100.0

    def on_snap_toggled(self, checked):
        """Toggle snap to grid for all MIDI blocks in this lane"""
        if isinstance(self.lane, MidiLane):
            self.timeline_widget.set_snap_to_grid(checked)
            for block_widget in self.midi_block_widgets:
                block_widget.set_snap_to_grid(checked)

    def update_mute_button_style(self):
        """Update mute button appearance based on state"""
        style = theme_manager.get_mute_button_compact_style(self.mute_button.isChecked())
        self.mute_button.setStyleSheet(style)

    def update_solo_button_style(self):
        """Update solo button appearance based on state"""
        style = theme_manager.get_solo_button_compact_style(self.solo_button.isChecked())
        self.solo_button.setStyleSheet(style)

