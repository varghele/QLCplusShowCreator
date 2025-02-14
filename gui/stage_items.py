from PyQt6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter
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

        # Rotation handle visibility
        self.show_rotation_handle = False
        self.rotation_handle_radius = 40

    def boundingRect(self):
        # Increased height to accommodate name and z-height text
        return QRectF(-self.size/2, -self.size/2, self.size, self.size + 20)

    def paint(self, painter, option, widget):
        # Set up pens and brushes based on selection state
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.blue, 3))  # Thicker blue outline when selected
            # Make the fill color slightly transparent when selected
            selected_color = QColor(self.channel_color)
            selected_color.setAlpha(160)  # Add some transparency
            painter.setBrush(QBrush(selected_color))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.setBrush(QBrush(QColor(self.channel_color)))

            # Draw different symbols based on fixture type
            if self.fixture_type == "PAR":
                # PAR is represented by a circle
                painter.drawEllipse(QRectF(-self.size / 2, -self.size / 2, self.size, self.size))

            elif self.fixture_type == "BAR":
                # BAR is represented by a wide rectangle
                painter.drawRect(QRectF(-self.size, -self.size / 4, self.size * 2, self.size / 2))

            elif self.fixture_type == "WASH":
                # WASH is represented by a rounded rectangle
                painter.drawRoundedRect(QRectF(-self.size / 2, -self.size / 2, self.size, self.size),
                                        self.size / 4, self.size / 4)

            elif self.fixture_type == "MH":
                # Moving Head is represented by a circle with a direction indicator
                painter.drawEllipse(QRectF(-self.size / 2, -self.size / 2, self.size, self.size))
                # Add direction indicator (a triangle)
                triangle = [
                    QPointF(0, -self.size / 2),  # Top point
                    QPointF(-self.size / 4, -self.size / 2 - self.size / 4),  # Bottom left
                    QPointF(self.size / 4, -self.size / 2 - self.size / 4)  # Bottom right
                ]
                painter.drawPolygon(triangle)

        # Draw rotation handle when hovered
        if self.show_rotation_handle:
            painter.setPen(QPen(Qt.GlobalColor.blue, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(-self.rotation_handle_radius/2,
                                     -self.rotation_handle_radius/2,
                                     self.rotation_handle_radius,
                                     self.rotation_handle_radius))

            # Draw rotation indicator using QPointF
            angle_rad = self.rotation_angle * 3.14159 / 180
            end_x = self.rotation_handle_radius/2 * cos(angle_rad)
            end_y = self.rotation_handle_radius/2 * sin(angle_rad)
            painter.drawLine(
                QPointF(0, 0),
                QPointF(end_x, end_y)
            )

        # Draw fixture name and Z-height
        painter.setPen(Qt.GlobalColor.black)
        name_rect = QRectF(-self.size/2, self.size/2, self.size, 20)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter,
                        f"{self.fixture_name}\nZ: {self.z_height}m")

    def hoverEnterEvent(self, event):
        self.show_rotation_handle = True
        self.update()

    def hoverLeaveEvent(self, event):
        self.show_rotation_handle = False
        self.update()

    def wheelEvent(self, event):
        # Rotate fixture with mouse wheel
        delta = event.angleDelta().y() / 8
        self.rotation_angle = (self.rotation_angle + delta) % 360
        self.update()


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

