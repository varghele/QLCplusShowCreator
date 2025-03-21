import sys
import os
import csv
import json
import xml.etree.ElementTree as ET
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (QMainWindow, QDialog, QFileDialog, QLineEdit, QMessageBox, QFormLayout, QDialogButtonBox,
                             QTableWidgetItem, QToolBar)
from PyQt6.QtGui import QAction, QFont
from .effect_selection import EffectSelectionDialog
from utils.create_workspace import create_qlc_workspace
from utils.fixture_utils import determine_fixture_type
from config.models import Configuration, Fixture, FixtureGroup, FixtureMode, ShowEffect, Show, ShowPart, Universe
from typing import Dict, List, Optional

from gui.Ui_MainWindow import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.config = Configuration()
        self.setupUi(self)

        # Initialize paths and data
        self.initialize_paths()

        # Set up tables
        self._setup_tables()

        # Set the configuration for StageView
        self.stage_view.set_config(self.config)

        # Connect signals
        self.connect_signals()

        # Initialize colors
        self.initialize_colors()

        # Initialize universes
        self.initialize_universes()

    def initialize_colors(self):
        self.group_colors = {}
        self.color_index = 0
        self.predefined_colors = [
            QtGui.QColor(255, 182, 193),  # Light pink
            QtGui.QColor(173, 216, 230),  # Light blue
            QtGui.QColor(144, 238, 144),  # Light green
            QtGui.QColor(255, 218, 185),  # Peach
            QtGui.QColor(221, 160, 221),  # Plum
            QtGui.QColor(176, 196, 222),  # Light steel blue
            QtGui.QColor(255, 255, 224),  # Light yellow
            QtGui.QColor(230, 230, 250)  # Lavender
        ]

    def initialize_universes(self):
        """Initialize universes and load them into the table"""
        if not hasattr(self.config, 'universes'):
            self.config.universes = {}
            self.config.initialize_default_universes()
        self.load_universes_to_table()

    def initialize_paths(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.setup_dir = os.path.join(self.project_root, "setup")
        self.fixture_paths = []

        # Load effects
        effects_json_path = os.path.join(self.project_root, "effects", "effects.json")
        with open(effects_json_path, 'r') as f:
            self.effects_dir = json.load(f)

    def connect_signals(self):
        # Connect table signals
        self.tableWidget.itemChanged.connect(self.update_config_from_table)

        # Add universe management signals
        self.add_universe_btn.clicked.connect(self.add_universe_config)
        self.remove_universe_btn.clicked.connect(self.remove_universe_config)
        self.update_config_btn.clicked.connect(self.update_universe_config_from_table)
        self.universe_list.itemChanged.connect(self.on_universe_item_changed)

        # Connect Fixture Tab buttons
        self.updateFixturesButton.clicked.connect(self.update_config_from_table)
        self.pushButton.clicked.connect(self.add_fixture)
        self.pushButton_2.clicked.connect(self.remove_fixture)

        # Connect Show Tab buttons
        self.pushButton_5.clicked.connect(self.save_show)
        self.pushButton_7.clicked.connect(self.update_show_tab_from_config)

        # Connect toolbar actions
        self.saveAction.triggered.connect(self.save_configuration)
        self.loadAction.triggered.connect(self.load_configuration)
        self.loadShowsAction.triggered.connect(self.import_show_structure)
        self.importWorkspaceAction.triggered.connect(self.import_workspace)
        self.createWorkspaceAction.triggered.connect(self.create_workspace)

        # Connect stage plot button #TODO: write the plot_stage function
        #self.plot_stage_btn.clicked.connect(self.plot_stage)

    def update_config_from_table(self, item=None):
        """Update configuration when table items change

        Args:
            item: When called from itemChanged signal, this is the QTableWidgetItem
                  When called from a button click, this is ignored
        """
        # If called from button click, item will be a boolean True
        # In this case, we should update all items
        if isinstance(item, bool) or item is None:
            # Update all fixtures
            for row in range(self.tableWidget.rowCount()):
                if row >= len(self.config.fixtures):
                    continue

                fixture = self.config.fixtures[row]

                # Update manufacturer
                manufacturer_item = self.tableWidget.item(row, 2)
                if manufacturer_item and manufacturer_item.text():
                    fixture.manufacturer = manufacturer_item.text()

                # Update model
                model_item = self.tableWidget.item(row, 3)
                if model_item and model_item.text():
                    fixture.model = model_item.text()

                # Update name
                name_item = self.tableWidget.item(row, 6)
                if name_item and name_item.text():
                    fixture.name = name_item.text()

                # Update direction (column 8)
                direction_combo = self.tableWidget.cellWidget(row, 8)
                if direction_combo and isinstance(direction_combo, QtWidgets.QComboBox):
                    display_value = direction_combo.currentText()
                    if display_value == "↑":
                        fixture.direction = "UP"
                    elif display_value == "↓":
                        fixture.direction = "DOWN"
                    else:
                        fixture.direction = "NONE"

            self.update_groups()

            # Refresh the table to show any changes
            self.update_fixture_tab_from_config()
            return

        # Original functionality for when an individual item changes
        row = item.row()
        col = item.column()

        if row >= len(self.config.fixtures):
            return

        fixture = self.config.fixtures[row]

        # Map column changes to fixture attributes
        if col == 2:  # Manufacturer
            fixture.manufacturer = item.text()
        elif col == 3:  # Model
            fixture.model = item.text()
        elif col == 6:  # Name
            fixture.name = item.text()

        self.update_groups()

    def update_config_from_widget(self, row: int, col: int, widget):
        """Update configuration when widgets (spinboxes, comboboxes) change"""
        if row >= len(self.config.fixtures):
            return

        fixture = self.config.fixtures[row]

        if col == 0:  # Universe
            fixture.universe = widget.value()
        elif col == 1:  # Address
            fixture.address = widget.value()
        elif col == 5:  # Mode
            fixture.current_mode = widget.currentText()
        elif col == 7:  # Group
            old_group = fixture.group
            new_group = widget.currentText()

            # Remove from old group if exists
            if old_group in self.config.groups:
                self.config.groups[old_group].fixtures.remove(fixture)
                if not self.config.groups[old_group].fixtures:
                    del self.config.groups[old_group]

            # Add to new group
            fixture.group = new_group
            if new_group:
                if new_group not in self.config.groups:
                    self.config.groups[new_group] = FixtureGroup(new_group, [])
                self.config.groups[new_group].fixtures.append(fixture)

        elif col == 8:  # Direction
            # Convert display arrows to standardized text values
            display_value = widget.currentText()
            if display_value == "↑":
                fixture.direction = "UP"
            elif display_value == "↓":
                fixture.direction = "DOWN"
            else:
                fixture.direction = "NONE"

    def update_groups(self):
        """Update groups in configuration"""
        # Store existing group colors before clearing
        existing_colors = {
            name: group.color
            for name, group in self.config.groups.items()
            if hasattr(group, 'color')
        }

        # Clear existing groups
        self.config.groups = {}

        # Rebuild groups from fixtures, preserving colors
        for fixture in self.config.fixtures:
            if fixture.group:
                if fixture.group not in self.config.groups:
                    color = existing_colors.get(fixture.group, '#808080')  # Use existing color or default
                    self.config.groups[fixture.group] = FixtureGroup(
                        fixture.group,
                        [],
                        color=color
                    )
                self.config.groups[fixture.group].fixtures.append(fixture)

    def handle_new_group(self, group_combo):
        """Handle adding a new group"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Group")
        layout = QFormLayout()
        new_group_input = QLineEdit()
        layout.addRow("Group Name:", new_group_input)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_group = new_group_input.text().strip()
            if new_group:
                current_index = group_combo.findText("Add New...")
                group_combo.removeItem(current_index)
                group_combo.addItem(new_group)
                group_combo.addItem("Add New...")
                group_combo.setCurrentText(new_group)

    def update_universe_config_from_table(self):
        """Update universe configuration values from the universe table"""
        for row in range(self.universe_list.rowCount()):
            # Check if we have a valid universe ID in the first column
            universe_id_item = self.universe_list.item(row, 0)
            if universe_id_item is None or not universe_id_item.text():
                continue

            try:
                universe_id = int(universe_id_item.text())

                # Skip if this universe doesn't exist in config
                if universe_id not in self.config.universes:
                    continue

                # Update IP Address
                ip_item = self.universe_list.item(row, 2)
                if ip_item and ip_item.text():
                    self.config.universes[universe_id].output['parameters']['ip'] = ip_item.text()

                # Update Port
                port_item = self.universe_list.item(row, 3)
                if port_item and port_item.text():
                    self.config.universes[universe_id].output['parameters']['port'] = port_item.text()

                # Update Subnet
                subnet_item = self.universe_list.item(row, 4)
                if subnet_item and subnet_item.text():
                    self.config.universes[universe_id].output['parameters']['subnet'] = subnet_item.text()

                # Update Universe
                uni_item = self.universe_list.item(row, 5)
                if uni_item and uni_item.text():
                    self.config.universes[universe_id].output['parameters']['universe'] = uni_item.text()

            except (ValueError, AttributeError) as e:
                print(f"Error updating universe {row}: {e}")

        print("Universe configuration updated from table")

    def update_fixture_tab_from_config(self):
        """Update fixture tab UI from configuration"""
        self.tableWidget.setRowCount(0)

        for fixture in self.config.fixtures:
            row = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row)

            # Universe
            universe_spin = QtWidgets.QSpinBox()
            universe_spin.setRange(1, 16)
            universe_spin.setValue(fixture.universe)
            self.tableWidget.setCellWidget(row, 0, universe_spin)

            # Address
            address_spin = QtWidgets.QSpinBox()
            address_spin.setRange(1, 512)
            address_spin.setValue(fixture.address)
            self.tableWidget.setCellWidget(row, 1, address_spin)

            # Other columns
            self.tableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(fixture.manufacturer))
            self.tableWidget.setItem(row, 3, QtWidgets.QTableWidgetItem(fixture.model))

            # Mode and Channels
            mode_combo = QtWidgets.QComboBox()
            if fixture.available_modes:
                # Add all available modes to combo box
                for mode in fixture.available_modes:
                    mode_combo.addItem(f"{mode.name} ({mode.channels}ch)")

                # Find and set current mode
                current_mode_text = next(
                    (f"{mode.name} ({mode.channels}ch)"
                     for mode in fixture.available_modes
                     if mode.name == fixture.current_mode),
                    fixture.current_mode
                )
                index = mode_combo.findText(current_mode_text)
                if index >= 0:
                    mode_combo.setCurrentIndex(index)
                    # Set initial channels value
                    channels = fixture.available_modes[index].channels
                    self.tableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem(str(channels)))

                # Create closure to update channels when mode changes
                def create_mode_handler(current_row, modes):
                    def handle_mode_change(index):
                        if 0 <= index < len(modes):
                            channels = modes[index].channels
                            self.tableWidget.setItem(current_row, 4,
                                                     QtWidgets.QTableWidgetItem(str(channels)))
                            # Update configuration
                            self.config.fixtures[current_row].current_mode = modes[index].name
                            # Update colors if needed
                            self.update_row_colors()

                    return handle_mode_change

                mode_combo.currentIndexChanged.connect(
                    create_mode_handler(row, fixture.available_modes)
                )
            else:
                mode_combo.addItem(fixture.current_mode)
                self.tableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem("0"))

            self.tableWidget.setCellWidget(row, 5, mode_combo)

            # Name
            self.tableWidget.setItem(row, 6, QtWidgets.QTableWidgetItem(fixture.name))

            # Group
            group_combo = QtWidgets.QComboBox()
            group_combo.setEditable(True)
            group_combo.addItem("")
            for group in sorted(self.config.groups.keys()):
                group_combo.addItem(group)
            group_combo.addItem("Add New...")
            group_combo.setCurrentText(fixture.group)

            def create_group_handler(current_row):
                def handle_group_change(text):
                    if text == "Add New...":
                        self.handle_new_group(group_combo)
                    else:
                        # Update configuration
                        self.config.fixtures[current_row].group = text
                        self.update_groups()
                    self.update_row_colors()

                return handle_group_change

            group_combo.currentTextChanged.connect(create_group_handler(row))
            self.tableWidget.setCellWidget(row, 7, group_combo)

            # Direction
            direction_combo = QtWidgets.QComboBox()
            direction_combo.addItems(["", "↑", "↓"])
            # Map the stored direction value to the correct display value
            display_value = ""
            if fixture.direction == "UP":
                display_value = "↑"
            elif fixture.direction == "DOWN":
                display_value = "↓"

            direction_combo.setCurrentText(display_value)
            self.tableWidget.setCellWidget(row, 8, direction_combo)

        self.update_row_colors()

    def update_show_tab_from_config(self):
        """Update show tab when switching to it or when configuration changes"""
        # Clear existing table
        self.tableWidget_3.setRowCount(0)

        # Get current show from combo box
        current_show = self.comboBox.currentText()
        if not current_show or current_show not in self.config.shows:
            return

        show = self.config.shows[current_show]

        # Set up headers if not already done
        headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color', 'Intensity', 'Spot']
        if self.tableWidget_3.columnCount() != len(headers):
            self.tableWidget_3.setColumnCount(len(headers))
            self.tableWidget_3.setHorizontalHeaderLabels(headers)
        # Set column widths for shows table
        self.tableWidget_3.setColumnWidth(0, 250)  # Show Part
        self.tableWidget_3.setColumnWidth(1, 250)  # Fixture Group
        self.tableWidget_3.setColumnWidth(2, 200)  # Effect
        self.tableWidget_3.setColumnWidth(3, 50)  # Speed
        self.tableWidget_3.setColumnWidth(4, 100)  # Color
        self.tableWidget_3.setColumnWidth(5, 200)  # Intensity
        self.tableWidget_3.setColumnWidth(6, 75)  # Spot

        # Add rows for each show part and fixture group combination
        row = 0
        for show_part in show.parts:
            for group_name in sorted(self.config.groups.keys()):
                self.tableWidget_3.insertRow(row)

                # Show Part (read-only)
                show_part_item = QtWidgets.QTableWidgetItem(show_part.name)
                show_part_item.setFlags(show_part_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.tableWidget_3.setItem(row, 0, show_part_item)

                # Fixture Group (read-only)
                group_item = QtWidgets.QTableWidgetItem(group_name)
                group_item.setFlags(group_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.tableWidget_3.setItem(row, 1, group_item)

                # Find existing effect for this combination
                existing_effect = next(
                    (effect for effect in show.effects
                     if effect.show_part == show_part.name
                     and effect.fixture_group == group_name),
                    None
                )

                # Effect button
                effect_button = QtWidgets.QPushButton()
                if existing_effect and existing_effect.effect:
                    effect_button.setText(existing_effect.effect)
                else:
                    effect_button.setText("Select Effect")

                def create_effect_handler(current_row, part_name, group):
                    def handle_effect():
                        dialog = EffectSelectionDialog(self.effects_dir, self)
                        if dialog.exec() == QDialog.DialogCode.Accepted:
                            effect = dialog.get_selected_effect()
                            button = self.tableWidget_3.cellWidget(current_row, 2)
                            if effect == "CLEAR":
                                button.setText("Select Effect")
                            else:
                                button.setText(effect)
                            self.update_show_effect(current_show, part_name, group,
                                                    effect or "",
                                                    self.get_speed(current_row),
                                                    self.get_color(current_row),
                                                    self.get_intensity(current_row),
                                                    self.get_spot(current_row))

                    return handle_effect

                effect_button.clicked.connect(
                    create_effect_handler(row, show_part.name, group_name)
                )
                self.tableWidget_3.setCellWidget(row, 2, effect_button)

                # Speed combo box
                speed_combo = QtWidgets.QComboBox()
                speed_values = ['1/32', '1/16', '1/8', '1/4', '1/2', '1', '2', '4', '8', '16', '32']
                speed_combo.addItems(speed_values)
                if existing_effect:
                    speed_combo.setCurrentText(existing_effect.speed)
                else:
                    speed_combo.setCurrentText('1')

                speed_combo.currentTextChanged.connect(
                    lambda value, r=row: self.update_show_effect(
                        current_show,
                        show_part.name,
                        group_name,
                        self.get_effect(r),
                        value,
                        self.get_color(r),
                        self.get_intensity(r),
                        self.get_spot(r)
                    )
                )
                self.tableWidget_3.setCellWidget(row, 3, speed_combo)

                # Color button
                color_button = QtWidgets.QPushButton()
                color_button.setFixedHeight(25)

                if existing_effect and existing_effect.color:
                    color_button.setStyleSheet(f"background-color: {existing_effect.color};")
                    color_button.setText(existing_effect.color)
                else:
                    color_button.setText("Pick Color")

                def create_color_handler(current_row, part_name, group):
                    def handle_color():
                        button = self.tableWidget_3.cellWidget(current_row, 4)
                        color = QtWidgets.QColorDialog.getColor(
                            initial=QtGui.QColor(existing_effect.color if existing_effect.color is not None else "#000000"),
                            options=QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel
                        )
                        if color.isValid():
                            hex_color = color.name().upper()
                            button.setStyleSheet(f"background-color: {hex_color};")
                            button.setText(hex_color)
                            self.update_show_effect(current_show, part_name, group,
                                                    self.get_effect(current_row),
                                                    self.get_speed(current_row),
                                                    hex_color,
                                                    self.get_intensity(current_row),
                                                    self.get_spot(current_row))

                    return handle_color

                color_button.clicked.connect(
                    create_color_handler(row, show_part.name, group_name)
                )
                self.tableWidget_3.setCellWidget(row, 4, color_button)

                # Intensity control
                intensity_widget = QtWidgets.QWidget()
                intensity_layout = QtWidgets.QHBoxLayout(intensity_widget)
                intensity_layout.setContentsMargins(2, 2, 2, 2)

                # Create slider
                intensity_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
                intensity_slider.setMinimum(0)
                intensity_slider.setMaximum(255)
                intensity_slider.setValue(200)  # Default value
                intensity_slider.setFixedWidth(100)

                # Create spinbox
                intensity_spinbox = QtWidgets.QSpinBox()
                intensity_spinbox.setMinimum(0)
                intensity_spinbox.setMaximum(255)
                intensity_spinbox.setValue(200)  # Default value
                intensity_spinbox.setFixedWidth(50)

                # Set initial values based on existing effect
                if existing_effect and existing_effect.intensity is not None:
                    intensity_slider.setValue(existing_effect.intensity)
                    intensity_spinbox.setValue(existing_effect.intensity)
                else:
                    intensity_slider.setValue(200)  # Default value
                    intensity_spinbox.setValue(200)  # Default value

                intensity_layout.addWidget(intensity_slider)
                intensity_layout.addWidget(intensity_spinbox)

                def create_intensity_handler(current_row, part_name, group):
                    def handle_intensity(value):
                        self.update_show_effect(
                            current_show,
                            part_name,
                            group,
                            self.get_effect(current_row),
                            self.get_speed(current_row),
                            self.get_color(current_row),
                            value,
                            self.get_spot(current_row)
                        )

                    return handle_intensity

                # Connect the controls to each other
                intensity_slider.valueChanged.connect(intensity_spinbox.setValue)
                intensity_spinbox.valueChanged.connect(intensity_slider.setValue)

                # Connect to the effect handler
                handler = create_intensity_handler(row, show_part.name, group_name)
                intensity_slider.valueChanged.connect(handler)

                self.tableWidget_3.setCellWidget(row, 5, intensity_widget)

                # Add Spot combo box
                spot_combo = QtWidgets.QComboBox()
                spot_combo.addItem("")  # Empty option
                if hasattr(self.config, 'spots'):
                    for spot_name in sorted(self.config.spots.keys()):
                        spot_combo.addItem(spot_name)

                # Set existing spot if any
                if existing_effect and hasattr(existing_effect, 'spot'):
                    spot_combo.setCurrentText(existing_effect.spot)

                def create_spot_handler(current_row, part_name, group):
                    def handle_spot_change(spot_name):
                        self.update_show_effect(
                            current_show,
                            part_name,
                            group,
                            self.get_effect(current_row),
                            self.get_speed(current_row),
                            self.get_color(current_row),
                            self.get_intensity(current_row),
                            spot_name
                        )

                    return handle_spot_change

                spot_combo.currentTextChanged.connect(
                    create_spot_handler(row, show_part.name, group_name)
                )
                self.tableWidget_3.setCellWidget(row, 6, spot_combo)

                # Set row background color based on show part
                qcolor = QtGui.QColor(show_part.color)
                qcolor.setAlpha(40)
                for col in range(5):
                    item = self.tableWidget_3.item(row, col)
                    if item:
                        item.setBackground(qcolor)

                row += 1

    def get_effect(self, row):
        """Get effect from table row"""
        button = self.tableWidget_3.cellWidget(row, 2)
        if button:
            text = button.text()
            return text if text != "Select Effect" else ""
        return ""

    def get_speed(self, row):
        """Get speed from table row"""
        combo = self.tableWidget_3.cellWidget(row, 3)
        return combo.currentText() if combo else "1"

    def get_color(self, row):
        """Get color from table row"""
        button = self.tableWidget_3.cellWidget(row, 4)
        if button:
            stylesheet = button.styleSheet()
            if "background-color:" in stylesheet:
                color = stylesheet.split("background-color:")[1].strip("; ")
                return color
        return ""

    def get_intensity(self, row):
        """Get intensity value from table row"""
        intensity_widget = self.tableWidget_3.cellWidget(row, 5)
        if intensity_widget:
            # Get the spinbox from the layout (second widget)
            layout = intensity_widget.layout()
            if layout:
                spinbox_item = layout.itemAt(1)
                if spinbox_item:
                    spinbox = spinbox_item.widget()
                    if isinstance(spinbox, QtWidgets.QSpinBox):
                        return spinbox.value()
                    # Fallback to slider if spinbox not found
                    slider_item = layout.itemAt(0)
                    if slider_item:
                        slider = slider_item.widget()
                        if isinstance(slider, QtWidgets.QSlider):
                            return slider.value()
        return 200  # Default value if widget not found

    def get_spot(self, row):
        """Get spot from table row"""
        spot_combo = self.tableWidget_3.cellWidget(row, 6)
        return spot_combo.currentText() if spot_combo else ""

    def update_show_effect(self, show_name, show_part, fixture_group, effect, speed, color, intensity=200, spot=""):
        """Update show effect in configuration"""
        if show_name not in self.config.shows:
            return

        show = self.config.shows[show_name]
        updated = False

        # Update existing effect if found
        for effect_obj in show.effects:
            if (effect_obj.show_part == show_part and
                    effect_obj.fixture_group == fixture_group):
                effect_obj.effect = effect
                effect_obj.speed = speed
                effect_obj.color = color
                effect_obj.intensity = intensity
                effect_obj.spot = spot
                updated = True
                break

        # Create new effect if not found
        if not updated:
            new_effect = ShowEffect(
                show_part=show_part,
                fixture_group=fixture_group,
                effect=effect,
                speed=speed,
                color=color,
                intensity=intensity,
                spot=spot
            )
            show.effects.append(new_effect)

        # Update the show in the configuration
        self.config.shows[show_name] = show

    def _setup_tables(self):
        # Setup Fixtures table
        headers = ['Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode', 'Name', 'Group', 'Direction']
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setHorizontalHeaderLabels(headers)

        # Set column widths
        self.tableWidget.setColumnWidth(0, 70)  # Universe
        self.tableWidget.setColumnWidth(1, 70)  # Address
        self.tableWidget.setColumnWidth(2, 200)  # Manufacturer
        self.tableWidget.setColumnWidth(3, 200)  # Model
        self.tableWidget.setColumnWidth(4, 70)  # Channels
        self.tableWidget.setColumnWidth(5, 150)  # Mode
        self.tableWidget.setColumnWidth(6, 150)  # Name
        self.tableWidget.setColumnWidth(7, 150)  # Group
        self.tableWidget.setColumnWidth(8, 80)  # Direction

        # Store existing groups
        self.existing_groups = set()

        # Make the table fill the available space
        self.tableWidget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                       QtWidgets.QSizePolicy.Policy.Expanding)
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        # Setup Shows table
        show_headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color', 'Intensity', 'Spot']
        self.tableWidget_3.setColumnCount(len(show_headers))
        self.tableWidget_3.setHorizontalHeaderLabels(show_headers)

        # Set column widths for shows table
        self.tableWidget_3.setColumnWidth(0, 250)  # Show Part
        self.tableWidget_3.setColumnWidth(1, 250)  # Fixture Group
        self.tableWidget_3.setColumnWidth(2, 200)  # Effect
        self.tableWidget_3.setColumnWidth(3, 50)  # Speed
        self.tableWidget_3.setColumnWidth(4, 100)  # Color
        self.tableWidget_3.setColumnWidth(5, 200)  # Intensity
        self.tableWidget_3.setColumnWidth(6, 75)  # Spot
        #self.tableWidget_3.horizontalHeader().setStretchLastSection(True)  # Intensity stretches

        # Make tableWidget_3 stretch to fill parent
        self.tableWidget_3.setGeometry(QtCore.QRect(10, 90, self.tab_2.width() - 20, self.tab_2.height() - 100))

        # Make table resize with parent
        def resize_table(event):
            self.tableWidget_3.setGeometry(QtCore.QRect(10, 90, event.size().width() - 20, event.size().height() - 100))

        # Connect resize event to the tab
        self.tab_2.resizeEvent = resize_table

        # Make columns stretch to fill table width
        header = self.tableWidget_3.horizontalHeader()
        for i in range(5):  # 5 columns: Show Part, Fixture Group, Effect, Speed, Color
            if i == 4:  # Last column (Color)
                header.setStretchLastSection(True)
            else:
                header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.Interactive)

        # Enable sorting and styling for all tables
        for table in [self.tableWidget, self.tableWidget_3]:
            table.setSortingEnabled(True)
            table.setShowGrid(True)
            table.setAlternatingRowColors(True)
            table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

    def update_row_colors(self):
        for row in range(self.tableWidget.rowCount()):
            group_combo = self.tableWidget.cellWidget(row, 7)  # Group column
            if group_combo:
                group_name = group_combo.currentText()
                if group_name and group_name != "Add New...":
                    # Get or create color for group
                    if group_name not in self.group_colors:
                        self.group_colors[group_name] = self.predefined_colors[
                            self.color_index % len(self.predefined_colors)]
                        self.color_index += 1

                    color = self.group_colors[group_name]

                    # Ensure items exist for all columns before setting background
                    for col in range(self.tableWidget.columnCount()):
                        item = self.tableWidget.item(row, col)
                        if not item and not self.tableWidget.cellWidget(row, col):
                            # Create item if neither item nor widget exists
                            self.tableWidget.setItem(row, col, QtWidgets.QTableWidgetItem(""))

                        # Update item background if it exists
                        if item:
                            item.setBackground(color)

                        # Update widget background if it exists
                        cell_widget = self.tableWidget.cellWidget(row, col)
                        if cell_widget:
                            cell_widget.setStyleSheet(f"background-color: {color.name()};")

                    # Update the group color in configuration
                    if group_name in self.config.groups:
                        self.config.groups[group_name].color = color.name()

                else:
                    # Reset color if no group is selected or "Add New..." is selected
                    for col in range(self.tableWidget.columnCount()):
                        item = self.tableWidget.item(row, col)
                        if item:
                            item.setBackground(QtGui.QColor())
                        cell_widget = self.tableWidget.cellWidget(row, col)
                        if cell_widget:
                            cell_widget.setStyleSheet("")

    def add_fixture(self):
        try:
            # Setting up the fixtures dir, both for user and qlc provided fixtures
            qlc_fixture_dirs = []
            if sys.platform.startswith('linux'):
                qlc_fixture_dirs.extend([
                    '/usr/share/qlcplus/fixtures',
                    os.path.expanduser('~/.qlcplus/fixtures')
                ])
            elif sys.platform == 'win32':
                qlc_fixture_dirs.extend([
                    os.path.join(os.path.expanduser('~'), 'QLC+', 'fixtures'),  # User fixtures
                    'C:\\QLC+\\Fixtures'  # System-wide fixtures
                ])
            elif sys.platform == 'darwin':
                qlc_fixture_dirs.append(os.path.expanduser('~/Library/Application Support/QLC+/fixtures'))

            # Creating list of available fixtures
            fixture_files = []
            for qlc_fixtures_dir in qlc_fixture_dirs:
                if os.path.exists(qlc_fixtures_dir):
                    for root, dirs, files in os.walk(qlc_fixtures_dir):
                        for file in files:
                            if file.endswith('.qxf'):
                                manufacturer = os.path.basename(root)
                                fixture_files.append({
                                    'manufacturer': manufacturer,
                                    'model': os.path.splitext(file)[0],
                                    'path': os.path.join(root, file)
                                })
            if not fixture_files:
                raise Exception("No fixture files found in QLC+ directories")

            # Create the fixture selection dialog - popup window
            dialog = QDialog(self)
            dialog.setWindowTitle("Select Fixture")
            dialog.setModal(True)
            dialog.resize(600, 800)  # Make the dialog window larger
            layout = QtWidgets.QVBoxLayout()
            layout.setSpacing(10)  # Add some spacing between elements

            # Add a search box with larger font
            search_box = QLineEdit()
            search_box.setPlaceholderText("Search fixtures...")
            font = QtGui.QFont()
            font.setPointSize(12)  # Increase font size
            search_box.setFont(font)
            search_box.setMinimumHeight(40)  # Make the search box taller
            layout.addWidget(search_box)

            # List widget with larger font
            list_widget = QtWidgets.QListWidget()
            list_widget.setFont(font)  # Use the same larger font
            list_widget.setSpacing(4)  # Add spacing between items

            # Sort and add items
            fixture_files.sort(key=lambda x: (x['manufacturer'].lower(), x['model'].lower()))
            for fixture in fixture_files:
                item = QtWidgets.QListWidgetItem(f"{fixture['manufacturer']} - {fixture['model']}")
                item.setData(QtCore.Qt.ItemDataRole.UserRole, fixture['path'])
                list_widget.addItem(item)

            layout.addWidget(list_widget)

            def filter_fixtures():
                search_text = search_box.text().lower()
                for i in range(list_widget.count()):
                    item = list_widget.item(i)
                    item.setHidden(search_text not in item.text().lower())

            search_box.textChanged.connect(filter_fixtures)

            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok |
                QDialogButtonBox.StandardButton.Cancel
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            dialog.setLayout(layout)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_items = list_widget.selectedItems()
                if selected_items:
                    selected_fixture = selected_items[0]
                    fixture_path = selected_fixture.data(QtCore.Qt.ItemDataRole.UserRole)

                    # Parse fixture file and get basic info
                    tree = ET.parse(fixture_path)
                    root = tree.getroot()
                    ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

                    manufacturer = root.find('.//Manufacturer', ns).text
                    model = root.find('.//Model', ns).text
                    fixture_type = determine_fixture_type(root)

                    # Get modes
                    modes = root.findall('.//Mode', ns)
                    mode_data = [{'name': mode.get('Name'), 'channels': len(mode.findall('Channel', ns))}
                                 for mode in modes]

                    # Create new row
                    row = self.tableWidget.rowCount()
                    self.tableWidget.insertRow(row)

                    def update_fixture_configuration():
                        """Update fixture and group configuration when any property changes"""
                        fixture = self.config.fixtures[row]
                        old_group = fixture.group

                        # Update fixture properties
                        fixture.universe = universe_spin.value()
                        fixture.address = address_spin.value()
                        fixture.name = self.tableWidget.item(row, 6).text() or model
                        fixture.group = group_combo.currentText() if group_combo.currentText() not in ["",
                                                                                                       "Add New..."] else ""
                        fixture.direction = direction_combo.currentText()
                        fixture.current_mode = mode_data[mode_combo.currentIndex()]['name']

                        # Handle group changes
                        if old_group != fixture.group:
                            # Remove from old group
                            if old_group and old_group in self.config.groups:
                                old_group_fixtures = self.config.groups[old_group].fixtures
                                old_group_fixtures[:] = [f for f in old_group_fixtures if f != fixture]

                            # Add to new group
                            if fixture.group and fixture.group in self.config.groups:
                                group = self.config.groups[fixture.group]
                                group.fixtures.append(fixture)

                                # The color is already set in the group configuration when the group was created
                                # No need to try to get it from the table items

                        self.update_row_colors()

                    # Create spinboxes and comboboxes
                    universe_spin = QtWidgets.QSpinBox()
                    universe_spin.setRange(1, 16)
                    universe_spin.setValue(1)

                    address_spin = QtWidgets.QSpinBox()
                    address_spin.setRange(1, 512)
                    address_spin.setValue(1)

                    # Create mode combo
                    mode_combo = QtWidgets.QComboBox()
                    for mode in mode_data:
                        mode_combo.addItem(f"{mode['name']} ({mode['channels']}ch)")

                    def update_channels(index):
                        channels_item = QtWidgets.QTableWidgetItem(str(mode_data[index]['channels']))
                        self.tableWidget.setItem(row, 4, channels_item)
                        update_fixture_configuration()

                    def sync_universe(value):
                        if universe_spin.value() != value:
                            universe_spin.setValue(value)
                        update_fixture_configuration()

                    def sync_address(value):
                        if address_spin.value() != value:
                            address_spin.setValue(value)
                        update_fixture_configuration()

                    # Connect change handlers
                    universe_spin.valueChanged.connect(sync_universe)
                    address_spin.valueChanged.connect(sync_address)
                    mode_combo.currentIndexChanged.connect(update_channels)

                    # Set up table widgets
                    self.tableWidget.setCellWidget(row, 0, universe_spin)
                    self.tableWidget.setCellWidget(row, 1, address_spin)
                    self.tableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(manufacturer))
                    self.tableWidget.setItem(row, 3, QtWidgets.QTableWidgetItem(model))
                    self.tableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem(str(mode_data[0]['channels'])))
                    self.tableWidget.setCellWidget(row, 5, mode_combo)

                    # Name field
                    name_item = QtWidgets.QTableWidgetItem("")
                    self.tableWidget.setItem(row, 6, name_item)
                    name_item.setFlags(name_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)

                    # Group combo
                    group_combo = QtWidgets.QComboBox()
                    group_combo.addItem("")
                    for group in sorted(self.existing_groups):
                        group_combo.addItem(group)
                    group_combo.addItem("Add New...")

                    def handle_group_selection(index):
                        if group_combo.currentText() == "Add New...":
                            dialog = QDialog(self)
                            dialog.setWindowTitle("Add New Group")
                            layout = QFormLayout()
                            new_group_input = QLineEdit()
                            layout.addRow("Group Name:", new_group_input)

                            button_box = QDialogButtonBox(
                                QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel
                            )
                            button_box.accepted.connect(dialog.accept)
                            button_box.rejected.connect(dialog.reject)
                            layout.addWidget(button_box)
                            dialog.setLayout(layout)

                            if dialog.exec() == QDialog.DialogCode.Accepted:
                                new_group = new_group_input.text().strip()
                                if new_group:
                                    color = self.predefined_colors[self.color_index % len(self.predefined_colors)]
                                    self.color_index += 1

                                    fixture_group = FixtureGroup(
                                        name=new_group,
                                        color=color.name(),
                                        fixtures=[]
                                    )

                                    self.config.groups[new_group] = fixture_group
                                    self.existing_groups.add(new_group)

                                    # Update UI
                                    current_index = group_combo.findText("Add New...")
                                    group_combo.removeItem(current_index)
                                    group_combo.addItem(new_group)
                                    group_combo.addItem("Add New...")
                                    group_combo.setCurrentText(new_group)

                        update_fixture_configuration()

                    group_combo.currentIndexChanged.connect(handle_group_selection)
                    self.tableWidget.setCellWidget(row, 7, group_combo)

                    # Direction combo
                    direction_combo = QtWidgets.QComboBox()
                    direction_combo.addItems(["", "↑", "↓"])

                    def update_direction(index):
                        # Convert display value to standardized value
                        display_value = direction_combo.currentText()
                        if display_value == "↑":
                            self.config.fixtures[row].direction = "UP"
                        elif display_value == "↓":
                            self.config.fixtures[row].direction = "DOWN"
                        else:
                            self.config.fixtures[row].direction = "NONE"
                        update_fixture_configuration()

                    direction_combo.currentIndexChanged.connect(update_direction)
                    self.tableWidget.setCellWidget(row, 8, direction_combo)

                    # Create initial fixture object
                    new_fixture = Fixture(
                        universe=universe_spin.value(),
                        address=address_spin.value(),
                        manufacturer=manufacturer,
                        model=model,
                        name=model,
                        group="",
                        direction="",
                        current_mode=mode_data[0]['name'],
                        available_modes=[FixtureMode(name=mode['name'], channels=mode['channels'])
                                         for mode in mode_data],
                        type=fixture_type,
                        x=0.0,
                        y=0.0,
                        z=0.0,
                        rotation=0.0
                    )

                    # Add to configuration
                    self.config.fixtures.append(new_fixture)

                    # Connect name changes
                    #def handle_name_change(item):
                    #    if item.column() == 6 and item.row() == row:
                    #        update_fixture_configuration()
                    #
                    #self.tableWidget.itemChanged.connect(handle_name_change)

                    print(f"Added fixture to table: {manufacturer} {model}")


        except Exception as e:
            print(f"Error adding fixture: {e}")
            import traceback
            traceback.print_exc()

    def remove_fixture(self):
        selected_rows = self.tableWidget.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()

            # Remove the fixture from the configuration
            if row < len(self.config.fixtures):
                # Get the fixture that's being deleted
                fixture = self.config.fixtures[row]

                # If it belongs to a group, remove it from the group
                if fixture.group and fixture.group in self.config.groups:
                    group = self.config.groups[fixture.group]
                    group.fixtures = [f for f in group.fixtures if f != fixture]

                    # If the group is now empty, remove it
                    if not group.fixtures:
                        del self.config.groups[fixture.group]

                # Remove the fixture from the configuration
                self.config.fixtures.pop(row)

            # Remove the row from the table
            self.tableWidget.removeRow(row)

            # Clean up fixture paths if needed
            if row < len(self.fixture_paths):
                self.fixture_paths.pop(row)

            # Update the groups to ensure consistency
            self.update_groups()

            # Update row colors to reflect any group changes
            self.update_row_colors()

    def import_workspace(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select QLC+ Workspace",
            "",
            "QLC+ Workspace Files (*.qxw)"
        )
        if file_path:
            self.extract_from_workspace(file_path)

    def extract_from_workspace(self, workspace_path):
        """Extract configuration from workspace file"""
        try:
            # Load configuration from workspace
            self.config = Configuration.from_workspace(workspace_path)

            # Import show structure into configuration
            self.config = Configuration.import_show_structure(self.config, os.path.dirname(workspace_path))

            # Update UI
            self.update_fixture_tab_from_config()
            self.update_show_tab_from_config()

            # Update stage view with new configuration
            self.stage_view.set_config(self.config)

            # Initialize universes if none exist in the loaded configuration
            if not hasattr(self.config, 'universes') or not self.config.universes:
                self.config.universes = {}
                self.config.initialize_default_universes()

            # Update universe table
            self.load_universes_to_table()

            # Initialize combo box with shows
            if self.config.shows:
                self.comboBox.clear()
                self.comboBox.addItems(sorted(self.config.shows.keys()))

                # Connect combo box selection to table update
                self.comboBox.currentTextChanged.connect(self.update_show_tab_from_config)

                # Initialize table with first show if available
                if self.comboBox.count() > 0:
                    first_show = self.comboBox.itemText(0)
                    self.comboBox.setCurrentText(first_show)
                    self.update_show_tab_from_config()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process workspace: {str(e)}")
            import traceback
            traceback.print_exc()

    # Show Tab -----------------------------------------
    def import_show_structure(self):
        try:
            # Set up fixed columns
            headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color', 'Intensity', 'Spot']
            self.tableWidget_3.setColumnCount(len(headers))
            self.tableWidget_3.setHorizontalHeaderLabels(headers)

            # Get all show directories
            shows_dir = os.path.join(self.project_root, "shows")

            # Scan for all show structure files
            for file in os.listdir(shows_dir):
                if file.endswith('.csv'):
                    show_name = os.path.splitext(file)[0]  # Remove .csv extension
                    structure_file = os.path.join(shows_dir, file)

                    # Create new Show object
                    show = Show(name=show_name)

                    with open(structure_file, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Create ShowPart with default white color
                            show_part = ShowPart(
                                name=row['showpart'],
                                color=row['color'],
                                signature=row['signature'],
                                bpm=row['bpm'],
                                num_bars=row['num_bars'],
                                transition=row['transition']
                            )
                            # Add part to show
                            show.parts.append(show_part)

                            # Create empty effects for each group
                            for group_name in self.config.groups.keys():
                                effect = ShowEffect(
                                    show_part=show_part.name,
                                    fixture_group=group_name,
                                    effect="",
                                    speed="1",
                                    color="",
                                    intensity=200,
                                    spot=""
                                )
                                show.effects.append(effect)

                    # Add show to configuration
                    self.config.shows[show_name] = show

            # Update combo box with available shows
            self.comboBox.clear()
            self.comboBox.addItems(sorted(self.config.shows.keys()))

            # Connect combo box selection to table update
            self.comboBox.currentTextChanged.connect(self.update_show_tab_from_config)

            # Initialize table with first show if available
            if self.comboBox.count() > 0:
                first_show = self.comboBox.itemText(0)
                self.update_show_tab_from_config()

            print("Show structure imported successfully")

        except Exception as e:
            print(f"Error importing show structure: {e}")
            import traceback
            traceback.print_exc()

    def _scan_fixture_definitions(self, required_models: set) -> dict:
        """Scan QLC+ fixture definitions for required models"""
        fixture_definitions = {}

        # Get QLC+ fixture directories based on platform
        qlc_fixture_dirs = self._get_qlc_fixture_dirs()

        for dir_path in qlc_fixture_dirs:
            if not os.path.exists(dir_path):
                continue

            for manufacturer_dir in os.listdir(dir_path):
                manufacturer_path = os.path.join(dir_path, manufacturer_dir)
                if not os.path.isdir(manufacturer_path):
                    continue

                for fixture_file in os.listdir(manufacturer_path):
                    if not fixture_file.endswith('.qxf'):
                        continue

                    fixture_path = os.path.join(manufacturer_path, fixture_file)
                    try:
                        definition = self._parse_fixture_definition(fixture_path)
                        if (definition['manufacturer'], definition['model']) in required_models:
                            key = f"{definition['manufacturer']}_{definition['model']}"
                            fixture_definitions[key] = definition
                    except Exception as e:
                        print(f"Error parsing fixture file {fixture_path}: {e}")

        return fixture_definitions

    def _get_qlc_fixture_dirs(self) -> List[str]:
        """Get QLC+ fixture directories based on platform"""
        if sys.platform.startswith('linux'):
            return [
                '/usr/share/qlcplus/fixtures',
                os.path.expanduser('~/.qlcplus/')
            ]
        elif sys.platform == 'win32':
            return [
                os.path.join(os.path.expanduser('~'), 'QLC+'),
                'C:\\QLC+\\Fixtures'
            ]
        elif sys.platform == 'darwin':
            return [
                os.path.expanduser('~/Library/Application Support/QLC+/fixtures')
            ]
        return []

    def _parse_fixture_definition(self, fixture_path: str) -> dict:
        """Parse QLC+ fixture definition file"""
        tree = ET.parse(fixture_path)
        root = tree.getroot()
        ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

        manufacturer = root.find('.//Manufacturer', ns).text
        model = root.find('.//Model', ns).text

        channels_info = []
        for channel in root.findall('.//Channel', ns):
            channel_data = {
                'name': channel.get('Name'),
                'preset': channel.get('Preset'),
                'group': channel.find('Group', ns).text if channel.find('Group', ns) else None,
                'capabilities': [
                    {
                        'min': int(cap.get('Min')),
                        'max': int(cap.get('Max')),
                        'preset': cap.get('Preset'),
                        'name': cap.text
                    }
                    for cap in channel.findall('Capability', ns)
                ]
            }
            channels_info.append(channel_data)

        modes_info = [
            {
                'name': mode.get('Name'),
                'channels': [
                    {
                        'number': int(ch.get('Number')),
                        'name': ch.text
                    }
                    for ch in mode.findall('Channel', ns)
                ]
            }
            for mode in root.findall('.//Mode', ns)
        ]

        return {
            'manufacturer': manufacturer,
            'model': model,
            'channels': channels_info,
            'modes': modes_info
        }

    def setup_tab_connections(self):
        """Set up tab change connections"""
        self.tabWidget.currentChanged.connect(self.handle_tab_change)

    def handle_tab_change(self, index):
        """Handle tab changes"""
        if self.tabWidget.tabText(index) == "Shows":
            self.update_show_tab_from_config()

    def save_show(self):
        """Save all effects for the current show"""
        current_show = self.comboBox.currentText()
        if not current_show:
            return

        # Iterate through all rows in the table
        for row in range(self.tableWidget_3.rowCount()):
            # Get show part name from column 0
            show_part = self.tableWidget_3.item(row, 0).text()

            # Get fixture group from column 1
            fixture_group = self.tableWidget_3.item(row, 1).text()

            # Get effect from column 2
            effect = self.get_effect(row)

            # Get speed from column 3
            speed = self.get_speed(row)

            # Get color from column 4
            color = self.get_color(row)

            # Get intensity from column 5
            intensity = self.get_intensity(row)

            # Get spot from column 6
            spot = self.get_spot(row)

            # Update the effect for this row
            self.update_show_effect(
                current_show,
                show_part,
                fixture_group,
                effect,
                speed,
                color,
                intensity,
                spot
            )
    # End of Show Tab ------------------------------------

    def save_configuration(self):
        """Save configuration to file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Configuration",
                "",
                "YAML Files (*.yaml);;All Files (*)"
            )

            if filename:
                self.config.save(filename)
                QMessageBox.information(self, "Success", "Configuration saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")

    def load_configuration(self):
        """Load configuration from file"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Load Configuration",
                "",
                "YAML Files (*.yaml);;All Files (*)"
            )

            if filename:
                # Load configuration
                self.config = Configuration.load(filename)

                # Initialize universes if none exist in loaded configuration
                if not hasattr(self.config, 'universes'):
                    self.config.universes = {}
                    self.config.initialize_default_universes()

                # Clear and update the universe table
                self.universe_list.setRowCount(0)
                self.load_universes_to_table()

                # Update other UI elements
                self.update_fixture_tab_from_config()
                self.update_show_tab_from_config()

                # Update stage view with new configuration
                self.stage_view.set_config(self.config)

                # Update combo box with shows if they exist
                if hasattr(self.config, 'shows') and self.config.shows:
                    self.comboBox.clear()
                    self.comboBox.addItems(sorted(self.config.shows.keys()))

                    # Initialize table with first show if available
                    if self.comboBox.count() > 0:
                        first_show = self.comboBox.itemText(0)
                        self.comboBox.setCurrentText(first_show)
                        self.update_show_tab_from_config()

                QMessageBox.information(self, "Success", "Configuration loaded successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load configuration: {str(e)}")
            import traceback
            traceback.print_exc()  # This will print the full error trace to console

    # Universe Handling for Configuration Tab--------------
    def add_universe_config(self):
        """Add a new universe configuration"""
        row = self.universe_list.rowCount()
        universe_id = row + 1

        # Add new universe to configuration
        self.config.add_universe(
            universe_id=universe_id,
            output_type='E1.31',
            ip=f'192.168.1.{universe_id}',
            port='6454',
            subnet='0',
            universe=str(universe_id)
        )

        # Update table
        self.load_universes_to_table()

    def remove_universe_config(self):
        """Remove selected universe configuration"""
        current_row = self.universe_list.currentRow()
        if current_row >= 0:
            universe_id = int(self.universe_list.item(current_row, 0).text())
            if universe_id in self.config.universes:
                self.config.remove_universe(universe_id)
            self.universe_list.removeRow(current_row)

    def load_universes_to_table(self):
        """Load universes from configuration to table"""
        # Clear the table first
        self.universe_list.setRowCount(0)

        if hasattr(self.config, 'universes'):
            for universe_id, universe in self.config.universes.items():
                row = self.universe_list.rowCount()
                self.universe_list.insertRow(row)

                # Universe ID
                self.universe_list.setItem(row, 0, QtWidgets.QTableWidgetItem(str(universe.id)))

                # Output type combo
                output_combo = QtWidgets.QComboBox()
                output_combo.addItems(["E1.31", "ArtNet", "DMX"])
                output_combo.setCurrentText(universe.output.get('plugin', 'E1.31'))
                output_combo.currentTextChanged.connect(lambda text, r=row: self.on_output_type_changed(r))
                self.universe_list.setCellWidget(row, 1, output_combo)

                # Parameters
                params = universe.output.get('parameters', {})
                self.universe_list.setItem(row, 2, QtWidgets.QTableWidgetItem(params.get('ip', '')))
                self.universe_list.setItem(row, 3, QtWidgets.QTableWidgetItem(params.get('port', '')))
                self.universe_list.setItem(row, 4, QtWidgets.QTableWidgetItem(params.get('subnet', '')))
                self.universe_list.setItem(row, 5, QtWidgets.QTableWidgetItem(params.get('universe', '')))

    def on_universe_item_changed(self, item):
        """Handle changes to universe table items"""
        row = item.row()
        col = item.column()
        universe_id = int(self.universe_list.item(row, 0).text())

        if universe_id in self.config.universes:
            # Update the appropriate field based on the column
            if col == 2:  # IP Address
                self.config.universes[universe_id].output['parameters']['ip'] = item.text()
            elif col == 3:  # Port
                self.config.universes[universe_id].output['parameters']['port'] = item.text()
            elif col == 4:  # Subnet
                self.config.universes[universe_id].output['parameters']['subnet'] = item.text()
            elif col == 5:  # Universe
                self.config.universes[universe_id].output['parameters']['universe'] = item.text()

    def on_output_type_changed(self, row):
        """Handle output type changes"""
        output_type = self.universe_list.cellWidget(row, 1).currentText()
        universe_id = int(self.universe_list.item(row, 0).text())

        if universe_id in self.config.universes:
            self.config.universes[universe_id].output['plugin'] = output_type
    # End of Universe Tab----------------------------------


    def create_workspace(self):
        try:
            create_qlc_workspace(self.config)

            print("Workspace created successfully")
            QtWidgets.QMessageBox.information(
                self,
                "Success",
                "QLC+ workspace has been created successfully.",
                QtWidgets.QMessageBox.StandardButton.Ok
            )

        except Exception as e:
            print(f"Error creating workspace: {e}")
            import traceback
            traceback.print_exc()

            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to create workspace: {str(e)}",
                QtWidgets.QMessageBox.StandardButton.Ok
            )


def main():
    try:
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()  # Create an instance of our MainWindow class
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

