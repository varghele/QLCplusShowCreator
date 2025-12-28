# gui/gui.py
# Refactored MainWindow using tab components

import os
import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtCore import QTimer
from config.models import Configuration
from utils.create_workspace import create_qlc_workspace
from gui.Ui_MainWindow import Ui_MainWindow
from gui.tabs import ConfigurationTab, FixturesTab, ShowsTab, StageTab, StructureTab
from gui.audio_settings_dialog import AudioSettingsDialog
from gui.progress_manager import ProgressManager, set_progress_manager


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

        # Set up status indicator timer
        self._setup_status_timer()

        # Initialize progress manager
        self.progress_manager = ProgressManager(self)
        set_progress_manager(self.progress_manager)

    def _setup_status_timer(self):
        """Set up timer for updating toolbar status indicators."""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_toolbar_status)
        self.status_timer.start(1000)  # Update every second
        # Initial update
        self._update_toolbar_status()

    def _update_toolbar_status(self):
        """Update ArtNet and TCP status indicators in toolbar."""
        # Update ArtNet status
        artnet_controller = getattr(self.shows_tab, 'artnet_controller', None)
        artnet_enabled = getattr(self.shows_tab, 'artnet_enabled', False)

        if artnet_controller and artnet_enabled:
            self.artnet_status_indicator.setText("ON")
            self.artnet_status_indicator.setStyleSheet("font-weight: bold; color: #4CAF50;")
            self.artnet_status_indicator.setToolTip("ArtNet DMX Output: Enabled")
        else:
            self.artnet_status_indicator.setText("OFF")
            self.artnet_status_indicator.setStyleSheet("font-weight: bold; color: #666;")
            self.artnet_status_indicator.setToolTip("ArtNet DMX Output: Disabled")

        # Update TCP status
        tcp_server = getattr(self.shows_tab, 'tcp_server', None)

        if tcp_server and tcp_server.is_running():
            client_count = tcp_server.get_client_count()
            if client_count > 0:
                self.tcp_status_indicator.setText(f"{client_count}")
                self.tcp_status_indicator.setStyleSheet("font-weight: bold; color: #4CAF50;")
                self.tcp_status_indicator.setToolTip(f"TCP Visualizer Server: {client_count} client(s) connected")
            else:
                self.tcp_status_indicator.setText("ON")
                self.tcp_status_indicator.setStyleSheet("font-weight: bold; color: #2196F3;")
                self.tcp_status_indicator.setToolTip("TCP Visualizer Server: Running, no clients")
        else:
            self.tcp_status_indicator.setText("OFF")
            self.tcp_status_indicator.setStyleSheet("font-weight: bold; color: #666;")
            self.tcp_status_indicator.setToolTip("TCP Visualizer Server: Not running")

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
        """Handle tab change - notify tabs of activation/deactivation."""
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

            # Call on_tab_deactivated on the previous tab
            if hasattr(self, '_current_tab_index') and self._current_tab_index in tab_map:
                prev_tab = tab_map[self._current_tab_index]
                if prev_tab and hasattr(prev_tab, 'on_tab_deactivated'):
                    prev_tab.on_tab_deactivated()

            # Store current tab index
            self._current_tab_index = index

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
        # Use lightweight update for shows tab - only update lane group combos
        # instead of recreating all lanes (major performance improvement)
        self.shows_tab.update_fixture_groups_only()

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
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration",
            "",
            "YAML Files (*.yaml);;All Files (*)"
        )

        if not file_path:
            return

        # Store path for the delayed loader
        self._pending_config_path = file_path

        # Show progress dialog first
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        dialog = self.progress_manager.start_modal(
            "Loading Configuration",
            "Opening file...",
            maximum=8  # Steps: open, parse, pre-cache, 5 tabs
        )

        # Force the dialog to actually render before starting blocking operations
        for _ in range(5):
            QApplication.processEvents()

        # Force repaint the dialog window
        if dialog:
            dialog.repaint()
            QApplication.processEvents()

        # Use a timer to delay the actual loading, giving the dialog time to fully render
        QTimer.singleShot(100, self._do_load_configuration)

    def _do_load_configuration(self):
        """Perform the actual configuration loading (called after dialog is visible)."""
        from PyQt6.QtWidgets import QApplication, QMessageBox

        try:
            file_path = self._pending_config_path

            # Load configuration
            self.progress_manager.update_modal(1, "Parsing YAML configuration...")
            QApplication.processEvents()
            self.config = Configuration.load(file_path)
            self.config_path = file_path

            # Pre-load fixture definitions into cache to speed up tab switching
            self.progress_manager.update_modal(2, "Loading fixture definitions...")
            QApplication.processEvents()
            self._preload_fixture_definitions()

            # Update all tabs with new configuration
            self.config_tab.config = self.config
            self.fixtures_tab.config = self.config
            self.stage_tab.config = self.config
            self.structure_tab.config = self.config
            self.shows_tab.config = self.config

            # Refresh all tabs
            self.progress_manager.update_modal(3, "Updating Configuration tab...")
            QApplication.processEvents()
            self.config_tab.update_from_config()

            self.progress_manager.update_modal(4, "Updating Fixtures tab...")
            QApplication.processEvents()
            self.fixtures_tab.update_from_config()

            self.progress_manager.update_modal(5, "Updating Stage tab...")
            QApplication.processEvents()
            self.stage_tab.update_from_config()

            self.progress_manager.update_modal(6, "Updating Structure tab...")
            QApplication.processEvents()
            self.structure_tab.update_from_config()

            self.progress_manager.update_modal(7, "Updating Shows tab...")
            QApplication.processEvents()
            self.shows_tab.update_from_config()

            self.progress_manager.update_modal(8, "Done!")
            self.progress_manager.finish_modal()

            QMessageBox.information(
                self,
                "Success",
                f"Configuration loaded from {file_path}"
            )
            print(f"Configuration loaded from {file_path}")

        except Exception as e:
            self.progress_manager.finish_modal()
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load configuration: {str(e)}"
            )
            print(f"Error loading configuration: {e}")
            import traceback
            traceback.print_exc()

    def _preload_fixture_definitions(self):
        """Pre-load fixture definitions into cache for faster access."""
        try:
            from utils.fixture_utils import get_cached_fixture_definitions

            # Collect all fixture models from configuration
            models_in_config = set()
            for fixture in self.config.fixtures:
                models_in_config.add((fixture.manufacturer, fixture.model))
            for group in self.config.groups.values():
                for fixture in group.fixtures:
                    models_in_config.add((fixture.manufacturer, fixture.model))

            # Load into cache
            if models_in_config:
                get_cached_fixture_definitions(models_in_config)
                print(f"Pre-loaded {len(models_in_config)} fixture definition(s) into cache")
        except Exception as e:
            print(f"Warning: Could not pre-load fixture definitions: {e}")

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

            # Show progress dialog
            self.progress_manager.start_modal(
                "Importing Workspace",
                "Parsing QLC+ workspace file...",
                maximum=7  # Steps: import, pre-cache, 5 tabs
            )

            # Import from workspace
            self.progress_manager.update_modal(1, "Importing fixtures and universes...")
            self.config = Configuration.from_workspace(file_path)

            # Pre-load fixture definitions into cache
            self.progress_manager.update_modal(2, "Loading fixture definitions...")
            self._preload_fixture_definitions()

            # Update all tabs
            self.config_tab.config = self.config
            self.fixtures_tab.config = self.config
            self.stage_tab.config = self.config
            self.structure_tab.config = self.config
            self.shows_tab.config = self.config

            # Refresh all tabs
            self.progress_manager.update_modal(3, "Updating Configuration tab...")
            self.config_tab.update_from_config()

            self.progress_manager.update_modal(4, "Updating Fixtures tab...")
            self.fixtures_tab.update_from_config()

            self.progress_manager.update_modal(5, "Updating Stage tab...")
            self.stage_tab.update_from_config()

            self.progress_manager.update_modal(6, "Updating Structure tab...")
            self.structure_tab.update_from_config()

            self.progress_manager.update_modal(7, "Updating Shows tab...")
            self.shows_tab.update_from_config()

            self.progress_manager.finish_modal()

            QMessageBox.information(
                self,
                "Success",
                f"Workspace imported from {file_path}"
            )
            print(f"Workspace imported from {file_path}")

        except Exception as e:
            self.progress_manager.finish_modal()
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
            # Show progress dialog
            self.progress_manager.start_modal(
                "Creating Workspace",
                "Saving configuration...",
                maximum=3  # Steps: save tabs, create workspace, done
            )

            # Save all tabs to configuration first
            self.progress_manager.update_modal(1, "Saving tab data...")
            self.config_tab.save_to_config()
            self.fixtures_tab.save_to_config()
            self.stage_tab.save_to_config()
            self.structure_tab.save_to_config()
            self.shows_tab.save_to_config()

            # Create workspace
            self.progress_manager.update_modal(2, "Generating QLC+ workspace XML...")
            create_qlc_workspace(self.config)

            self.progress_manager.update_modal(3, "Finalizing...")
            self.progress_manager.finish_modal()

            workspace_path = os.path.join(self.project_root, 'workspace.qxw')
            QMessageBox.information(
                self,
                "Success",
                f"Workspace created at {workspace_path}"
            )
            print(f"Workspace created at {workspace_path}")

        except Exception as e:
            self.progress_manager.finish_modal()
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
