# timeline_ui/master_timeline_widget.py
# Master timeline widget showing song structure, playhead, and grid
# Adapted from midimaker_and_show_structure/ui/master_timeline_widget.py

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygon, QBrush
from .timeline_widget import TimelineWidget


class MasterTimelineWidget(TimelineWidget):
    """Master timeline widget with enhanced playhead and song structure display."""

    playhead_moved = pyqtSignal(float)  # Emits new playhead position in seconds

    def __init__(self, parent=None):
        # Initialize attributes before calling super()
        self.song_structure = None
        self.playhead_position = 0.0
        self.dragging_playhead = False
        self.zoom_factor = 1.0
        self.base_pixels_per_second = 60
        self.min_zoom = 0.1
        self.max_zoom = 5.0

        super().__init__(parent)

        self.setMinimumHeight(40)
        self.setMinimumWidth(2000)
        self.setStyleSheet("""
            MasterTimelineWidget {
                background-color: #e8e8e8;
                border: 2px solid #bbb;
                border-radius: 4px;
            }
        """)

    def set_playhead_position(self, position: float):
        """Set playhead position and update display."""
        self.playhead_position = position
        self.update()

        # Auto-scroll to keep playhead visible
        self.ensure_playhead_visible()

    def ensure_playhead_visible(self):
        """Ensure playhead is visible by scrolling if necessary."""
        if hasattr(self.parent(), 'ensureWidgetVisible'):
            playhead_x = int(self.time_to_pixel(self.playhead_position))
            margin = 100
            self.parent().ensureVisible(playhead_x, 0, margin, self.height())

    def get_previous_part_bpm(self, current_part) -> float:
        """Get BPM of the previous part."""
        try:
            if self.song_structure and self.song_structure.parts:
                part_index = self.song_structure.parts.index(current_part)
                if part_index > 0:
                    return self.song_structure.parts[part_index - 1].bpm
        except (ValueError, IndexError, AttributeError):
            pass
        return current_part.bpm

    def paintEvent(self, event):
        """Draw the master timeline."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw song structure parts as colored backgrounds
        if self.song_structure and hasattr(self.song_structure, 'parts') and self.song_structure.parts:
            try:
                self.draw_song_structure(painter, width, height)
            except Exception as e:
                print(f"Error drawing song structure: {e}")

        # Draw grid
        self.draw_grid(painter, width, height)

        # Draw playhead
        self.draw_playhead(painter, width, height)

    def draw_song_structure(self, painter, width, height):
        """Draw song structure parts as colored segments with labels."""
        try:
            for part in self.song_structure.parts:
                start_x = self.time_to_pixel(part.start_time)
                end_x = self.time_to_pixel(part.start_time + part.duration)

                if end_x < 0 or start_x > width:
                    continue

                # Draw colored background
                color = QColor(part.color)
                color.setAlpha(100)
                painter.fillRect(int(start_x), 0, int(end_x - start_x), height, color)

                # Draw part border
                border_pen = QPen(QColor(part.color), 2)
                painter.setPen(border_pen)
                painter.drawRect(int(start_x), 0, int(end_x - start_x), height)

                # Draw part name if there's enough space
                if end_x - start_x > 50:
                    painter.setPen(QPen(QColor("#000000"), 1))
                    font = painter.font()
                    font.setPointSize(9)
                    font.setBold(True)
                    painter.setFont(font)

                    text_rect = QRectF(start_x + 5, 5, end_x - start_x - 10, 20)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft, part.name)

                    # Draw BPM info
                    font.setPointSize(8)
                    font.setBold(False)
                    painter.setFont(font)
                    bpm_text = f"{part.bpm} BPM"
                    if part.transition == "gradual":
                        prev_bpm = self.get_previous_part_bpm(part)
                        if prev_bpm != part.bpm:
                            bpm_text = f"{prev_bpm}->{part.bpm} BPM"

                    bpm_rect = QRectF(start_x + 5, 25, end_x - start_x - 10, 15)
                    painter.drawText(bpm_rect, Qt.AlignmentFlag.AlignLeft, bpm_text)
        except Exception as e:
            print(f"Error in draw_song_structure: {e}")

    def draw_grid(self, painter, width, height):
        """Draw time-based grid with beat lines."""
        has_structure = (self.song_structure and
                        hasattr(self.song_structure, 'parts') and self.song_structure.parts)
        if has_structure:
            try:
                bar_pen = QPen(QColor("#666666"), 1)
                beat_pen = QPen(QColor("#aaaaaa"), 1)

                num_parts = len(self.song_structure.parts)
                for part_idx, part in enumerate(self.song_structure.parts):
                    beats_per_bar = self._get_beats_per_bar(part.signature)
                    total_beats_in_part = int(part.num_bars * beats_per_bar)
                    seconds_per_beat = 60.0 / part.bpm

                    is_last_part = (part_idx == num_parts - 1)
                    max_beat_index = total_beats_in_part if is_last_part else total_beats_in_part - 1

                    for beat_index in range(max_beat_index + 1):
                        beat_time = part.start_time + (beat_index * seconds_per_beat)
                        beat_x = self.time_to_pixel(beat_time)
                        beat_x_rounded = round(beat_x)

                        if 0 <= beat_x_rounded <= width:
                            is_bar_line = (beat_index % beats_per_bar == 0)
                            painter.setPen(bar_pen if is_bar_line else beat_pen)
                            painter.drawLine(beat_x_rounded, 0, beat_x_rounded, height)

            except Exception as e:
                import traceback
                print(f"Error in draw_grid: {e}")
                traceback.print_exc()
                self.draw_basic_grid(painter, width, height)
        else:
            self.draw_basic_grid(painter, width, height)

    def draw_playhead(self, painter, width, height):
        """Draw enhanced playhead with triangle."""
        try:
            playhead_x = self.time_to_pixel(self.playhead_position)
            playhead_x_rounded = round(playhead_x)

            if 0 <= playhead_x_rounded <= width:
                # Playhead line
                playhead_pen = QPen(QColor("#FF4444"), 2)
                painter.setPen(playhead_pen)
                painter.drawLine(playhead_x_rounded, 0, playhead_x_rounded, height)

                # Playhead triangle at top
                triangle_size = 8
                triangle = QPolygon([
                    QPoint(playhead_x_rounded, 0),
                    QPoint(playhead_x_rounded - triangle_size, triangle_size),
                    QPoint(playhead_x_rounded + triangle_size, triangle_size)
                ])

                painter.setBrush(QBrush(QColor("#FF4444")))
                painter.drawPolygon(triangle)
        except (AttributeError, TypeError):
            super().draw_playhead(painter, width, height)

    def _get_beats_per_bar(self, signature: str) -> float:
        """Calculate beats per bar from time signature."""
        try:
            numerator, denominator = map(int, signature.split('/'))
            return (numerator * 4) / denominator
        except (ValueError, ZeroDivisionError):
            return 4.0


class MasterTimelineContainer(QWidget):
    """Container for master timeline with label and info display."""

    playhead_moved = pyqtSignal(float)
    scroll_position_changed = pyqtSignal(int)
    zoom_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(95)
        self.setMaximumHeight(100)

        # Top row with timeline label and info
        top_row_layout = QHBoxLayout()

        # Timeline label (matches lane control width)
        timeline_label = QWidget()
        timeline_label.setFixedWidth(320)
        label_layout = QHBoxLayout(timeline_label)
        master_label = QLabel("Master Timeline")
        master_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        label_layout.addWidget(master_label)
        label_layout.addStretch()

        # Info display widget
        self.info_widget = QLabel()
        self.info_widget.setStyleSheet("color: #333; font-size: 10px; font-weight: bold;")
        self.info_widget.setText("Time: 0.00s | BPM: 120.0 | Zoom: 1.0x")

        top_row_layout.addWidget(timeline_label)
        top_row_layout.addWidget(self.info_widget, 1)

        # Bottom row with scrollable timeline
        bottom_row_layout = QHBoxLayout()

        # Empty space to align with lane controls
        spacer_widget = QWidget()
        spacer_widget.setFixedWidth(320)

        # Scrollable timeline area
        self.timeline_scroll = QScrollArea()
        self.timeline_widget = MasterTimelineWidget()
        self.timeline_widget.playhead_moved.connect(self.playhead_moved.emit)
        self.timeline_widget.zoom_changed.connect(self.zoom_changed.emit)
        self.timeline_widget.playhead_moved.connect(self.update_info_display)

        self.timeline_scroll.setWidget(self.timeline_widget)
        self.timeline_scroll.setWidgetResizable(False)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Connect scroll events
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(
            self.scroll_position_changed.emit)

        bottom_row_layout.addWidget(spacer_widget)
        bottom_row_layout.addWidget(self.timeline_scroll, 1)

        # Add both rows to the main layout
        layout.addLayout(top_row_layout)
        layout.addLayout(bottom_row_layout)

    def update_info_display(self, position: float):
        """Update the info display with current values."""
        current_bpm = self.timeline_widget.get_current_bpm()
        zoom_factor = self.timeline_widget.zoom_factor

        # Get current song part if available
        part_info = ""
        if self.timeline_widget.song_structure:
            current_part = self.timeline_widget.song_structure.get_part_at_time(position)
            if current_part:
                part_info = f" | Part: {current_part.name}"

        info_text = f"Time: {position:.2f}s | BPM: {current_bpm:.1f} | Zoom: {zoom_factor:.1f}x{part_info}"
        self.info_widget.setText(info_text)

    def set_bpm(self, bpm: float):
        """Set BPM for timeline calculations."""
        self.timeline_widget.set_bpm(bpm)

    def set_playhead_position(self, position: float):
        """Set playhead position."""
        self.timeline_widget.set_playhead_position(position)
        self.update_info_display(position)

    def set_snap_to_grid(self, snap: bool):
        """Set snap to grid for playhead."""
        self.timeline_widget.set_snap_to_grid(snap)

    def sync_scroll_position(self, position: int):
        """Sync scroll position with other timelines."""
        self.timeline_scroll.horizontalScrollBar().setValue(position)

    def set_zoom_factor(self, zoom_factor: float):
        """Set zoom factor for timeline."""
        self.timeline_widget.zoom_factor = zoom_factor
        self.timeline_widget.update_timeline_width()
        self.timeline_widget.update()
