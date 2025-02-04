import sys
import os
import json
import xml.etree.ElementTree as ET
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QToolBar
from PyQt6.QtGui import QAction, QFont
from config.models import Configuration
from .tabs.ShowTab import ShowTab
from .tabs.FixtureTab import FixtureTab
from config.models import FixtureGroup, Fixture

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("QLCAutoShow")
        self.resize(1200, 900)

        # Create central widget
        self.centralwidget = QtWidgets.QWidget(parent=self)
        self.centralwidget.setObjectName("centralwidget")

        # Create toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        # Create Save and Load actions
        self.saveAction = QAction("Save Configuration", self)
        self.loadAction = QAction("Load Configuration", self)
        self.toolbar.addAction(self.saveAction)
        self.toolbar.addAction(self.loadAction)

        # Main layout
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.tabWidget = QtWidgets.QTabWidget(parent=self.centralwidget)

        # Create tabs
        self.tab = QtWidgets.QWidget()  # Fixtures tab
        self.tab_stage = QtWidgets.QWidget()  # Stage tab
        self.tab_2 = QtWidgets.QWidget()  # Shows tab

        # Setup individual tabs
        self.setupFixturesTab()
        self.setupStageTab()
        self.setupShowsTab()

        # Add tabs to widget
        self.tabWidget.addTab(self.tab, "Fixtures")
        self.tabWidget.addTab(self.tab_stage, "Stage")
        self.tabWidget.addTab(self.tab_2, "Shows")

        self.horizontalLayout.addWidget(self.tabWidget)
        self.setCentralWidget(self.centralwidget)

        # Setup status bar
        self.statusbar = QtWidgets.QStatusBar(parent=self)
        self.setStatusBar(self.statusbar)

        # Initialize configuration
        self.config = Configuration(fixtures=[], groups={})

        # Initialize paths and data
        self.initialize_paths()

        # Set up tables
        self._setup_tables()

        # Initialize tab handlers
        self.fixture_tab = FixtureTab(self)
        self.show_tab = ShowTab(self)

        # Connect signals
        self.connect_signals()

    def _setup_tables(self):
        """Set up the tables with their columns and properties"""
        # Setup Fixtures table
        headers = ['Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode', 'Name', 'Group', 'Direction']
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setHorizontalHeaderLabels(headers)

        # Set column widths for fixtures table
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
        show_headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color']
        self.tableWidget_3.setColumnCount(len(show_headers))
        self.tableWidget_3.setHorizontalHeaderLabels(show_headers)

        # Make tableWidget_3 stretch to fill parent
        self.tableWidget_3.setGeometry(QtCore.QRect(10, 90, self.tab_2.width() - 20, self.tab_2.height() - 100))

        # Make table resize with parent
        def resize_table(event):
            self.tableWidget_3.setGeometry(QtCore.QRect(10, 90, event.size().width() - 20, event.size().height() - 100))

        # Connect resize event to the tab
        self.tab_2.resizeEvent = resize_table

        # Make columns stretch to fill table width
        header = self.tableWidget_3.horizontalHeader()
        for i in range(len(show_headers)):
            if i == len(show_headers) - 1:  # Last column
                header.setStretchLastSection(True)
            else:
                header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.Interactive)

        # Enable sorting and styling for all tables
        for table in [self.tableWidget, self.tableWidget_3]:
            table.setSortingEnabled(True)
            table.setShowGrid(True)
            table.setAlternatingRowColors(True)
            table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

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

        # Other buttons
        self.pushButton_3 = QtWidgets.QPushButton("Import QLC WorkSpace", parent=self.tab)
        self.pushButton_3.setGeometry(QtCore.QRect(978, 10, 191, 31))

        self.pushButton_4 = QtWidgets.QPushButton("Load Fixtures To Show", parent=self.tab)
        self.pushButton_4.setGeometry(QtCore.QRect(110, 14, 181, 31))

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

        self.pushButton_6 = QtWidgets.QPushButton("Create Workspace", parent=self.tab_2)
        self.pushButton_6.setGeometry(QtCore.QRect(1020, 20, 141, 31))

        self.pushButton_7 = QtWidgets.QPushButton("Save Show", parent=self.tab_2)
        self.pushButton_7.setGeometry(QtCore.QRect(200, 20, 101, 31))

        # Shows combo box
        self.comboBox = QtWidgets.QComboBox(parent=self.tab_2)
        self.comboBox.setGeometry(QtCore.QRect(10, 60, 171, 25))

    def setupStageTab(self):
        # Stage tab implementation here
        pass

    def initialize_paths(self):
        """Initialize project paths"""
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.setup_dir = os.path.join(self.project_root, "setup")

        # Load effects
        effects_json_path = os.path.join(self.project_root, "effects", "effects.json")
        with open(effects_json_path, 'r') as f:
            self.effects_dir = json.load(f)

    def connect_signals(self):
        """Connect main window signals"""
        # Connect tab change signal
        self.tabWidget.currentChanged.connect(self.handle_tab_change)

        # Connect toolbar actions
        self.saveAction.triggered.connect(self.save_configuration)
        self.loadAction.triggered.connect(self.load_configuration)

    def handle_tab_change(self, index):
        """Handle tab changes"""
        if self.tabWidget.tabText(index) == "Shows":
            self.show_tab.update_show_tab_from_config()

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
                self.config = Configuration.load(filename)
                self.fixture_tab.update_fixture_tab_from_config()
                self.show_tab.update_show_tab_from_config()
                QMessageBox.information(self, "Success", "Configuration loaded successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load configuration: {str(e)}")

    def extract_from_workspace(self, workspace_path):
        """Extract configuration from workspace file"""
        try:
            # Load configuration from workspace
            self.config = Configuration.from_workspace(workspace_path)

            # Import show structure into configuration
            self.config = Configuration.import_show_structure(self.config, os.path.dirname(workspace_path))

            # Update UI
            self.fixture_tab.update_fixture_tab_from_config()
            self.show_tab.update_show_tab_from_config()

            # Initialize combo box with shows
            if self.config.shows:
                self.show_tab.comboBox.clear()
                self.show_tab.comboBox.addItems(sorted(self.config.shows.keys()))

                # Connect combo box selection to table update
                self.show_tab.comboBox.currentTextChanged.connect(self.show_tab.update_show_tab_from_config)

                # Initialize table with first show if available
                if self.show_tab.comboBox.count() > 0:
                    first_show = self.show_tab.comboBox.itemText(0)
                    self.show_tab.comboBox.setCurrentText(first_show)
                    self.show_tab.update_show_tab_from_config()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to process workspace: {str(e)}")
            import traceback
            traceback.print_exc()


def main():
    try:
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
