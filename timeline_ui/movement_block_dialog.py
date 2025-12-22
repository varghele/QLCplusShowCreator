# timeline_ui/movement_block_dialog.py
# Dialog for editing movement sublane block parameters

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QGroupBox, QSlider, QDoubleSpinBox, QSpinBox,
                             QLabel, QDialogButtonBox, QCheckBox, QFrame,
                             QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from config.models import MovementBlock


class PanTiltWidget(QFrame):
    """2D widget for pan/tilt position control."""

    position_changed = pyqtSignal(float, float)  # pan, tilt (0-255)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet("background-color: #1a1a2e; border: 1px solid #555;")

        self._pan = 127.5
        self._tilt = 127.5
        self._dragging = False

    def set_position(self, pan: float, tilt: float):
        """Set the pan/tilt position (0-255)."""
        self._pan = max(0, min(255, pan))
        self._tilt = max(0, min(255, tilt))
        self.update()

    def pan(self) -> float:
        return self._pan

    def tilt(self) -> float:
        return self._tilt

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 10

        # Draw grid
        painter.setPen(QPen(QColor(50, 50, 70), 1))
        # Vertical lines
        for i in range(5):
            x = margin + (w - 2 * margin) * i / 4
            painter.drawLine(int(x), margin, int(x), h - margin)
        # Horizontal lines
        for i in range(5):
            y = margin + (h - 2 * margin) * i / 4
            painter.drawLine(margin, int(y), w - margin, int(y))

        # Draw center crosshair
        painter.setPen(QPen(QColor(100, 100, 120), 1, Qt.PenStyle.DashLine))
        center_x = w / 2
        center_y = h / 2
        painter.drawLine(int(center_x), margin, int(center_x), h - margin)
        painter.drawLine(margin, int(center_y), w - margin, int(center_y))

        # Draw position indicator
        pos_x = margin + (self._pan / 255) * (w - 2 * margin)
        pos_y = margin + (self._tilt / 255) * (h - 2 * margin)

        # Outer circle
        painter.setPen(QPen(QColor(255, 165, 0), 2))
        painter.setBrush(QBrush(QColor(255, 165, 0, 100)))
        painter.drawEllipse(int(pos_x - 8), int(pos_y - 8), 16, 16)

        # Center dot
        painter.setBrush(QBrush(QColor(255, 200, 50)))
        painter.drawEllipse(int(pos_x - 3), int(pos_y - 3), 6, 6)

        # Labels
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(margin, h - 2, "0")
        painter.drawText(w - margin - 20, h - 2, "255")
        painter.drawText(2, margin + 10, "0")
        painter.drawText(2, h - margin, "255")
        painter.drawText(int(center_x - 10), h - 2, "Pan")
        painter.drawText(2, int(center_y), "Tilt")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._update_position(event.position())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_position(event.position())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def _update_position(self, pos):
        """Update position from mouse coordinates."""
        w = self.width()
        h = self.height()
        margin = 10

        # Convert to 0-255 range
        pan = (pos.x() - margin) / (w - 2 * margin) * 255
        tilt = (pos.y() - margin) / (h - 2 * margin) * 255

        # Clamp to valid range
        pan = max(0, min(255, pan))
        tilt = max(0, min(255, tilt))

        self._pan = pan
        self._tilt = tilt
        self.update()
        self.position_changed.emit(pan, tilt)


class MovementBlockDialog(QDialog):
    """Dialog for editing movement sublane block parameters."""

    def __init__(self, block: MovementBlock, parent=None):
        """Create the movement block dialog.

        Args:
            block: MovementBlock to edit
            parent: Parent widget
        """
        super().__init__(parent)
        self.block = block

        self.setWindowTitle("Edit Movement Block")
        self.setMinimumWidth(500)
        self.setMinimumHeight(520)

        self._apply_groupbox_style()
        self.setup_ui()
        self.load_current_values()

    def _apply_groupbox_style(self):
        """Apply consistent styling to group boxes."""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
        """)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Timing info (read-only display)
        timing_group = QGroupBox("Timing")
        timing_layout = QFormLayout()

        self.start_label = QLabel()
        self.end_label = QLabel()
        self.duration_label = QLabel()
        timing_layout.addRow("Start:", self.start_label)
        timing_layout.addRow("End:", self.end_label)
        timing_layout.addRow("Duration:", self.duration_label)

        timing_group.setLayout(timing_layout)
        layout.addWidget(timing_group)

        # Position group with 2D widget
        position_group = QGroupBox("Position")
        position_layout = QHBoxLayout()

        # 2D control widget
        self.pan_tilt_widget = PanTiltWidget()
        self.pan_tilt_widget.position_changed.connect(self._on_position_widget_changed)
        position_layout.addWidget(self.pan_tilt_widget)

        # Numeric controls
        numeric_layout = QVBoxLayout()

        # Pan controls
        pan_group = QGroupBox("Pan")
        pan_layout = QFormLayout()

        pan_row = QHBoxLayout()
        self.pan_slider = QSlider(Qt.Orientation.Horizontal)
        self.pan_slider.setRange(0, 255)
        self.pan_spinbox = QDoubleSpinBox()
        self.pan_spinbox.setRange(0, 255)
        self.pan_spinbox.setDecimals(1)
        self.pan_slider.valueChanged.connect(lambda v: self.pan_spinbox.setValue(v))
        self.pan_spinbox.valueChanged.connect(lambda v: self.pan_slider.setValue(int(v)))
        self.pan_slider.valueChanged.connect(self._on_slider_changed)
        pan_row.addWidget(self.pan_slider, 1)
        pan_row.addWidget(self.pan_spinbox)
        pan_layout.addRow("Coarse:", pan_row)

        pan_fine_row = QHBoxLayout()
        self.pan_fine_spinbox = QDoubleSpinBox()
        self.pan_fine_spinbox.setRange(0, 255)
        self.pan_fine_spinbox.setDecimals(1)
        pan_fine_row.addWidget(self.pan_fine_spinbox)
        pan_layout.addRow("Fine:", pan_fine_row)

        pan_group.setLayout(pan_layout)
        numeric_layout.addWidget(pan_group)

        # Tilt controls
        tilt_group = QGroupBox("Tilt")
        tilt_layout = QFormLayout()

        tilt_row = QHBoxLayout()
        self.tilt_slider = QSlider(Qt.Orientation.Horizontal)
        self.tilt_slider.setRange(0, 255)
        self.tilt_spinbox = QDoubleSpinBox()
        self.tilt_spinbox.setRange(0, 255)
        self.tilt_spinbox.setDecimals(1)
        self.tilt_slider.valueChanged.connect(lambda v: self.tilt_spinbox.setValue(v))
        self.tilt_spinbox.valueChanged.connect(lambda v: self.tilt_slider.setValue(int(v)))
        self.tilt_slider.valueChanged.connect(self._on_slider_changed)
        tilt_row.addWidget(self.tilt_slider, 1)
        tilt_row.addWidget(self.tilt_spinbox)
        tilt_layout.addRow("Coarse:", tilt_row)

        tilt_fine_row = QHBoxLayout()
        self.tilt_fine_spinbox = QDoubleSpinBox()
        self.tilt_fine_spinbox.setRange(0, 255)
        self.tilt_fine_spinbox.setDecimals(1)
        tilt_fine_row.addWidget(self.tilt_fine_spinbox)
        tilt_layout.addRow("Fine:", tilt_fine_row)

        tilt_group.setLayout(tilt_layout)
        numeric_layout.addWidget(tilt_group)

        # Center button
        center_btn = QPushButton("Center Position")
        center_btn.clicked.connect(self._center_position)
        numeric_layout.addWidget(center_btn)

        position_layout.addLayout(numeric_layout)
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)

        # Speed and interpolation group
        options_group = QGroupBox("Options")
        options_layout = QFormLayout()

        # Speed
        speed_row = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 255)
        self.speed_spinbox = QSpinBox()
        self.speed_spinbox.setRange(0, 255)
        self.speed_slider.valueChanged.connect(self.speed_spinbox.setValue)
        self.speed_spinbox.valueChanged.connect(self.speed_slider.setValue)
        speed_row.addWidget(self.speed_slider, 1)
        speed_row.addWidget(self.speed_spinbox)
        options_layout.addRow("Speed:", speed_row)

        # Interpolation checkbox
        self.interpolate_checkbox = QCheckBox("Interpolate from previous position")
        self.interpolate_checkbox.setToolTip(
            "When enabled, the fixture will gradually move from its previous\n"
            "position to this block's position during any gap before this block."
        )
        options_layout.addRow(self.interpolate_checkbox)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_position_widget_changed(self, pan, tilt):
        """Handle position change from 2D widget."""
        self.pan_slider.blockSignals(True)
        self.pan_spinbox.blockSignals(True)
        self.tilt_slider.blockSignals(True)
        self.tilt_spinbox.blockSignals(True)

        self.pan_slider.setValue(int(pan))
        self.pan_spinbox.setValue(pan)
        self.tilt_slider.setValue(int(tilt))
        self.tilt_spinbox.setValue(tilt)

        self.pan_slider.blockSignals(False)
        self.pan_spinbox.blockSignals(False)
        self.tilt_slider.blockSignals(False)
        self.tilt_spinbox.blockSignals(False)

    def _on_slider_changed(self):
        """Handle slider changes and update 2D widget."""
        self.pan_tilt_widget.set_position(
            self.pan_spinbox.value(),
            self.tilt_spinbox.value()
        )

    def _center_position(self):
        """Reset to center position."""
        self.pan_slider.setValue(127)
        self.pan_spinbox.setValue(127.5)
        self.tilt_slider.setValue(127)
        self.tilt_spinbox.setValue(127.5)
        self.pan_tilt_widget.set_position(127.5, 127.5)

    def load_current_values(self):
        """Load current block values into the dialog."""
        # Timing
        self.start_label.setText(f"{self.block.start_time:.2f}s")
        self.end_label.setText(f"{self.block.end_time:.2f}s")
        duration = self.block.end_time - self.block.start_time
        self.duration_label.setText(f"{duration:.2f}s")

        # Position
        self.pan_slider.setValue(int(self.block.pan))
        self.pan_spinbox.setValue(self.block.pan)
        self.pan_fine_spinbox.setValue(self.block.pan_fine)
        self.tilt_slider.setValue(int(self.block.tilt))
        self.tilt_spinbox.setValue(self.block.tilt)
        self.tilt_fine_spinbox.setValue(self.block.tilt_fine)
        self.pan_tilt_widget.set_position(self.block.pan, self.block.tilt)

        # Speed
        self.speed_slider.setValue(int(self.block.speed))

        # Interpolation
        self.interpolate_checkbox.setChecked(self.block.interpolate_from_previous)

    def accept(self):
        """Save parameters to block and close."""
        self.block.pan = self.pan_spinbox.value()
        self.block.tilt = self.tilt_spinbox.value()
        self.block.pan_fine = self.pan_fine_spinbox.value()
        self.block.tilt_fine = self.tilt_fine_spinbox.value()
        self.block.speed = float(self.speed_spinbox.value())
        self.block.interpolate_from_previous = self.interpolate_checkbox.isChecked()

        super().accept()
