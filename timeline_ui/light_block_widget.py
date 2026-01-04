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
    block_edited = pyqtSignal()  # Emitted when block content is edited (for auto-save)

    RESIZE_HANDLE_WIDTH = 8  # Pixels for resize handle area

    def __init__(self, block: LightBlock, timeline_widget, lane_widget, parent=None):
        """Create a light block widget.

        Args:
            block: LightBlock data model
            timeline_widget: Parent TimelineWidget for coordinate conversion
            lane_widget: Parent LightLaneWidget for capability/sublane info
            parent: Parent widget (defaults to timeline_widget)
        """
        super().__init__(parent or timeline_widget)
        self.block = block
        self.timeline_widget = timeline_widget
        self.lane_widget = lane_widget

        self.dragging = False
        self.resizing_left = False
        self.resizing_right = False
        self.drag_start_pos = None
        self.drag_start_time = None
        self.drag_start_duration = None
        self.snap_to_grid = True
        self.shift_drag_copying = False  # True when shift+drag to copy

        # Sublane interaction state
        self.clicked_sublane_type = None  # Which sublane type was clicked (if any)
        self.selected_sublane_type = None  # Which sublane type is currently selected (for highlighting)
        self.selected_sublane_block = None  # Which specific sublane block is selected (CHANGED: now a reference)
        self.resizing_sublane = None  # Which sublane is being resized (CHANGED: now stores block reference)
        self.resizing_sublane_edge = None  # 'left' or 'right'
        self.dragging_sublane = None  # Which sublane is being dragged (CHANGED: now stores block reference)
        self.drag_start_sublane_start = None  # Start time of sublane being resized/dragged
        self.drag_start_sublane_end = None  # End time of sublane being resized/dragged

        # Drag-to-create state
        self.creating_sublane = None  # Which sublane type is being created
        self.create_start_time = None  # Start time for new block being created
        self.create_end_time = None  # End time for new block being created (updated during drag)

        # Overlap feedback state
        self.overlap_detected = False  # True when current drag/resize would create overlap

        # Intensity handle state (for dimmer blocks)
        self.dragging_intensity_handle = None  # Which dimmer block's intensity handle is being dragged
        self.drag_start_intensity = None  # Initial intensity value when drag started

        self.setMinimumHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)  # Enable mouse tracking for cursor updates on hover

        self.setup_ui()
        self.update_position()

    def setup_ui(self):
        """Set up the block's visual appearance."""
        # No UI widgets needed - we'll draw everything in paintEvent
        pass

    def _get_display_name(self) -> str:
        """Get display name for the block."""
        name = "No Effect"
        if self.block.effect_name:
            # Show just the function name, not the module
            parts = self.block.effect_name.split('.')
            name = parts[-1] if parts else self.block.effect_name

        # Add asterisk if modified
        if self.block.modified:
            name += " *"

        return name

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
        self.update()  # Trigger repaint

    def update_position(self):
        """Update widget position and size based on block envelope data."""
        # Calculate position based on envelope start/end times
        x = int(self.timeline_widget.time_to_pixel(self.block.start_time))
        duration = self.block.end_time - self.block.start_time
        width = int(self.timeline_widget.time_to_pixel(duration))
        width = max(20, width)  # Minimum width

        # Height: fill entire timeline height (spans all sublanes)
        height = self.timeline_widget.height()

        # Position at top of timeline (y=0)
        self.setGeometry(x, 0, width, height)

    def set_snap_to_grid(self, snap: bool):
        """Enable/disable snap to grid."""
        self.snap_to_grid = snap

    def pixel_to_time(self, pixel_x):
        """Convert pixel X position (relative to envelope) to absolute time."""
        envelope_start_pixel = self.timeline_widget.time_to_pixel(self.block.start_time)
        absolute_pixel = envelope_start_pixel + pixel_x
        return self.timeline_widget.pixel_to_time(absolute_pixel)

    def paintEvent(self, event):
        """Draw the effect envelope and sublane blocks."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw effect envelope (subtle background)
        self._draw_envelope(painter)

        # Draw individual sublane blocks
        self._draw_sublane_blocks(painter)

        # Draw resize handles on envelope
        self._draw_resize_handles(painter)

        # Draw preview of block being created
        if self.creating_sublane and self.create_start_time is not None and self.create_end_time is not None:
            self._draw_create_preview(painter)

        # Draw effect name label LAST (on top of everything)
        self._draw_effect_label(painter)

    def _draw_envelope(self, painter):
        """Draw the effect envelope as a subtle border/background."""
        # Subtle background color
        envelope_color = QColor(60, 60, 60, 100)
        painter.setBrush(QBrush(envelope_color))

        # Border color - thicker dashed line
        border_color = QColor(150, 150, 150, 200)
        pen = QPen(border_color, 2, Qt.PenStyle.DashLine)
        pen.setDashPattern([4, 3])  # Custom dash pattern: 4px dash, 3px gap
        painter.setPen(pen)

        # Draw envelope rectangle
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 3, 3)

    def _draw_effect_label(self, painter):
        """Draw effect name label on top of everything."""
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import QRect

        # Set font
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        # Get text
        text = self._get_display_name()

        # Calculate text size
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        # Position at top-left with padding
        x_pos = 6
        y_pos = 6
        padding = 4

        # Draw semi-transparent dark background behind text
        bg_rect = QRect(x_pos - padding, y_pos - padding,
                       text_width + 2 * padding, text_height + 2 * padding)
        painter.setBrush(QBrush(QColor(30, 30, 30, 200)))  # Dark gray, semi-transparent
        painter.setPen(QPen(QColor(100, 100, 100), 1))  # Subtle border
        painter.drawRoundedRect(bg_rect, 3, 3)

        # Draw text in white
        painter.setPen(QPen(QColor(255, 255, 255)))  # White text
        painter.drawText(x_pos, y_pos + text_height - 3, text)

    def _draw_sublane_blocks(self, painter):
        """Draw individual sublane blocks within the envelope."""
        sublane_height = self.lane_widget.sublane_height

        # Check if fixture has dimmer capability
        has_dimmer = self.lane_widget.capabilities.has_dimmer if hasattr(self.lane_widget, 'capabilities') and self.lane_widget.capabilities else True
        has_colour = self.lane_widget.capabilities.has_colour if hasattr(self.lane_widget, 'capabilities') and self.lane_widget.capabilities else False

        # Draw dimmer blocks (iterate through list)
        for dimmer_block in self.block.dimmer_blocks:
            # Use orange/amber color if controlling RGB instead of dimmer
            if not has_dimmer and has_colour:
                dimmer_color = QColor(255, 140, 0)  # Orange (RGB control mode)
            else:
                dimmer_color = QColor(255, 200, 100)  # Warm yellow (normal dimmer)

            self._draw_sublane_block(
                painter,
                dimmer_block,
                "dimmer",
                dimmer_color,
                sublane_height
            )

        # Draw colour blocks (iterate through list)
        for colour_block in self.block.colour_blocks:
            color = self._get_colour_block_color(colour_block)
            self._draw_sublane_block(
                painter,
                colour_block,
                "colour",
                color,
                sublane_height
            )

        # Draw movement blocks (iterate through list)
        for movement_block in self.block.movement_blocks:
            self._draw_sublane_block(
                painter,
                movement_block,
                "movement",
                QColor(100, 150, 255),  # Blue
                sublane_height
            )

        # Draw special blocks (iterate through list)
        for special_block in self.block.special_blocks:
            self._draw_sublane_block(
                painter,
                special_block,
                "special",
                QColor(200, 100, 255),  # Purple
                sublane_height
            )

    def _draw_sublane_block(self, painter, sublane_block, sublane_type, color, sublane_height):
        """Draw a single sublane block."""
        # Get sublane row index
        sublane_index = self.lane_widget.get_sublane_index(sublane_type)

        # Calculate y position for this sublane
        y_offset = sublane_index * sublane_height

        # Calculate x position and width based on block times relative to envelope
        block_start_pixel = self.timeline_widget.time_to_pixel(sublane_block.start_time)
        block_end_pixel = self.timeline_widget.time_to_pixel(sublane_block.end_time)
        envelope_start_pixel = self.timeline_widget.time_to_pixel(self.block.start_time)

        x_offset = block_start_pixel - envelope_start_pixel
        width = block_end_pixel - block_start_pixel

        # Draw the sublane block
        painter.setBrush(QBrush(color))

        # Use thicker, brighter border if THIS SPECIFIC BLOCK is selected (CHANGED: check block reference)
        is_selected = (sublane_block is self.selected_sublane_block)
        if is_selected:
            painter.setPen(QPen(QColor(255, 255, 255), 3))  # Bright white border when selected
        else:
            painter.setPen(QPen(color.darker(130), 2))

        # Draw with some margin from edges
        margin = 2
        painter.drawRoundedRect(
            int(x_offset + margin),
            int(y_offset + margin),
            int(width - 2 * margin),
            int(sublane_height - 2 * margin),
            3, 3
        )

        # Draw grid and intensity handle for dimmer blocks
        if sublane_type == "dimmer":
            self._draw_dimmer_block_grid(painter, sublane_block, x_offset, y_offset, width, sublane_height, margin)
            self._draw_intensity_handle(painter, sublane_block, x_offset, y_offset, width, sublane_height, margin)

            # Draw RGB icon if controlling RGB instead of dimmer
            has_dimmer = self.lane_widget.capabilities.has_dimmer if hasattr(self.lane_widget, 'capabilities') and self.lane_widget.capabilities else True
            has_colour = self.lane_widget.capabilities.has_colour if hasattr(self.lane_widget, 'capabilities') and self.lane_widget.capabilities else False
            if not has_dimmer and has_colour and width >= 40:
                self._draw_rgb_icon(painter, x_offset, y_offset, width, sublane_height, margin)

        # Draw grid for movement blocks (similar to dimmer blocks)
        if sublane_type == "movement":
            self._draw_movement_block_grid(painter, sublane_block, x_offset, y_offset, width, sublane_height, margin)

        # Draw text label if block is wide enough
        self._draw_sublane_block_label(painter, sublane_block, sublane_type, x_offset, y_offset, width, sublane_height, margin)

        # Draw resize handles if THIS SPECIFIC BLOCK is selected (CHANGED: check block reference)
        if is_selected:
            handle_color = QColor(255, 255, 255, 150)
            painter.setBrush(QBrush(handle_color))
            painter.setPen(Qt.PenStyle.NoPen)

            # Left handle
            painter.drawRect(int(x_offset + margin), int(y_offset + margin),
                           4, int(sublane_height - 2 * margin))
            # Right handle
            painter.drawRect(int(x_offset + width - margin - 4), int(y_offset + margin),
                           4, int(sublane_height - 2 * margin))

    def _draw_sublane_block_label(self, painter, sublane_block, sublane_type, x_offset, y_offset, width, sublane_height, margin):
        """Draw text label on sublane block if wide enough."""
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import QRect

        # Minimum width to show label (in pixels)
        MIN_WIDTH_FOR_LABEL = 60

        if width < MIN_WIDTH_FOR_LABEL:
            return  # Block too narrow, skip label

        # Sublane type labels
        sublane_labels = {
            "dimmer": "Dimmer",
            "colour": "Colour",
            "movement": "Movement",
            "special": "Special"
        }

        # Get label text
        label_text = sublane_labels.get(sublane_type, sublane_type.capitalize())

        # Get additional info if block is wide enough
        info_text = ""
        if width >= 100:  # Wide enough for additional info
            info_text = self._get_sublane_block_info(sublane_block, sublane_type)

        # Combine label and info
        if info_text:
            full_text = f"{label_text}: {info_text}"
        else:
            full_text = label_text

        # Set font
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)

        # Calculate text size
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(full_text)
        text_height = metrics.height()

        # Check if text fits within block width
        if text_width + 10 > width - 2 * margin:
            # Text too wide, try just the label without info
            full_text = label_text
            text_width = metrics.horizontalAdvance(full_text)
            if text_width + 10 > width - 2 * margin:
                return  # Even just label doesn't fit, skip

        # Calculate centered position
        text_x = int(x_offset + (width - text_width) / 2)
        text_y = int(y_offset + (sublane_height + text_height) / 2 - 2)

        # Draw text with dark outline for better visibility
        painter.setPen(QPen(QColor(40, 40, 40)))
        painter.drawText(text_x, text_y, full_text)

    def _draw_rgb_icon(self, painter, x_offset, y_offset, width, sublane_height, margin):
        """Draw small RGB icon in corner of dimmer block to indicate RGB control mode."""
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import QRect

        # Draw "RGB" text in top-right corner
        font = QFont()
        font.setPointSize(6)
        font.setBold(True)
        painter.setFont(font)

        icon_text = "RGB"
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(icon_text)
        text_height = metrics.height()

        # Position in top-right corner with padding
        icon_x = int(x_offset + width - text_width - 6)
        icon_y = int(y_offset + margin + text_height)

        # Draw semi-transparent background
        bg_rect = QRect(icon_x - 2, icon_y - text_height, text_width + 4, text_height + 2)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
        painter.drawRoundedRect(bg_rect, 2, 2)

        # Draw text
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(icon_x, icon_y, icon_text)

    def _draw_intensity_handle(self, painter, sublane_block, x_offset, y_offset, width, sublane_height, margin):
        """Draw intensity handle and darkened area above it for dimmer blocks."""
        try:
            # Get intensity (0-255)
            intensity = getattr(sublane_block, 'intensity', 255.0)

            # Calculate handle Y position (top=255, bottom=0)
            # Invert: higher intensity = higher position (toward top)
            usable_height = sublane_height - 2 * margin
            intensity_ratio = intensity / 255.0
            handle_y_offset = y_offset + margin + (usable_height * (1.0 - intensity_ratio))

            # Draw darkened overlay above the handle
            if intensity < 255:
                dark_overlay = QColor(0, 0, 0, 100)
                painter.setBrush(QBrush(dark_overlay))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(
                    int(x_offset + margin),
                    int(y_offset + margin),
                    int(width - 2 * margin),
                    int(handle_y_offset - (y_offset + margin))
                )

            # Draw intensity handle line
            handle_pen = QPen(QColor(255, 255, 255, 200), 2)
            painter.setPen(handle_pen)
            painter.drawLine(
                int(x_offset + margin),
                int(handle_y_offset),
                int(x_offset + width - margin),
                int(handle_y_offset)
            )

            # Draw intensity label if dragging this handle
            if hasattr(self, 'dragging_intensity_handle') and self.dragging_intensity_handle is sublane_block:
                from PyQt6.QtGui import QFont
                from PyQt6.QtCore import QRect

                # Draw intensity value label
                font = QFont()
                font.setPointSize(8)
                font.setBold(True)
                painter.setFont(font)

                intensity_text = f"{int(intensity)}"
                metrics = painter.fontMetrics()
                text_width = metrics.horizontalAdvance(intensity_text)
                text_height = metrics.height()

                # Position label near the handle
                label_x = int(x_offset + width / 2 - text_width / 2)
                label_y = int(handle_y_offset - 5)

                # Draw background
                bg_rect = QRect(label_x - 3, label_y - text_height, text_width + 6, text_height + 3)
                painter.setBrush(QBrush(QColor(40, 40, 40, 200)))
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawRoundedRect(bg_rect, 2, 2)

                # Draw text
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(label_x, label_y, intensity_text)

        except Exception as e:
            # Silently fail if handle cannot be drawn
            pass

    def _draw_dimmer_block_grid(self, painter, sublane_block, x_offset, y_offset, width, sublane_height, margin):
        """Draw beat grid lines inside dimmer block based on speed setting."""
        try:
            # Get speed setting
            effect_speed = getattr(sublane_block, 'effect_speed', '1')

            # Convert speed to multiplier
            if '/' in effect_speed:
                num, denom = map(int, effect_speed.split('/'))
                speed_multiplier = num / denom
            else:
                speed_multiplier = float(effect_speed)

            # Get BPM at block start time
            if hasattr(self.timeline_widget, 'song_structure') and self.timeline_widget.song_structure:
                part_at_block = self.timeline_widget.song_structure.get_part_at_time(sublane_block.start_time)
                if part_at_block:
                    bpm = part_at_block.bpm
                    # Parse time signature
                    numerator, denominator = map(int, part_at_block.signature.split('/'))
                    beats_per_bar = (numerator * 4) / denominator
                else:
                    bpm = 120
                    beats_per_bar = 4.0
            else:
                bpm = 120
                beats_per_bar = 4.0

            # Calculate time per step (in seconds)
            seconds_per_beat = 60.0 / bpm
            seconds_per_step = seconds_per_beat / speed_multiplier

            # Calculate block duration
            block_duration = sublane_block.end_time - sublane_block.start_time

            # Calculate number of steps
            num_steps = int(block_duration / seconds_per_step)

            # Draw grid lines (black for better visibility on yellow dimmer blocks)
            grid_pen = QPen(QColor(0, 0, 0, 120), 1, Qt.PenStyle.DotLine)
            painter.setPen(grid_pen)

            for step in range(1, num_steps):  # Skip first (start) and last (end)
                step_time = sublane_block.start_time + (step * seconds_per_step)
                step_pixel = self.timeline_widget.time_to_pixel(step_time)
                envelope_start_pixel = self.timeline_widget.time_to_pixel(self.block.start_time)

                x = step_pixel - envelope_start_pixel

                # Draw vertical line
                painter.drawLine(
                    int(x),
                    int(y_offset + margin),
                    int(x),
                    int(y_offset + sublane_height - margin)
                )
        except Exception as e:
            # Silently fail if grid cannot be drawn
            pass

    def _draw_movement_block_grid(self, painter, sublane_block, x_offset, y_offset, width, sublane_height, margin):
        """Draw beat grid lines inside movement block based on speed setting."""
        try:
            # Get speed setting (movement blocks now have effect_speed like dimmer blocks)
            effect_speed = getattr(sublane_block, 'effect_speed', '1')

            # Convert speed to multiplier
            if '/' in effect_speed:
                num, denom = map(int, effect_speed.split('/'))
                speed_multiplier = num / denom
            else:
                speed_multiplier = float(effect_speed)

            # Get BPM at block start time
            if hasattr(self.timeline_widget, 'song_structure') and self.timeline_widget.song_structure:
                part_at_block = self.timeline_widget.song_structure.get_part_at_time(sublane_block.start_time)
                if part_at_block:
                    bpm = part_at_block.bpm
                    # Parse time signature
                    numerator, denominator = map(int, part_at_block.signature.split('/'))
                    beats_per_bar = (numerator * 4) / denominator
                else:
                    bpm = 120
                    beats_per_bar = 4.0
            else:
                bpm = 120
                beats_per_bar = 4.0

            # Calculate time per step (in seconds)
            seconds_per_beat = 60.0 / bpm
            seconds_per_step = seconds_per_beat / speed_multiplier

            # Calculate block duration
            block_duration = sublane_block.end_time - sublane_block.start_time

            # Calculate number of steps
            num_steps = int(block_duration / seconds_per_step)

            # Draw grid lines (black like dimmer blocks for consistency)
            grid_pen = QPen(QColor(0, 0, 0, 120), 1, Qt.PenStyle.DotLine)
            painter.setPen(grid_pen)

            for step in range(1, num_steps):  # Skip first (start) and last (end)
                step_time = sublane_block.start_time + (step * seconds_per_step)
                step_pixel = self.timeline_widget.time_to_pixel(step_time)
                envelope_start_pixel = self.timeline_widget.time_to_pixel(self.block.start_time)

                x = step_pixel - envelope_start_pixel

                # Draw vertical line
                painter.drawLine(
                    int(x),
                    int(y_offset + margin),
                    int(x),
                    int(y_offset + sublane_height - margin)
                )
        except Exception as e:
            # Silently fail if grid cannot be drawn
            pass

    def _get_sublane_block_info(self, sublane_block, sublane_type):
        """Get short info text about sublane block content."""
        try:
            if sublane_type == "dimmer":
                # Show effect type and intensity
                intensity = int(sublane_block.intensity)
                effect_type = getattr(sublane_block, 'effect_type', 'static')
                # Capitalize first letter of effect type
                effect_display = effect_type.capitalize()
                return f"{effect_display} ({intensity})"
            elif sublane_type == "colour":
                # Show color mode or RGB values
                if hasattr(sublane_block, 'color_mode') and sublane_block.color_mode:
                    return sublane_block.color_mode
                return "RGB"
            elif sublane_type == "movement":
                # Show effect type (and pan/tilt for static)
                effect_type = getattr(sublane_block, 'effect_type', 'static')
                effect_display = effect_type.replace('_', ' ').title()
                if effect_type == "static" and hasattr(sublane_block, 'pan') and hasattr(sublane_block, 'tilt'):
                    pan = int(sublane_block.pan)
                    tilt = int(sublane_block.tilt)
                    return f"P{pan}/T{tilt}"
                return effect_display
            elif sublane_type == "special":
                # Show if any special effects are active
                active_effects = []
                if hasattr(sublane_block, 'gobo') and sublane_block.gobo:
                    active_effects.append("Gobo")
                if hasattr(sublane_block, 'prism') and sublane_block.prism:
                    active_effects.append("Prism")
                if active_effects:
                    return active_effects[0]  # Show first effect
                return "FX"
        except Exception:
            pass
        return ""

    def _draw_resize_handles(self, painter):
        """Draw resize handles on the envelope edges."""
        handle_color = QColor(255, 255, 255, 100)
        painter.setBrush(QBrush(handle_color))
        painter.setPen(Qt.PenStyle.NoPen)

        # Left handle
        painter.drawRect(0, 0, 3, self.height())
        # Right handle
        painter.drawRect(self.width() - 3, 0, 3, self.height())

    def _draw_create_preview(self, painter):
        """Draw preview of block being created."""
        sublane_height = self.lane_widget.sublane_height

        # Get sublane row index
        sublane_index = self.lane_widget.get_sublane_index(self.creating_sublane)
        y_offset = sublane_index * sublane_height

        # Calculate x position and width
        start_pixel = self.timeline_widget.time_to_pixel(self.create_start_time)
        end_pixel = self.timeline_widget.time_to_pixel(self.create_end_time)
        envelope_start_pixel = self.timeline_widget.time_to_pixel(self.block.start_time)

        x_offset = start_pixel - envelope_start_pixel
        width = end_pixel - start_pixel

        # Get color for this sublane type (semi-transparent)
        # Use RED if overlap detected (invalid placement)
        if self.overlap_detected:
            color = QColor(255, 0, 0, 150)  # RED - overlap warning!
            border_color = QColor(255, 100, 100, 200)
        else:
            # Normal colors
            if self.creating_sublane == "dimmer":
                color = QColor(255, 200, 100, 120)  # Yellow, semi-transparent
            elif self.creating_sublane == "colour":
                color = QColor(100, 255, 150, 120)  # Green, semi-transparent
            elif self.creating_sublane == "movement":
                color = QColor(100, 150, 255, 120)  # Blue, semi-transparent
            elif self.creating_sublane == "special":
                color = QColor(200, 100, 255, 120)  # Purple, semi-transparent
            else:
                color = QColor(150, 150, 150, 120)  # Gray, semi-transparent
            border_color = QColor(255, 255, 255, 150)

        # Draw preview block
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(border_color, 2, Qt.PenStyle.DashLine))

        margin = 2
        painter.drawRoundedRect(
            int(x_offset + margin),
            int(y_offset + margin),
            int(width - 2 * margin),
            int(sublane_height - 2 * margin),
            3, 3
        )

    def _get_colour_block_color(self, colour_block):
        """Get display color for colour block based on its RGB values.

        Args:
            colour_block: The ColourBlock instance to get color from

        Returns:
            QColor for display
        """
        if not colour_block:
            return QColor(100, 255, 150)  # Default green

        # Use RGB values if available
        if colour_block.red > 0 or colour_block.green > 0 or colour_block.blue > 0:
            return QColor(int(colour_block.red), int(colour_block.green), int(colour_block.blue))

        # Default to green
        return QColor(100, 255, 150)

    def _get_sublane_row_at_y(self, y_pos):
        """Detect which sublane row a Y position is in.

        Args:
            y_pos: Y coordinate relative to widget

        Returns:
            Sublane type string ("dimmer", "colour", "movement", "special") or None
        """
        sublane_height = self.lane_widget.sublane_height

        # Check each sublane row based on capabilities
        sublane_types = []
        # Show dimmer sublane if has dimmer OR colour (dimmer controls RGB for no-dimmer fixtures)
        if self.lane_widget.capabilities.has_dimmer or self.lane_widget.capabilities.has_colour:
            sublane_types.append("dimmer")
        if self.lane_widget.capabilities.has_colour:
            sublane_types.append("colour")
        if self.lane_widget.capabilities.has_movement:
            sublane_types.append("movement")
        if self.lane_widget.capabilities.has_special:
            sublane_types.append("special")

        for i, sublane_type in enumerate(sublane_types):
            y_min = i * sublane_height
            y_max = (i + 1) * sublane_height
            if y_min <= y_pos < y_max:
                return sublane_type

        return None

    def _get_sublane_block_at_pos(self, pos):
        """Detect which sublane block (if any) contains the given position.

        Args:
            pos: QPoint position relative to widget

        Returns:
            Tuple of (sublane_type, sublane_block) or (None, None)
        """
        sublane_height = self.lane_widget.sublane_height

        # Check all sublane blocks in all lists (CHANGED: iterate through lists)
        sublane_block_lists = [
            ("dimmer", self.block.dimmer_blocks),
            ("colour", self.block.colour_blocks),
            ("movement", self.block.movement_blocks),
            ("special", self.block.special_blocks)
        ]

        for sublane_type, sublane_blocks in sublane_block_lists:
            # Get sublane row index
            sublane_index = self.lane_widget.get_sublane_index(sublane_type)

            # Calculate y bounds for this sublane row
            y_min = sublane_index * sublane_height
            y_max = (sublane_index + 1) * sublane_height

            # Check if Y position is in this sublane row
            if not (y_min <= pos.y() <= y_max):
                continue

            # Check each block in this sublane row
            for sublane_block in sublane_blocks:
                # Calculate x bounds relative to envelope
                block_start_pixel = self.timeline_widget.time_to_pixel(sublane_block.start_time)
                block_end_pixel = self.timeline_widget.time_to_pixel(sublane_block.end_time)
                envelope_start_pixel = self.timeline_widget.time_to_pixel(self.block.start_time)

                x_min = block_start_pixel - envelope_start_pixel
                x_max = block_end_pixel - envelope_start_pixel

                # Check if position is within this sublane block
                if x_min <= pos.x() <= x_max:
                    return (sublane_type, sublane_block)

        return (None, None)

    def _is_on_intensity_handle(self, pos, sublane_type, sublane_block):
        """Check if position is on the intensity handle of a dimmer block.

        Args:
            pos: QPoint position relative to widget
            sublane_type: Type of sublane
            sublane_block: The sublane block object

        Returns:
            True if on intensity handle, False otherwise
        """
        if sublane_type != "dimmer":
            return False

        try:
            sublane_height = self.lane_widget.sublane_height
            margin = 2

            # Get sublane row index
            sublane_index = self.lane_widget.get_sublane_index(sublane_type)
            y_offset = sublane_index * sublane_height

            # Calculate handle Y position
            intensity = getattr(sublane_block, 'intensity', 255.0)
            usable_height = sublane_height - 2 * margin
            intensity_ratio = intensity / 255.0
            handle_y_offset = y_offset + margin + (usable_height * (1.0 - intensity_ratio))

            # Check if Y position is near the handle (within 8 pixels)
            handle_tolerance = 8
            if abs(pos.y() - handle_y_offset) <= handle_tolerance:
                # Also check X position is within block bounds
                block_start_pixel = self.timeline_widget.time_to_pixel(sublane_block.start_time)
                block_end_pixel = self.timeline_widget.time_to_pixel(sublane_block.end_time)
                envelope_start_pixel = self.timeline_widget.time_to_pixel(self.block.start_time)

                x_min = block_start_pixel - envelope_start_pixel
                x_max = block_end_pixel - envelope_start_pixel

                if x_min <= pos.x() <= x_max:
                    return True

        except Exception:
            pass

        return False

    def _is_on_sublane_block_edge(self, pos, sublane_type, sublane_block):
        """Check if position is on the left or right edge of a sublane block.

        Args:
            pos: QPoint position relative to widget
            sublane_type: Type of sublane ("dimmer", "colour", etc.)
            sublane_block: The sublane block object

        Returns:
            'left', 'right', or None
        """
        # Calculate x bounds relative to envelope
        block_start_pixel = self.timeline_widget.time_to_pixel(sublane_block.start_time)
        block_end_pixel = self.timeline_widget.time_to_pixel(sublane_block.end_time)
        envelope_start_pixel = self.timeline_widget.time_to_pixel(self.block.start_time)

        x_min = block_start_pixel - envelope_start_pixel
        x_max = block_end_pixel - envelope_start_pixel

        # Check edges (8 pixel handle width)
        if abs(pos.x() - x_min) <= self.RESIZE_HANDLE_WIDTH:
            return 'left'
        elif abs(pos.x() - x_max) <= self.RESIZE_HANDLE_WIDTH:
            return 'right'

        return None

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
        """Handle mouse press for dragging/resizing envelope or sublane blocks."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()

            # Check if Shift is held for copy operation
            shift_held = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

            # First, check if clicking on a sublane block
            sublane_type, sublane_block = self._get_sublane_block_at_pos(pos)

            if sublane_block is not None:
                # Clicked on a sublane block - select it (CHANGED: store block reference)
                self.clicked_sublane_type = sublane_type
                self.selected_sublane_type = sublane_type
                self.selected_sublane_block = sublane_block  # Store block reference
                self.update()  # Trigger repaint to show selection

                # Store initial sublane times for resizing
                self.drag_start_sublane_start = sublane_block.start_time
                self.drag_start_sublane_end = sublane_block.end_time

                # Check if clicking on intensity handle (for dimmer blocks)
                if self._is_on_intensity_handle(pos, sublane_type, sublane_block):
                    # Start dragging intensity handle
                    self.dragging_intensity_handle = sublane_block
                    self.drag_start_intensity = sublane_block.intensity
                # Check if clicking on edge for resizing
                elif self._is_on_sublane_block_edge(pos, sublane_type, sublane_block):
                    # Start resizing sublane block (CHANGED: store block reference)
                    self.resizing_sublane = sublane_block
                    edge = self._is_on_sublane_block_edge(pos, sublane_type, sublane_block)
                    self.resizing_sublane_edge = edge
                else:
                    # Clicked on sublane block body - enable dragging (CHANGED: store block reference)
                    self.dragging_sublane = sublane_block

            else:
                # Clicked on envelope background - deselect any sublane
                self.selected_sublane_type = None
                self.selected_sublane_block = None
                self.update()  # Trigger repaint

                # Check if clicking within a sublane row (for drag-to-create)
                sublane_row = self._get_sublane_row_at_y(pos.y())

                if sublane_row:
                    # Clicking in a sublane row - start drag-to-create
                    self.creating_sublane = sublane_row
                    # Convert click position to time
                    click_time = self.pixel_to_time(pos.x())
                    if self.snap_to_grid:
                        click_time = self.timeline_widget.find_nearest_beat_time(click_time)
                    self.create_start_time = click_time
                    self.create_end_time = click_time  # Will be updated in mouseMoveEvent
                else:
                    # Not in a sublane row - check envelope resize handles
                    x = pos.x()

                    if x <= self.RESIZE_HANDLE_WIDTH:
                        self.resizing_left = True
                    elif x >= self.width() - self.RESIZE_HANDLE_WIDTH:
                        self.resizing_right = True
                    else:
                        self.dragging = True
                        # Check if shift is held for copy operation
                        if shift_held:
                            self.shift_drag_copying = True

            self.drag_start_pos = event.globalPosition().toPoint()
            self.drag_start_time = self.block.start_time
            self.drag_start_duration = self.block.end_time - self.block.start_time

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for dragging/resizing."""
        if not (self.dragging or self.resizing_left or self.resizing_right or self.resizing_sublane or self.dragging_sublane or self.creating_sublane or self.dragging_intensity_handle):
            # Update cursor based on position
            pos = event.pos()

            # Check if hovering over a sublane block
            sublane_type, sublane_block = self._get_sublane_block_at_pos(pos)
            if sublane_block:
                # Check if hovering over intensity handle
                if self._is_on_intensity_handle(pos, sublane_type, sublane_block):
                    # On intensity handle - show vertical resize cursor
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                    return
                # Check if hovering over edge
                edge = self._is_on_sublane_block_edge(pos, sublane_type, sublane_block)
                if edge:
                    # On sublane edge - show resize cursor
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                    return

            # Check envelope edges
            x = pos.x()
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

        elif self.resizing_sublane:
            # Resize sublane block (CHANGED: self.resizing_sublane is now the block reference)
            sublane_block = self.resizing_sublane

            if self.resizing_sublane_edge == 'left':
                # Resize from left edge (changes start time)
                new_start = self.drag_start_sublane_start + delta_time

                if self.snap_to_grid:
                    new_start = self.timeline_widget.find_nearest_beat_time(new_start)

                # Don't allow shrinking below minimum duration
                if new_start >= 0 and (self.drag_start_sublane_end - new_start) >= 0.1:
                    sublane_block.start_time = new_start
                    # Update envelope bounds
                    self.block.update_envelope_bounds()
                    self.block.modified = True
                    self.update_position()
                    self.update()  # Redraw

            elif self.resizing_sublane_edge == 'right':
                # Resize from right edge (changes end time)
                new_end = self.drag_start_sublane_end + delta_time

                if self.snap_to_grid:
                    new_end = self.timeline_widget.find_nearest_beat_time(new_end)

                # Don't allow shrinking below minimum duration
                if (new_end - self.drag_start_sublane_start) >= 0.1:
                    sublane_block.end_time = new_end
                    # Update envelope bounds
                    self.block.update_envelope_bounds()
                    self.block.modified = True
                    self.update_position()
                    self.update()  # Redraw

        elif self.dragging_sublane:
            # Drag sublane block (CHANGED: self.dragging_sublane is now the block reference)
            sublane_block = self.dragging_sublane

            # Calculate new start time
            new_start = self.drag_start_sublane_start + delta_time

            if self.snap_to_grid:
                new_start = self.timeline_widget.find_nearest_beat_time(new_start)

            # Calculate duration and new end time
            duration = self.drag_start_sublane_end - self.drag_start_sublane_start
            new_end = new_start + duration

            # Don't allow negative start time
            if new_start >= 0:
                sublane_block.start_time = new_start
                sublane_block.end_time = new_end
                # Update envelope bounds
                self.block.update_envelope_bounds()
                self.block.modified = True
                self.update_position()
                self.update()  # Redraw

        elif self.creating_sublane:
            # Update end time for block being created
            pos = event.pos()
            current_time = self.pixel_to_time(pos.x())

            if self.snap_to_grid:
                current_time = self.timeline_widget.find_nearest_beat_time(current_time)

            self.create_end_time = max(current_time, self.create_start_time + 0.1)  # Minimum duration

            # Check for overlap in Movement/Special sublanes
            if self.creating_sublane in ["movement", "special"]:
                self.overlap_detected = self._check_overlap(
                    self.creating_sublane,
                    self.create_start_time,
                    self.create_end_time
                )
            else:
                self.overlap_detected = False

            self.update()  # Redraw to show preview

        elif self.dragging_intensity_handle:
            # Drag intensity handle vertically
            pos = event.pos()

            # Get sublane info
            sublane_type = "dimmer"  # Intensity handle only for dimmer blocks
            sublane_height = self.lane_widget.sublane_height
            margin = 2

            # Get sublane row index
            sublane_index = self.lane_widget.get_sublane_index(sublane_type)
            y_offset = sublane_index * sublane_height

            # Calculate new intensity from Y position
            usable_height = sublane_height - 2 * margin
            # Y position relative to sublane top
            y_in_sublane = pos.y() - (y_offset + margin)

            # Clamp to usable height
            y_in_sublane = max(0, min(y_in_sublane, usable_height))

            # Convert to intensity (inverted: top=255, bottom=0)
            intensity_ratio = 1.0 - (y_in_sublane / usable_height)
            new_intensity = intensity_ratio * 255.0

            # Clamp intensity
            new_intensity = max(0.0, min(255.0, new_intensity))

            # Update intensity
            self.dragging_intensity_handle.intensity = new_intensity

            # Mark block as modified
            self.block.modified = True

            # Redraw to update handle position and label
            self.update()

    def _get_sublane_block_by_type(self, sublane_type):
        """Get sublane block object by type."""
        if sublane_type == "dimmer":
            return self.block.dimmer_block
        elif sublane_type == "colour":
            return self.block.colour_block
        elif sublane_type == "movement":
            return self.block.movement_block
        elif sublane_type == "special":
            return self.block.special_block
        return None

    def _check_overlap(self, sublane_type, start_time, end_time, exclude_block=None):
        """Check if a time range would overlap with existing blocks in a sublane.

        Args:
            sublane_type: Type of sublane to check
            start_time: Proposed start time
            end_time: Proposed end time
            exclude_block: Block to exclude from overlap check (when resizing/moving existing block)

        Returns:
            True if overlap detected, False otherwise
        """
        # Get the list of blocks for this sublane type
        if sublane_type == "dimmer":
            blocks = self.block.dimmer_blocks
        elif sublane_type == "colour":
            blocks = self.block.colour_blocks
        elif sublane_type == "movement":
            blocks = self.block.movement_blocks
        elif sublane_type == "special":
            blocks = self.block.special_blocks
        else:
            return False

        # Check for overlaps with existing blocks
        for existing_block in blocks:
            if existing_block is exclude_block:
                continue  # Skip the block we're currently editing

            # Two ranges overlap if: start1 < end2 AND start2 < end1
            if start_time < existing_block.end_time and existing_block.start_time < end_time:
                return True  # Overlap detected

        return False

    def _create_sublane_block(self, sublane_type, start_time, end_time):
        """Create a new sublane block of the specified type.

        Args:
            sublane_type: Type of sublane ("dimmer", "colour", "movement", "special")
            start_time: Start time for the block
            end_time: End time for the block
        """
        from config.models import DimmerBlock, ColourBlock, MovementBlock, SpecialBlock

        # Check for overlaps in Movement/Special sublanes (prevent conflicts)
        if sublane_type in ["movement", "special"]:
            if self._check_overlap(sublane_type, start_time, end_time):
                print(f"Warning: Cannot create {sublane_type} block - overlaps with existing block")
                return  # Abort creation

        # Create the appropriate sublane block and APPEND to list (CHANGED: was replacing single block)
        if sublane_type == "dimmer":
            new_block = DimmerBlock(
                start_time=start_time,
                end_time=end_time,
                intensity=255.0
            )
            self.block.dimmer_blocks.append(new_block)
        elif sublane_type == "colour":
            new_block = ColourBlock(
                start_time=start_time,
                end_time=end_time,
                color_mode="RGB",
                red=255.0,
                green=255.0,
                blue=255.0
            )
            self.block.colour_blocks.append(new_block)
        elif sublane_type == "movement":
            new_block = MovementBlock(
                start_time=start_time,
                end_time=end_time,
                pan=127.5,
                tilt=127.5
            )
            self.block.movement_blocks.append(new_block)
        elif sublane_type == "special":
            new_block = SpecialBlock(
                start_time=start_time,
                end_time=end_time
            )
            self.block.special_blocks.append(new_block)

        # Update envelope bounds and mark as modified
        self.block.update_envelope_bounds()
        self.block.modified = True
        self.update_position()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop dragging/resizing."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Handle shift+drag copy completion
            if self.shift_drag_copying and self.dragging:
                # Create a copy of the effect at the new position
                new_start_time = self.block.start_time  # Current position after drag
                # Reset original block to its starting position
                self.block.start_time = self.drag_start_time
                self.block.end_time = self.drag_start_time + self.drag_start_duration
                # Update sublane blocks back to original times
                self._restore_sublane_times()
                self.update_position()

                # Create copy at new position via lane widget
                if hasattr(self.lane_widget, 'paste_effect_at_time'):
                    from .effect_clipboard import copy_effect, paste_effect
                    copy_effect(self.block)
                    self.lane_widget.paste_effect_at_time(new_start_time)

                self.shift_drag_copying = False

            # Handle drag-to-create completion
            if self.creating_sublane and self.create_start_time is not None and self.create_end_time is not None:
                # Only create if no overlap (overlap_detected flag is set during mouseMoveEvent)
                if not self.overlap_detected:
                    # Create the new sublane block
                    self._create_sublane_block(self.creating_sublane, self.create_start_time, self.create_end_time)
                # Clear creation state
                self.creating_sublane = None
                self.create_start_time = None
                self.create_end_time = None
                self.overlap_detected = False
                self.update()

            self.dragging = False
            self.resizing_left = False
            self.resizing_right = False
            self.drag_start_pos = None

            # Clear sublane interaction state
            self.clicked_sublane_type = None
            self.resizing_sublane = None
            self.resizing_sublane_edge = None
            self.dragging_sublane = None
            self.dragging_intensity_handle = None
            # Note: We keep self.selected_sublane_block so the selection persists after release

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click to open effect editor or sublane block editor."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            sublane_type, sublane_block = self._get_sublane_block_at_pos(pos)

            if sublane_block is not None:
                # Double-clicked on a sublane block - open sublane-specific dialog
                self.open_sublane_dialog(sublane_type, sublane_block)
            else:
                # Double-clicked on envelope - open effect dialog
                self.open_effect_dialog()

    def contextMenuEvent(self, event):
        """Handle right-click context menu."""
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)

        # Check if right-clicked on a sublane block
        pos = self.mapFromGlobal(event.globalPos())
        sublane_type, sublane_block = self._get_sublane_block_at_pos(pos)

        if sublane_block is not None:
            # Sublane block context menu
            sublane_labels = {
                "dimmer": "Dimmer",
                "colour": "Colour",
                "movement": "Movement",
                "special": "Special"
            }
            label = sublane_labels.get(sublane_type, sublane_type.capitalize())

            edit_sublane_action = menu.addAction(f"Edit {label} Block...")
            edit_sublane_action.triggered.connect(
                lambda: self.open_sublane_dialog(sublane_type, sublane_block)
            )

            delete_sublane_action = menu.addAction(f"Delete {label} Block")
            delete_sublane_action.triggered.connect(
                lambda: self._delete_sublane_block(sublane_type, sublane_block)
            )

            menu.addSeparator()

        edit_action = menu.addAction("Edit Effect Envelope...")
        edit_action.triggered.connect(self.open_effect_dialog)

        menu.addSeparator()

        copy_action = menu.addAction("Copy Effect")
        copy_action.triggered.connect(self.copy_effect)

        menu.addSeparator()

        delete_action = menu.addAction("Delete Entire Effect")
        delete_action.triggered.connect(lambda: self.remove_requested.emit(self))

        menu.exec(event.globalPos())

    def open_effect_dialog(self):
        """Open the effect editor dialog for the envelope."""
        from .effect_block_dialog import EffectBlockDialog
        dialog = EffectBlockDialog(self.block, parent=self)
        if dialog.exec():
            self.update_display()
            self.block_edited.emit()  # Trigger auto-save

    def open_sublane_dialog(self, sublane_type: str, sublane_block):
        """Open the appropriate dialog for a sublane block.

        Args:
            sublane_type: Type of sublane ("dimmer", "colour", "movement", "special")
            sublane_block: The sublane block to edit
        """
        dialog = None

        if sublane_type == "dimmer":
            from .dimmer_block_dialog import DimmerBlockDialog
            dialog = DimmerBlockDialog(sublane_block, parent=self)
        elif sublane_type == "colour":
            from .colour_block_dialog import ColourBlockDialog
            # Get color wheel options from fixture if available
            color_wheel_options = self._get_color_wheel_options()
            dialog = ColourBlockDialog(sublane_block, color_wheel_options=color_wheel_options, parent=self)
        elif sublane_type == "movement":
            from .movement_block_dialog import MovementBlockDialog
            dialog = MovementBlockDialog(sublane_block, parent=self)
        elif sublane_type == "special":
            from .special_block_dialog import SpecialBlockDialog
            dialog = SpecialBlockDialog(sublane_block, parent=self)

        if dialog and dialog.exec():
            # Mark effect as modified since sublane was changed
            self.block.modified = True
            self.update_display()
            self.block_edited.emit()  # Trigger auto-save

    def _get_color_wheel_options(self):
        """Get color wheel options from fixture group if available.

        Returns:
            List of (name, dmx_value, hex_color) tuples, or empty list
        """
        try:
            # Check if we have access to config through lane_widget
            if not self.lane_widget or not self.lane_widget.config:
                return []

            # Get fixture group
            group_name = self.lane_widget.lane.fixture_group
            if group_name not in self.lane_widget.config.groups:
                return []

            group = self.lane_widget.config.groups[group_name]

            # Get color wheel options from fixtures
            from utils.fixture_utils import get_color_wheel_options
            return get_color_wheel_options(group.fixtures)

        except Exception:
            # If anything goes wrong, just return empty list
            return []

    def _delete_sublane_block(self, sublane_type: str, sublane_block):
        """Delete a specific sublane block.

        Args:
            sublane_type: Type of sublane
            sublane_block: The block to delete
        """
        block_list = None
        if sublane_type == "dimmer":
            block_list = self.block.dimmer_blocks
        elif sublane_type == "colour":
            block_list = self.block.colour_blocks
        elif sublane_type == "movement":
            block_list = self.block.movement_blocks
        elif sublane_type == "special":
            block_list = self.block.special_blocks

        if block_list and sublane_block in block_list:
            block_list.remove(sublane_block)
            # Clear selection if deleted block was selected
            if self.selected_sublane_block == sublane_block:
                self.selected_sublane_block = None
                self.selected_sublane_type = None
            self.block.modified = True
            self.update_display()

    def _restore_sublane_times(self):
        """Restore all sublane block times to match the original envelope position.

        Used when cancelling a shift+drag copy to reset the visual dragging.
        """
        # Calculate the time offset that was applied during dragging
        current_duration = self.block.end_time - self.block.start_time
        original_duration = self.drag_start_duration

        # The blocks were dragged with the envelope, so we need to restore them
        # to match the original start time
        time_delta = self.drag_start_time - self.block.start_time

        # Since we already reset self.block.start_time and end_time,
        # we need to adjust all sublane blocks to match
        for dimmer_block in self.block.dimmer_blocks:
            dimmer_block.start_time += time_delta
            dimmer_block.end_time += time_delta

        for colour_block in self.block.colour_blocks:
            colour_block.start_time += time_delta
            colour_block.end_time += time_delta

        for movement_block in self.block.movement_blocks:
            movement_block.start_time += time_delta
            movement_block.end_time += time_delta

        for special_block in self.block.special_blocks:
            special_block.start_time += time_delta
            special_block.end_time += time_delta

    def copy_effect(self):
        """Copy this effect to the clipboard."""
        from .effect_clipboard import copy_effect
        copy_effect(self.block)

    def wheelEvent(self, event):
        """Handle mouse wheel for speed adjustment (Ctrl+wheel) on dimmer and movement blocks."""
        from PyQt6.QtCore import Qt

        # Check if Ctrl is pressed and a dimmer or movement block is selected
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.selected_sublane_type in ["dimmer", "movement"] and self.selected_sublane_block:
                # Speed options in order
                speed_options = ["1/4", "1/2", "1", "2", "4"]

                # Get current speed
                current_speed = getattr(self.selected_sublane_block, 'effect_speed', '1')

                # Find current index
                try:
                    current_index = speed_options.index(current_speed)
                except ValueError:
                    current_index = 2  # Default to "1"

                # Determine direction (up = faster, down = slower)
                delta = event.angleDelta().y()
                if delta > 0:
                    # Scroll up - increase speed
                    new_index = min(current_index + 1, len(speed_options) - 1)
                else:
                    # Scroll down - decrease speed
                    new_index = max(current_index - 1, 0)

                # Update speed
                self.selected_sublane_block.effect_speed = speed_options[new_index]

                # Mark block as modified
                self.block.modified = True

                # Repaint to update grid
                self.update()

                # Accept event to prevent propagation
                event.accept()
                return

        # If not handled, pass to parent
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        """Handle key press for deletion."""
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.remove_requested.emit(self)
        else:
            super().keyPressEvent(event)
