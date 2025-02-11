from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit
import os
import sys
import xml.etree.ElementTree as ET
from config.models import FixtureGroup

class FixtureTab:
    def __init__(self, main_window):
        self.main_window = main_window
        self.config = main_window.config
        self.tableWidget = main_window.tableWidget
        self.project_root = main_window.project_root
        self.setup_dir = main_window.setup_dir
        self.group_colors = {}
        self.color_index = 0
        self.existing_groups = set()

        # Initialize colors
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

        self.setup_ui_connections()

    def setup_ui_connections(self):
        """Set up signal connections for fixture tab"""
        self.tableWidget.itemChanged.connect(self.update_config_from_table)
        self.main_window.pushButton.clicked.connect(self.add_fixture)
        self.main_window.pushButton_2.clicked.connect(self.remove_fixture)
        self.main_window.pushButton_3.clicked.connect(self.import_workspace)
        self.main_window.pushButton_4.clicked.connect(self.load_fixtures_to_show)

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
                for mode in fixture.available_modes:
                    mode_combo.addItem(f"{mode.name} ({mode.channels}ch)")

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
                    self.tableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem(str(channels)))

                mode_combo.currentIndexChanged.connect(
                    self.create_mode_handler(row, fixture.available_modes)
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
            group_combo.currentTextChanged.connect(self.create_group_handler(row))
            self.tableWidget.setCellWidget(row, 7, group_combo)

            # Direction
            direction_combo = QtWidgets.QComboBox()
            direction_combo.addItems(["", "↑", "↓"])
            direction_combo.setCurrentText(fixture.direction)
            self.tableWidget.setCellWidget(row, 8, direction_combo)

        self.update_row_colors()

    def create_mode_handler(self, current_row, modes):
        def handle_mode_change(index):
            if 0 <= index < len(modes):
                channels = modes[index].channels
                self.tableWidget.setItem(current_row, 4,
                                       QtWidgets.QTableWidgetItem(str(channels)))
                self.config.fixtures[current_row].current_mode = modes[index].name
                self.update_row_colors()
        return handle_mode_change

    def create_group_handler(self, current_row):
        def handle_group_change(text):
            if text == "Add New...":
                self.handle_new_group(self.tableWidget.cellWidget(current_row, 7))
            else:
                self.config.fixtures[current_row].group = text
                self.update_groups()
            self.update_row_colors()
        return handle_group_change

    def handle_new_group(self, combo_box):
        """Handle adding a new group"""
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Add New Group")
        layout = QtWidgets.QVBoxLayout()

        # Add input field
        input_field = QLineEdit()
        layout.addWidget(input_field)

        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_group = input_field.text().strip()
            if new_group and new_group != "Add New...":
                current_index = combo_box.currentIndex()
                combo_box.insertItem(current_index, new_group)
                combo_box.setCurrentText(new_group)

    def update_config_from_table(self, item):
        """Update configuration when table items change"""
        row = item.row()
        col = item.column()

        if row >= len(self.config.fixtures):
            return

        fixture = self.config.fixtures[row]

        if col == 2:  # Manufacturer
            fixture.manufacturer = item.text()
        elif col == 3:  # Model
            fixture.model = item.text()
        elif col == 6:  # Name
            fixture.name = item.text()

        self.update_groups()

    def update_config_from_widget(self, row, col, widget):
        """Update configuration when widgets change"""
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
            self.handle_group_change(fixture, widget)
        elif col == 8:  # Direction
            fixture.direction = widget.currentText()

    def update_groups(self):
        """Update groups in configuration"""
        self.config.groups = {}
        for fixture in self.config.fixtures:
            if fixture.group:
                if fixture.group not in self.config.groups:
                    self.config.groups[fixture.group] = FixtureGroup(fixture.group, [])
                self.config.groups[fixture.group].fixtures.append(fixture)

    def update_row_colors(self):
        """Update row colors based on groups"""
        for row in range(self.tableWidget.rowCount()):
            group_combo = self.tableWidget.cellWidget(row, 7)
            if group_combo:
                group_name = group_combo.currentText()
                if group_name:
                    if group_name not in self.group_colors:
                        self.group_colors[group_name] = self.predefined_colors[
                            self.color_index % len(self.predefined_colors)]
                        self.color_index += 1
                    color = self.group_colors[group_name]
                    self.apply_row_color(row, color)
                else:
                    self.clear_row_color(row)

    def apply_row_color(self, row, color):
        """Apply color to a table row"""
        for col in range(self.tableWidget.columnCount()):
            item = self.tableWidget.item(row, col)
            if item:
                item.setBackground(color)
            cell_widget = self.tableWidget.cellWidget(row, col)
            if cell_widget:
                cell_widget.setStyleSheet(f"background-color: {color.name()};")

    def clear_row_color(self, row):
        """Clear color from a table row"""
        for col in range(self.tableWidget.columnCount()):
            item = self.tableWidget.item(row, col)
            if item:
                item.setBackground(QtGui.QColor())
            cell_widget = self.tableWidget.cellWidget(row, col)
            if cell_widget:
                cell_widget.setStyleSheet("")

    def add_fixture(self):
        """Add a new fixture"""
        try:
            qlc_fixture_dirs = []
            if sys.platform.startswith('linux'):
                qlc_fixture_dirs.extend([
                    '/usr/share/qlcplus/fixtures',
                    os.path.expanduser('~/.qlcplus/fixtures')
                ])
            elif sys.platform == 'win32':
                qlc_fixture_dirs.extend([
                    os.path.join(os.path.expanduser('~'), 'QLC+', 'fixtures'),
                    'C:\\QLC+\\Fixtures'
                ])
            elif sys.platform == 'darwin':
                qlc_fixture_dirs.append(os.path.expanduser('~/Library/Application Support/QLC+/fixtures'))

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

            dialog = QDialog(self.main_window)
            dialog.setWindowTitle("Select Fixture")
            dialog.setModal(True)
            dialog.resize(600, 800)
            layout = QtWidgets.QVBoxLayout()

            search_box = QLineEdit()
            search_box.setPlaceholderText("Search fixtures...")
            font = QtGui.QFont()
            font.setPointSize(12)
            search_box.setFont(font)
            search_box.setMinimumHeight(40)
            layout.addWidget(search_box)

            list_widget = QtWidgets.QListWidget()
            list_widget.setFont(font)
            list_widget.setSpacing(4)

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
                    self.process_selected_fixture(fixture_path)

        except Exception as e:
            print(f"Error adding fixture: {e}")
            import traceback
            traceback.print_exc()

    def process_selected_fixture(self, fixture_path):
        """Process selected fixture and add it to the table"""
        tree = ET.parse(fixture_path)
        root = tree.getroot()
        ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

        manufacturer = root.find('.//Manufacturer', ns).text
        model = root.find('.//Model', ns).text

        modes = root.findall('.//Mode', ns)
        mode_data = []
        for mode in modes:
            mode_name = mode.get('Name')
            channels = mode.findall('Channel', ns)
            mode_data.append({
                'name': mode_name,
                'channels': len(channels)
            })

        row = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row)
        self.setup_row_widgets(row, manufacturer, model, mode_data)

    def remove_fixture(self):
        """Remove selected fixture"""
        selected_rows = self.tableWidget.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            self.tableWidget.removeRow(row)
            if row < len(self.config.fixtures):
                self.config.fixtures.pop(row)
            self.update_groups()
            self.update_row_colors()

    def import_workspace(self):
        """Import workspace"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.main_window,
            "Select QLC+ Workspace",
            "",
            "QLC+ Workspace Files (*.qxw)"
        )
        if file_path:
            self.main_window.extract_from_workspace(file_path)

    def load_fixtures_to_show(self):
        pass

