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
        self.toolbar.addAction(self.importWorkspaceAction)
        self.toolbar.addAction(self.createWorkspaceAction)

        # Main layout
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.tabWidget = QtWidgets.QTabWidget(parent=self.centralwidget)

        # Configuration/Universes tab (UI created by ConfigurationTab)
        self.tab_config = QtWidgets.QWidget()

        # Fixtures Tab (UI created by FixturesTab)
        self.tab = QtWidgets.QWidget()

        # Stage Tab (UI created by StageTab)
        self.tab_stage = QtWidgets.QWidget()

        # Shows Tab (UI created by ShowsTab)
        self.tab_2 = QtWidgets.QWidget()

        # Structure Tab (UI created by StructureTab)
        self.tab_structure = QtWidgets.QWidget()

        # Add tabs to widget
        self.tabWidget.addTab(self.tab_config, "Configuration")
        self.tabWidget.addTab(self.tab, "Fixtures")
        self.tabWidget.addTab(self.tab_stage, "Stage")
        self.tabWidget.addTab(self.tab_structure, "Structure")
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
        # Tab titles
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_config), _translate("MainWindow", "Configuration"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Fixtures"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_stage), _translate("MainWindow", "Stage"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_structure), _translate("MainWindow", "Structure"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Shows"))
        # Toolbar actions
        self.saveAction.setText(_translate("MainWindow", "Save Configuration"))
        self.loadAction.setText(_translate("MainWindow", "Load Configuration"))

    def setupStatusAndMenu(self, MainWindow):
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        MainWindow.setStatusBar(self.statusbar)

        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1200, 22))

        # File menu
        self.menuFile = QtWidgets.QMenu("File", parent=self.menubar)
        self.actionSaveConfig = QAction("Save Configuration", MainWindow)
        self.actionSaveConfig.setShortcut("Ctrl+S")
        self.actionLoadConfig = QAction("Load Configuration", MainWindow)
        self.actionLoadConfig.setShortcut("Ctrl+O")
        self.actionImportWorkspace = QAction("Import QLC+ Workspace...", MainWindow)
        self.actionCreateWorkspace = QAction("Create QLC+ Workspace", MainWindow)
        self.actionExit = QAction("Exit", MainWindow)
        self.actionExit.setShortcut("Ctrl+Q")

        self.menuFile.addAction(self.actionSaveConfig)
        self.menuFile.addAction(self.actionLoadConfig)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionImportWorkspace)
        self.menuFile.addAction(self.actionCreateWorkspace)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExit)

        # Settings menu
        self.menuSettings = QtWidgets.QMenu("Settings", parent=self.menubar)
        self.actionAudioSettings = QAction("Audio Settings...", MainWindow)
        self.actionAudioSettings.setShortcut("Ctrl+,")
        self.menuSettings.addAction(self.actionAudioSettings)

        # Help menu
        self.menuHelp = QtWidgets.QMenu("Help", parent=self.menubar)
        self.actionAbout = QAction("About", MainWindow)
        self.menuHelp.addAction(self.actionAbout)

        # Add menus to menubar
        MainWindow.setMenuBar(self.menubar)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())