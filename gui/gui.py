# gui/gui.py
# Refactored MainWindow using tab components

import os
import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from config.models import Configuration
from utils.create_workspace import create_qlc_workspace
from gui.Ui_MainWindow import Ui_MainWindow
from gui.tabs import ConfigurationTab, FixturesTab, ShowsTab, StageTab, StructureTab
from gui.audio_settings_dialog import AudioSettingsDialog


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
        self.structure_tab = StructureTab(self.config, self)
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

        # Structure tab (tab_structure)
        layout = self.tab_structure.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.deleteLater()

        new_layout = QtWidgets.QVBoxLayout(self.tab_structure)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.addWidget(self.structure_tab)

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
        self.importWorkspaceAction.triggered.connect(self.import_workspace)
        self.createWorkspaceAction.triggered.connect(self.create_workspace)

        # File menu actions
        self.actionSaveConfig.triggered.connect(self.save_configuration)
        self.actionLoadConfig.triggered.connect(self.load_configuration)
        self.actionImportWorkspace.triggered.connect(self.import_workspace)
        self.actionCreateWorkspace.triggered.connect(self.create_workspace)
        self.actionExit.triggered.connect(self.close)

        # Tab change handler
        self.tabWidget.currentChanged.connect(self._on_tab_changed)

        # Settings menu actions
        self.actionAudioSettings.triggered.connect(self.open_audio_settings)

        # Help menu actions
        self.actionAbout.triggered.connect(self.show_about)

    def _on_tab_changed(self, index):
        """Handle tab change - notify tabs of activation."""
        try:
            print(f"DEBUG: Tab changed to index {index}")

            # Map tab indices to tab widgets (check actual attribute names)
            tab_map = {}

            # Try to get the actual tab widgets
            if hasattr(self, 'config_tab'):
                tab_map[0] = self.config_tab
            if hasattr(self, 'fixtures_tab'):
                tab_map[1] = self.fixtures_tab
            if hasattr(self, 'stage_tab'):
                tab_map[2] = self.stage_tab
            if hasattr(self, 'structure_tab'):
                tab_map[3] = self.structure_tab
            if hasattr(self, 'shows_tab'):
                tab_map[4] = self.shows_tab

            # Call on_tab_activated on the newly activated tab
            if index in tab_map:
                tab = tab_map[index]
                if tab and hasattr(tab, 'on_tab_activated'):
                    print(f"DEBUG: Calling on_tab_activated for tab {index}")
                    tab.on_tab_activated()
            else:
                print(f"DEBUG: No handler for tab index {index}")
        except Exception as e:
            print(f"ERROR in _on_tab_changed: {e}")
            import traceback
            traceback.print_exc()

    def on_groups_changed(self):
        """Coordinate updates when fixture groups change

        Called by FixturesTab when groups are modified.
        Propagates changes to dependent tabs (Stage, Structure, and Shows).
        """
        self.stage_tab.update_from_config()
        self.structure_tab.update_from_config()
        self.shows_tab.update_from_config()

    def on_show_selected(self, show_name: str, source_tab: str):
        """Coordinate show selection across tabs.

        Called when a show is selected in either Structure or Shows tab.
        Syncs the selection to the other tab.

        Args:
            show_name: Name of the selected show
            source_tab: Which tab triggered the selection ('structure' or 'shows')
        """
        if source_tab == 'shows':
            # Update structure tab to match
            if self.structure_tab.show_combo.currentText() != show_name:
                self.structure_tab.show_combo.blockSignals(True)
                self.structure_tab.show_combo.setCurrentText(show_name)
                self.structure_tab.show_combo.blockSignals(False)
                self.structure_tab._load_show(show_name)
        elif source_tab == 'structure':
            # Update shows tab to match
            if self.shows_tab.show_combo.currentText() != show_name:
                self.shows_tab.show_combo.blockSignals(True)
                self.shows_tab.show_combo.setCurrentText(show_name)
                self.shows_tab.show_combo.blockSignals(False)
                self.shows_tab._load_show(show_name)

    def save_configuration(self):
        """Save configuration to YAML file"""
        try:
            # Save all tabs to configuration
            self.config_tab.save_to_config()
            self.fixtures_tab.save_to_config()
            self.stage_tab.save_to_config()
            self.structure_tab.save_to_config()
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
            self.structure_tab.config = self.config
            self.shows_tab.config = self.config

            # Refresh all tabs
            self.config_tab.update_from_config()
            self.fixtures_tab.update_from_config()
            self.stage_tab.update_from_config()
            self.structure_tab.update_from_config()
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
            self.structure_tab.config = self.config
            self.shows_tab.config = self.config

            # Refresh all tabs
            self.config_tab.update_from_config()
            self.fixtures_tab.update_from_config()
            self.stage_tab.update_from_config()
            self.structure_tab.update_from_config()
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
            self.structure_tab.save_to_config()
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

    def open_audio_settings(self):
        """Open audio settings dialog"""
        try:
            # Get audio engine and device manager from shows tab if available
            audio_engine = getattr(self.shows_tab, 'audio_engine', None)
            device_manager = getattr(self.shows_tab, 'device_manager', None)

            dialog = AudioSettingsDialog(
                device_manager=device_manager,
                audio_engine=audio_engine,
                parent=self
            )

            if dialog.exec():
                # Settings were applied
                settings = dialog.get_settings()
                if settings:
                    # Store settings for shows tab to use
                    self.audio_settings = settings

                    # If shows tab has audio components, update them
                    if hasattr(self.shows_tab, 'apply_audio_settings'):
                        self.shows_tab.apply_audio_settings(settings)

                    print(f"Audio settings applied: device={settings['device_index']}, "
                          f"rate={settings['sample_rate']}, buffer={settings['buffer_size']}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open audio settings: {str(e)}"
            )
            print(f"Error opening audio settings: {e}")
            import traceback
            traceback.print_exc()

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About QLCAutoShow",
            "QLCAutoShow\n\n"
            "A tool for creating QLC+ light shows with timeline-based editing.\n\n"
            "Features:\n"
            "- Fixture management and grouping\n"
            "- Stage layout visualization\n"
            "- Timeline-based show editing\n"
            "- Audio playback with waveform display\n"
            "- QLC+ workspace export"
        )

    def closeEvent(self, event):
        """Handle application close"""
        # Clean up shows tab audio resources
        if hasattr(self.shows_tab, 'cleanup'):
            self.shows_tab.cleanup()

        event.accept()
