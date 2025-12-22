# timeline_ui/light_lane_widget.py
# Light lane widget for displaying and editing light effect lanes
# Adapted from midimaker_and_show_structure/ui/lane_widget.py

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QPushButton, QCheckBox, QLineEdit, QFrame,
                             QScrollArea, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from .timeline_widget import TimelineWidget
from .light_block_widget import LightBlockWidget
from timeline.light_lane import LightLane


class LightLaneWidget(QFrame):
    """Widget for displaying and editing a light lane.

    Shows lane controls on the left (name, fixture group, mute/solo)
    and a scrollable timeline with effect blocks on the right.
    """

    remove_requested = pyqtSignal(object)  # Emits self when remove requested
    scroll_position_changed = pyqtSignal(int)  # Emits horizontal scroll position
    zoom_changed = pyqtSignal(float)  # Emits zoom factor
    playhead_moved = pyqtSignal(float)  # Emits playhead position

    def __init__(self, lane: LightLane, fixture_groups: list = None, parent=None, config=None):
        """Create a new light lane widget.

        Args:
            lane: LightLane instance to display
            fixture_groups: List of available fixture group names
            parent: Parent widget
            config: Configuration object (for capability detection)
        """
        super().__init__(parent)
        self.lane = lane
        self.fixture_groups = fixture_groups or []
        self.light_block_widgets = []
        self.main_window = parent
        self.config = config

        # Detect capabilities and calculate sublane layout
        self.capabilities = self._detect_group_capabilities()
        self.num_sublanes = self._count_sublanes()
        self.sublane_height = 50  # Height per sublane in pixels
        self.min_lane_height = 95  # Minimum height to accommodate control panel

        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)

        # Dynamic height based on number of sublanes, with minimum for control panel
        # Add buffer for margins, padding, and horizontal scrollbar
        buffer_height = 40  # Extra space for layout margins and scrollbar
        total_height = max(self.min_lane_height, self.num_sublanes * self.sublane_height + buffer_height)
        self.setMinimumHeight(total_height)
        self.setMaximumHeight(total_height)

        self.setStyleSheet("""
            LightLaneWidget {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 4px;
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)

        # Lane controls section (left side)
        controls_widget = self.create_controls_widget()
        main_layout.addWidget(controls_widget)

        # Timeline section (right side) - scrollable
        self.timeline_scroll = QScrollArea()
        self.timeline_widget = TimelineWidget()

        # Configure sublanes
        self.timeline_widget.num_sublanes = self.num_sublanes
        self.timeline_widget.sublane_height = self.sublane_height
        self.timeline_widget.capabilities = self.capabilities
        # Timeline height should exactly fit sublanes (no buffer needed here)
        timeline_height = self.num_sublanes * self.sublane_height
        self.timeline_widget.setMinimumHeight(timeline_height)
        self.timeline_widget.setMaximumHeight(timeline_height)  # Prevent vertical growth

        self.timeline_widget.zoom_changed.connect(self.zoom_changed.emit)
        self.timeline_widget.zoom_changed.connect(self.on_timeline_zoom_changed)
        self.timeline_widget.playhead_moved.connect(self.playhead_moved.emit)

        # Create light block widgets for existing blocks
        for block in self.lane.light_blocks:
            self.create_light_block_widget(block)

        self.timeline_scroll.setWidget(self.timeline_widget)
        self.timeline_scroll.setWidgetResizable(False)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Connect scroll events
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(
            self.scroll_position_changed.emit)

        main_layout.addWidget(self.timeline_scroll, 1)

    def create_controls_widget(self):
        """Create the lane controls section."""
        widget = QWidget()
        widget.setFixedWidth(320)
        layout = QVBoxLayout(widget)
        layout.setSpacing(4)

        # Row 1: Name and remove button
        name_layout = QHBoxLayout()

        name_label = QLabel("Name:")
        name_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        name_layout.addWidget(name_label)

        self.name_edit = QLineEdit(self.lane.name)
        self.name_edit.textChanged.connect(self.on_name_changed)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 2px 5px;
            }
        """)
        name_layout.addWidget(self.name_edit)

        self.remove_button = QPushButton("×")
        self.remove_button.setFixedSize(25, 25)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
        """)
        name_layout.addWidget(self.remove_button)

        layout.addLayout(name_layout)

        # Row 2: Fixture group
        group_layout = QHBoxLayout()

        group_label = QLabel("Group:")
        group_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        group_layout.addWidget(group_label)

        self.group_combo = QComboBox()
        self.group_combo.addItems(self.fixture_groups)
        if self.lane.fixture_group in self.fixture_groups:
            self.group_combo.setCurrentText(self.lane.fixture_group)
        self.group_combo.currentTextChanged.connect(self.on_group_changed)
        self.group_combo.setStyleSheet("""
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 2px 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin-right: 5px;
            }
        """)
        group_layout.addWidget(self.group_combo, 1)

        layout.addLayout(group_layout)

        # Row 3: Mute, Solo, Add Block
        controls_layout = QHBoxLayout()

        # Mute button
        self.mute_button = QPushButton("M")
        self.mute_button.setFixedSize(30, 25)
        self.mute_button.setCheckable(True)
        self.mute_button.setChecked(self.lane.muted)
        self.mute_button.toggled.connect(self.on_mute_toggled)
        self.update_mute_button_style()
        controls_layout.addWidget(self.mute_button)

        # Solo button
        self.solo_button = QPushButton("S")
        self.solo_button.setFixedSize(30, 25)
        self.solo_button.setCheckable(True)
        self.solo_button.setChecked(self.lane.solo)
        self.solo_button.toggled.connect(self.on_solo_toggled)
        self.update_solo_button_style()
        controls_layout.addWidget(self.solo_button)

        controls_layout.addSpacing(10)

        # Snap checkbox
        self.snap_checkbox = QCheckBox("Snap")
        self.snap_checkbox.setChecked(True)
        self.snap_checkbox.setStyleSheet("color: white; font-size: 12px;")
        self.snap_checkbox.toggled.connect(self.on_snap_toggled)
        controls_layout.addWidget(self.snap_checkbox)

        controls_layout.addStretch()

        # Add Block button
        self.add_block_button = QPushButton("Add Block")
        self.add_block_button.clicked.connect(self.add_light_block)
        self.add_block_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 3px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        controls_layout.addWidget(self.add_block_button)

        layout.addLayout(controls_layout)

        return widget

    def _detect_group_capabilities(self):
        """Detect capabilities from fixture group."""
        from config.models import FixtureGroupCapabilities

        # If no config provided, return default (all capabilities)
        if not self.config:
            return FixtureGroupCapabilities(True, True, True, True)

        # Check if group exists in config
        if self.lane.fixture_group not in self.config.groups:
            return FixtureGroupCapabilities(True, True, True, True)

        group = self.config.groups[self.lane.fixture_group]

        # Check if capabilities already cached
        if group.capabilities:
            return group.capabilities

        # Otherwise detect and cache
        from utils.fixture_utils import detect_fixture_group_capabilities
        caps = detect_fixture_group_capabilities(group.fixtures)
        group.capabilities = caps
        return caps

    def _count_sublanes(self):
        """Count number of active sublanes."""
        count = 0
        if self.capabilities.has_dimmer:
            count += 1
        if self.capabilities.has_colour:
            count += 1
        if self.capabilities.has_movement:
            count += 1
        if self.capabilities.has_special:
            count += 1
        return max(1, count)  # At least 1 sublane

    def get_sublane_index(self, sublane_type: str) -> int:
        """Get the row index (0-based) for a sublane type.

        Args:
            sublane_type: "dimmer", "colour", "movement", or "special"

        Returns:
            Row index, or 0 if not found
        """
        index = 0

        if sublane_type == "dimmer":
            if self.capabilities.has_dimmer:
                return index
            else:
                return 0
        if self.capabilities.has_dimmer:
            index += 1

        if sublane_type == "colour":
            if self.capabilities.has_colour:
                return index
            else:
                return 0
        if self.capabilities.has_colour:
            index += 1

        if sublane_type == "movement":
            if self.capabilities.has_movement:
                return index
            else:
                return 0
        if self.capabilities.has_movement:
            index += 1

        if sublane_type == "special":
            if self.capabilities.has_special:
                return index
            else:
                return 0

        return 0  # Fallback

    def set_song_structure(self, song_structure):
        """Set song structure for this lane's timeline."""
        self.timeline_widget.set_song_structure(song_structure)

    def set_playhead_position(self, position: float):
        """Set playhead position for this lane's timeline."""
        self.timeline_widget.set_playhead_position(position)

    def set_zoom_factor(self, zoom_factor: float):
        """Set zoom factor for this lane's timeline."""
        self.timeline_widget.set_zoom_factor(zoom_factor)

        # Update light block positions
        for block_widget in self.light_block_widgets:
            block_widget.update_position()

    def sync_scroll_position(self, position: int):
        """Sync scroll position with master timeline."""
        self.timeline_scroll.horizontalScrollBar().setValue(position)

    def update_bpm(self, bpm: float):
        """Update BPM for grid calculations."""
        self.timeline_widget.set_bpm(bpm)

    def create_light_block_widget(self, block):
        """Create a widget for a light block."""
        block_widget = LightBlockWidget(block, self.timeline_widget, self)
        block_widget.remove_requested.connect(self.remove_light_block_widget)
        block_widget.position_changed.connect(self.on_block_position_changed)
        block_widget.duration_changed.connect(self.on_block_duration_changed)

        self.light_block_widgets.append(block_widget)
        block_widget.show()

    def add_light_block(self):
        """Add a new light block at the current playhead position."""
        from config.models import DimmerBlock, ColourBlock, MovementBlock, SpecialBlock

        start_time = self.timeline_widget.playhead_position
        end_time = start_time + 4.0  # Default 4 second duration

        # Create sublane blocks based on capabilities
        dimmer_block = None
        colour_block = None
        movement_block = None
        special_block = None

        if self.capabilities.has_dimmer:
            dimmer_block = DimmerBlock(
                start_time=start_time,
                end_time=end_time,
                intensity=255.0
            )

        if self.capabilities.has_colour:
            colour_block = ColourBlock(
                start_time=start_time,
                end_time=end_time,
                color_mode="RGB",
                red=255.0,
                green=255.0,
                blue=255.0
            )

        if self.capabilities.has_movement:
            movement_block = MovementBlock(
                start_time=start_time,
                end_time=end_time,
                pan=127.5,
                tilt=127.5
            )

        if self.capabilities.has_special:
            special_block = SpecialBlock(
                start_time=start_time,
                end_time=end_time
            )

        # Create the light block with sublane blocks
        block = self.lane.add_light_block_with_sublanes(
            start_time=start_time,
            end_time=end_time,
            effect_name="",
            dimmer_block=dimmer_block,
            colour_block=colour_block,
            movement_block=movement_block,
            special_block=special_block
        )
        self.create_light_block_widget(block)

    def remove_light_block_widget(self, block_widget):
        """Remove a light block widget and its data."""
        self.lane.remove_light_block(block_widget.block)
        self.light_block_widgets.remove(block_widget)
        block_widget.deleteLater()

    def on_timeline_zoom_changed(self, zoom_factor):
        """Handle timeline zoom changes."""
        for block_widget in self.light_block_widgets:
            block_widget.update_position()

    def on_block_position_changed(self, block_widget, new_start_time):
        """Handle block position change."""
        # Block's start_time is already updated in the widget
        pass

    def on_block_duration_changed(self, block_widget, new_duration):
        """Handle block duration change."""
        # Block's duration is already updated in the widget
        pass

    # Event handlers
    def on_name_changed(self, text):
        self.lane.name = text

    def on_group_changed(self, group_name):
        self.lane.fixture_group = group_name

    def on_mute_toggled(self, checked):
        self.lane.muted = checked
        self.update_mute_button_style()

    def on_solo_toggled(self, checked):
        self.lane.solo = checked
        self.update_solo_button_style()

    def on_snap_toggled(self, checked):
        self.timeline_widget.set_snap_to_grid(checked)
        for block_widget in self.light_block_widgets:
            block_widget.set_snap_to_grid(checked)

    def update_mute_button_style(self):
        """Update mute button appearance based on state."""
        if self.mute_button.isChecked():
            self.mute_button.setStyleSheet("""
                QPushButton {
                    background-color: #d32f2f;
                    color: white;
                    font-weight: bold;
                    border: none;
                    border-radius: 3px;
                }
            """)
        else:
            self.mute_button.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: white;
                    font-weight: bold;
                    border: none;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)

    def update_solo_button_style(self):
        """Update solo button appearance based on state."""
        if self.solo_button.isChecked():
            self.solo_button.setStyleSheet("""
                QPushButton {
                    background-color: #FFC107;
                    color: black;
                    font-weight: bold;
                    border: none;
                    border-radius: 3px;
                }
            """)
        else:
            self.solo_button.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: white;
                    font-weight: bold;
                    border: none;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
