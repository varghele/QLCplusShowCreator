# gui/tabs/fixtures_tab.py

import os
import sys
import xml.etree.ElementTree as ET
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
from PyQt6.QtGui import QFont
from config.models import Configuration, Fixture, FixtureMode, FixtureGroup
from utils.fixture_utils import determine_fixture_type
from .base_tab import BaseTab


class FixturesTab(BaseTab):
    """Fixture inventory and group management tab

    Handles fixture CRUD operations, QLC+ fixture scanning, group management,
    and color-coded table display. This is the central tab for fixture configuration.
    """

    def __init__(self, config: Configuration, parent=None):
        """Initialize fixtures tab

        Args:
            config: Shared Configuration object
            parent: Parent widget (typically MainWindow)
        """
        # Initialize color management before super().__init__()
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
            QtGui.QColor(230, 230, 250)   # Lavender
        ]
        self.existing_groups = set()
        self.fixture_paths = []

        super().__init__(config, parent)

    def setup_ui(self):
        """Set up fixture management UI"""
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Button toolbar
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setSpacing(8)

        # Add Fixture button
        self.add_btn = QtWidgets.QPushButton("+")
        self.add_btn.setFixedSize(31, 31)
        self.add_btn.setToolTip("Add Fixture")
        toolbar.addWidget(self.add_btn)

        # Remove Fixture button
        self.remove_btn = QtWidgets.QPushButton("-")
        self.remove_btn.setFixedSize(31, 31)
        self.remove_btn.setToolTip("Remove Fixture")
        toolbar.addWidget(self.remove_btn)

        # Duplicate Fixture button
        self.duplicate_btn = QtWidgets.QPushButton("⎘")
        self.duplicate_btn.setFixedSize(31, 31)
        self.duplicate_btn.setToolTip("Duplicate Fixture")
        toolbar.addWidget(self.duplicate_btn)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Fixtures label
        self.label = QtWidgets.QLabel("Fixtures")
        self.label.setFont(QFont("", 14, QFont.Weight.Bold))
        main_layout.addWidget(self.label)

        # Fixtures table
        self.table = QtWidgets.QTableWidget()

        # Setup table structure
        self._setup_table()

        main_layout.addWidget(self.table)

        # Load initial data
        self.update_from_config()

    def _setup_table(self):
        """Initialize table structure and properties"""
        headers = ['Universe', 'Address', 'Manufacturer', 'Model', 'Channels',
                   'Mode', 'Name', 'Group', 'Direction']
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        # Make table stretch to fill available space
        self.table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Interactive
        )

        # Set initial column widths (these are now resizable)
        self.table.setColumnWidth(0, 70)   # Universe
        self.table.setColumnWidth(1, 70)   # Address
        self.table.setColumnWidth(2, 180)  # Manufacturer
        self.table.setColumnWidth(3, 180)  # Model
        self.table.setColumnWidth(4, 70)   # Channels
        self.table.setColumnWidth(5, 140)  # Mode
        self.table.setColumnWidth(6, 140)  # Name
        self.table.setColumnWidth(7, 140)  # Group
        self.table.setColumnWidth(8, 80)   # Direction

        # Table properties
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

    def connect_signals(self):
        """Connect widget signals to handlers"""
        self.add_btn.clicked.connect(self._add_fixture)
        self.remove_btn.clicked.connect(self._remove_fixture)
        self.duplicate_btn.clicked.connect(self._duplicate_fixture)
        self.table.itemChanged.connect(self.save_to_config)

    def update_from_config(self):
        """Refresh fixture table from configuration"""
        # Block signals during population
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        # Update existing groups set
        self.existing_groups = set(self.config.groups.keys())

        for fixture in self.config.fixtures:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Universe spinbox
            universe_spin = QtWidgets.QSpinBox()
            universe_spin.setRange(1, 16)
            universe_spin.setValue(fixture.universe)
            universe_spin.valueChanged.connect(self.save_to_config)
            self.table.setCellWidget(row, 0, universe_spin)

            # Address spinbox
            address_spin = QtWidgets.QSpinBox()
            address_spin.setRange(1, 512)
            address_spin.setValue(fixture.address)
            address_spin.valueChanged.connect(self.save_to_config)
            self.table.setCellWidget(row, 1, address_spin)

            # Manufacturer and Model
            manufacturer_item = QtWidgets.QTableWidgetItem(fixture.manufacturer)
            manufacturer_item.setBackground(QtGui.QColor(255, 255, 255))  # White background
            self.table.setItem(row, 2, manufacturer_item)

            model_item = QtWidgets.QTableWidgetItem(fixture.model)
            model_item.setBackground(QtGui.QColor(255, 255, 255))  # White background
            self.table.setItem(row, 3, model_item)

            # Mode combo box
            mode_combo = QtWidgets.QComboBox()
            if fixture.available_modes:
                for mode in fixture.available_modes:
                    mode_combo.addItem(f"{mode.name} ({mode.channels}ch)")

                # Set current mode
                current_mode_text = next(
                    (f"{mode.name} ({mode.channels}ch)"
                     for mode in fixture.available_modes
                     if mode.name == fixture.current_mode),
                    fixture.current_mode
                )
                index = mode_combo.findText(current_mode_text)
                if index >= 0:
                    mode_combo.setCurrentIndex(index)
                    channels = fixture.available_modes[index].channels
                    channels_item = QtWidgets.QTableWidgetItem(str(channels))
                    channels_item.setBackground(QtGui.QColor(255, 255, 255))  # White background
                    self.table.setItem(row, 4, channels_item)

                # Create closure for mode change handler
                def create_mode_handler(current_row, modes):
                    def handle_mode_change(index):
                        if 0 <= index < len(modes):
                            channels = modes[index].channels
                            channels_item = QtWidgets.QTableWidgetItem(str(channels))
                            channels_item.setBackground(QtGui.QColor(255, 255, 255))  # White background
                            self.table.setItem(current_row, 4, channels_item)
                            self.config.fixtures[current_row].current_mode = modes[index].name
                            self._update_row_colors()
                            # Notify main window of changes
                            main_window = self.window()
                            if main_window and hasattr(main_window, 'on_groups_changed'):
                                main_window.on_groups_changed()
                    return handle_mode_change

                mode_combo.currentIndexChanged.connect(
                    create_mode_handler(row, fixture.available_modes)
                )
            else:
                mode_combo.addItem(fixture.current_mode)
                channels_item = QtWidgets.QTableWidgetItem("0")
                channels_item.setBackground(QtGui.QColor(255, 255, 255))  # White background
                self.table.setItem(row, 4, channels_item)

            self.table.setCellWidget(row, 5, mode_combo)

            # Name
            name_item = QtWidgets.QTableWidgetItem(fixture.name)
            name_item.setBackground(QtGui.QColor(255, 255, 255))  # White background
            self.table.setItem(row, 6, name_item)

            # Group combo box
            group_combo = QtWidgets.QComboBox()
            group_combo.setEditable(True)
            group_combo.addItem("")
            for group in sorted(self.config.groups.keys()):
                group_combo.addItem(group)
            group_combo.addItem("Add New...")
            group_combo.setCurrentText(fixture.group)

            # Create closure for group change handler
            def create_group_handler(current_row, combo):
                def handle_group_change(text):
                    if text == "Add New...":
                        self._handle_new_group(combo)
                    elif text:
                        self.config.fixtures[current_row].group = text
                        self._update_groups()
                        # If this is a new group, add it to all other comboboxes
                        self._add_group_to_all_combos(text, combo)
                    else:
                        self.config.fixtures[current_row].group = ""
                        self._update_groups()
                    self._update_row_colors()
                    # Notify main window of changes
                    main_window = self.window()
                    if main_window and hasattr(main_window, 'on_groups_changed'):
                        main_window.on_groups_changed()
                return handle_group_change

            group_combo.currentTextChanged.connect(create_group_handler(row, group_combo))
            self.table.setCellWidget(row, 7, group_combo)

            # Direction combo box
            direction_combo = QtWidgets.QComboBox()
            direction_combo.addItems(["", "↑", "↓", "⊙", "⊗"])
            display_value = ""
            if fixture.direction == "UP":
                display_value = "↑"
            elif fixture.direction == "DOWN":
                display_value = "↓"
            elif fixture.direction == "TOWARD":
                display_value = "⊙"
            elif fixture.direction == "AWAY":
                display_value = "⊗"
            direction_combo.setCurrentText(display_value)
            direction_combo.currentIndexChanged.connect(self.save_to_config)
            self.table.setCellWidget(row, 8, direction_combo)

        # Re-enable signals and update colors
        self.table.blockSignals(False)
        self._update_row_colors()

    def save_to_config(self, item=None):
        """Update configuration from table values"""
        # Update all fixtures from table
        for row in range(self.table.rowCount()):
            if row >= len(self.config.fixtures):
                continue

            fixture = self.config.fixtures[row]

            # Update universe and address
            universe_spin = self.table.cellWidget(row, 0)
            if universe_spin and isinstance(universe_spin, QtWidgets.QSpinBox):
                fixture.universe = universe_spin.value()

            address_spin = self.table.cellWidget(row, 1)
            if address_spin and isinstance(address_spin, QtWidgets.QSpinBox):
                fixture.address = address_spin.value()

            # Update manufacturer
            manufacturer_item = self.table.item(row, 2)
            if manufacturer_item and manufacturer_item.text():
                fixture.manufacturer = manufacturer_item.text()

            # Update model
            model_item = self.table.item(row, 3)
            if model_item and model_item.text():
                fixture.model = model_item.text()

            # Update mode
            mode_combo = self.table.cellWidget(row, 5)
            if mode_combo and isinstance(mode_combo, QtWidgets.QComboBox):
                mode_text = mode_combo.currentText()
                if " (" in mode_text:
                    mode_name = mode_text.split(" (")[0]
                    fixture.current_mode = mode_name

            # Update name
            name_item = self.table.item(row, 6)
            if name_item and name_item.text():
                fixture.name = name_item.text()

            # Update group
            group_combo = self.table.cellWidget(row, 7)
            if group_combo and isinstance(group_combo, QtWidgets.QComboBox):
                group_name = group_combo.currentText()
                if group_name and group_name != "Add New...":
                    fixture.group = group_name
                else:
                    fixture.group = ""

            # Update direction
            direction_combo = self.table.cellWidget(row, 8)
            if direction_combo and isinstance(direction_combo, QtWidgets.QComboBox):
                display_value = direction_combo.currentText()
                if display_value == "↑":
                    fixture.direction = "UP"
                elif display_value == "↓":
                    fixture.direction = "DOWN"
                elif display_value == "⊙":
                    fixture.direction = "TOWARD"
                elif display_value == "⊗":
                    fixture.direction = "AWAY"
                else:
                    fixture.direction = "NONE"

        self._update_groups()

        # Notify main window of group changes if needed
        main_window = self.window()
        if main_window and hasattr(main_window, 'on_groups_changed'):
            main_window.on_groups_changed()

    def _update_groups(self):
        """Rebuild groups from fixtures, preserving colors"""
        # Store existing colors
        existing_colors = {
            name: group.color
            for name, group in self.config.groups.items()
            if hasattr(group, 'color')
        }

        # Clear and rebuild groups
        self.config.groups = {}

        for fixture in self.config.fixtures:
            if fixture.group:
                if fixture.group not in self.config.groups:
                    color = existing_colors.get(fixture.group, '#808080')
                    self.config.groups[fixture.group] = FixtureGroup(
                        fixture.group,
                        [],
                        color=color
                    )
                self.config.groups[fixture.group].fixtures.append(fixture)

        # Update existing groups set
        self.existing_groups = set(self.config.groups.keys())

    def _handle_new_group(self, group_combo):
        """Show dialog to create new group"""
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
                # Update the current fixture's group combobox
                current_index = group_combo.findText("Add New...")
                group_combo.removeItem(current_index)
                group_combo.addItem(new_group)
                group_combo.addItem("Add New...")
                group_combo.setCurrentText(new_group)

                # Update all other fixtures' group comboboxes with the new group
                self._add_group_to_all_combos(new_group, group_combo)

    def _add_group_to_all_combos(self, group_name, exclude_combo=None):
        """Add a group name to all group comboboxes if it doesn't exist

        Args:
            group_name: The group name to add
            exclude_combo: Optional combobox to exclude from update
        """
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, 7)
            if combo and combo != exclude_combo:
                # Check if group already exists in this combo
                if combo.findText(group_name) == -1:
                    # Find "Add New..." item and insert new group before it
                    add_new_index = combo.findText("Add New...")
                    if add_new_index != -1:
                        combo.insertItem(add_new_index, group_name)

    def _update_row_colors(self):
        """Apply group colors to table rows"""
        for row in range(self.table.rowCount()):
            group_combo = self.table.cellWidget(row, 7)
            if group_combo:
                group_name = group_combo.currentText()
                if group_name and group_name != "Add New...":
                    # Get or create color for group
                    if group_name not in self.group_colors:
                        self.group_colors[group_name] = self.predefined_colors[
                            self.color_index % len(self.predefined_colors)]
                        self.color_index += 1

                    color = self.group_colors[group_name]

                    # Apply color to all cells in row
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if not item and not self.table.cellWidget(row, col):
                            self.table.setItem(row, col, QtWidgets.QTableWidgetItem(""))

                        if item:
                            item.setBackground(color)

                        cell_widget = self.table.cellWidget(row, col)
                        if cell_widget:
                            cell_widget.setStyleSheet(f"background-color: {color.name()};")

                    # Update group color in configuration
                    if group_name in self.config.groups:
                        self.config.groups[group_name].color = color.name()
                else:
                    # Reset color to white if no group
                    white_color = QtGui.QColor(255, 255, 255)
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if item:
                            item.setBackground(white_color)
                        cell_widget = self.table.cellWidget(row, col)
                        if cell_widget:
                            cell_widget.setStyleSheet("background-color: white;")

    def _add_fixture(self):
        """Show dialog to add fixture from QLC+ definitions"""
        try:
            # Scan QLC+ fixture directories
            qlc_fixture_dirs = []

            # Always include project's custom_fixtures folder first
            project_custom_fixtures = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'custom_fixtures')
            if os.path.exists(project_custom_fixtures):
                qlc_fixture_dirs.append(project_custom_fixtures)

            if sys.platform.startswith('linux'):
                # Linux paths
                qlc_fixture_dirs.append(os.path.expanduser('~/.qlcplus/Fixtures'))
                qlc_fixture_dirs.append('/usr/share/qlcplus/Fixtures')

            elif sys.platform == 'win32':
                # Windows paths
                qlc_fixture_dirs.append(os.path.join(os.path.expanduser('~'), 'QLC+', 'Fixtures'))
                qlc_fixture_dirs.append('C:\\QLC+\\Fixtures')
                qlc_fixture_dirs.append('C:\\QLC+5\\Fixtures')

            elif sys.platform == 'darwin':
                # macOS paths
                qlc_fixture_dirs.append(os.path.expanduser('~/Library/Application Support/QLC+/Fixtures'))
                qlc_fixture_dirs.append('/Applications/QLC+.app/Contents/Resources/Fixtures')

            # Build fixture list
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

            # Create selection dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Select Fixture")
            dialog.setModal(True)
            dialog.resize(600, 800)
            layout = QtWidgets.QVBoxLayout()
            layout.setSpacing(10)

            # Search box
            search_box = QLineEdit()
            search_box.setPlaceholderText("Search fixtures...")
            font = QtGui.QFont()
            font.setPointSize(12)
            search_box.setFont(font)
            search_box.setMinimumHeight(40)
            layout.addWidget(search_box)

            # List widget
            list_widget = QtWidgets.QListWidget()
            list_widget.setFont(font)
            list_widget.setSpacing(4)

            # Add sorted fixtures
            fixture_files.sort(key=lambda x: (x['manufacturer'].lower(), x['model'].lower()))
            for fixture in fixture_files:
                item = QtWidgets.QListWidgetItem(
                    f"{fixture['manufacturer']} - {fixture['model']}"
                )
                item.setData(QtCore.Qt.ItemDataRole.UserRole, fixture['path'])
                list_widget.addItem(item)

            layout.addWidget(list_widget)

            # Search filter
            def filter_fixtures():
                search_text = search_box.text().lower()
                for i in range(list_widget.count()):
                    item = list_widget.item(i)
                    item.setHidden(search_text not in item.text().lower())

            search_box.textChanged.connect(filter_fixtures)

            # Dialog buttons
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
                    self._process_fixture_selection(selected_items[0])

        except Exception as e:
            print(f"Error adding fixture: {e}")
            import traceback
            traceback.print_exc()

    def _process_fixture_selection(self, selected_item):
        """Process selected fixture and add to configuration"""
        fixture_path = selected_item.data(QtCore.Qt.ItemDataRole.UserRole)

        # Parse fixture file
        tree = ET.parse(fixture_path)
        root = tree.getroot()
        ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

        manufacturer = root.find('.//Manufacturer', ns).text
        model = root.find('.//Model', ns).text
        fixture_type = determine_fixture_type(root)

        # Get modes
        modes = root.findall('.//Mode', ns)
        mode_data = [
            {'name': mode.get('Name'), 'channels': len(mode.findall('Channel', ns))}
            for mode in modes
        ]

        # Create fixture object
        new_fixture = Fixture(
            universe=1,
            address=1,
            manufacturer=manufacturer,
            model=model,
            name=model,
            group="",
            direction="",
            current_mode=mode_data[0]['name'],
            available_modes=[
                FixtureMode(name=mode['name'], channels=mode['channels'])
                for mode in mode_data
            ],
            type=fixture_type,
            x=0.0,
            y=0.0,
            z=0.0,
            rotation=0.0
        )

        # Add to configuration
        self.config.fixtures.append(new_fixture)

        # Refresh table
        self.update_from_config()

        # Notify main window of changes
        main_window = self.window()
        if main_window and hasattr(main_window, 'on_groups_changed'):
            main_window.on_groups_changed()

        print(f"Added fixture: {manufacturer} {model}")

    def _remove_fixture(self):
        """Remove selected fixture from configuration"""
        selected_rows = self.table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()

            if row < len(self.config.fixtures):
                fixture = self.config.fixtures[row]

                # Remove from group
                if fixture.group and fixture.group in self.config.groups:
                    group = self.config.groups[fixture.group]
                    group.fixtures = [f for f in group.fixtures if f != fixture]

                    # Remove empty group
                    if not group.fixtures:
                        del self.config.groups[fixture.group]

                # Remove fixture
                self.config.fixtures.pop(row)

            # Remove table row
            self.table.removeRow(row)

            # Clean up fixture paths
            if row < len(self.fixture_paths):
                self.fixture_paths.pop(row)

            self._update_groups()
            self._update_row_colors()

            # Notify main window
            main_window = self.window()
            if main_window and hasattr(main_window, 'on_groups_changed'):
                main_window.on_groups_changed()

    def _duplicate_fixture(self):
        """Duplicate selected fixture with offset address"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QtWidgets.QMessageBox.warning(
                self,
                "No Selection",
                "Please select a fixture to duplicate.",
                QtWidgets.QMessageBox.StandardButton.Ok
            )
            return

        row = selected_rows[0].row()

        if row >= len(self.config.fixtures):
            return

        # Get original fixture
        original_fixture = self.config.fixtures[row]

        # Get channel count
        channel_count = 0
        for mode in original_fixture.available_modes:
            if mode.name == original_fixture.current_mode:
                channel_count = mode.channels
                break

        # Create duplicate
        new_fixture = Fixture(
            universe=original_fixture.universe,
            address=original_fixture.address + channel_count,
            manufacturer=original_fixture.manufacturer,
            model=original_fixture.model,
            name=f"{original_fixture.name} (Copy)",
            group=original_fixture.group,
            direction=original_fixture.direction,
            current_mode=original_fixture.current_mode,
            available_modes=[
                FixtureMode(name=mode.name, channels=mode.channels)
                for mode in original_fixture.available_modes
            ],
            type=original_fixture.type,
            x=original_fixture.x,
            y=original_fixture.y,
            z=original_fixture.z,
            rotation=original_fixture.rotation
        )

        # Add to configuration
        self.config.fixtures.append(new_fixture)

        # Add to group
        if new_fixture.group and new_fixture.group in self.config.groups:
            self.config.groups[new_fixture.group].fixtures.append(new_fixture)

        # Refresh table
        self.update_from_config()

        # Notify main window of changes
        main_window = self.window()
        if main_window and hasattr(main_window, 'on_groups_changed'):
            main_window.on_groups_changed()

        print(f"Duplicated fixture: {original_fixture.manufacturer} {original_fixture.model}")
