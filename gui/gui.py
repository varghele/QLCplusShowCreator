import sys
import os
import csv
import json
import xml.etree.ElementTree as ET
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QDialog, QFileDialog, QLineEdit, QFormLayout, QDialogButtonBox
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QTableWidgetItem, QToolBar
from PyQt6.QtGui import QAction, QFont
from .effect_selection import EffectSelectionDialog
from utils.create_workspace import create_qlc_workspace
from config.models import Configuration, FixtureGroup, ShowEffect, Show, ShowPart, Universe
from .tabs.Universe import UniverseDialog
from typing import Dict, List, Optional



class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("QLCAutoShow")
        MainWindow.resize(1200, 900)

        # Create central widget
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        # Create toolbar
        self.toolbar = QToolBar()
        MainWindow.addToolBar(self.toolbar)

        # Create actions with icons from QtWidgets.QStyle
        style = self.style()  # Get style from the widget
        self.saveAction = QAction(QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton),
            "Save Configuration", MainWindow)
        self.loadAction = QAction(QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton),
            "Load Configuration", MainWindow)
        self.loadShowsAction = QAction(QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_TitleBarShadeButton),
            "Load Shows", MainWindow)
        self.importWorkspaceAction = QAction(QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView),
            "Import Workspace", MainWindow)
        self.createWorkspaceAction = QAction(QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_MediaSeekForward),
            "Create Workspace", MainWindow)

        # Add actions to toolbar
        self.toolbar.addAction(self.saveAction)
        self.toolbar.addAction(self.loadAction)
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                             QtWidgets.QSizePolicy.Policy.Expanding)
        self.toolbar.addWidget(spacer)
        self.toolbar.addAction(self.loadShowsAction)
        self.toolbar.addAction(self.importWorkspaceAction)
        self.toolbar.addAction(self.createWorkspaceAction)

        # Main layout
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.tabWidget = QtWidgets.QTabWidget(parent=self.centralwidget)

        # Configuration/Universes tab
        self.tab_config = QtWidgets.QWidget()
        self.setupConfigTab()

        # Fixtures Tab
        self.tab = QtWidgets.QWidget()
        self.setupFixturesTab()

        # Stage Tab
        self.tab_stage = QtWidgets.QWidget()
        self.setupStageTab()

        # Shows Tab
        self.tab_2 = QtWidgets.QWidget()
        self.setupShowsTab()

        # Add tabs to widget
        self.tabWidget.addTab(self.tab_config, "Configuration")
        self.tabWidget.addTab(self.tab, "Fixtures")
        self.tabWidget.addTab(self.tab_stage, "Stage")
        self.tabWidget.addTab(self.tab_2, "Shows")

        self.horizontalLayout.addWidget(self.tabWidget)
        MainWindow.setCentralWidget(self.centralwidget)

        # Setup status bar and menu
        self.setupStatusAndMenu(MainWindow)

        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "QLCAutoShow"))
        self.pushButton.setToolTip(_translate("MainWindow", "<html><head/><body><p>Add Fixture</p></body></html>"))
        self.pushButton.setText(_translate("MainWindow", "+"))
        self.pushButton_2.setToolTip(_translate("MainWindow", "<html><head/><body><p>Remove Fixture</p></body></html>"))
        self.pushButton_2.setText(_translate("MainWindow", "-"))
        self.label.setText(_translate("MainWindow", "Fixtures"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Fixtures"))
        self.pushButton_5.setText(_translate("MainWindow", "Load Shows"))
        self.pushButton_7.setText(_translate("MainWindow", "Save Show"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_stage), _translate("MainWindow", "Stage"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Shows"))
        self.saveAction.setText(_translate("MainWindow", "Save Configuration"))
        self.loadAction.setText(_translate("MainWindow", "Load Configuration"))

    def setupConfigTab(self):
        # Main layout for the configuration tab
        layout = QtWidgets.QVBoxLayout(self.tab_config)

        # Universe list
        self.universe_list = QtWidgets.QTableWidget()
        self.universe_list.setColumnCount(6)
        self.universe_list.setHorizontalHeaderLabels([
            "Universe", "Output Type", "IP Address", "Port", "Subnet", "Universe"
        ])

        # Set table properties
        self.universe_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.universe_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        # Add/Remove buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.add_universe_btn = QtWidgets.QPushButton("+")
        self.remove_universe_btn = QtWidgets.QPushButton("-")
        button_layout.addWidget(self.add_universe_btn)
        button_layout.addWidget(self.remove_universe_btn)
        button_layout.addStretch()

        # Add widgets to main layout
        layout.addLayout(button_layout)
        layout.addWidget(self.universe_list)

    def setupFixturesTab(self):
        # Add Fixture buttons
        self.pushButton = QtWidgets.QPushButton(parent=self.tab)
        self.pushButton.setGeometry(QtCore.QRect(10, 14, 31, 31))
        self.pushButton.setText("+")
        self.pushButton.setToolTip("Add Fixture")

        self.pushButton_2 = QtWidgets.QPushButton(parent=self.tab)
        self.pushButton_2.setGeometry(QtCore.QRect(50, 14, 31, 31))
        self.pushButton_2.setText("-")
        self.pushButton_2.setToolTip("Remove Fixture")

        # Fixtures table
        self.tableWidget = QtWidgets.QTableWidget(parent=self.tab)
        self.tableWidget.setGeometry(QtCore.QRect(10, 80, 1151, 640))

        # Fixtures label
        self.label = QtWidgets.QLabel("Fixtures", parent=self.tab)
        self.label.setGeometry(QtCore.QRect(10, 60, 81, 17))
        self.label.setFont(QFont("", 14, QFont.Weight.Bold))

    def setupShowsTab(self):
        # Shows table
        self.tableWidget_3 = QtWidgets.QTableWidget(parent=self.tab_2)
        self.tableWidget_3.setGeometry(QtCore.QRect(10, 90, 1151, 701))

        # Shows buttons
        self.pushButton_5 = QtWidgets.QPushButton("Load Shows", parent=self.tab_2)
        self.pushButton_5.setGeometry(QtCore.QRect(10, 20, 171, 31))

        self.pushButton_7 = QtWidgets.QPushButton("Save Show", parent=self.tab_2)
        self.pushButton_7.setGeometry(QtCore.QRect(200, 20, 101, 31))

        # Shows combo box
        self.comboBox = QtWidgets.QComboBox(parent=self.tab_2)
        self.comboBox.setGeometry(QtCore.QRect(10, 60, 171, 25))

    def setupStageTab(self):
        # Stage tab implementation here
        pass

    def setupStatusAndMenu(self, MainWindow):
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        MainWindow.setStatusBar(self.statusbar)

        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1200, 22))
        self.menuQLCAutoShow = QtWidgets.QMenu(parent=self.menubar)
        MainWindow.setMenuBar(self.menubar)
        self.menuQLCAutoShow.addSeparator()
        self.menubar.addAction(self.menuQLCAutoShow.menuAction())


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.config = Configuration()

        # Initialize paths and data
        self.initialize_paths()

        # Set up tables
        self._setup_tables()

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
        self.universe_list.itemChanged.connect(self.on_universe_item_changed)

        # Connect existing buttons
        self.pushButton.clicked.connect(self.add_fixture)
        self.pushButton_2.clicked.connect(self.remove_fixture)

        self.pushButton_5.clicked.connect(self.import_show_structure)
        #self.pushButton_7.clicked.connect(self.save_show)

        # Connect toolbar actions
        self.saveAction.triggered.connect(self.save_configuration)
        self.loadAction.triggered.connect(self.load_configuration)
        self.loadShowsAction.triggered.connect(self.import_show_structure)
        self.importWorkspaceAction.triggered.connect(self.import_workspace)
        self.createWorkspaceAction.triggered.connect(self.create_workspace)

    def update_config_from_table(self, item):
        """Update configuration when table items change"""
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
            fixture.direction = widget.currentText()

    def update_groups(self):
        """Update groups in configuration"""
        # Clear existing groups
        self.config.groups = {}

        # Rebuild groups from fixtures
        for fixture in self.config.fixtures:
            if fixture.group:
                if fixture.group not in self.config.groups:
                    self.config.groups[fixture.group] = FixtureGroup(fixture.group, [])
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
            direction_combo.setCurrentText(fixture.direction)
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
        headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color']
        if self.tableWidget_3.columnCount() != len(headers):
            self.tableWidget_3.setColumnCount(len(headers))
            self.tableWidget_3.setHorizontalHeaderLabels(headers)

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
                                                    self.get_color(current_row))

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
                        self.get_color(r)
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
                            initial=QtGui.QColor(existing_effect.color if existing_effect else "#000000"),
                            options=QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel
                        )
                        if color.isValid():
                            hex_color = color.name().upper()
                            button.setStyleSheet(f"background-color: {hex_color};")
                            button.setText(hex_color)
                            self.update_show_effect(current_show, part_name, group,
                                                    self.get_effect(current_row),
                                                    self.get_speed(current_row),
                                                    hex_color)

                    return handle_color

                color_button.clicked.connect(
                    create_color_handler(row, show_part.name, group_name)
                )
                self.tableWidget_3.setCellWidget(row, 4, color_button)

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
        return button.property("current_effect") if button else ""

    def get_speed(self, row):
        """Get speed from table row"""
        combo = self.tableWidget_3.cellWidget(row, 3)
        return combo.currentText() if combo else "1"

    def get_color(self, row):
        """Get color from table row"""
        button = self.tableWidget_3.cellWidget(row, 4)
        return button.property("current_color") if button else ""

    def update_show_effect(self, show_name, show_part, fixture_group, effect, speed, color):
        """Update show effect in configuration"""
        if show_name not in self.config.shows:
            return

        show = self.config.shows[show_name]

        # Find existing effect or create new one
        existing_effect = next(
            (effect for effect in show.effects
             if effect.show_part == show_part
             and effect.fixture_group == fixture_group),
            None
        )

        if existing_effect:
            existing_effect.effect = effect
            existing_effect.speed = speed
            existing_effect.color = color
        else:
            show.effects.append(ShowEffect(
                show_part=show_part,
                fixture_group=fixture_group,
                effect=effect,
                speed=speed,
                color=color
            ))

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
        """Extract configuration from workspace file"""
        try:
            # Load configuration from workspace
            self.config = Configuration.from_workspace(workspace_path)

            # Import show structure into configuration
            self.config = Configuration.import_show_structure(self.config, os.path.dirname(workspace_path))

            # Update UI
            self.update_fixture_tab_from_config()
            self.update_show_tab_from_config()

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
            headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color']
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
                                    color=""
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

    def update_show_table_old(self, show_name):
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

    def save_show_old(self):
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

    def import_show_structure_old(self):
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

