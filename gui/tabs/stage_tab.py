# gui/tabs/stage_tab.py

import subprocess
import sys
import os

from PyQt6 import QtWidgets
from PyQt6.QtCore import QTimer
from config.models import Configuration
from .base_tab import BaseTab
from gui.StageView import StageView
from gui.stage_items import FixtureItem
from gui.dialogs.orientation_dialog import OrientationDialog


class StageTab(BaseTab):
    """Stage layout and fixture positioning tab

    Provides visual stage representation with fixture positioning,
    grid controls, and spot/mark management. Composes the existing
    StageView component with control panel UI.
    """

    def __init__(self, config: Configuration, parent=None):
        """Initialize stage tab

        Args:
            config: Shared Configuration object
            parent: Parent widget (typically MainWindow)
        """
        super().__init__(config, parent)

        # Tab active state (for pausing TCP updates when not visible)
        self._tab_active = False

        # Throttle timer for TCP updates (avoid flooding during drag)
        self._tcp_update_timer = QTimer()
        self._tcp_update_timer.setSingleShot(True)
        self._tcp_update_timer.setInterval(100)  # 100ms throttle
        self._tcp_update_timer.timeout.connect(self._do_tcp_update)
        self._tcp_update_pending = False

    def setup_ui(self):
        """Set up stage visualization UI"""
        # Create main layout for the tab
        main_layout = QtWidgets.QHBoxLayout(self)

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
        self.snap_to_grid.setChecked(True)  # Enable by default

        grid_layout.addRow(self.grid_toggle)
        grid_layout.addRow("Grid Size (m):", self.grid_size)
        grid_layout.addRow(self.snap_to_grid)

        # Stage marks group
        spot_group = QtWidgets.QGroupBox("Stage Marks")
        spot_layout = QtWidgets.QVBoxLayout(spot_group)

        self.add_spot_btn = QtWidgets.QPushButton("Add Mark")
        self.remove_item_btn = QtWidgets.QPushButton("Remove Selected")

        spot_layout.addWidget(self.add_spot_btn)
        spot_layout.addWidget(self.remove_item_btn)

        # Fixture Orientation group
        orientation_group = QtWidgets.QGroupBox("Fixture Orientation")
        orientation_layout = QtWidgets.QVBoxLayout(orientation_group)

        self.show_axes_checkbox = QtWidgets.QCheckBox("Show orientation axes")
        self.show_axes_checkbox.setToolTip("Show XYZ axes on fixtures when selected or hovered")

        self.show_all_axes_checkbox = QtWidgets.QCheckBox("Show all axes")
        self.show_all_axes_checkbox.setToolTip("Show axes on all fixtures (not just selected)")
        self.show_all_axes_checkbox.setEnabled(False)  # Disabled until show_axes is checked

        orientation_layout.addWidget(self.show_axes_checkbox)
        orientation_layout.addWidget(self.show_all_axes_checkbox)

        # Plot stage group
        plot_group = QtWidgets.QGroupBox("Stage Plot")
        plot_layout = QtWidgets.QVBoxLayout(plot_group)

        self.plot_stage_btn = QtWidgets.QPushButton("Plot Stage")
        plot_layout.addWidget(self.plot_stage_btn)

        # Visualizer group
        visualizer_group = QtWidgets.QGroupBox("3D Visualizer")
        visualizer_layout = QtWidgets.QVBoxLayout(visualizer_group)

        # Launch button
        self.launch_visualizer_btn = QtWidgets.QPushButton("Launch Visualizer")
        self.launch_visualizer_btn.setToolTip("Start the 3D Visualizer application")
        visualizer_layout.addWidget(self.launch_visualizer_btn)

        # TCP status indicator
        tcp_status_layout = QtWidgets.QHBoxLayout()
        tcp_status_layout.addWidget(QtWidgets.QLabel("TCP Server:"))
        self.tcp_status_label = QtWidgets.QLabel()
        self.tcp_status_label.setStyleSheet("font-weight: bold;")
        tcp_status_layout.addWidget(self.tcp_status_label)
        tcp_status_layout.addStretch()
        visualizer_layout.addLayout(tcp_status_layout)

        # Visualizer process reference
        self.visualizer_process = None

        # Timer to update TCP status
        self.tcp_status_timer = QTimer()
        self.tcp_status_timer.timeout.connect(self._update_tcp_status)
        self.tcp_status_timer.start(1000)  # Update every second

        # Initial status update
        self._update_tcp_status()

        # Add groups to control panel in order
        control_layout.addWidget(dim_group)
        control_layout.addWidget(grid_group)
        control_layout.addWidget(spot_group)
        control_layout.addWidget(orientation_group)
        control_layout.addWidget(plot_group)
        control_layout.addWidget(visualizer_group)
        control_layout.addStretch()

        # Create stage view area (right side)
        stage_view_container = QtWidgets.QWidget()
        stage_view_layout = QtWidgets.QVBoxLayout(stage_view_container)

        # Initialize StageView with configuration
        self.stage_view = StageView(self)
        self.stage_view.set_config(self.config)
        stage_view_layout.addWidget(self.stage_view)

        # Add both panels to main layout
        main_layout.addWidget(control_panel)
        main_layout.addWidget(stage_view_container, stretch=1)

    def connect_signals(self):
        """Connect widget signals to handlers"""
        # Stage dimension controls - auto-update on change
        self.stage_width.valueChanged.connect(self._update_stage)
        self.stage_height.valueChanged.connect(self._update_stage)
        self.update_stage_btn.clicked.connect(self._update_stage)

        # Grid controls
        self.grid_toggle.stateChanged.connect(
            lambda state: self.stage_view.updateGrid(visible=bool(state))
        )
        self.grid_size.valueChanged.connect(self._update_grid_size)
        self.snap_to_grid.stateChanged.connect(
            lambda state: self.stage_view.set_snap_to_grid(bool(state))
        )

        # Connect fixture changes to TCP update (for live visualizer sync)
        self.stage_view.fixtures_changed.connect(self._notify_tcp_update)

        # Spot/mark controls
        self.add_spot_btn.clicked.connect(lambda: self.stage_view.add_spot())
        self.remove_item_btn.clicked.connect(self.stage_view.remove_selected_items)

        # Visualizer controls
        self.launch_visualizer_btn.clicked.connect(self._launch_visualizer)

        # Orientation display controls
        self.show_axes_checkbox.stateChanged.connect(self._on_show_axes_changed)
        self.show_all_axes_checkbox.stateChanged.connect(self._on_show_all_axes_changed)

        # Orientation dialog trigger from right-click menu
        self.stage_view.set_orientation_requested.connect(self._on_set_orientation_requested)

    def update_from_config(self):
        """Refresh stage view from configuration"""
        if self.stage_view:
            self.stage_view.set_config(self.config)

        # Load stage dimensions and grid size from config
        if self.config:
            self.stage_width.blockSignals(True)
            self.stage_height.blockSignals(True)
            self.grid_size.blockSignals(True)

            self.stage_width.setValue(int(self.config.stage_width))
            self.stage_height.setValue(int(self.config.stage_height))
            if hasattr(self.config, 'grid_size'):
                self.grid_size.setValue(self.config.grid_size)

            self.stage_width.blockSignals(False)
            self.stage_height.blockSignals(False)
            self.grid_size.blockSignals(False)

    def save_to_config(self):
        """Save fixture positions and spots back to configuration"""
        if self.stage_view:
            self.stage_view.save_positions_to_config()

    def _update_stage(self):
        """Update stage dimensions from spin box values"""
        width = self.stage_width.value()
        height = self.stage_height.value()

        # Update StageView
        self.stage_view.updateStage(width, height)
        self.stage_view.update_from_config()

        # Update Configuration for TCP sync
        if self.config:
            self.config.stage_width = float(width)
            self.config.stage_height = float(height)

            # Notify TCP server if running (for live visualizer updates)
            self._notify_tcp_update()

    def _update_grid_size(self, value: float):
        """Update grid size from spin box value"""
        # Update StageView
        self.stage_view.updateGrid(size_m=value)

        # Update Configuration for TCP sync
        if self.config:
            self.config.grid_size = value

            # Notify TCP server if running (for live visualizer updates)
            self._notify_tcp_update()

    def _launch_visualizer(self):
        """Launch the 3D Visualizer application."""
        # Check if visualizer is already running
        if self.visualizer_process is not None:
            poll_result = self.visualizer_process.poll()
            if poll_result is None:
                # Process is still running
                QtWidgets.QMessageBox.information(
                    self,
                    "Visualizer Running",
                    "The Visualizer is already running."
                )
                return

        # Check if TCP server is running, offer to start it if not
        if not self._ensure_tcp_server_running():
            return

        # Get path to visualizer main.py
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        visualizer_path = os.path.join(project_root, "visualizer", "main.py")

        if not os.path.exists(visualizer_path):
            QtWidgets.QMessageBox.warning(
                self,
                "Visualizer Not Found",
                f"Could not find visualizer at:\n{visualizer_path}"
            )
            return

        try:
            # Launch visualizer as subprocess
            self.visualizer_process = subprocess.Popen(
                [sys.executable, visualizer_path],
                cwd=project_root
            )
            print(f"Visualizer launched (PID: {self.visualizer_process.pid})")
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Launch Error",
                f"Failed to launch Visualizer:\n{str(e)}"
            )

    def _ensure_tcp_server_running(self) -> bool:
        """
        Ensure TCP server is running before launching visualizer.

        Returns:
            True if server is running (or was started), False if user cancelled
        """
        try:
            main_window = self.window()
            if not main_window:
                return True  # Can't check, proceed anyway

            shows_tab = getattr(main_window, 'shows_tab', None)
            if not shows_tab:
                return True  # Can't check, proceed anyway

            tcp_server = getattr(shows_tab, 'tcp_server', None)

            # Check if server is running
            if tcp_server and tcp_server.is_running():
                return True  # Already running

            # Server not running - ask user if they want to start it
            reply = QtWidgets.QMessageBox.question(
                self,
                "Start TCP Server?",
                "The TCP server is not running.\n\n"
                "The Visualizer needs the TCP server to receive stage configuration.\n\n"
                "Start the TCP server now?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.Yes
            )

            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # Start the TCP server via ShowsTab
                try:
                    # Use _on_tcp_toggle which handles all the init logic
                    if hasattr(shows_tab, '_on_tcp_toggle'):
                        shows_tab._on_tcp_toggle(True)

                        # Update the checkbox in ShowsTab if it exists
                        tcp_checkbox = getattr(shows_tab, 'tcp_checkbox', None)
                        if tcp_checkbox:
                            tcp_checkbox.blockSignals(True)
                            tcp_checkbox.setChecked(True)
                            tcp_checkbox.blockSignals(False)
                    else:
                        QtWidgets.QMessageBox.warning(
                            self,
                            "Cannot Start Server",
                            "TCP server initialization not available.\n"
                            "Please enable 'Visualizer Server' in the Shows tab."
                        )
                        return False

                    # Verify it started
                    tcp_server = getattr(shows_tab, 'tcp_server', None)
                    if tcp_server and tcp_server.is_running():
                        print("TCP server started successfully")
                        self._update_tcp_status()
                        return True
                    else:
                        QtWidgets.QMessageBox.warning(
                            self,
                            "Server Start Failed",
                            "Failed to start TCP server.\n"
                            "Please check the Shows tab for errors."
                        )
                        return False

                except Exception as e:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Server Start Failed",
                        f"Failed to start TCP server:\n{str(e)}"
                    )
                    return False
            else:
                # User chose not to start server
                return False

        except Exception as e:
            print(f"Error checking TCP server: {e}")
            return True  # Proceed anyway on error

    def _update_tcp_status(self):
        """Update TCP server status indicator."""
        # Try to get TCP server from ShowsTab via parent (MainWindow)
        tcp_server = None
        try:
            # Navigate up to MainWindow via Qt parent hierarchy
            main_window = self.window()
            if main_window:
                shows_tab = getattr(main_window, 'shows_tab', None)
                if shows_tab:
                    tcp_server = getattr(shows_tab, 'tcp_server', None)
        except Exception:
            pass

        if tcp_server is None:
            self.tcp_status_label.setText("Not initialized")
            self.tcp_status_label.setStyleSheet("color: #666; font-weight: bold;")
        elif not tcp_server.is_running():
            self.tcp_status_label.setText("Stopped")
            self.tcp_status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        else:
            client_count = tcp_server.get_client_count()
            if client_count == 0:
                self.tcp_status_label.setText("Running (no clients)")
                self.tcp_status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
            else:
                self.tcp_status_label.setText(f"Connected ({client_count})")
                self.tcp_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")

    def on_tab_activated(self):
        """Called when stage tab becomes visible."""
        self._tab_active = True
        # Send current state to visualizer when tab becomes active
        self._notify_tcp_update()

    def on_tab_deactivated(self):
        """Called when switching away from stage tab."""
        self._tab_active = False
        # Stop any pending updates
        self._tcp_update_timer.stop()
        self._tcp_update_pending = False

    def _notify_tcp_update(self):
        """Notify TCP server about configuration changes (throttled for live updates)."""
        # Only send updates when tab is active (reduces lag when working on other tabs)
        if not self._tab_active:
            return

        # Use throttle timer to avoid flooding during drag operations
        self._tcp_update_pending = True
        if not self._tcp_update_timer.isActive():
            self._tcp_update_timer.start()

    def _do_tcp_update(self):
        """Actually send the TCP update (called by throttle timer)."""
        if not self._tcp_update_pending:
            return
        self._tcp_update_pending = False

        try:
            # Get shows_tab which hosts the TCP server
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'shows_tab'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'shows_tab'):
                shows_tab = main_window.shows_tab
                tcp_server = getattr(shows_tab, 'tcp_server', None)

                if tcp_server and tcp_server.is_running() and self.config:
                    # Update the server's config and push to clients
                    tcp_server.update_config(self.config)
        except Exception as e:
            print(f"Error notifying TCP server: {e}")

    def _on_show_axes_changed(self, state):
        """Handle show orientation axes checkbox change."""
        show_axes = bool(state)
        FixtureItem.show_orientation_axes = show_axes

        # Enable/disable "show all" checkbox based on main checkbox
        self.show_all_axes_checkbox.setEnabled(show_axes)
        if not show_axes:
            self.show_all_axes_checkbox.setChecked(False)

        # Trigger redraw of all fixtures
        self.stage_view.viewport().update()

    def _on_show_all_axes_changed(self, state):
        """Handle show all axes checkbox change."""
        FixtureItem.show_all_axes = bool(state)

        # Trigger redraw of all fixtures
        self.stage_view.viewport().update()

    def _on_set_orientation_requested(self, fixture_items: list):
        """Handle request to set orientation for selected fixtures."""
        if not fixture_items:
            return

        # Store fixture items for deferred dialog opening
        self._pending_orientation_fixtures = fixture_items

        # Defer dialog opening to next event loop iteration to avoid context menu issues
        QTimer.singleShot(0, self._open_orientation_dialog)

    def _open_orientation_dialog(self):
        """Open the orientation dialog (deferred from context menu)."""
        fixture_items = getattr(self, '_pending_orientation_fixtures', None)
        if not fixture_items:
            return

        self._pending_orientation_fixtures = None

        # Open orientation dialog
        dialog = OrientationDialog(fixture_items, self.config, self)

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            # Get values from dialog
            values = dialog.get_orientation_values()

            # Apply to all selected fixture items
            for fixture_item in fixture_items:
                fixture_item.mounting = values['mounting']
                fixture_item.rotation_angle = values['yaw']  # yaw maps to rotation_angle
                fixture_item.pitch = values['pitch']
                fixture_item.roll = values['roll']
                fixture_item.z_height = values['z_height']
                fixture_item.orientation_uses_group_default = False  # User set custom value
                fixture_item.update()

                # Update the config fixture
                if self.config:
                    config_fixture = next(
                        (f for f in self.config.fixtures if f.name == fixture_item.fixture_name),
                        None
                    )
                    if config_fixture:
                        config_fixture.mounting = values['mounting']
                        config_fixture.yaw = values['yaw']
                        config_fixture.pitch = values['pitch']
                        config_fixture.roll = values['roll']
                        config_fixture.z = values['z_height']
                        config_fixture.orientation_uses_group_default = False

            # Apply to group default if checkbox was checked
            if values['apply_to_group'] and self.config:
                groups = set(f.group for f in fixture_items if hasattr(f, 'group') and f.group)
                for group_name in groups:
                    if group_name in self.config.groups:
                        group = self.config.groups[group_name]
                        group.default_mounting = values['mounting']
                        group.default_yaw = values['yaw']
                        group.default_pitch = values['pitch']
                        group.default_roll = values['roll']
                        group.default_z_height = values['z_height']

            # Save changes and notify
            self.stage_view.save_positions_to_config()
            self._notify_tcp_update()
