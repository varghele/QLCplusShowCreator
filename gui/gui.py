import sys
import os
import csv
import json
import xml.etree.ElementTree as ET
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QDialog, QFileDialog, QLineEdit, QFormLayout, QDialogButtonBox
from .effect_selection import EffectSelectionDialog
from utils.create_workspace import create_qlc_workspace


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("QLCAutoShow")
        MainWindow.resize(1200, 900)  # Changed window size
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.tabWidget = QtWidgets.QTabWidget(parent=self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")

        # Fixtures Tab
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")

        # Buttons remain the same size but adjusted positions
        self.pushButton = QtWidgets.QPushButton(parent=self.tab)
        self.pushButton.setGeometry(QtCore.QRect(10, 14, 31, 31))
        self.pushButton.setObjectName("pushButton")

        self.pushButton_2 = QtWidgets.QPushButton(parent=self.tab)
        self.pushButton_2.setGeometry(QtCore.QRect(50, 14, 31, 31))
        self.pushButton_2.setObjectName("pushButton_2")

        self.pushButton_3 = QtWidgets.QPushButton(parent=self.tab)
        self.pushButton_3.setGeometry(QtCore.QRect(978, 10, 191, 31))  # Adjusted x position
        self.pushButton_3.setObjectName("pushButton_3")

        self.pushButton_4 = QtWidgets.QPushButton(parent=self.tab)
        self.pushButton_4.setGeometry(QtCore.QRect(110, 14, 181, 31))
        self.pushButton_4.setObjectName("pushButton_4")

        # Tables with increased width and height
        self.tableWidget = QtWidgets.QTableWidget(parent=self.tab)
        self.tableWidget.setGeometry(QtCore.QRect(10, 80, 1151, 640))  # Increased height
        self.tableWidget.setObjectName("tableWidget")

        # Labels
        self.label = QtWidgets.QLabel(parent=self.tab)
        self.label.setGeometry(QtCore.QRect(10, 60, 81, 17))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setObjectName("label")

        self.tabWidget.addTab(self.tab, "")

        # Shows Tab
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")

        self.tableWidget_3 = QtWidgets.QTableWidget(parent=self.tab_2)
        self.tableWidget_3.setGeometry(QtCore.QRect(10, 90, 1151, 701))  # Increased width and height
        self.tableWidget_3.setObjectName("tableWidget_3")

        self.pushButton_5 = QtWidgets.QPushButton(parent=self.tab_2)
        self.pushButton_5.setGeometry(QtCore.QRect(10, 20, 171, 31))
        self.pushButton_5.setObjectName("pushButton_5")

        self.pushButton_6 = QtWidgets.QPushButton(parent=self.tab_2)
        self.pushButton_6.setGeometry(QtCore.QRect(1151-131, 20, 141, 31))  # Adjusted x position
        self.pushButton_6.setObjectName("pushButton_6")

        self.pushButton_7 = QtWidgets.QPushButton(parent=self.tab_2)
        self.pushButton_7.setGeometry(QtCore.QRect(200, 20, 101, 31))  # Adjusted x position
        self.pushButton_7.setObjectName("pushButton_6")

        self.comboBox = QtWidgets.QComboBox(parent=self.tab_2)
        self.comboBox.setGeometry(QtCore.QRect(10, 60, 171, 25))
        self.comboBox.setObjectName("comboBox")

        self.tabWidget.addTab(self.tab_2, "")
        self.horizontalLayout.addWidget(self.tabWidget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1200, 22))  # Adjusted width
        self.menubar.setObjectName("menubar")
        self.menuQLCAutoShow = QtWidgets.QMenu(parent=self.menubar)
        self.menuQLCAutoShow.setObjectName("menuQLCAutoShow")
        MainWindow.setMenuBar(self.menubar)
        self.menuQLCAutoShow.addSeparator()
        self.menubar.addAction(self.menuQLCAutoShow.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.pushButton.setToolTip(_translate("MainWindow", "<html><head/><body><p>Add Fixture</p></body></html>"))
        self.pushButton.setText(_translate("MainWindow", "+"))
        self.pushButton_2.setToolTip(_translate("MainWindow", "<html><head/><body><p>Remove Fixture</p></body></html>"))
        self.pushButton_2.setText(_translate("MainWindow", "-"))
        self.pushButton_3.setText(_translate("MainWindow", "Import QLC WorkSpace"))
        self.pushButton_4.setText(_translate("MainWindow", "Load Fixtures To Show"))
        self.label.setText(_translate("MainWindow", "Fixtures"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Fixtures"))
        self.pushButton_5.setText(_translate("MainWindow", "Load Shows"))
        self.pushButton_6.setText(_translate("MainWindow", "Create Workspace"))
        self.pushButton_7.setText(_translate("MainWindow", "Save Show"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Shows"))
        self.menuQLCAutoShow.setTitle(_translate("MainWindow", "QLCAutoShow"))


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Get the project root directory
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.setup_dir = os.path.join(self.project_root, "setup")

        # Initialize fixture paths list
        self.fixture_paths = []

        # Load effects dictionary using correct path
        effects_json_path = os.path.join(self.project_root, "effects", "effects.json")
        with open(effects_json_path, 'r') as f:
            self.effects_dir = json.load(f)

        # Set up table headers
        self._setup_tables()

        # Connect buttons to functions
        self.pushButton.clicked.connect(self.add_fixture)
        self.pushButton_2.clicked.connect(self.remove_fixture)
        self.pushButton_3.clicked.connect(self.import_workspace)
        self.pushButton_4.clicked.connect(self.load_fixtures_to_show)
        self.pushButton_5.clicked.connect(self.import_show_structure)
        self.pushButton_7.clicked.connect(self.save_show)
        self.pushButton_6.clicked.connect(self.create_workspace)

        # Add this after other initializations
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
        show_headers = ['Show Part', 'Fixture Group', 'Value']
        self.tableWidget_3.setColumnCount(len(show_headers))
        self.tableWidget_3.setHorizontalHeaderLabels(show_headers)

        # Set column widths for shows table
        #self.tableWidget_3.setColumnWidth(0, 200)  # Show Part
        #self.tableWidget_3.setColumnWidth(1, 200)  # Fixture Group
        #self.tableWidget_3.horizontalHeader().setStretchLastSection(True)  # Value stretches

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

    def save_cell_value(self, row, show_name):
        try:
            # Get the values from the row
            show_part = self.tableWidget_3.item(row, 0).text()
            fixture_group = self.tableWidget_3.item(row, 1).text()
            effect = self.tableWidget_3.item(row, 2).text() if self.tableWidget_3.item(row, 2) else ""

            # Safely get speed value
            speed_widget = self.tableWidget_3.cellWidget(row, 3)
            speed = speed_widget.currentText() if speed_widget else "1"  # Default to "1" if widget doesn't exist

            # Safely get color value
            color_button = self.tableWidget_3.cellWidget(row, 4)
            color = color_button.property("current_color") if color_button else ""

            # Create the show directory if it doesn't exist
            show_dir = os.path.join(self.project_root, "shows", show_name)
            os.makedirs(show_dir, exist_ok=True)

            # Load existing data
            values_file = os.path.join(show_dir, f"{show_name}_values.json")
            show_data = []
            if os.path.exists(values_file):
                with open(values_file, 'r') as f:
                    try:
                        show_data = json.load(f)
                    except:
                        pass

            # Update or add the value
            found = False
            for item in show_data:
                if item['show_part'] == show_part and item['fixture_group'] == fixture_group:
                    item.update({
                        'effect': effect,
                        'speed': speed,
                        'color': color
                    })
                    found = True
                    break

            if not found:
                show_data.append({
                    'show_part': show_part,
                    'fixture_group': fixture_group,
                    'effect': effect,
                    'speed': speed,
                    'color': color
                })

            # Save the updated data
            with open(values_file, 'w') as f:
                json.dump(show_data, f, indent=2)

        except Exception as e:
            print(f"Error saving cell value: {e}")
            import traceback
            traceback.print_exc()

    def update_row_colors(self):
        for row in range(self.tableWidget.rowCount()):
            group_combo = self.tableWidget.cellWidget(row, 7)  # Group column
            if group_combo:
                group_name = group_combo.currentText()
                if group_name:
                    if group_name not in self.group_colors:
                        self.group_colors[group_name] = self.predefined_colors[
                            self.color_index % len(self.predefined_colors)]
                        self.color_index += 1
                    color = self.group_colors[group_name]
                    for col in range(self.tableWidget.columnCount()):
                        item = self.tableWidget.item(row, col)
                        if item:
                            item.setBackground(color)
                        cell_widget = self.tableWidget.cellWidget(row, col)
                        if cell_widget:
                            cell_widget.setStyleSheet(f"background-color: {color.name()};")
                else:
                    # Reset color if no group is selected
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
                qlc_fixture_dirs.append(os.path.join(os.path.expanduser('~'), 'QLC+', 'fixtures'))
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

                    # Parse the fixture file
                    tree = ET.parse(fixture_path)
                    root = tree.getroot()
                    ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

                    # Extract basic fixture information
                    manufacturer = root.find('.//Manufacturer', ns).text
                    model = root.find('.//Model', ns).text
                    fixture_type = root.find('.//Type', ns).text

                    # Get all available modes
                    modes = root.findall('.//Mode', ns)
                    mode_data = []
                    for mode in modes:
                        mode_name = mode.get('Name')
                        channels = mode.findall('Channel', ns)
                        mode_data.append({
                            'name': mode_name,
                            'channels': len(channels)
                        })

                    # Create mode selection combobox for fixtures table
                    mode_combo = QtWidgets.QComboBox()
                    for mode in mode_data:
                        mode_combo.addItem(f"{mode['name']} ({mode['channels']}ch)")

                    # Update fixtures table
                    row = self.tableWidget.rowCount()
                    self.tableWidget.insertRow(row)

                    # Create universe spinbox for fixtures table
                    universe_spin = QtWidgets.QSpinBox()
                    universe_spin.setRange(1, 16)
                    universe_spin.setValue(1)
                    self.tableWidget.setCellWidget(row, 0, universe_spin)  # Use setCellWidget instead of setItem

                    self.tableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(manufacturer))
                    self.tableWidget.setItem(row, 3, QtWidgets.QTableWidgetItem(model))
                    self.tableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem(str(mode_data[0]['channels'])))
                    self.tableWidget.setCellWidget(row, 5, mode_combo)
                    self.tableWidget.setItem(row, 6, QtWidgets.QTableWidgetItem(""))  # Name
                    self.tableWidget.setItem(row, 7, QtWidgets.QTableWidgetItem("None"))  # Group

                    # Create universe spinbox for fixture groups table
                    universe_spin_groups = QtWidgets.QSpinBox()
                    universe_spin_groups.setRange(1, 16)
                    universe_spin_groups.setValue(1)

                    # Create address spinboxes
                    address_spin = QtWidgets.QSpinBox()
                    address_spin.setRange(1, 512)  # DMX address range
                    address_spin.setValue(1)
                    self.tableWidget.setCellWidget(row, 1, address_spin)  # Address column

                    address_spin_groups = QtWidgets.QSpinBox()
                    address_spin_groups.setRange(1, 512)
                    address_spin_groups.setValue(1)

                    # Create mode selection combobox for fixture groups table
                    mode_combo_groups = QtWidgets.QComboBox()
                    for mode in mode_data:
                        mode_combo_groups.addItem(f"{mode['name']} ({mode['channels']}ch)")

                    def update_channels(index):
                        # Update channels in fixtures table
                        channels_item = QtWidgets.QTableWidgetItem(str(mode_data[index]['channels']))
                        self.tableWidget.setItem(row, 4, channels_item)

                    def sync_universe(value):
                        if universe_spin.value() != value:
                            universe_spin.setValue(value)
                        if universe_spin_groups.value() != value:
                            universe_spin_groups.setValue(value)

                    # Add address sync function
                    def sync_address(value):
                        if address_spin.value() != value:
                            address_spin.setValue(value)
                        if address_spin_groups.value() != value:
                            address_spin_groups.setValue(value)

                    # Connect universe change handlers
                    universe_spin.valueChanged.connect(sync_universe)
                    universe_spin_groups.valueChanged.connect(sync_universe)

                    # Connect mode change handlers
                    mode_combo.currentIndexChanged.connect(update_channels)
                    mode_combo_groups.currentIndexChanged.connect(update_channels)

                    # Sync the two comboboxes
                    def sync_modes(index):
                        if mode_combo.currentIndex() != index:
                            mode_combo.setCurrentIndex(index)
                        if mode_combo_groups.currentIndex() != index:
                            mode_combo_groups.setCurrentIndex(index)

                    mode_combo.currentIndexChanged.connect(sync_modes)
                    mode_combo_groups.currentIndexChanged.connect(sync_modes)

                    # Connect address change handlers
                    address_spin.valueChanged.connect(sync_address)
                    address_spin_groups.valueChanged.connect(sync_address)

                    # Create group selection combobox
                    group_combo = QtWidgets.QComboBox()
                    group_combo.addItem("")  # Empty option
                    for group in sorted(self.existing_groups):
                        group_combo.addItem(group)
                    group_combo.addItem("Add New...")
                    self.tableWidget.setCellWidget(row, 7, group_combo)

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
                                    self.existing_groups.add(new_group)
                                    current_index = group_combo.findText("Add New...")
                                    group_combo.removeItem(current_index)
                                    group_combo.addItem(new_group)
                                    group_combo.addItem("Add New...")
                                    group_combo.setCurrentText(new_group)
                                    self.update_row_colors()
                        else:
                            self.update_row_colors()

                    group_combo.currentIndexChanged.connect(handle_group_selection)
                    self.tableWidget.setCellWidget(row, 7, group_combo)

                    # Create direction combobox
                    direction_combo = QtWidgets.QComboBox()
                    direction_combo.addItems(["", "↑", "↓"])  # Using Unicode arrows
                    self.tableWidget.setCellWidget(row, 8, direction_combo)  # Direction column

                    # Add empty Group cell
                    self.tableWidget.setItem(row, 7, QtWidgets.QTableWidgetItem(""))  # Group

                    print(f"Added fixture to table: {manufacturer} {model}")


        except Exception as e:
            print(f"Error adding fixture: {e}")
            import traceback
            traceback.print_exc()

    def remove_fixture(self):
        selected_rows = self.tableWidget.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            self.tableWidget.removeRow(row)
            if row < len(self.fixture_paths):
                self.fixture_paths.pop(row)

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
        try:
            # Ensure setup directory exists
            os.makedirs(self.setup_dir, exist_ok=True)

            # Get QLC+ fixture directories
            qlc_fixture_dirs = []
            if sys.platform.startswith('linux'):
                qlc_fixture_dirs.extend([
                    '/usr/share/qlcplus/fixtures',
                    os.path.expanduser('~/.qlcplus/fixtures')
                ])
            elif sys.platform == 'win32':
                qlc_fixture_dirs.append(os.path.join(os.path.expanduser('~'), 'QLC+', 'fixtures'))
            elif sys.platform == 'darwin':
                qlc_fixture_dirs.append(os.path.expanduser('~/Library/Application Support/QLC+/fixtures'))

            # Scan all fixture definitions first
            fixture_definitions = {}
            for dir_path in qlc_fixture_dirs:
                if os.path.exists(dir_path):
                    for manufacturer_dir in os.listdir(dir_path):
                        manufacturer_path = os.path.join(dir_path, manufacturer_dir)
                        if os.path.isdir(manufacturer_path):
                            for fixture_file in os.listdir(manufacturer_path):
                                if fixture_file.endswith('.qxf'):
                                    fixture_path = os.path.join(manufacturer_path, fixture_file)
                                    try:
                                        tree = ET.parse(fixture_path)
                                        root = tree.getroot()
                                        ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

                                        manufacturer = root.find('.//Manufacturer', ns).text
                                        model = root.find('.//Model', ns).text

                                        # Get all available modes
                                        modes = []
                                        for mode in root.findall('.//Mode', ns):
                                            mode_name = mode.get('Name')
                                            channels = mode.findall('Channel', ns)
                                            modes.append({
                                                'name': mode_name,
                                                'channels': len(channels)
                                            })

                                        fixture_definitions[(manufacturer, model)] = {
                                            'path': fixture_path,
                                            'modes': modes
                                        }
                                    except Exception as e:
                                        print(f"Error parsing fixture file {fixture_path}: {e}")

            # Parse workspace
            tree = ET.parse(workspace_path)
            root = tree.getroot()
            ns = {'qlc': 'http://www.qlcplus.org/Workspace'}

            # Extract fixtures with their groups
            fixtures_data = []
            for fixture in root.findall(".//qlc:Engine/qlc:Fixture", ns):
                fixture_id = fixture.find("qlc:ID", ns).text
                universe = int(fixture.find("qlc:Universe", ns).text) + 1
                address = int(fixture.find("qlc:Address", ns).text) + 1
                manufacturer = fixture.find("qlc:Manufacturer", ns).text
                model = fixture.find("qlc:Model", ns).text
                current_mode = fixture.find("qlc:Mode", ns).text

                # Find group for this fixture
                group_name = ""
                for group in root.findall(".//qlc:Engine/qlc:ChannelsGroup", ns):
                    if group.text and fixture_id in group.text.split(','):
                        group_name = group.get('Name')
                        self.existing_groups.add(group_name)
                        break

                # Get fixture definition if available
                fixture_def = fixture_definitions.get((manufacturer, model))

                fixtures_data.append({
                    'Universe': universe,
                    'Address': address,
                    'Manufacturer': manufacturer,
                    'Model': model,
                    'Name': fixture.find("qlc:Name", ns).text,
                    'Group': group_name,
                    'Direction': "",
                    'CurrentMode': current_mode,
                    'AvailableModes': fixture_def['modes'] if fixture_def else None
                })

            # Update fixtures table
            self.tableWidget.setRowCount(0)
            for fixture in fixtures_data:
                row = self.tableWidget.rowCount()
                self.tableWidget.insertRow(row)

                # Create spinboxes for Universe and Address
                universe_spin = QtWidgets.QSpinBox()
                universe_spin.setRange(1, 16)
                universe_spin.setValue(fixture['Universe'])
                self.tableWidget.setCellWidget(row, 0, universe_spin)

                address_spin = QtWidgets.QSpinBox()
                address_spin.setRange(1, 512)
                address_spin.setValue(fixture['Address'])
                self.tableWidget.setCellWidget(row, 1, address_spin)

                # Add manufacturer and model
                self.tableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(fixture['Manufacturer']))
                self.tableWidget.setItem(row, 3, QtWidgets.QTableWidgetItem(fixture['Model']))

                # Create mode combobox with available modes
                mode_combo = QtWidgets.QComboBox()
                if fixture['AvailableModes']:
                    for mode in fixture['AvailableModes']:
                        mode_combo.addItem(f"{mode['name']} ({mode['channels']}ch)")

                    # Set current mode
                    current_mode = fixture['CurrentMode']
                    index = mode_combo.findText(current_mode, QtCore.Qt.MatchFlag.MatchStartsWith)
                    if index >= 0:
                        mode_combo.setCurrentIndex(index)
                        self.tableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem(
                            str(fixture['AvailableModes'][index]['channels'])))

                    # Create closure to capture the current row
                    def create_update_channels(current_row):
                        def update_channels(index):
                            channels = fixture['AvailableModes'][index]['channels']
                            self.tableWidget.setItem(current_row, 4, QtWidgets.QTableWidgetItem(str(channels)))
                            # Reapply color after updating channels
                            group_combo = self.tableWidget.cellWidget(current_row, 7)
                            if group_combo and group_combo.currentText():
                                group_name = group_combo.currentText()
                                if group_name in self.group_colors:
                                    color = self.group_colors[group_name]
                                    self.tableWidget.item(current_row, 4).setBackground(color)

                        return update_channels

                    mode_combo.currentIndexChanged.connect(create_update_channels(row))
                else:
                    mode_combo.addItem(fixture['CurrentMode'])
                self.tableWidget.setCellWidget(row, 5, mode_combo)

                # Add name
                self.tableWidget.setItem(row, 6, QtWidgets.QTableWidgetItem(fixture['Name']))

                # Create group combobox
                group_combo = QtWidgets.QComboBox()
                group_combo.setEditable(True)
                group_combo.addItem("")
                for group in sorted(self.existing_groups):
                    group_combo.addItem(group)
                group_combo.addItem("Add New...")
                group_combo.setCurrentText(fixture['Group'])

                def handle_group_selection(text):
                    if text == "Add New...":
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
                                self.existing_groups.add(new_group)
                                current_index = group_combo.findText("Add New...")
                                group_combo.removeItem(current_index)
                                group_combo.addItem(new_group)
                                group_combo.addItem("Add New...")
                                group_combo.setCurrentText(new_group)
                    self.update_row_colors()

                group_combo.currentTextChanged.connect(handle_group_selection)
                self.tableWidget.setCellWidget(row, 7, group_combo)

                # Create direction combobox
                direction_combo = QtWidgets.QComboBox()
                direction_combo.addItems(["", "↑", "↓"])
                self.tableWidget.setCellWidget(row, 8, direction_combo)

            # Update row colors
            self.update_row_colors()

            print("Workspace data displayed successfully")

        except Exception as e:
            print(f"Error processing workspace file: {e}")
            import traceback
            traceback.print_exc()

    def update_show_table(self, show_name):
        if show_name in self.show_structures:  # Note: make show_structures a class attribute
            show_parts = self.show_structures[show_name]

            # Clear existing table
            self.tableWidget_3.setRowCount(0)

            # Set up fixed columns
            headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color']
            self.tableWidget_3.setColumnCount(len(headers))
            self.tableWidget_3.setHorizontalHeaderLabels(headers)

            # Read structure file to get colors
            structure_file = os.path.join(self.project_root, "shows", show_name, f"{show_name}_structure.csv")
            part_colors = {}
            with open(structure_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    part_colors[row['showpart']] = row['color']

            # Load existing values from JSON if it exists
            values_file = os.path.join(self.project_root, "shows", show_name, f"{show_name}_values.json")
            existing_values = {}
            if os.path.exists(values_file):
                try:
                    with open(values_file, 'r') as f:
                        values_data = json.load(f)
                        for item in values_data:
                            key = (item['show_part'], item['fixture_group'])
                            existing_values[key] = item
                except Exception as e:
                    print(f"Error loading values file: {e}")

            # Read fixture groups from groups.csv
            groups_file = os.path.join(self.setup_dir, "groups.csv")
            fixture_groups = set()
            with open(groups_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    fixture_groups.add(row['category'])

            # Add rows for each show part and fixture group combination
            row = 0
            for show_part in show_parts:
                for group in sorted(fixture_groups):
                    self.tableWidget_3.insertRow(row)

                    # Show Part (read-only)
                    show_part_item = QtWidgets.QTableWidgetItem(show_part)
                    show_part_item.setFlags(show_part_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                    self.tableWidget_3.setItem(row, 0, show_part_item)

                    # Fixture Group (read-only)
                    group_item = QtWidgets.QTableWidgetItem(group)
                    group_item.setFlags(group_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                    self.tableWidget_3.setItem(row, 1, group_item)

                    # Speed (combo box)
                    speed_combo = QtWidgets.QComboBox()
                    speed_values = ['1/32', '1/16', '1/8', '1/4', '1/2', '1', '2', '4', '8', '16', '32']
                    speed_combo.addItems(speed_values)

                    # Set default speed or load existing value
                    key = (show_part, group)
                    if key in existing_values and existing_values[key].get('speed'):
                        speed_combo.setCurrentText(existing_values[key]['speed'])
                    else:
                        speed_combo.setCurrentText('1')

                    self.tableWidget_3.setCellWidget(row, 3, speed_combo)

                    # Effect (button to open selection dialog)
                    effect_button = QtWidgets.QPushButton("Select Effect")
                    if key in existing_values and existing_values[key].get('effect'):
                        effect_button.setText(existing_values[key]['effect'])
                        effect_button.setProperty("current_effect", existing_values[key]['effect'])
                    else:
                        effect_button.setText("Select Effect")
                        effect_button.setProperty("current_effect", "")

                    def create_effect_selector(target_row):
                        def show_effect_dialog():
                            # Get the button from the correct row
                            button = self.tableWidget_3.cellWidget(target_row, 2)
                            if not button:
                                return

                            dialog = EffectSelectionDialog(self.effects_dir, self)
                            if dialog.exec() == QDialog.DialogCode.Accepted:
                                selected_effect = dialog.get_selected_effect()
                                if selected_effect == "CLEAR":
                                    button.setText("Select Effect")
                                    button.setProperty("current_effect", "")
                                elif selected_effect:
                                    button.setText(selected_effect)
                                    button.setProperty("current_effect", selected_effect)

                        return show_effect_dialog

                    # Connect the button with explicit row reference
                    effect_button.clicked.connect(create_effect_selector(row))
                    self.tableWidget_3.setCellWidget(row, 2, effect_button)

                    # Color picker button
                    color_button = QtWidgets.QPushButton()
                    color_button.setFixedHeight(25)

                    # Load existing color values if available
                    if key in existing_values:
                        values = existing_values[key]
                        if values.get('color'):
                            color_button.setStyleSheet(f"background-color: {values['color']};")
                            color_button.setText(values['color'])
                            color_button.setProperty("current_color", values['color'])
                    else:
                        color_button.setText("Pick Color")

                    def create_color_picker(button, row_num):
                        def show_color_picker():
                            color = QtWidgets.QColorDialog.getColor(
                                initial=QtGui.QColor(button.property("current_color") or "#000000"),
                                options=QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel
                            )
                            if color.isValid():
                                hex_color = color.name().upper()
                                button.setStyleSheet(f"background-color: {hex_color};")
                                button.setText(hex_color)
                                button.setProperty("current_color", hex_color)
                                #self.save_cell_value(row_num, show_name)

                        return show_color_picker

                    color_button.clicked.connect(create_color_picker(color_button, row))
                    self.tableWidget_3.setCellWidget(row, 4, color_button)

                    # Connect speed combo box changes
                    #speed_combo.currentTextChanged.connect(lambda _, r=row: self.save_cell_value(r, show_name))

                    # Set row background color
                    if show_part in part_colors:
                        color = part_colors[show_part]
                        qcolor = QtGui.QColor(color)
                        qcolor.setAlpha(40)
                        for col in range(5):
                            item = self.tableWidget_3.item(row, col)
                            if item:
                                item.setBackground(qcolor)

                    row += 1

            # Connect table item changed signal (for Effect column)
            def on_item_changed(item):
                if item.column() == 2:  # Effect column
                    #self.save_cell_value(item.row(), show_name)
                    pass

            # Disconnect existing signals if any
            try:
                self.tableWidget_3.itemChanged.disconnect()
            except:
                pass

            self.tableWidget_3.itemChanged.connect(on_item_changed)

            # Make columns stretch to fill table width
            header = self.tableWidget_3.horizontalHeader()
            for i in range(5):
                if i == 4:
                    header.setStretchLastSection(True)
                else:
                    header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.Stretch)

            print("Show structure updated successfully")

    def save_show(self):
        try:
            current_show = self.comboBox.currentText()
            if not current_show:
                return

            show_data = []
            row_count = self.tableWidget_3.rowCount()

            for row in range(row_count):
                show_part = self.tableWidget_3.item(row, 0).text()
                fixture_group = self.tableWidget_3.item(row, 1).text()
                # Save effects from button
                effect_button = self.tableWidget_3.cellWidget(row, 2)
                effect = effect_button.property("current_effect") if effect_button else ""
                # Save speed from speed widget
                speed_widget = self.tableWidget_3.cellWidget(row, 3)
                speed = speed_widget.currentText() if speed_widget else "1"
                # Save colors
                color_button = self.tableWidget_3.cellWidget(row, 4)
                color = color_button.property("current_color") if color_button else ""

                show_data.append({
                    'show_part': show_part,
                    'fixture_group': fixture_group,
                    'effect': effect,
                    'speed': speed,
                    'color': color
                })

            # Save to JSON file
            show_dir = os.path.join(self.project_root, "shows", current_show)
            os.makedirs(show_dir, exist_ok=True)
            values_file = os.path.join(show_dir, f"{current_show}_values.json")

            with open(values_file, 'w') as f:
                json.dump(show_data, f, indent=2)

            print(f"Show {current_show} saved successfully")

        except Exception as e:
            print(f"Error saving show: {e}")
            import traceback
            traceback.print_exc()

    def import_show_structure(self):
        try:
            # Set up fixed columns
            headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color']
            self.tableWidget_3.setColumnCount(len(headers))
            self.tableWidget_3.setHorizontalHeaderLabels(headers)

            # Get all show directories
            shows_dir = os.path.join(self.project_root, "shows")
            self.show_structures = {}  # Make this a class attribute

            # Scan for all show structure files
            for show_dir in os.listdir(shows_dir):
                show_path = os.path.join(shows_dir, show_dir)
                if os.path.isdir(show_path):
                    structure_file = os.path.join(show_path, f"{show_dir}_structure.csv")
                    if os.path.exists(structure_file):
                        show_parts = []
                        with open(structure_file, 'r') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                show_parts.append(row['showpart'])
                        self.show_structures[show_dir] = show_parts

            # Update combo box with available shows
            self.comboBox.clear()
            self.comboBox.addItems(sorted(self.show_structures.keys()))

            # Connect combo box selection to table update
            self.comboBox.currentTextChanged.connect(self.update_show_table)

            # Initialize table with first show if available
            if self.comboBox.count() > 0:
                first_show = self.comboBox.itemText(0)
                self.update_show_table(first_show)

            print("Show structure imported successfully")

        except Exception as e:
            print(f"Error importing show structure: {e}")
            import traceback
            traceback.print_exc()

    def load_fixtures_to_show(self):
        try:
            # Get unique manufacturer/model combinations from the table
            models_in_table = set()
            for row in range(self.tableWidget.rowCount()):
                manufacturer = self.tableWidget.item(row, 2).text()
                model = self.tableWidget.item(row, 3).text()
                models_in_table.add((manufacturer, model))

            # Get QLC+ fixture directories
            qlc_fixture_dirs = []
            if sys.platform.startswith('linux'):
                qlc_fixture_dirs.extend([
                    '/usr/share/qlcplus/fixtures',
                    os.path.expanduser('~/.qlcplus/fixtures')
                ])
            elif sys.platform == 'win32':
                qlc_fixture_dirs.append(os.path.join(os.path.expanduser('~'), 'QLC+', 'fixtures'))
            elif sys.platform == 'darwin':
                qlc_fixture_dirs.append(os.path.expanduser('~/Library/Application Support/QLC+/fixtures'))

            # Dictionary to store fixture definitions
            fixture_definitions = {}

            # Scan all fixtures and store definitions
            for dir_path in qlc_fixture_dirs:
                if os.path.exists(dir_path):
                    for manufacturer_dir in os.listdir(dir_path):
                        manufacturer_path = os.path.join(dir_path, manufacturer_dir)
                        if os.path.isdir(manufacturer_path):
                            for fixture_file in os.listdir(manufacturer_path):
                                if fixture_file.endswith('.qxf'):
                                    fixture_path = os.path.join(manufacturer_path, fixture_file)
                                    try:
                                        tree = ET.parse(fixture_path)
                                        root = tree.getroot()
                                        ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

                                        manufacturer = root.find('.//Manufacturer', ns).text
                                        model = root.find('.//Model', ns).text

                                        # Only process if this fixture is in our table
                                        if (manufacturer, model) in models_in_table:
                                            # Get physical information
                                            physical = root.find('.//Physical', ns)
                                            physical_info = {}
                                            if physical is not None:
                                                for elem in physical:
                                                    physical_info[elem.tag] = elem.text

                                            # Get channels information
                                            channels_info = []
                                            for channel in root.findall('.//Channel', ns):
                                                channel_data = {
                                                    'name': channel.text,
                                                    'number': channel.get('Number'),
                                                    'group': channel.find('Group', ns).text if channel.find('Group',
                                                                                                            ns) is not None else None,
                                                    'byte': channel.find('Byte', ns).text if channel.find('Byte',
                                                                                                          ns) is not None else None,
                                                    'capabilities': []
                                                }

                                                # Get capabilities
                                                for capability in channel.findall('Capability', ns):
                                                    cap_data = {
                                                        'min': capability.get('Min'),
                                                        'max': capability.get('Max'),
                                                        'name': capability.text,
                                                        'color': capability.get('Color'),
                                                        'resource': capability.get('Resource')
                                                    }
                                                    channel_data['capabilities'].append(cap_data)

                                                channels_info.append(channel_data)

                                            # Get modes information
                                            modes_info = []
                                            for mode in root.findall('.//Mode', ns):
                                                mode_data = {
                                                    'name': mode.get('Name'),
                                                    'physical': {},
                                                    'channels': []
                                                }

                                                # Get mode-specific physical info
                                                mode_physical = mode.find('Physical', ns)
                                                if mode_physical is not None:
                                                    for elem in mode_physical:
                                                        mode_data['physical'][elem.tag] = elem.text

                                                # Get channels for this mode
                                                for channel in mode.findall('Channel', ns):
                                                    mode_data['channels'].append({
                                                        'number': channel.get('Number'),
                                                        'name': channel.text
                                                    })

                                                modes_info.append(mode_data)

                                            # Store the fixture definition
                                            key = f"{manufacturer}_{model}"
                                            fixture_definitions[key] = {
                                                'manufacturer': manufacturer,
                                                'model': model,
                                                'physical': physical_info,
                                                'channels': channels_info,
                                                'modes': modes_info
                                            }

                                    except Exception as e:
                                        print(f"Error parsing fixture file {fixture_path}: {e}")

            # Write fixture definitions to JSON
            fixtures_json_path = os.path.join(self.setup_dir, "fixtures.json")
            with open(fixtures_json_path, 'w') as f:
                json.dump(fixture_definitions, f, indent=4)

                # Save current fixture data to CSV
                fixtures_csv_path = os.path.join(self.setup_dir, "fixtures.csv")
                with open(fixtures_csv_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        ['Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode', 'Name', 'Group',
                         'Direction'])

                    for row in range(self.tableWidget.rowCount()):
                        universe = self.tableWidget.cellWidget(row, 0).value()
                        address = self.tableWidget.cellWidget(row, 1).value()
                        manufacturer = self.tableWidget.item(row, 2).text()
                        model = self.tableWidget.item(row, 3).text()
                        channels = self.tableWidget.item(row, 4).text()

                        # Get mode without channel count
                        mode_combo = self.tableWidget.cellWidget(row, 5)
                        mode_text = mode_combo.currentText() if mode_combo else ""
                        mode = mode_text.split(' (')[0] if ' (' in mode_text else mode_text

                        #mode = self.tableWidget.cellWidget(row, 5).currentText()
                        name = self.tableWidget.item(row, 6).text()
                        group = self.tableWidget.cellWidget(row, 7).currentText()
                        direction = self.tableWidget.cellWidget(row, 8).currentText()

                        writer.writerow(
                            [universe, address, manufacturer, model, channels, mode, name, group, direction])
                    print("Fixtures saved successfully to fixtures.csv")

            # Save current fixture data to groups.csv
            groups_csv_path = os.path.join(self.setup_dir, "groups.csv")
            with open(groups_csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'category', 'Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode'])

                # Track unique groups for id assignment
                group_ids = {}
                current_id = 0

                for row in range(self.tableWidget.rowCount()):
                    # Get group from the group combobox
                    group_combo = self.tableWidget.cellWidget(row, 7)
                    if group_combo and group_combo.currentText():
                        group = group_combo.currentText()

                        # Get or assign group id
                        if group not in group_ids:
                            group_ids[group] = current_id
                            current_id += 1

                        # Get mode without channel count
                        mode_combo = self.tableWidget.cellWidget(row, 5)
                        mode_text = mode_combo.currentText() if mode_combo else ""
                        mode = mode_text.split(' (')[0] if ' (' in mode_text else mode_text

                        # Write row to CSV
                        writer.writerow([
                            group_ids[group],  # id
                            group,  # category
                            self.tableWidget.cellWidget(row, 0).value(),  # Universe
                            self.tableWidget.cellWidget(row, 1).value(),  # Address
                            self.tableWidget.item(row, 2).text(),  # Manufacturer
                            self.tableWidget.item(row, 3).text(),  # Model
                            self.tableWidget.item(row, 4).text(),  # Channels
                            mode  # Mode (without channel count)
                        ])

            print("Groups saved successfully to groups.csv")
            print("Fixture definitions saved successfully to fixtures.json")


        except Exception as e:
            print(f"Error loading fixtures: {e}")
            import traceback
            traceback.print_exc()

    def create_workspace(self):
        try:
            # First save the current show to ensure all data is up to date
            self.save_show()

            # Get current show name
            current_show = self.comboBox.currentText()
            if not current_show:
                print("No show selected")
                return

            # Create workspace using the imported function
            # Pass the project root directory to ensure correct file paths
            create_qlc_workspace()

            print("Workspace created successfully")

            # Show success message to the user
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

            # Show error message to the user
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

