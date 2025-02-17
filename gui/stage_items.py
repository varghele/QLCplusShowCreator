from PyQt6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsView
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QFontMetrics
from math import sin, cos


class FixtureItem(QGraphicsItem):
    def __init__(self, fixture_name, fixture_type, channel_color, parent=None):
        super().__init__(parent)
        self.fixture_name = fixture_name
        self.fixture_type = fixture_type
        self.channel_color = channel_color
        self.rotation_angle = 0
        self.z_height = 0

        # Enable dragging and mouse interaction
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

        # Size of the fixture symbol
        self.size = 30

        # Text height
        self.text_height = 25  # Height reserved for text

        # Rotation handle visibility
        self.show_rotation_handle = False
        self.rotation_handle_radius = 40

    def boundingRect(self):
        # Include the main fixture symbol plus text area
        return QRectF(-self.size / 2, -self.size / 2, self.size, self.size + self.text_height)

    def paint(self, painter, option, widget):
        painter.save()  # Save the current painter state

        # Apply rotation transformation
        painter.translate(0, 0)  # Translate to center point
        painter.rotate(self.rotation_angle)  # Rotate by current angle

        # Set smaller font size
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        # Set up pens and brushes based on selection state
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.blue, 3))
            selected_color = QColor(self.channel_color)
            selected_color.setAlpha(160)
            painter.setBrush(QBrush(selected_color))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.setBrush(QBrush(QColor(self.channel_color)))

        # Draw different symbols based on fixture type
        if self.fixture_type == "PAR":
            painter.drawEllipse(QRectF(-self.size / 2, -self.size / 2, self.size, self.size))
        elif self.fixture_type == "BAR":
            painter.drawRect(QRectF(-self.size, -self.size / 4, self.size * 2, self.size / 2))
        elif self.fixture_type == "WASH":
            painter.drawRoundedRect(QRectF(-self.size / 2, -self.size / 2, self.size, self.size),
                                    self.size / 4, self.size / 4)
        elif self.fixture_type == "MH":
            painter.drawEllipse(QRectF(-self.size / 2, -self.size / 2, self.size, self.size))
            triangle = [
                QPointF(0, -self.size / 2),
                QPointF(-self.size / 4, -self.size / 2 - self.size / 4),
                QPointF(self.size / 4, -self.size / 2 - self.size / 4)
            ]
            painter.drawPolygon(triangle)

        # Reset transformation for rotation handle and text
        painter.restore()  # Restore the original painter state

        # Draw rotation handle when hovered
        if self.show_rotation_handle:
            painter.setPen(QPen(Qt.GlobalColor.blue, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(-self.rotation_handle_radius / 2,
                                       -self.rotation_handle_radius / 2,
                                       self.rotation_handle_radius,
                                       self.rotation_handle_radius))

            angle_rad = self.rotation_angle * 3.14159 / 180
            end_x = self.rotation_handle_radius / 2 * cos(angle_rad)
            end_y = self.rotation_handle_radius / 2 * sin(angle_rad)
            painter.drawLine(QPointF(0, 0), QPointF(end_x, end_y))

        # Draw text (not rotated)
        text = f"{self.fixture_name}\nZ:{self.z_height:.1f}"
        text_rect = QRectF(-self.size / 2, self.size / 2, self.size, self.text_height)

        # Find the right font size that fits
        font = painter.font()
        font_size = 10
        while font_size > 6:
            font.setPointSize(font_size)
            painter.setFont(font)
            metrics = QFontMetrics(font)
            text_bounds = metrics.boundingRect(text_rect.toRect(),
                                               Qt.AlignmentFlag.AlignCenter, text)
            if text_bounds.height() <= text_rect.height() and \
                    text_bounds.width() <= text_rect.width():
                break
            font_size -= 1

        # Draw the text
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def hoverEnterEvent(self, event):
        self.show_rotation_handle = True
        self.update()

    def hoverLeaveEvent(self, event):
        self.show_rotation_handle = False
        self.update()

    def wheelEvent(self, event):
        """Handle mouse wheel events for rotating the fixture or changing z-height"""
        # For Qt6 compatibility
        if hasattr(event, 'angleDelta'):
            delta = event.angleDelta().y()
        else:
            delta = event.delta()

        # Normalize delta
        delta = delta / 120.0

        # Check if Shift key is pressed
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Adjust z-height when Shift is pressed
            z_step = 0.1  # Height adjustment in meters
            if delta > 0:
                self.z_height = max(0, self.z_height + z_step)  # Don't go below 0
            else:
                self.z_height = max(0, self.z_height - z_step)
        else:
            # Regular rotation behavior
            rotation_step = 5
            if delta > 0:
                self.rotation_angle = (self.rotation_angle + rotation_step) % 360
            else:
                self.rotation_angle = (self.rotation_angle - rotation_step) % 360

        # Update the fixture
        self.update()

        # Accept the event
        event.accept()


class SpotItem(QGraphicsItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.size = 20  # Size of the X

    def boundingRect(self):
        # Make bounding rect slightly larger to accommodate selection indicator
        return QRectF(-self.size/2 - 2, -self.size/2 - 2, self.size + 4, self.size + 4)

    def paint(self, painter, option, widget):
        # Set up pens based on selection state
        if self.isSelected():
            # Draw selection indicator (circle)
            painter.setPen(QPen(Qt.GlobalColor.blue, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(-self.size/2 - 2, -self.size/2 - 2,
                                     self.size + 4, self.size + 4))
            # Draw X with blue color when selected
            painter.setPen(QPen(Qt.GlobalColor.blue, 5))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 5))

        # Draw X
        painter.drawLine(QPointF(-self.size/2, -self.size/2),
                        QPointF(self.size/2, self.size/2))
        painter.drawLine(QPointF(-self.size/2, self.size/2),
                        QPointF(self.size/2, -self.size/2))

