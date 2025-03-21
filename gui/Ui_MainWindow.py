from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtWidgets import QToolBar
from PyQt6.QtGui import QAction, QFont
from gui.StageView import StageView


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("QLCAutoShow")
        MainWindow.resize(1250, 900)

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
        # Add buttons directly to the tab
        self.add_universe_btn = QtWidgets.QPushButton(parent=self.tab_config)
        self.add_universe_btn.setGeometry(QtCore.QRect(10, 14, 31, 31))
        self.add_universe_btn.setText("+")
        self.add_universe_btn.setToolTip("Add Universe")

        self.remove_universe_btn = QtWidgets.QPushButton(parent=self.tab_config)
        self.remove_universe_btn.setGeometry(QtCore.QRect(50, 14, 31, 31))
        self.remove_universe_btn.setText("-")
        self.remove_universe_btn.setToolTip("Remove Universe")

        self.update_config_btn = QtWidgets.QPushButton(parent=self.tab_config)
        self.update_config_btn.setGeometry(QtCore.QRect(90, 14, 115, 31))
        self.update_config_btn.setText("Update Config")
        self.update_config_btn.setToolTip("Update Configuration")

        # Universe list label
        self.config_label = QtWidgets.QLabel("Config", parent=self.tab_config)
        self.config_label.setGeometry(QtCore.QRect(10, 60, 81, 17))
        self.config_label.setFont(QFont("", 14, QFont.Weight.Bold))

        # Universe list table
        self.universe_list = QtWidgets.QTableWidget(parent=self.tab_config)
        self.universe_list.setGeometry(QtCore.QRect(10, 80, 1151, 640))
        self.universe_list.setColumnCount(6)
        self.universe_list.setHorizontalHeaderLabels([
            "Universe", "Output Type", "IP Address", "Port", "Subnet", "Universe"
        ])

        # Set table properties
        self.universe_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.universe_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

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

        # Update Fixtures button
        self.updateFixturesButton = QtWidgets.QPushButton(parent=self.tab)
        self.updateFixturesButton.setGeometry(QtCore.QRect(90, 14, 115, 31))
        self.updateFixturesButton.setText("Update Fixtures")
        self.updateFixturesButton.setToolTip("Update Fixtures in Config")

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
        self.pushButton_5 = QtWidgets.QPushButton("Save Shows", parent=self.tab_2)
        self.pushButton_5.setGeometry(QtCore.QRect(10, 20, 171, 31))

        self.pushButton_7 = QtWidgets.QPushButton("Update", parent=self.tab_2)
        self.pushButton_7.setGeometry(QtCore.QRect(200, 20, 101, 31))

        # Shows combo box
        self.comboBox = QtWidgets.QComboBox(parent=self.tab_2)
        self.comboBox.setGeometry(QtCore.QRect(10, 60, 171, 25))

    def setupStageTab(self):
        # Create main layout for the tab
        main_layout = QtWidgets.QHBoxLayout(self.tab_stage)

        # Left control panel
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QVBoxLayout(control_panel)
        control_panel.setFixedWidth(250)

        # Stage dimensions group
        dim_group = QtWidgets.QGroupBox("Stage Dimensions")
        dim_layout = QtWidgets.QFormLayout(dim_group)

        self.stage_width = QtWidgets.QSpinBox()
        self.stage_width.setRange(1, 1000)
        self.stage_width.setValue(10)  # Default 10 meters
        self.stage_height = QtWidgets.QSpinBox()
        self.stage_height.setRange(1, 1000)
        self.stage_height.setValue(6)  # Default 6 meters

        dim_layout.addRow("Width (m):", self.stage_width)
        dim_layout.addRow("Depth (m):", self.stage_height)

        # Update stage button
        self.update_stage_btn = QtWidgets.QPushButton("Update Stage")
        dim_layout.addRow(self.update_stage_btn)
        self.save_stage_btn = QtWidgets.QPushButton("Save Stage")
        dim_layout.addRow(self.save_stage_btn)

        # Grid controls group
        grid_group = QtWidgets.QGroupBox("Grid Settings")
        grid_layout = QtWidgets.QFormLayout(grid_group)

        self.grid_toggle = QtWidgets.QCheckBox("Show Grid")
        self.grid_toggle.setChecked(True)  # Grid visible by default

        self.grid_size = QtWidgets.QDoubleSpinBox()
        self.grid_size.setRange(0.1, 50)
        self.grid_size.setValue(0.5)  # Default 0.5m grid
        self.grid_size.setSingleStep(0.1)

        self.snap_to_grid = QtWidgets.QCheckBox("Snap to Grid")

        # Connect the snap to grid checkbox
        self.snap_to_grid.stateChanged.connect(lambda state: self.stage_view.set_snap_to_grid(bool(state)))

        grid_layout.addRow(self.grid_toggle)
        grid_layout.addRow("Grid Size (m):", self.grid_size)
        grid_layout.addRow(self.snap_to_grid)

        # Add groups to control panel
        control_layout.addWidget(dim_group)
        control_layout.addWidget(grid_group)

        # Add Plot Stage button
        plot_group = QtWidgets.QGroupBox("Stage Plot")
        plot_layout = QtWidgets.QVBoxLayout(plot_group)

        self.plot_stage_btn = QtWidgets.QPushButton("Plot Stage")
        plot_layout.addWidget(self.plot_stage_btn)

        control_layout.addWidget(plot_group)
        control_layout.addStretch()

        # Create stage view area (right side)
        stage_view_container = QtWidgets.QWidget()
        stage_view_layout = QtWidgets.QVBoxLayout(stage_view_container)

        # Initialize StageView with configuration
        self.stage_view = StageView(self)  # Initialize without config
        stage_view_layout.addWidget(self.stage_view)

        # Add update button connection
        self.update_stage_btn.clicked.connect(self.update_stage)
        self.save_stage_btn.clicked.connect(self.save_stage)

        self.grid_toggle.stateChanged.connect(lambda state:
                                              self.stage_view.updateGrid(visible=bool(state))
                                              )

        self.grid_size.valueChanged.connect(lambda value:
                                            self.stage_view.updateGrid(size_m=value)
                                            )

        # Add both panels to main layout
        main_layout.addWidget(control_panel)
        main_layout.addWidget(stage_view_container, stretch=1)

        # Add spot controls
        spot_group = QtWidgets.QGroupBox("Stage Marks")
        spot_layout = QtWidgets.QVBoxLayout(spot_group)

        self.add_spot_btn = QtWidgets.QPushButton("Add Mark")
        self.remove_item_btn = QtWidgets.QPushButton("Remove Selected")

        spot_layout.addWidget(self.add_spot_btn)
        spot_layout.addWidget(self.remove_item_btn)

        control_layout.addWidget(spot_group)

        # Connect the buttons
        self.add_spot_btn.clicked.connect(lambda: self.stage_view.add_spot())
        self.remove_item_btn.clicked.connect(self.stage_view.remove_selected_items)

    def update_stage(self):
        """Update stage view from current configuration"""
        self.stage_view.updateStage(
            self.stage_width.value(),
            self.stage_height.value()
        )
        self.stage_view.update_from_config()

    def save_stage(self):
        """Saves stage parameters to config"""
        self.stage_view.save_positions_to_config()

    def setupStatusAndMenu(self, MainWindow):
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        MainWindow.setStatusBar(self.statusbar)

        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1200, 22))
        self.menuQLCAutoShow = QtWidgets.QMenu(parent=self.menubar)
        MainWindow.setMenuBar(self.menubar)
        self.menuQLCAutoShow.addSeparator()
        self.menubar.addAction(self.menuQLCAutoShow.menuAction())