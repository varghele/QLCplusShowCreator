from PyQt6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsView
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QFontMetrics, QFont
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

    def mouseMoveEvent(self, event):
        """Handle mouse movement for dragging fixtures"""
        if Qt.MouseButton.LeftButton & event.buttons():
            # Get the view
            view = self.scene().views()[0]

            # Get the new position
            new_pos = event.scenePos()

            # If view has snapping enabled, snap to grid during movement
            if hasattr(view, 'snap_enabled') and view.snap_enabled:
                # Calculate the snapped position
                snapped_pos = view.snap_to_grid_position(new_pos)
                self.setPos(snapped_pos)
            else:
                self.setPos(new_pos)

            # Update the configuration through the view
            if hasattr(view, 'save_positions_to_config'):
                view.save_positions_to_config()

            event.accept()
            return

        super().mouseMoveEvent(event)

    def paint(self, painter, option, widget):
        painter.save()  # Save the current painter state

        # Apply rotation transformation
        painter.translate(0, 0)  # Translate to center point
        painter.rotate(self.rotation_angle + 90)  # Rotate by current angle, Add 90 degrees to make 0 point downwards

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
            # Draw the base circle
            painter.drawEllipse(QRectF(-self.size / 2, -self.size / 2, self.size, self.size))

            # Draw triangle pointing in the same direction as rotation handle
            triangle = [
                QPointF(self.size / 2, 0),  # Bot point
                QPointF(0, -self.size / 4),  # Left point
                QPointF(0, self.size / 4)  # Right point
            ]
            painter.drawPolygon(triangle)

        # Reset transformation for rotation handle and text
        painter.restore()  # Restore the original painter state
        painter.save()

        # Draw rotation handle and angle text when hovered
        if self.show_rotation_handle:
            painter.setPen(QPen(Qt.GlobalColor.blue, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            # Draw rotation circle
            painter.drawEllipse(QRectF(-self.rotation_handle_radius / 2,
                                       -self.rotation_handle_radius / 2,
                                       self.rotation_handle_radius,
                                       self.rotation_handle_radius))

            # Draw rotation line
            angle_rad = (self.rotation_angle + 90) * 3.14159 / 180
            end_x = self.rotation_handle_radius / 2 * cos(angle_rad)
            end_y = self.rotation_handle_radius / 2 * sin(angle_rad)
            painter.drawLine(QPointF(0, 0), QPointF(end_x, end_y))

            # Draw angle text
            angle_text = f"{int(self.rotation_angle)}°"
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)

            # Position the angle text above the fixture
            text_width = QFontMetrics(font).horizontalAdvance(angle_text)
            angle_text_rect = QRectF(-text_width / 2, -self.rotation_handle_radius - 20,
                                     text_width, 20)
            painter.drawText(angle_text_rect, Qt.AlignmentFlag.AlignCenter, angle_text)

        painter.restore()

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
        if hasattr(event, 'angleDelta'):
            delta = event.angleDelta().y()
        else:
            delta = event.delta()

        delta = delta / 120.0

        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Z-height adjustment remains the same
            z_step = 0.1
            if delta > 0:
                self.z_height = max(0, self.z_height + z_step)
            else:
                self.z_height = max(0, self.z_height - z_step)
        else:
            # Modified rotation behavior for -180 to 180 range
            rotation_step = 5
            new_angle = self.rotation_angle + (rotation_step if delta > 0 else -rotation_step)

            # Convert to -180 to 180 range
            if new_angle > 180:
                new_angle -= 360
            elif new_angle < -180:
                new_angle += 360

            self.rotation_angle = new_angle

        self.update()

        # Auto-save to config after rotation/z-height change
        view = self.scene().views()[0]
        if hasattr(view, 'save_positions_to_config'):
            view.save_positions_to_config()

        event.accept()


class SpotItem(QGraphicsItem):
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.size = 20  # Size of the X
        self.name = name
        self.last_pos = self.pos()  # Store last position for snapping

    def boundingRect(self):
        text_width = len(self.name) * 8  # Approximate width of text
        return QRectF(-self.size/2 - 2, -self.size/2 - 2,
                     max(self.size + 4, text_width), self.size + 20)

    def mouseMoveEvent(self, event):
        view = self.scene().views()[0]  # Get the main view
        if view.snap_enabled:
            # Get current position in scene coordinates
            new_pos = event.scenePos()

            # Use view's snap_to_grid_position for center-based snapping
            snapped_pos = view.snap_to_grid_position(new_pos)
            self.setPos(snapped_pos)
        else:
            super().mouseMoveEvent(event)

        # Store new position
        self.last_pos = self.pos()

        # Auto-save to config after move
        if hasattr(view, 'save_positions_to_config'):
            view.save_positions_to_config()

    def paint(self, painter, option, widget):
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.blue, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(-self.size/2 - 2, -self.size/2 - 2,
                                     self.size + 4, self.size + 4))
            painter.setPen(QPen(Qt.GlobalColor.blue, 5))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 5))

        # Draw X
        painter.drawLine(QPointF(-self.size/2, -self.size/2),
                        QPointF(self.size/2, self.size/2))
        painter.drawLine(QPointF(-self.size/2, self.size/2),
                        QPointF(self.size/2, -self.size/2))

        # Draw name below the X
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(QPointF(-self.size/2, self.size + 5), self.name)

