# timeline_ui/light_block_widget.py
# Visual widget for light effect blocks on timeline
# Adapted from midimaker_and_show_structure/ui/midi_block_widget.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QMouseEvent
from config.models import LightBlock


class LightBlockWidget(QWidget):
    """Visual representation of a light effect block on the timeline.

    Supports dragging to move, edge dragging to resize, and double-click to edit.
    """

    remove_requested = pyqtSignal(object)  # Emits self when delete requested
    position_changed = pyqtSignal(object, float)  # Emits (self, new_start_time)
    duration_changed = pyqtSignal(object, float)  # Emits (self, new_duration)

    RESIZE_HANDLE_WIDTH = 8  # Pixels for resize handle area

    def __init__(self, block: LightBlock, timeline_widget, parent=None):
        """Create a light block widget.

        Args:
            block: LightBlock data model
            timeline_widget: Parent TimelineWidget for coordinate conversion
            parent: Parent widget (defaults to timeline_widget)
        """
        super().__init__(parent or timeline_widget)
        self.block = block
        self.timeline_widget = timeline_widget

        self.dragging = False
        self.resizing_left = False
        self.resizing_right = False
        self.drag_start_pos = None
        self.drag_start_time = None
        self.drag_start_duration = None
        self.snap_to_grid = True

        self.setMinimumHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setup_ui()
        self.update_position()

    def setup_ui(self):
        """Set up the block's visual appearance."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(1)

        # Effect name label
        self.effect_label = QLabel(self._get_display_name())
        self.effect_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px;")
        self.effect_label.setWordWrap(True)
        layout.addWidget(self.effect_label)

        # Parameters label
        self.params_label = QLabel(self._format_parameters())
        self.params_label.setStyleSheet("color: #ddd; font-size: 9px;")
        layout.addWidget(self.params_label)

        layout.addStretch()

    def _get_display_name(self) -> str:
        """Get display name for the block."""
        if self.block.effect_name:
            # Show just the function name, not the module
            parts = self.block.effect_name.split('.')
            return parts[-1] if parts else self.block.effect_name
        return "No Effect"

    def _format_parameters(self) -> str:
        """Format block parameters for display."""
        params = self.block.parameters
        parts = []
        if params.get('speed') and params['speed'] != '1':
            parts.append(f"×{params['speed']}")
        if params.get('intensity'):
            parts.append(f"I:{params['intensity']}")
        return " ".join(parts) if parts else ""

    def update_display(self):
        """Update the display after block data changes."""
        self.effect_label.setText(self._get_display_name())
        self.params_label.setText(self._format_parameters())
        self.update()

    def update_position(self):
        """Update widget position and size based on block data."""
        x = int(self.timeline_widget.time_to_pixel(self.block.start_time))
        width = int(self.timeline_widget.time_to_pixel(self.block.duration))
        width = max(20, width)  # Minimum width

        # Height: fill most of timeline, with margins
        height = self.timeline_widget.height() - 10
        height = max(30, height)

        self.setGeometry(x, 5, width, height)

    def set_snap_to_grid(self, snap: bool):
        """Enable/disable snap to grid."""
        self.snap_to_grid = snap

    def paintEvent(self, event):
        """Draw the block with color based on effect."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Determine color based on effect
        color = self._get_block_color()

        # Draw background
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(120), 2))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

        # Draw resize handles (subtle indicators)
        handle_color = QColor(255, 255, 255, 80)
        painter.setBrush(QBrush(handle_color))
        painter.setPen(Qt.PenStyle.NoPen)

        # Left handle
        painter.drawRect(0, 0, 3, self.height())
        # Right handle
        painter.drawRect(self.width() - 3, 0, 3, self.height())

    def _get_block_color(self) -> QColor:
        """Get color for block based on effect or parameters."""
        # Use color from parameters if set
        if self.block.parameters.get('color'):
            return QColor(self.block.parameters['color'])

        # Default colors based on effect type
        if not self.block.effect_name:
            return QColor("#666666")

        effect_lower = self.block.effect_name.lower()
        if 'static' in effect_lower:
            return QColor("#4CAF50")  # Green
        elif 'fade' in effect_lower:
            return QColor("#2196F3")  # Blue
        elif 'pulse' in effect_lower or 'strobe' in effect_lower:
            return QColor("#FF9800")  # Orange
        elif 'wave' in effect_lower:
            return QColor("#9C27B0")  # Purple
        elif 'rainbow' in effect_lower or 'color' in effect_lower:
            return QColor("#E91E63")  # Pink
        else:
            return QColor("#607D8B")  # Blue-gray

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for dragging/resizing."""
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.pos().x()

            # Check if clicking on resize handles
            if x <= self.RESIZE_HANDLE_WIDTH:
                self.resizing_left = True
            elif x >= self.width() - self.RESIZE_HANDLE_WIDTH:
                self.resizing_right = True
            else:
                self.dragging = True

            self.drag_start_pos = event.globalPosition().toPoint()
            self.drag_start_time = self.block.start_time
            self.drag_start_duration = self.block.duration

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for dragging/resizing."""
        if not (self.dragging or self.resizing_left or self.resizing_right):
            # Update cursor based on position
            x = event.pos().x()
            if x <= self.RESIZE_HANDLE_WIDTH or x >= self.width() - self.RESIZE_HANDLE_WIDTH:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            return

        current_pos = event.globalPosition().toPoint()
        delta_pixels = current_pos.x() - self.drag_start_pos.x()
        delta_time = delta_pixels / self.timeline_widget.pixels_per_second

        if self.dragging:
            # Move the block
            new_time = max(0.0, self.drag_start_time + delta_time)

            if self.snap_to_grid:
                new_time = self.timeline_widget.find_nearest_beat_time(new_time)

            self.block.start_time = new_time
            self.update_position()
            self.position_changed.emit(self, new_time)

        elif self.resizing_left:
            # Resize from left edge (changes start time and duration)
            new_start = self.drag_start_time + delta_time
            new_duration = self.drag_start_duration - delta_time

            if self.snap_to_grid:
                new_start = self.timeline_widget.find_nearest_beat_time(new_start)
                new_duration = (self.drag_start_time + self.drag_start_duration) - new_start

            if new_start >= 0 and new_duration >= 0.1:
                self.block.start_time = new_start
                self.block.duration = new_duration
                self.update_position()
                self.position_changed.emit(self, new_start)
                self.duration_changed.emit(self, new_duration)

        elif self.resizing_right:
            # Resize from right edge (changes duration only)
            new_duration = self.drag_start_duration + delta_time

            if self.snap_to_grid:
                new_end = self.block.start_time + new_duration
                new_end = self.timeline_widget.find_nearest_beat_time(new_end)
                new_duration = new_end - self.block.start_time

            if new_duration >= 0.1:
                self.block.duration = new_duration
                self.update_position()
                self.duration_changed.emit(self, new_duration)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop dragging/resizing."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing_left = False
            self.resizing_right = False
            self.drag_start_pos = None

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click to open effect editor."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_effect_dialog()

    def contextMenuEvent(self, event):
        """Handle right-click context menu."""
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)

        edit_action = menu.addAction("Edit Effect...")
        edit_action.triggered.connect(self.open_effect_dialog)

        menu.addSeparator()

        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.remove_requested.emit(self))

        menu.exec(event.globalPos())

    def open_effect_dialog(self):
        """Open the effect editor dialog."""
        from .effect_block_dialog import EffectBlockDialog
        dialog = EffectBlockDialog(self.block, parent=self)
        if dialog.exec():
            self.update_display()

    def keyPressEvent(self, event):
        """Handle key press for deletion."""
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.remove_requested.emit(self)
        else:
            super().keyPressEvent(event)
