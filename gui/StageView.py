from PyQt6 import QtWidgets, QtGui, QtCore
from gui.stage_items import FixtureItem, SpotItem
from config.models import Spot


class StageView(QtWidgets.QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = None  # Store configuration
        self.scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Globally track if snapping is enabled
        self.snap_enabled = False

        # Stage properties (in meters)
        self.stage_width_m = 10.0  # Default 10m
        self.stage_depth_m = 6.0  # Default 6m
        self.pixels_per_meter = 50  # Scale factor
        self.padding = 10  # Padding in pixels

        # Grid properties
        self.grid_visible = True
        self.grid_size_m = 0.5  # Default 0.5m grid

        # Initialize view
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(
            QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )

        # List to store fixture items
        self.fixtures = {}
        self.spots = {}  # name: SpotItem
        self.spot_counter = 1  # Counter for generating unique spot names

        # Initial update
        self.updateStage()

    def set_config(self, config):
        """Update the configuration and refresh the view"""
        self.config = config
        self.update_from_config()

    def update_from_config(self):
        """Update all fixtures from current configuration"""
        if not self.config:
            return

        # Clear and update fixtures
        for fixture in self.fixtures.values():
            self.scene.removeItem(fixture)
        self.fixtures.clear()

        # Clear and update spots
        for spot in self.spots.values():
            self.scene.removeItem(spot)
        self.spots.clear()

        # Reset spot counter
        self.spot_counter = 1

        # Update fixtures
        if hasattr(self.config, 'fixtures'):
            for fixture in self.config.fixtures:
                group_color = '#808080'
                if fixture.group and hasattr(self.config, 'groups'):
                    group = self.config.groups.get(fixture.group)
                    if group:
                        group_color = group.color

                fixture_item = FixtureItem(
                    fixture_name=fixture.name,
                    fixture_type=fixture.type,
                    channel_color=group_color
                )

                # Set position directly from fixture properties
                fixture_item.setPos(
                    self.padding + fixture.x * self.pixels_per_meter,
                    self.padding + fixture.y * self.pixels_per_meter
                )

                # Set z-height and rotation directly from fixture properties
                fixture_item.z_height = fixture.z
                fixture_item.rotation_angle = fixture.rotation

                # Store additional properties
                fixture_item.universe = fixture.universe
                fixture_item.address = fixture.address
                fixture_item.manufacturer = fixture.manufacturer
                fixture_item.model = fixture.model
                fixture_item.group = fixture.group
                fixture_item.direction = fixture.direction
                fixture_item.current_mode = fixture.current_mode
                fixture_item.available_modes = fixture.available_modes

                self.scene.addItem(fixture_item)
                self.fixtures[fixture.name] = fixture_item

        # Update spots
        if hasattr(self.config, 'spots'):
            for spot_name, spot_data in self.config.spots.items():
                spot_item = SpotItem(name=spot_name)
                spot_item.setPos(
                    self.padding + spot_data.x * self.pixels_per_meter,
                    self.padding + spot_data.y * self.pixels_per_meter
                )

                self.scene.addItem(spot_item)
                self.spots[spot_name] = spot_item

                # Update spot counter
                try:
                    spot_number = int(spot_name.replace('Spot', ''))
                    self.spot_counter = max(self.spot_counter, spot_number + 1)
                except ValueError:
                    pass

    def save_positions_to_config(self):
        """Save current fixture positions and spot positions back to configuration"""
        # Save fixture positions
        for fixture_name, fixture_item in self.fixtures.items():
            # Find the corresponding fixture in config
            config_fixture = next((f for f in self.config.fixtures if f.name == fixture_name), None)
            if config_fixture:
                # Convert position from pixels to meters
                pos = fixture_item.pos()

                # Update fixture properties directly
                config_fixture.x = (pos.x() - self.padding) / self.pixels_per_meter
                config_fixture.y = (pos.y() - self.padding) / self.pixels_per_meter
                config_fixture.z = fixture_item.z_height
                config_fixture.rotation = fixture_item.rotation_angle

        # Save spot positions
        for spot_name, spot_item in self.spots.items():
            if spot_name in self.config.spots:
                pos = spot_item.pos()
                self.config.spots[spot_name].x = (pos.x() - self.padding) / self.pixels_per_meter
                self.config.spots[spot_name].y = (pos.y() - self.padding) / self.pixels_per_meter

    def set_snap_to_grid(self, enabled):
        """Enable or disable snap to grid"""
        self.snap_enabled = enabled
        if enabled:
            self.snap_all_fixtures_to_grid()

    def snap_to_grid_position(self, pos):
        """Convert a position to the nearest grid point if snapping is enabled"""
        if not self.snap_enabled:
            return pos

        # Convert position to meters (accounting for padding)
        x_m = (pos.x() - self.padding) / self.pixels_per_meter
        y_m = (pos.y() - self.padding) / self.pixels_per_meter

        # Snap to nearest grid point
        x_m = round(x_m / self.grid_size_m) * self.grid_size_m
        y_m = round(y_m / self.grid_size_m) * self.grid_size_m

        # Convert back to pixels and add padding
        return QtCore.QPointF(
            x_m * self.pixels_per_meter + self.padding,
            y_m * self.pixels_per_meter + self.padding
        )

    def snap_all_fixtures_to_grid(self):
        """Snap all existing fixtures to the grid"""
        if not self.snap_enabled:
            return

        for fixture in self.fixtures.values():
            current_pos = fixture.pos()
            snapped_pos = self.snap_to_grid_position(current_pos)
            fixture.setPos(snapped_pos)

        self.save_positions_to_config()

    def add_spot(self, x=100, y=100):
        """Add a new spot to the stage"""
        spot_name = f"Spot{self.spot_counter}"
        spot = SpotItem(name=spot_name)
        spot.setPos(x, y)
        self.scene.addItem(spot)
        self.spots[spot_name] = spot
        self.spot_counter += 1

        # Add to configuration
        if self.config:
            self.config.spots[spot_name] = Spot(
                name=spot_name,
                x=x / self.pixels_per_meter,  # Convert to meters
                y=y / self.pixels_per_meter
            )
        return spot

    def remove_selected_items(self):
        """Remove selected items from the stage"""
        for item in self.scene.selectedItems():
            if isinstance(item, FixtureItem):
                self.scene.removeItem(item)
                if item.fixture_name in self.fixtures:
                    del self.fixtures[item.fixture_name]
            elif isinstance(item, SpotItem):
                self.scene.removeItem(item)
                if item.name in self.spots:
                    del self.spots[item.name]
                    if self.config:
                        del self.config.spots[item.name]

                    # Update spot counter if necessary
                    try:
                        removed_number = int(item.name.replace('Spot', ''))
                        if removed_number == self.spot_counter - 1:
                            # If we removed the last spot, decrease the counter
                            self.spot_counter = removed_number
                    except ValueError:
                        pass  # If the name doesn't follow the SpotX format, ignore

    def updateStage(self, width_m=None, depth_m=None):
        """Update stage dimensions"""
        if width_m is not None:
            self.stage_width_m = width_m
        if depth_m is not None:
            self.stage_depth_m = depth_m

        # Convert to pixels
        width_px = self.stage_width_m * self.pixels_per_meter
        depth_px = self.stage_depth_m * self.pixels_per_meter

        # Calculate total size including padding
        total_width = width_px + (2 * self.padding)
        total_depth = depth_px + (2 * self.padding)

        # Update scene rect with padding
        self.scene.setSceneRect(0, 0, total_width, total_depth)

        # Fit view to scene
        self.fitInView(
            self.scene.sceneRect(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio
        )

        self.viewport().update()

    def updateGrid(self, visible=None, size_m=None):
        """Update grid properties"""
        if visible is not None:
            self.grid_visible = visible
        if size_m is not None:
            self.grid_size_m = size_m
        self.viewport().update()

    def drawBackground(self, painter, rect):
        """Draw stage and grid"""
        super().drawBackground(painter, rect)

        # Convert stage dimensions to pixels and ensure they're integers
        width_px = int(self.stage_width_m * self.pixels_per_meter)
        depth_px = int(self.stage_depth_m * self.pixels_per_meter)

        # Draw stage outline with padding
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 2))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(240, 240, 240)))
        painter.drawRect(
            self.padding,
            self.padding,
            width_px,
            depth_px
        )

        # Draw grid if enabled
        if self.grid_visible:
            painter.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200), 1))
            grid_size_px = int(self.grid_size_m * self.pixels_per_meter)

            # Draw vertical grid lines
            for x in range(self.padding, width_px + self.padding + 1, grid_size_px):
                painter.drawLine(x, self.padding, x, depth_px + self.padding)

            # Draw horizontal grid lines
            for y in range(self.padding, depth_px + self.padding + 1, grid_size_px):
                painter.drawLine(self.padding, y, width_px + self.padding, y)

    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        self.updateStage()

