# gui/gui_new.py
# Refactored MainWindow using tab components

import os
import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from config.models import Configuration
from utils.create_workspace import create_qlc_workspace
from gui.Ui_MainWindow import Ui_MainWindow
from gui.tabs import ConfigurationTab, FixturesTab, ShowsTab, StageTab


class MainWindow(QMainWindow, Ui_MainWindow):
    """Main application window with tab-based architecture

    Orchestrates tab components and handles application-level operations:
    - File operations (save/load configuration)
    - Workspace import/export
    - Cross-tab coordination
    - Toolbar and menu actions
    """

    def __init__(self):
        super().__init__()

        # Initialize configuration
        self.config = Configuration()

        # Set up UI from designer file
        self.setupUi(self)

        # Initialize paths
        self._initialize_paths()

        # Create and integrate tab components
        self._create_tabs()

        # Connect application-level signals
        self._connect_signals()

    def _initialize_paths(self):
        """Initialize project paths"""
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.setup_dir = os.path.join(self.project_root, "setup")
        self.config_path = None

    def _create_tabs(self):
        """Create and integrate tab components"""
        # Create tab instances with shared configuration
        self.config_tab = ConfigurationTab(self.config, self)
        self.fixtures_tab = FixturesTab(self.config, self)
        self.stage_tab = StageTab(self.config, self)
        self.shows_tab = ShowsTab(self.config, self)

        # Replace placeholder tabs with actual tab widgets
        # The tab widget structure is created in Ui_MainWindow
        # We need to replace the placeholder widgets

        # Configuration tab (tab_config)
        layout = self.tab_config.layout()
        if layout:
            # Clear existing widgets
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.deleteLater()

        # Set the config_tab as the layout/content
        new_layout = QtWidgets.QVBoxLayout(self.tab_config)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.addWidget(self.config_tab)

        # Fixtures tab (tab)
        layout = self.tab.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.deleteLater()

        new_layout = QtWidgets.QVBoxLayout(self.tab)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.addWidget(self.fixtures_tab)

        # Stage tab (tab_stage) - already has StageView, update it
        # Stage tab already has a layout from setupStageTab, we'll replace it entirely
        if self.tab_stage.layout():
            old_layout = self.tab_stage.layout()
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            old_layout.deleteLater()

        new_layout = QtWidgets.QVBoxLayout(self.tab_stage)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.addWidget(self.stage_tab)

        # Shows tab (tab_2)
        layout = self.tab_2.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.deleteLater()

        new_layout = QtWidgets.QVBoxLayout(self.tab_2)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.addWidget(self.shows_tab)

    def _connect_signals(self):
        """Connect application-level signals"""
        # Toolbar actions
        self.saveAction.triggered.connect(self.save_configuration)
        self.loadAction.triggered.connect(self.load_configuration)
        self.loadShowsAction.triggered.connect(self.import_show_structure)
        self.importWorkspaceAction.triggered.connect(self.import_workspace)
        self.createWorkspaceAction.triggered.connect(self.create_workspace)

    def on_groups_changed(self):
        """Coordinate updates when fixture groups change

        Called by FixturesTab when groups are modified.
        Propagates changes to dependent tabs (Stage and Shows).
        """
        self.stage_tab.update_from_config()
        self.shows_tab.update_from_config()

    def save_configuration(self):
        """Save configuration to YAML file"""
        try:
            # Save all tabs to configuration
            self.config_tab.save_to_config()
            self.fixtures_tab.save_to_config()
            self.stage_tab.save_to_config()
            self.shows_tab.save_to_config()

            # Prompt for file path if not set
            if not self.config_path:
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Save Configuration",
                    "",
                    "YAML Files (*.yaml);;All Files (*)"
                )
                if not file_path:
                    return
                self.config_path = file_path

            # Save configuration
            self.config.save(self.config_path)
            QMessageBox.information(
                self,
                "Success",
                f"Configuration saved to {self.config_path}"
            )
            print(f"Configuration saved to {self.config_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save configuration: {str(e)}"
            )
            print(f"Error saving configuration: {e}")
            import traceback
            traceback.print_exc()

    def load_configuration(self):
        """Load configuration from YAML file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Configuration",
                "",
                "YAML Files (*.yaml);;All Files (*)"
            )

            if not file_path:
                return

            # Load configuration
            self.config = Configuration.load(file_path)
            self.config_path = file_path

            # Update all tabs with new configuration
            self.config_tab.config = self.config
            self.fixtures_tab.config = self.config
            self.stage_tab.config = self.config
            self.shows_tab.config = self.config

            # Refresh all tabs
            self.config_tab.update_from_config()
            self.fixtures_tab.update_from_config()
            self.stage_tab.update_from_config()
            self.shows_tab.update_from_config()

            QMessageBox.information(
                self,
                "Success",
                f"Configuration loaded from {file_path}"
            )
            print(f"Configuration loaded from {file_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load configuration: {str(e)}"
            )
            print(f"Error loading configuration: {e}")
            import traceback
            traceback.print_exc()

    def import_workspace(self):
        """Import configuration from QLC+ workspace file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import QLC+ Workspace",
                "",
                "QLC+ Workspace (*.qxw);;All Files (*)"
            )

            if not file_path:
                return

            # Import from workspace
            self.config = Configuration.from_workspace(file_path)

            # Update all tabs
            self.config_tab.config = self.config
            self.fixtures_tab.config = self.config
            self.stage_tab.config = self.config
            self.shows_tab.config = self.config

            # Refresh all tabs
            self.config_tab.update_from_config()
            self.fixtures_tab.update_from_config()
            self.stage_tab.update_from_config()
            self.shows_tab.update_from_config()

            QMessageBox.information(
                self,
                "Success",
                f"Workspace imported from {file_path}"
            )
            print(f"Workspace imported from {file_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to import workspace: {str(e)}"
            )
            print(f"Error importing workspace: {e}")
            import traceback
            traceback.print_exc()

    def import_show_structure(self):
        """Import show structure from CSV files"""
        try:
            self.shows_tab.import_show_structure()
            QMessageBox.information(
                self,
                "Success",
                "Show structure imported successfully"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to import show structure: {str(e)}"
            )
            print(f"Error importing show structure: {e}")
            import traceback
            traceback.print_exc()

    def create_workspace(self):
        """Create QLC+ workspace file from configuration"""
        try:
            # Save all tabs to configuration first
            self.config_tab.save_to_config()
            self.fixtures_tab.save_to_config()
            self.stage_tab.save_to_config()
            self.shows_tab.save_to_config()

            # Create workspace
            create_qlc_workspace(self.config)

            workspace_path = os.path.join(self.project_root, 'workspace.qxw')
            QMessageBox.information(
                self,
                "Success",
                f"Workspace created at {workspace_path}"
            )
            print(f"Workspace created at {workspace_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create workspace: {str(e)}"
            )
            print(f"Error creating workspace: {e}")
            import traceback
            traceback.print_exc()
