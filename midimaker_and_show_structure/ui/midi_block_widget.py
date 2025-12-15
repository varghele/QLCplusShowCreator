from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QSpinBox, QLineEdit,
                             QFrame, QDialog, QDialogButtonBox, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPalette, QMouseEvent, QPainter, QPen
from core.midi_block import MidiBlock, MidiMessageType


class MidiBlockWidget(QFrame):
    remove_requested = pyqtSignal(object)
    position_changed = pyqtSignal(object, float)  # Emits self and new start_time
    duration_changed = pyqtSignal(object, float)  # Emits self and new duration

    def __init__(self, block: MidiBlock, parent=None):
        super().__init__(parent)
        self.block = block
        self.parent_widget = parent
        self.dragging = False
        self.resizing = False
        self.drag_start_pos = QPoint()
        self.resize_start_width = 0
        self.snap_to_grid = True
        self.grid_size = 60  # pixels per second (time-based layout)
        self.resize_edge_margin = 8  # pixels from right edge to detect resize
        self.has_moved = False  # Track if actual movement occurred

        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setFixedHeight(50)
        self.setMinimumWidth(3)  # Allow very small widths for zoomed-out view

        # Apply color scheme based on message type
        self.apply_color_scheme()

        self.setup_ui()
        self.update_position()

        # Enable mouse tracking for cursor changes
        self.setMouseTracking(True)

    def get_color_scheme(self):
        """Get color scheme based on MIDI message type"""
        if self.block.message_type == MidiMessageType.PROGRAM_CHANGE:
            # Blue for Program Change
            return {
                'bg': '#2196F3',
                'border': '#1976D2',
                'hover': '#42A5F5',
                'dragging': '#64B5F6'
            }
        elif self.block.message_type == MidiMessageType.CONTROL_CHANGE:
            # Green for Control Change
            return {
                'bg': '#4CAF50',
                'border': '#45a049',
                'hover': '#5CBF60',
                'dragging': '#66BB6A'
            }
        elif self.block.message_type == MidiMessageType.NOTE_ON:
            # Orange for Note On
            return {
                'bg': '#FF9800',
                'border': '#F57C00',
                'hover': '#FFB74D',
                'dragging': '#FFCC80'
            }
        elif self.block.message_type == MidiMessageType.NOTE_OFF:
            # Red for Note Off
            return {
                'bg': '#F44336',
                'border': '#D32F2F',
                'hover': '#EF5350',
                'dragging': '#E57373'
            }
        elif self.block.message_type == MidiMessageType.KEMPER_RIG_CHANGE:
            # Kemper green for Kemper Rig Change
            return {
                'bg': '#073f2c',
                'border': '#05301f',
                'hover': '#0a5038',
                'dragging': '#0d6045'
            }
        elif self.block.message_type == MidiMessageType.VOICELIVE3_PRESET:
            # Greyish blue for Voicelive3 Preset
            return {
                'bg': '#5c6d7e',
                'border': '#4a5a6a',
                'hover': '#6e8090',
                'dragging': '#8095a8'
            }
        elif self.block.message_type == MidiMessageType.QUAD_CORTEX_PRESET:
            # Gray for Quad Cortex Preset
            return {
                'bg': '#6b6b6b',
                'border': '#505050',
                'hover': '#7d7d7d',
                'dragging': '#909090'
            }
        else:
            # Default gray for unknown types
            return {
                'bg': '#9E9E9E',
                'border': '#757575',
                'hover': '#BDBDBD',
                'dragging': '#E0E0E0'
            }

    def apply_color_scheme(self):
        """Apply color scheme to the widget"""
        colors = self.get_color_scheme()
        self.setStyleSheet(f"""
            MidiBlockWidget {{
                background-color: {colors['bg']};
                border: 2px solid {colors['border']};
                border-radius: 5px;
            }}
            MidiBlockWidget:hover {{
                background-color: {colors['hover']};
            }}
            MidiBlockWidget[dragging="true"] {{
                background-color: {colors['dragging']};
                border: 2px solid {colors['border']};
                opacity: 0.8;
            }}
        """)

    def setup_ui(self):
        # Create a simple centered label for MIDI info
        self.info_label = QLabel(self.get_simple_info(), self)
        self.info_label.setStyleSheet("""
            color: black;
            font-weight: bold;
            font-size: 12px;
            background-color: rgba(255, 255, 255, 0.7);
            padding: 2px;
            border-radius: 3px;
        """)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setWordWrap(True)

        # Remove button (small, top-right corner)
        self.remove_button = QPushButton("×", self)
        self.remove_button.setFixedSize(14, 14)
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 7px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))

    def resizeEvent(self, event):
        """Handle resize to position labels"""
        super().resizeEvent(event)

        # Center the info label
        if hasattr(self, 'info_label'):
            label_width = min(self.width() - 10, 200)
            label_height = 40
            x = (self.width() - label_width) // 2
            y = (self.height() - label_height) // 2
            self.info_label.setGeometry(x, y, label_width, label_height)

        # Keep remove button in top-right corner
        if hasattr(self, 'remove_button'):
            self.remove_button.move(self.width() - 16, 2)

    def get_simple_info(self):
        """Get simple display string showing MIDI type and values"""
        if self.block.message_type == MidiMessageType.PROGRAM_CHANGE:
            return f"PC\n{self.block.value1}"
        elif self.block.message_type == MidiMessageType.CONTROL_CHANGE:
            return f"CC\n{self.block.value1}={self.block.value2}"
        elif self.block.message_type == MidiMessageType.NOTE_ON:
            return f"NON\n{self.block.value1}"
        elif self.block.message_type == MidiMessageType.NOTE_OFF:
            return f"NOF\n{self.block.value1}"
        elif self.block.message_type == MidiMessageType.KEMPER_RIG_CHANGE:
            return f"KEMP\n{self.block.value1}:{self.block.value2}"
        elif self.block.message_type == MidiMessageType.VOICELIVE3_PRESET:
            return f"VL3\n{self.block.value1}:{self.block.value2}"
        elif self.block.message_type == MidiMessageType.QUAD_CORTEX_PRESET:
            scene_letter = chr(65 + self.block.value3)  # 0-7 -> A-H
            return f"QC\n{self.block.value1}:{self.block.value2}:{scene_letter}"
        return "MIDI"

    def get_block_info(self, compact=False):
        """Get display string for block info

        Args:
            compact: If True, return abbreviated version for narrow blocks
        """
        if compact:
            # Compact version for narrow blocks
            if self.block.message_type == MidiMessageType.PROGRAM_CHANGE:
                return f"PC:{self.block.value1}"
            elif self.block.message_type == MidiMessageType.CONTROL_CHANGE:
                return f"CC{self.block.value1}={self.block.value2}"
            elif self.block.message_type == MidiMessageType.NOTE_ON:
                return f"NON:{self.block.value1}"
            elif self.block.message_type == MidiMessageType.NOTE_OFF:
                return f"NOF:{self.block.value1}"
            elif self.block.message_type == MidiMessageType.KEMPER_RIG_CHANGE:
                return f"KEMP:{self.block.value1}:{self.block.value2}"
            elif self.block.message_type == MidiMessageType.VOICELIVE3_PRESET:
                return f"VL3:{self.block.value1}:{self.block.value2}"
            elif self.block.message_type == MidiMessageType.QUAD_CORTEX_PRESET:
                scene_letter = chr(65 + self.block.value3)  # 0-7 -> A-H
                return f"QC:{self.block.value1}:{self.block.value2}:{scene_letter}"
            return "MIDI"
        else:
            # Full version for wider blocks
            if self.block.message_type == MidiMessageType.PROGRAM_CHANGE:
                return f"PC: {self.block.value1}"
            elif self.block.message_type == MidiMessageType.CONTROL_CHANGE:
                return f"CC{self.block.value1} = {self.block.value2}"
            elif self.block.message_type == MidiMessageType.NOTE_ON:
                return f"NON: {self.block.value1}\nVel: {self.block.value2}"
            elif self.block.message_type == MidiMessageType.NOTE_OFF:
                return f"NOF: {self.block.value1}\nVel: {self.block.value2}"
            elif self.block.message_type == MidiMessageType.KEMPER_RIG_CHANGE:
                return f"KEMPER\nBank: {self.block.value1}\nSlot: {self.block.value2}"
            elif self.block.message_type == MidiMessageType.VOICELIVE3_PRESET:
                return f"VL3\nBank: {self.block.value1}\nPatch: {self.block.value2}"
            elif self.block.message_type == MidiMessageType.QUAD_CORTEX_PRESET:
                scene_letter = chr(65 + self.block.value3)  # 0-7 -> A-H
                return f"QC\nBank: {self.block.value1}\nPreset: {self.block.value2}\nScene: {scene_letter}"
            return "MIDI"

    def update_position(self):
        """Update widget position based on block start time"""
        if self.parent_widget:
            # Calculate position based on start time and grid
            x_pos = int(self.block.start_time * self.grid_size)
            self.move(x_pos, self.y())

            # Update width based on duration (minimum 3px to stay visible)
            width = max(3, int(self.block.duration * self.grid_size))
            self.setFixedWidth(width)

            # Update info label text
            if hasattr(self, 'info_label'):
                self.info_label.setText(self.get_simple_info())

    def set_grid_size(self, pixels_per_second):
        """Set the grid size for positioning calculations (pixels per second)"""
        self.grid_size = pixels_per_second
        self.update_position()

    def set_snap_to_grid(self, snap):
        """Enable or disable snap to grid"""
        self.snap_to_grid = snap

    def is_near_right_edge(self, pos: QPoint) -> bool:
        """Check if mouse position is near the right edge for resizing"""
        return self.width() - pos.x() <= self.resize_edge_margin

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.has_moved = False  # Reset movement flag
            if self.is_near_right_edge(event.pos()):
                # Start resizing
                self.resizing = True
                self.drag_start_pos = event.pos()
                self.resize_start_width = self.width()
            else:
                # Start dragging
                self.dragging = True
                self.drag_start_pos = event.pos()
                self.setProperty("dragging", "true")
                self.setStyleSheet(self.styleSheet())  # Refresh style
            self.raise_()  # Bring to front while dragging/resizing
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Update cursor based on position (when not dragging/resizing)
        if not self.dragging and not self.resizing:
            if self.is_near_right_edge(event.pos()):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

        # Handle resizing
        if self.resizing and (event.buttons() & Qt.MouseButton.LeftButton):
            self.has_moved = True  # Mark that movement occurred
            # Calculate new width based on mouse movement
            delta_x = event.pos().x() - self.drag_start_pos.x()
            new_width = self.resize_start_width + delta_x

            # Apply minimum width constraint (larger for manual resize to allow edge grabbing)
            new_width = max(15, new_width)

            # Apply snap to grid if enabled (beat-based)
            if self.snap_to_grid and self.parent_widget and hasattr(self.parent_widget, 'find_nearest_beat_time'):
                # Calculate the end time based on new width
                new_duration = new_width / self.grid_size
                end_time = self.block.start_time + new_duration

                # Snap the end time to nearest beat
                snapped_end_time = self.parent_widget.find_nearest_beat_time(end_time)

                # Calculate snapped duration and width
                snapped_duration = max(0.1, snapped_end_time - self.block.start_time)
                new_width = int(snapped_duration * self.grid_size)

            # Update widget width
            self.setFixedWidth(new_width)

            # Update block duration
            new_duration = new_width / self.grid_size
            self.block.duration = max(0.1, new_duration)  # Minimum 0.1 second duration

        # Handle dragging
        elif self.dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.has_moved = True  # Mark that movement occurred
            # Calculate new position
            delta = event.pos() - self.drag_start_pos
            new_pos = self.pos() + delta

            # Constrain to parent widget bounds
            if self.parent_widget:
                parent_rect = self.parent_widget.rect()
                new_pos.setX(max(0, min(new_pos.x(), parent_rect.width() - self.width())))
                new_pos.setY(self.y())  # Keep Y position fixed

            # Apply snap to grid if enabled (beat-based)
            if self.snap_to_grid and self.parent_widget and hasattr(self.parent_widget, 'find_nearest_beat_time'):
                # Convert position to time
                new_start_time = new_pos.x() / self.grid_size

                # Snap to nearest beat
                snapped_start_time = self.parent_widget.find_nearest_beat_time(new_start_time)

                # Convert back to position
                new_pos.setX(int(snapped_start_time * self.grid_size))

            self.move(new_pos)

            # Update block start time based on position
            new_start_time = new_pos.x() / self.grid_size
            self.block.start_time = max(0, new_start_time)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging:
                self.dragging = False
                self.setProperty("dragging", "false")
                self.setStyleSheet(self.styleSheet())  # Refresh style

                # Emit position changed signal
                self.position_changed.emit(self, self.block.start_time)

            elif self.resizing:
                self.resizing = False

                # Emit duration changed signal
                self.duration_changed.emit(self, self.block.duration)

            # Reset cursor
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        # Allow editing if we haven't actually moved/resized (just clicked)
        if event.button() == Qt.MouseButton.LeftButton and not self.has_moved:
            self.edit_block()
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event):
        """Reset cursor when mouse leaves the widget"""
        if not self.dragging and not self.resizing:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def edit_block(self):
        """Open edit dialog for the MIDI block"""
        dialog = MidiBlockEditDialog(self.block, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.update_display()

    def update_display(self):
        """Update the widget display after block changes"""
        if hasattr(self, 'info_label'):
            self.info_label.setText(self.get_simple_info())
        self.apply_color_scheme()  # Update colors in case message type changed
        self.update_position()


class MidiBlockEditDialog(QDialog):
    def __init__(self, block: MidiBlock, parent=None):
        super().__init__(parent)
        self.block = block

        self.setWindowTitle("Edit MIDI Block")
        self.setModal(True)
        self.resize(300, 300)

        self.setup_ui()
        self.load_values()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Form layout for inputs
        form_layout = QFormLayout()

        # Block name
        self.name_edit = QLineEdit()
        form_layout.addRow("Name:", self.name_edit)

        # Start time and duration
        self.start_time_spinbox = QSpinBox()
        self.start_time_spinbox.setRange(0, 99999)
        self.start_time_spinbox.setSuffix(" ms")
        form_layout.addRow("Start Time:", self.start_time_spinbox)

        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setRange(100, 99999)
        self.duration_spinbox.setSuffix(" ms")
        form_layout.addRow("Duration:", self.duration_spinbox)

        # Message type
        self.message_type_combo = QComboBox()
        self.message_type_combo.addItems(["Control Change", "Program Change", "Note On", "Note Off", "Kemper Rig Change", "Voicelive3 Preset", "Quad Cortex Preset"])
        self.message_type_combo.currentTextChanged.connect(self.on_message_type_changed)
        form_layout.addRow("Message Type:", self.message_type_combo)

        # Value 1 (CC number, Program number, Note number)
        self.value1_spinbox = QSpinBox()
        self.value1_spinbox.setRange(0, 127)
        self.value1_label = QLabel("CC Number:")
        form_layout.addRow(self.value1_label, self.value1_spinbox)

        # Value 2 (CC value, velocity, etc.)
        self.value2_spinbox = QSpinBox()
        self.value2_spinbox.setRange(0, 127)
        self.value2_label = QLabel("CC Value:")
        form_layout.addRow(self.value2_label, self.value2_spinbox)

        # Value 3 (for presets requiring 3 parameters, e.g., QC scene)
        self.value3_spinbox = QSpinBox()
        self.value3_spinbox.setRange(0, 7)
        self.value3_label = QLabel("Scene (A-H):")
        form_layout.addRow(self.value3_label, self.value3_spinbox)
        self.value3_label.setVisible(False)
        self.value3_spinbox.setVisible(False)

        layout.addLayout(form_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_values(self):
        """Load current block values into the form"""
        self.name_edit.setText(self.block.name)
        self.start_time_spinbox.setValue(int(self.block.start_time * 1000))
        self.duration_spinbox.setValue(int(self.block.duration * 1000))

        # Set message type
        type_map = {
            MidiMessageType.CONTROL_CHANGE: 0,
            MidiMessageType.PROGRAM_CHANGE: 1,
            MidiMessageType.NOTE_ON: 2,
            MidiMessageType.NOTE_OFF: 3,
            MidiMessageType.KEMPER_RIG_CHANGE: 4,
            MidiMessageType.VOICELIVE3_PRESET: 5,
            MidiMessageType.QUAD_CORTEX_PRESET: 6
        }
        self.message_type_combo.setCurrentIndex(type_map.get(self.block.message_type, 0))

        self.value1_spinbox.setValue(self.block.value1)
        self.value2_spinbox.setValue(self.block.value2)
        self.value3_spinbox.setValue(self.block.value3)

        self.on_message_type_changed(self.message_type_combo.currentText())

    def on_message_type_changed(self, text):
        """Update labels based on selected message type"""
        # Hide value3 by default, only show for QC
        self.value3_label.setVisible(False)
        self.value3_spinbox.setVisible(False)

        if text == "Control Change":
            self.value1_label.setText("CC Number:")
            self.value2_label.setText("CC Value:")
            self.value1_spinbox.setRange(0, 127)
            self.value2_spinbox.setRange(0, 127)
            self.value2_spinbox.setEnabled(True)
        elif text == "Program Change":
            self.value1_label.setText("Program Number:")
            self.value2_label.setText("(Unused)")
            self.value1_spinbox.setRange(0, 127)
            self.value2_spinbox.setEnabled(False)
        elif text in ["Note On", "Note Off"]:
            self.value1_label.setText("Note Number:")
            self.value2_label.setText("Velocity:")
            self.value1_spinbox.setRange(0, 127)
            self.value2_spinbox.setRange(0, 127)
            self.value2_spinbox.setEnabled(True)
        elif text == "Kemper Rig Change":
            self.value1_label.setText("Bank (0-124):")
            self.value2_label.setText("Slot (1-5):")
            self.value1_spinbox.setRange(0, 124)
            self.value2_spinbox.setRange(1, 5)
            self.value2_spinbox.setEnabled(True)
        elif text == "Voicelive3 Preset":
            self.value1_label.setText("Bank (0-3):")
            self.value2_label.setText("Patch (0-127):")
            self.value1_spinbox.setRange(0, 3)
            self.value2_spinbox.setRange(0, 127)
            self.value2_spinbox.setEnabled(True)
        elif text == "Quad Cortex Preset":
            self.value1_label.setText("Bank (0-15):")
            self.value2_label.setText("Preset (0-127):")
            self.value3_label.setText("Scene (0-7, A-H):")
            self.value1_spinbox.setRange(0, 15)
            self.value2_spinbox.setRange(0, 127)
            self.value3_spinbox.setRange(0, 7)
            self.value2_spinbox.setEnabled(True)
            self.value3_label.setVisible(True)
            self.value3_spinbox.setVisible(True)

    def accept(self):
        """Save values back to the block"""
        self.block.name = self.name_edit.text()
        self.block.start_time = self.start_time_spinbox.value() / 1000.0
        self.block.duration = self.duration_spinbox.value() / 1000.0

        # Set message type and values
        text = self.message_type_combo.currentText()
        if text == "Control Change":
            self.block.set_control_change(self.value1_spinbox.value(), self.value2_spinbox.value())
        elif text == "Program Change":
            self.block.set_program_change(self.value1_spinbox.value())
        elif text == "Note On":
            self.block.set_note(self.value1_spinbox.value(), self.value2_spinbox.value(), True)
        elif text == "Note Off":
            self.block.set_note(self.value1_spinbox.value(), self.value2_spinbox.value(), False)
        elif text == "Kemper Rig Change":
            self.block.set_kemper_rig_change(self.value1_spinbox.value(), self.value2_spinbox.value())
        elif text == "Voicelive3 Preset":
            self.block.set_voicelive3_preset(self.value1_spinbox.value(), self.value2_spinbox.value())
        elif text == "Quad Cortex Preset":
            self.block.set_quad_cortex_preset(self.value1_spinbox.value(), self.value2_spinbox.value(), self.value3_spinbox.value())

        super().accept()
