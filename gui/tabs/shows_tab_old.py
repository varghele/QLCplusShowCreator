# gui/tabs/shows_tab.py

import os
import csv
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QDialog
from config.models import Configuration, Show, ShowPart, ShowEffect
from gui.effect_selection import EffectSelectionDialog
from .base_tab import BaseTab


class ShowsTab(BaseTab):
    """Show structure and effects management tab

    Manages show structure (parts, timing), effect assignments per group,
    and CSV import for show structure. Provides matrix-style table with
    effects, colors, speeds, and intensities.
    """

    def __init__(self, config: Configuration, parent=None):
        """Initialize shows tab

        Args:
            config: Shared Configuration object
            parent: Parent widget (typically MainWindow)
        """
        self.effects_dir = "effects"
        self.project_root = os.getcwd()
        super().__init__(config, parent)

    def setup_ui(self):
        """Set up show management UI"""
        # Save Shows button
        self.save_btn = QtWidgets.QPushButton("Save Shows", parent=self)
        self.save_btn.setGeometry(QtCore.QRect(10, 20, 171, 31))

        # Update button
        self.update_btn = QtWidgets.QPushButton("Update", parent=self)
        self.update_btn.setGeometry(QtCore.QRect(200, 20, 101, 31))

        # Show selection combo box
        self.show_combo = QtWidgets.QComboBox(parent=self)
        self.show_combo.setGeometry(QtCore.QRect(10, 60, 171, 25))

        # Shows table
        self.table = QtWidgets.QTableWidget(parent=self)
        self.table.setGeometry(QtCore.QRect(10, 90, 1151, 701))

        # Setup table structure
        self._setup_table()

        # Load initial data
        self.update_from_config()

    def _setup_table(self):
        """Initialize table structure and properties"""
        headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color', 'Intensity', 'Spot']
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        # Set column widths
        self.table.setColumnWidth(0, 250)  # Show Part
        self.table.setColumnWidth(1, 250)  # Fixture Group
        self.table.setColumnWidth(2, 200)  # Effect
        self.table.setColumnWidth(3, 50)   # Speed
        self.table.setColumnWidth(4, 100)  # Color
        self.table.setColumnWidth(5, 200)  # Intensity
        self.table.setColumnWidth(6, 75)   # Spot

        # Table properties
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

    def connect_signals(self):
        """Connect widget signals to handlers"""
        self.save_btn.clicked.connect(self.save_to_config)
        self.update_btn.clicked.connect(self.update_from_config)
        self.show_combo.currentTextChanged.connect(self._on_show_changed)

    def update_from_config(self):
        """Refresh shows table from configuration"""
        # Update show combo box
        current_show = self.show_combo.currentText()
        self.show_combo.blockSignals(True)
        self.show_combo.clear()
        self.show_combo.addItems(sorted(self.config.shows.keys()))

        # Restore selection if possible
        if current_show and current_show in self.config.shows:
            self.show_combo.setCurrentText(current_show)

        self.show_combo.blockSignals(False)

        # Update table for current show
        self._populate_show_table()

    def _on_show_changed(self, show_name):
        """Handle show selection change"""
        self._populate_show_table()

    def _populate_show_table(self):
        """Populate table with show parts and effects"""
        # Clear table
        self.table.setRowCount(0)

        # Get current show
        current_show = self.show_combo.currentText()
        if not current_show or current_show not in self.config.shows:
            return

        show = self.config.shows[current_show]

        # Build table: one row per (show_part, fixture_group) combination
        row = 0
        for show_part in show.parts:
            for group_name in sorted(self.config.groups.keys()):
                self.table.insertRow(row)

                # Show Part (read-only)
                show_part_item = QtWidgets.QTableWidgetItem(show_part.name)
                show_part_item.setFlags(
                    show_part_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable
                )
                self.table.setItem(row, 0, show_part_item)

                # Fixture Group (read-only)
                group_item = QtWidgets.QTableWidgetItem(group_name)
                group_item.setFlags(
                    group_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable
                )
                self.table.setItem(row, 1, group_item)

                # Find existing effect for this combination
                existing_effect = next(
                    (effect for effect in show.effects
                     if effect.show_part == show_part.name
                     and effect.fixture_group == group_name),
                    None
                )

                # Effect button
                self._setup_effect_button(row, current_show, show_part.name,
                                         group_name, existing_effect)

                # Speed combo box
                self._setup_speed_combo(row, current_show, show_part.name,
                                       group_name, existing_effect)

                # Color button
                self._setup_color_button(row, current_show, show_part.name,
                                        group_name, existing_effect)

                # Intensity controls
                self._setup_intensity_controls(row, current_show, show_part.name,
                                              group_name, existing_effect)

                # Spot combo box
                self._setup_spot_combo(row, current_show, show_part.name,
                                      group_name, existing_effect)

                # Set row background color based on show part
                qcolor = QtGui.QColor(show_part.color)
                qcolor.setAlpha(40)
                for col in range(5):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(qcolor)

                row += 1

    def _setup_effect_button(self, row, show_name, part_name, group_name, existing_effect):
        """Create effect selection button for table cell"""
        effect_button = QtWidgets.QPushButton()
        if existing_effect and existing_effect.effect:
            effect_button.setText(existing_effect.effect)
        else:
            effect_button.setText("Select Effect")

        def handle_effect():
            dialog = EffectSelectionDialog(self.effects_dir, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                effect = dialog.get_selected_effect()
                if effect == "CLEAR":
                    effect_button.setText("Select Effect")
                else:
                    effect_button.setText(effect)
                self._update_show_effect(show_name, part_name, group_name,
                                       effect or "",
                                       self._get_speed(row),
                                       self._get_color(row),
                                       self._get_intensity(row),
                                       self._get_spot(row))

        effect_button.clicked.connect(handle_effect)
        self.table.setCellWidget(row, 2, effect_button)

    def _setup_speed_combo(self, row, show_name, part_name, group_name, existing_effect):
        """Create speed combo box for table cell"""
        speed_combo = QtWidgets.QComboBox()
        speed_values = ['1/32', '1/16', '1/8', '1/4', '1/2', '1', '2', '4', '8', '16', '32']
        speed_combo.addItems(speed_values)

        if existing_effect:
            speed_combo.setCurrentText(existing_effect.speed)
        else:
            speed_combo.setCurrentText('1')

        def handle_speed(value):
            self._update_show_effect(show_name, part_name, group_name,
                                   self._get_effect(row),
                                   value,
                                   self._get_color(row),
                                   self._get_intensity(row),
                                   self._get_spot(row))

        speed_combo.currentTextChanged.connect(handle_speed)
        self.table.setCellWidget(row, 3, speed_combo)

    def _setup_color_button(self, row, show_name, part_name, group_name, existing_effect):
        """Create color picker button for table cell"""
        color_button = QtWidgets.QPushButton()
        color_button.setFixedHeight(25)

        if existing_effect and existing_effect.color:
            color_button.setStyleSheet(f"background-color: {existing_effect.color};")
            color_button.setText(existing_effect.color)
        else:
            color_button.setText("Pick Color")

        def handle_color():
            initial_color = QtGui.QColor(
                existing_effect.color if existing_effect and existing_effect.color else "#000000"
            )
            color = QtWidgets.QColorDialog.getColor(
                initial=initial_color,
                options=QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel
            )
            if color.isValid():
                hex_color = color.name().upper()
                color_button.setStyleSheet(f"background-color: {hex_color};")
                color_button.setText(hex_color)
                self._update_show_effect(show_name, part_name, group_name,
                                       self._get_effect(row),
                                       self._get_speed(row),
                                       hex_color,
                                       self._get_intensity(row),
                                       self._get_spot(row))

        color_button.clicked.connect(handle_color)
        self.table.setCellWidget(row, 4, color_button)

    def _setup_intensity_controls(self, row, show_name, part_name, group_name, existing_effect):
        """Create intensity slider and spinbox for table cell"""
        intensity_widget = QtWidgets.QWidget()
        intensity_layout = QtWidgets.QHBoxLayout(intensity_widget)
        intensity_layout.setContentsMargins(2, 2, 2, 2)

        # Slider
        intensity_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        intensity_slider.setMinimum(0)
        intensity_slider.setMaximum(255)
        intensity_slider.setFixedWidth(100)

        # Spinbox
        intensity_spinbox = QtWidgets.QSpinBox()
        intensity_spinbox.setMinimum(0)
        intensity_spinbox.setMaximum(255)
        intensity_spinbox.setFixedWidth(50)

        # Set initial values
        initial_value = existing_effect.intensity if existing_effect and existing_effect.intensity is not None else 200
        intensity_slider.setValue(initial_value)
        intensity_spinbox.setValue(initial_value)

        intensity_layout.addWidget(intensity_slider)
        intensity_layout.addWidget(intensity_spinbox)

        # Connect controls to each other
        intensity_slider.valueChanged.connect(intensity_spinbox.setValue)
        intensity_spinbox.valueChanged.connect(intensity_slider.setValue)

        # Connect to effect handler
        def handle_intensity(value):
            self._update_show_effect(show_name, part_name, group_name,
                                   self._get_effect(row),
                                   self._get_speed(row),
                                   self._get_color(row),
                                   value,
                                   self._get_spot(row))

        intensity_slider.valueChanged.connect(handle_intensity)

        self.table.setCellWidget(row, 5, intensity_widget)

    def _setup_spot_combo(self, row, show_name, part_name, group_name, existing_effect):
        """Create spot selection combo box for table cell"""
        spot_combo = QtWidgets.QComboBox()
        spot_combo.addItem("")  # Empty option

        if hasattr(self.config, 'spots'):
            for spot_name in sorted(self.config.spots.keys()):
                spot_combo.addItem(spot_name)

        # Set existing spot if any
        if existing_effect and hasattr(existing_effect, 'spot'):
            spot_combo.setCurrentText(existing_effect.spot)

        def handle_spot_change(spot_name):
            self._update_show_effect(show_name, part_name, group_name,
                                   self._get_effect(row),
                                   self._get_speed(row),
                                   self._get_color(row),
                                   self._get_intensity(row),
                                   spot_name)

        spot_combo.currentTextChanged.connect(handle_spot_change)
        self.table.setCellWidget(row, 6, spot_combo)

    def _get_effect(self, row):
        """Get effect from table row"""
        button = self.table.cellWidget(row, 2)
        if button:
            text = button.text()
            return text if text != "Select Effect" else ""
        return ""

    def _get_speed(self, row):
        """Get speed from table row"""
        combo = self.table.cellWidget(row, 3)
        return combo.currentText() if combo else "1"

    def _get_color(self, row):
        """Get color from table row"""
        button = self.table.cellWidget(row, 4)
        if button:
            stylesheet = button.styleSheet()
            if "background-color:" in stylesheet:
                color = stylesheet.split("background-color:")[1].strip("; ")
                return color
        return ""

    def _get_intensity(self, row):
        """Get intensity value from table row"""
        intensity_widget = self.table.cellWidget(row, 5)
        if intensity_widget:
            layout = intensity_widget.layout()
            if layout:
                spinbox_item = layout.itemAt(1)
                if spinbox_item:
                    spinbox = spinbox_item.widget()
                    if isinstance(spinbox, QtWidgets.QSpinBox):
                        return spinbox.value()
        return 200  # Default value

    def _get_spot(self, row):
        """Get spot from table row"""
        spot_combo = self.table.cellWidget(row, 6)
        return spot_combo.currentText() if spot_combo else ""

    def _update_show_effect(self, show_name, show_part, fixture_group, effect,
                           speed, color, intensity=200, spot=""):
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

        # Update show in configuration
        self.config.shows[show_name] = show

    def save_to_config(self):
        """Save all effects for current show"""
        current_show = self.show_combo.currentText()
        if not current_show:
            return

        # Iterate through all rows and save effects
        for row in range(self.table.rowCount()):
            show_part = self.table.item(row, 0).text()
            fixture_group = self.table.item(row, 1).text()

            self._update_show_effect(
                current_show,
                show_part,
                fixture_group,
                self._get_effect(row),
                self._get_speed(row),
                self._get_color(row),
                self._get_intensity(row),
                self._get_spot(row)
            )

    def import_show_structure(self):
        """Import show structure from CSV files"""
        try:
            shows_dir = os.path.join(self.project_root, "shows")

            # Scan for CSV files
            for file in os.listdir(shows_dir):
                if file.endswith('.csv'):
                    show_name = os.path.splitext(file)[0]
                    structure_file = os.path.join(shows_dir, file)

                    # Create or update show
                    if show_name in self.config.shows:
                        show = self.config.shows[show_name]
                        show.parts.clear()
                    else:
                        show = Show(name=show_name)
                        self.config.shows[show_name] = show

                    # Read CSV and create show parts
                    with open(structure_file, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            show_part = ShowPart(
                                name=row['showpart'],
                                color=row['color'],
                                signature=row['signature'],
                                bpm=float(row['bpm']),
                                num_bars=int(row['num_bars']),
                                transition=row['transition']
                            )
                            show.parts.append(show_part)

                            # Create empty effects for each group
                            for group_name in self.config.groups.keys():
                                existing_effect = next(
                                    (e for e in show.effects
                                     if e.show_part == show_part.name
                                     and e.fixture_group == group_name),
                                    None
                                )

                                # Create new effect if none exists
                                if existing_effect is None:
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

            # Update UI
            self.update_from_config()

            print("Show structure imported successfully")

        except Exception as e:
            print(f"Error importing show structure: {e}")
            import traceback
            traceback.print_exc()
