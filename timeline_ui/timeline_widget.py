# timeline_ui/timeline_widget.py
# Base timeline widget with grid drawing and snap functionality
# Adapted from midimaker_and_show_structure/ui/lane_widget.py

import json
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QWheelEvent, QBrush


class TimelineWidget(QWidget):
    """Base timeline widget with grid drawing and snap functionality.

    Provides time-based grid drawing, zoom, scroll, and playhead functionality.
    Can be subclassed for specific use cases (master timeline, lane timelines).
    """

    zoom_changed = pyqtSignal(float)  # Emits new zoom factor
    playhead_moved = pyqtSignal(float)  # Emits playhead position in seconds
    paste_requested = pyqtSignal(float)  # Emits time position when paste requested
    riff_dropped = pyqtSignal(str, float)  # Emits (riff_path, drop_time) when riff dropped

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bpm = 120.0
        self.zoom_factor = 1.0
        self.base_pixels_per_second = 60  # Base: 60 pixels per second
        self.pixels_per_second = self.base_pixels_per_second
        self.snap_to_grid = True
        self.playhead_position = 0.0  # Position in seconds
        self.dragging_playhead = False
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.song_structure = None

        # Sublane support
        self.num_sublanes = 1  # Number of sublanes (1-4)
        self.sublane_height = 60  # Height per sublane in pixels
        self.capabilities = None  # FixtureGroupCapabilities (for label drawing)

        # Drag-drop support for riffs
        self.setAcceptDrops(True)
        self._drag_preview_time = None  # Time position for drag preview
        self._drag_preview_length = None  # Length of riff being dragged (in beats)

        self.setMinimumHeight(60)
        self.update_timeline_width()
        self.setStyleSheet("background-color: #f8f8f8; border: 1px solid #ddd;")

    def update_timeline_width(self):
        """Update timeline width based on zoom level and song structure."""
        self.pixels_per_second = self.base_pixels_per_second * self.zoom_factor

        # Check if we have song structure to calculate width
        if self.song_structure and hasattr(self.song_structure, 'parts') and self.song_structure.parts:
            try:
                total_duration = self.song_structure.get_total_duration()
                new_width = max(2000, int(total_duration * self.pixels_per_second) + 100)
            except (AttributeError, ZeroDivisionError, TypeError):
                new_width = max(2000, int(60 * self.pixels_per_second))
        else:
            new_width = max(2000, int(60 * self.pixels_per_second))

        self.setMinimumWidth(new_width)

    def time_to_pixel(self, time: float) -> float:
        """Convert time in seconds to pixel position."""
        return time * self.pixels_per_second

    def pixel_to_time(self, pixel: float) -> float:
        """Convert pixel position to time in seconds."""
        return pixel / self.pixels_per_second

    def set_song_structure(self, song_structure):
        """Set song structure for this timeline."""
        self.song_structure = song_structure
        self.update_timeline_width()
        self.update()

    def set_bpm(self, bpm: float):
        """Set BPM for grid calculations."""
        self.bpm = bpm
        self.update()

    def set_zoom_factor(self, zoom_factor: float):
        """Set zoom factor externally."""
        self.zoom_factor = zoom_factor
        self.update_timeline_width()
        self.update()

    def set_snap_to_grid(self, snap: bool):
        """Enable/disable snap to grid."""
        self.snap_to_grid = snap

    def set_playhead_position(self, position: float):
        """Set playhead position and update display."""
        self.playhead_position = position
        self.update()

    def get_current_bpm(self) -> float:
        """Get BPM at current playhead position."""
        if self.song_structure and hasattr(self.song_structure, 'get_bpm_at_time'):
            try:
                return self.song_structure.get_bpm_at_time(self.playhead_position)
            except (AttributeError, TypeError):
                pass
        return self.bpm

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel events for zooming."""
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Shift + wheel = zoom
            delta = event.angleDelta().y()
            zoom_in = delta > 0

            # Get mouse position for zoom center
            mouse_x = event.position().x()

            # Calculate time position at mouse cursor before zoom
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

                # Maintain mouse position after zoom
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

    def mousePressEvent(self, event):
        """Handle mouse press for playhead dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_playhead = True
            self.update_playhead_from_mouse(event.pos().x())

    def mouseMoveEvent(self, event):
        """Handle mouse move for playhead dragging."""
        if self.dragging_playhead:
            self.update_playhead_from_mouse(event.pos().x())

    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop playhead dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_playhead = False

    def contextMenuEvent(self, event):
        """Handle right-click context menu for paste."""
        from timeline_ui.effect_clipboard import has_clipboard_data

        menu = QMenu(self)

        # Calculate time at click position
        click_time = self.pixel_to_time(event.pos().x())
        if self.snap_to_grid:
            click_time = self.find_nearest_beat_time(click_time)

        # Add paste action if clipboard has data
        if has_clipboard_data():
            paste_action = menu.addAction("Paste Effect")
            paste_action.triggered.connect(lambda: self.paste_requested.emit(click_time))
        else:
            paste_action = menu.addAction("Paste Effect (no effect copied)")
            paste_action.setEnabled(False)

        menu.exec(event.globalPos())

    def update_playhead_from_mouse(self, x_pos: int):
        """Update playhead position based on mouse position."""
        time_position = self.pixel_to_time(x_pos)

        # Apply snap to grid if enabled
        if self.snap_to_grid:
            time_position = self.find_nearest_beat_time(time_position)

        time_position = max(0.0, time_position)
        self.playhead_position = time_position
        self.playhead_moved.emit(time_position)
        self.update()

    def find_nearest_beat_time(self, target_time: float) -> float:
        """Find the nearest beat position using song structure if available."""
        if not (self.song_structure and hasattr(self.song_structure, 'parts') and self.song_structure.parts):
            # Fallback to simple beat snapping with default BPM
            beat_duration = 60.0 / self.bpm
            nearest_beat = round(target_time / beat_duration)
            return nearest_beat * beat_duration

        # Use song structure's snap function
        return self.song_structure.find_nearest_beat_time(target_time)

    def draw_grid(self, painter, width, height):
        """Draw grid with song structure awareness."""
        if self.song_structure and hasattr(self.song_structure, 'parts') and self.song_structure.parts:
            try:
                self.draw_song_structure_grid(painter, width, height)
            except Exception as e:
                print(f"Error drawing song structure grid: {e}")
                self.draw_basic_grid(painter, width, height)
        else:
            self.draw_basic_grid(painter, width, height)

    def draw_song_structure_grid(self, painter, width, height):
        """Draw grid based on song structure."""
        beat_pen = QPen(QColor("#cccccc"), 1)
        bar_pen = QPen(QColor("#999999"), 2)
        part_pen = QPen(QColor("#666666"), 3)

        num_parts = len(self.song_structure.parts)
        for part_idx, part in enumerate(self.song_structure.parts):
            beats_per_bar = self._get_beats_per_bar(part.signature)
            total_beats_in_part = int(part.num_bars * beats_per_bar)
            seconds_per_beat = 60.0 / part.bpm

            # Draw part boundary
            start_x = round(self.time_to_pixel(part.start_time))
            if 0 <= start_x <= width:
                painter.setPen(part_pen)
                painter.drawLine(start_x, 0, start_x, height)

            # For all parts except the last, skip the final beat
            is_last_part = (part_idx == num_parts - 1)
            max_beat = total_beats_in_part if is_last_part else total_beats_in_part - 1

            # Draw beat lines within this part
            for beat_index in range(max_beat + 1):
                beat_time = part.start_time + (beat_index * seconds_per_beat)
                beat_x = round(self.time_to_pixel(beat_time))

                if 0 <= beat_x <= width:
                    painter.setPen(bar_pen if beat_index % beats_per_bar == 0 else beat_pen)
                    painter.drawLine(beat_x, 0, beat_x, height)

    def draw_basic_grid(self, painter, width, height):
        """Draw basic grid without song structure (time-based)."""
        beat_pen = QPen(QColor("#cccccc"), 1)
        bar_pen = QPen(QColor("#999999"), 2)

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

    def draw_playhead(self, painter, width, height):
        """Draw playhead at time position."""
        playhead_x = round(self.time_to_pixel(self.playhead_position))

        if 0 <= playhead_x <= width:
            playhead_pen = QPen(QColor("#FF4444"), 2)
            painter.setPen(playhead_pen)
            painter.drawLine(playhead_x, 0, playhead_x, height)

    def draw_song_structure_background(self, painter, width, height):
        """Draw song structure parts as subtle colored backgrounds."""
        if not (self.song_structure and hasattr(self.song_structure, 'parts') and self.song_structure.parts):
            return

        try:
            for part in self.song_structure.parts:
                start_x = self.time_to_pixel(part.start_time)
                end_x = self.time_to_pixel(part.start_time + part.duration)

                if end_x < 0 or start_x > width:
                    continue

                # Draw colored background with lower alpha for subtle effect
                color = QColor(part.color)
                color.setAlpha(40)
                painter.fillRect(int(start_x), 0, int(end_x - start_x), height, color)

        except Exception as e:
            print(f"Error drawing song structure background: {e}")

    def draw_sublane_separators(self, painter, width, height):
        """Draw horizontal lines separating sublanes."""
        if self.num_sublanes <= 1:
            return

        separator_pen = QPen(QColor("#666666"), 1, Qt.PenStyle.DashLine)
        painter.setPen(separator_pen)

        for i in range(1, self.num_sublanes):
            y = i * self.sublane_height
            painter.drawLine(0, int(y), width, int(y))

    def draw_sublane_labels(self, painter, width, height):
        """Draw sublane type labels on the left side of each row."""
        if self.num_sublanes <= 1 or not self.capabilities:
            return

        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import QRect

        # Get sublane types in order
        sublane_types = []
        if self.capabilities.has_dimmer:
            sublane_types.append(("Dimmer", QColor(255, 200, 100)))
        if self.capabilities.has_colour:
            sublane_types.append(("Colour", QColor(100, 255, 150)))
        if self.capabilities.has_movement:
            sublane_types.append(("Movement", QColor(100, 150, 255)))
        if self.capabilities.has_special:
            sublane_types.append(("Special", QColor(200, 100, 255)))

        # Set font for labels
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)

        # Draw each label
        for i, (label, color) in enumerate(sublane_types):
            y_offset = i * self.sublane_height

            # Calculate text size
            metrics = painter.fontMetrics()
            text_width = metrics.horizontalAdvance(label)
            text_height = metrics.height()

            # Position at left with padding
            x_pos = 4
            y_pos = y_offset + (self.sublane_height + text_height) // 2 - 3
            padding = 3

            # Draw semi-transparent colored background
            bg_rect = QRect(x_pos - padding, y_offset + 2,
                           text_width + 2 * padding, text_height + padding)
            bg_color = QColor(color)
            bg_color.setAlpha(100)
            painter.setBrush(bg_color)
            painter.setPen(QPen(color.darker(130), 1))
            painter.drawRoundedRect(bg_rect, 2, 2)

            # Draw text in dark color for contrast
            painter.setPen(QPen(QColor(40, 40, 40)))
            painter.drawText(x_pos, y_pos, label)

    def paintEvent(self, event):
        """Draw the timeline."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw song structure backgrounds first (subtle colors)
        self.draw_song_structure_background(painter, width, height)

        # Draw grid
        self.draw_grid(painter, width, height)

        # Draw sublane separators
        self.draw_sublane_separators(painter, width, height)

        # Draw sublane labels
        self.draw_sublane_labels(painter, width, height)

        # Draw drag preview (if dragging a riff)
        self.draw_drag_preview(painter, width, height)

        # Draw playhead
        self.draw_playhead(painter, width, height)

    def _get_beats_per_bar(self, signature: str) -> float:
        """Calculate beats per bar from time signature."""
        try:
            numerator, denominator = map(int, signature.split('/'))
            return (numerator * 4) / denominator
        except (ValueError, ZeroDivisionError):
            return 4.0

    # =========================================================================
    # DRAG-DROP SUPPORT FOR RIFFS
    # =========================================================================

    def dragEnterEvent(self, event):
        """Handle drag enter - accept riff drops."""
        if event.mimeData().hasFormat("application/x-qlc-riff"):
            event.acceptProposedAction()

            # Parse riff data for preview
            try:
                riff_data = json.loads(event.mimeData().data("application/x-qlc-riff").data().decode())
                self._drag_preview_length = riff_data.get("length_beats", 4.0)
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._drag_preview_length = 4.0

            self._update_drag_preview(event.position().x())
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move - update preview position."""
        if event.mimeData().hasFormat("application/x-qlc-riff"):
            event.acceptProposedAction()
            self._update_drag_preview(event.position().x())
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave - clear preview."""
        self._drag_preview_time = None
        self._drag_preview_length = None
        self.update()

    def dropEvent(self, event):
        """Handle drop - emit riff_dropped signal."""
        if event.mimeData().hasFormat("application/x-qlc-riff"):
            try:
                riff_data = json.loads(event.mimeData().data("application/x-qlc-riff").data().decode())
                riff_path = riff_data.get("path", "")

                # Calculate drop time with snap
                drop_time = self.pixel_to_time(event.position().x())
                if self.snap_to_grid:
                    drop_time = self.find_nearest_beat_time(drop_time)
                drop_time = max(0.0, drop_time)

                # Emit signal for parent to handle
                self.riff_dropped.emit(riff_path, drop_time)

                event.acceptProposedAction()
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                print(f"Error processing dropped riff: {e}")
                event.ignore()
        else:
            event.ignore()

        # Clear preview
        self._drag_preview_time = None
        self._drag_preview_length = None
        self.update()

    def _update_drag_preview(self, x_pos: float):
        """Update drag preview position."""
        drop_time = self.pixel_to_time(x_pos)
        if self.snap_to_grid:
            drop_time = self.find_nearest_beat_time(drop_time)
        self._drag_preview_time = max(0.0, drop_time)
        self.update()

    def _get_riff_duration_seconds(self, length_beats: float) -> float:
        """Calculate riff duration in seconds based on current BPM."""
        bpm = self.get_current_bpm()
        return length_beats * 60.0 / bpm

    def draw_drag_preview(self, painter, width, height):
        """Draw preview rectangle during riff drag."""
        if self._drag_preview_time is None or self._drag_preview_length is None:
            return

        # Calculate preview rectangle
        start_x = self.time_to_pixel(self._drag_preview_time)
        duration_secs = self._get_riff_duration_seconds(self._drag_preview_length)
        end_x = self.time_to_pixel(self._drag_preview_time + duration_secs)

        # Draw semi-transparent blue rectangle
        preview_color = QColor(0, 120, 215, 80)
        border_color = QColor(0, 120, 215, 200)

        painter.setBrush(QBrush(preview_color))
        painter.setPen(QPen(border_color, 2, Qt.PenStyle.DashLine))
        painter.drawRect(int(start_x), 2, int(end_x - start_x), height - 4)
