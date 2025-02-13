from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QToolBar
from PyQt6.QtGui import QAction, QFont


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