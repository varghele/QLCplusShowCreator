# visualizer/main.py
# QLC+ Show Creator - 3D Visualizer Entry Point
#
# Real-time 3D visualization of lighting effects.
# - Receives configuration via TCP from Show Creator
# - Receives DMX data via ArtNet from Show Creator or QLC+

import sys
import os

# Add parent directory to path for shared module imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStatusBar, QToolBar, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

# Import shared modules from Show Creator
from config.models import Configuration, Fixture, FixtureGroup
from utils.fixture_utils import determine_fixture_type

# Import visualizer modules
from visualizer.tcp import VisualizerTCPClient


class VisualizerWindow(QMainWindow):
    """
    Main window for the QLC+ Show Creator Visualizer.

    Provides 3D visualization of lighting effects by:
    - Receiving stage/fixture configuration via TCP
    - Receiving DMX data via ArtNet
    - Rendering fixtures and volumetric beams
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("QLC+ Visualizer")
        self.setMinimumSize(1024, 768)

        # Configuration state (received via TCP)
        self.stage_width: float = 10.0  # meters
        self.stage_height: float = 8.0  # meters
        self.fixtures: list = []
        self.groups: dict = {}

        # Connection state
        self.tcp_connected: bool = False
        self.artnet_receiving: bool = False

        # TCP client for receiving configuration
        self.tcp_client = VisualizerTCPClient()
        self._connect_tcp_signals()

        # Initialize UI (toolbar must be before statusbar due to connect_action reference)
        self._init_ui()
        self._init_toolbar()
        self._init_statusbar()

        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # Update every second

    def _connect_tcp_signals(self):
        """Connect TCP client signals to UI handlers."""
        self.tcp_client.connected.connect(self._on_tcp_connected)
        self.tcp_client.disconnected.connect(self._on_tcp_disconnected)
        self.tcp_client.connection_error.connect(self._on_tcp_error)
        self.tcp_client.stage_received.connect(self.set_stage_dimensions)
        self.tcp_client.fixtures_received.connect(self.set_fixtures)
        self.tcp_client.groups_received.connect(self.set_groups)
        self.tcp_client.update_received.connect(self._on_config_update)

    def _on_tcp_connected(self):
        """Handle TCP connected event."""
        self._update_tcp_indicator(True)
        print("TCP connected to Show Creator")

    def _on_tcp_disconnected(self):
        """Handle TCP disconnected event."""
        self._update_tcp_indicator(False)
        print("TCP disconnected from Show Creator")

    def _on_tcp_error(self, error_msg: str):
        """Handle TCP connection error."""
        self._update_tcp_indicator(False)
        self.statusbar.showMessage(f"Connection error: {error_msg}", 5000)

    def _on_config_update(self, update_type: str, data: dict):
        """Handle configuration update from Show Creator."""
        print(f"Config update received: {update_type}")
        # Re-request full config on update
        # (The server will send new stage/fixtures/groups messages)

    def _init_ui(self):
        """Initialize the main UI layout."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Placeholder for 3D viewport (Phase V4)
        self.viewport_frame = QFrame()
        self.viewport_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.viewport_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border: 1px solid #333;
            }
        """)

        # Viewport placeholder label
        viewport_layout = QVBoxLayout(self.viewport_frame)
        self.viewport_label = QLabel("3D Viewport\n\nPhase V4: ModernGL rendering will be added here")
        self.viewport_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewport_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 18px;
                font-style: italic;
            }
        """)
        viewport_layout.addWidget(self.viewport_label)

        layout.addWidget(self.viewport_frame)

    def _init_statusbar(self):
        """Initialize the status bar with connection indicators."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # TCP connection status
        self.tcp_status_label = QLabel()
        self._update_tcp_indicator(False)
        self.statusbar.addWidget(self.tcp_status_label)

        # Separator
        separator1 = QLabel(" | ")
        separator1.setStyleSheet("color: #666;")
        self.statusbar.addWidget(separator1)

        # ArtNet status
        self.artnet_status_label = QLabel()
        self._update_artnet_indicator(False)
        self.statusbar.addWidget(artnet_label := QLabel("ArtNet: "))
        self.statusbar.addWidget(self.artnet_status_label)

        # Separator
        separator2 = QLabel(" | ")
        separator2.setStyleSheet("color: #666;")
        self.statusbar.addWidget(separator2)

        # Stage info
        self.stage_info_label = QLabel()
        self._update_stage_info()
        self.statusbar.addWidget(self.stage_info_label)

        # Fixture count (right side)
        self.fixture_count_label = QLabel("Fixtures: 0")
        self.statusbar.addPermanentWidget(self.fixture_count_label)

    def _init_toolbar(self):
        """Initialize the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Connect button
        self.connect_action = QAction("Connect", self)
        self.connect_action.setToolTip("Connect to Show Creator (TCP port 9000)")
        self.connect_action.triggered.connect(self._on_connect_clicked)
        toolbar.addAction(self.connect_action)

        toolbar.addSeparator()

        # Reset view button
        self.reset_view_action = QAction("Reset View", self)
        self.reset_view_action.setToolTip("Reset camera to default position")
        self.reset_view_action.triggered.connect(self._on_reset_view)
        toolbar.addAction(self.reset_view_action)

    def _update_tcp_indicator(self, connected: bool):
        """Update TCP connection indicator."""
        self.tcp_connected = connected
        if connected:
            self.tcp_status_label.setText("TCP: Connected")
            self.tcp_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.connect_action.setText("Disconnect")
        else:
            self.tcp_status_label.setText("TCP: Disconnected")
            self.tcp_status_label.setStyleSheet("color: #f44336;")
            self.connect_action.setText("Connect")

    def _update_artnet_indicator(self, receiving: bool):
        """Update ArtNet receiving indicator."""
        self.artnet_receiving = receiving
        if receiving:
            self.artnet_status_label.setText("Receiving")
            self.artnet_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.artnet_status_label.setText("No Data")
            self.artnet_status_label.setStyleSheet("color: #666;")

    def _update_stage_info(self):
        """Update stage dimensions display."""
        self.stage_info_label.setText(f"Stage: {self.stage_width:.1f}m x {self.stage_height:.1f}m")

    def _update_fixture_count(self):
        """Update fixture count display."""
        self.fixture_count_label.setText(f"Fixtures: {len(self.fixtures)}")

    def _update_status(self):
        """Periodic status update (called by timer)."""
        # This will be expanded in Phase V2/V3 to check actual connection states
        pass

    def _on_connect_clicked(self):
        """Handle connect/disconnect button click."""
        if self.tcp_connected:
            print("Disconnecting from Show Creator...")
            self.tcp_client.disconnect()
        else:
            print(f"Connecting to Show Creator at {self.tcp_client.host}:{self.tcp_client.port}...")
            self.tcp_client.connect()

    def _on_reset_view(self):
        """Reset camera to default position."""
        # TODO: Phase V4 - Reset 3D camera
        print("Reset view (3D camera will be added in Phase V4)")

    # --- Configuration Handling (will be called by TCP client in Phase V2) ---

    def set_stage_dimensions(self, width: float, height: float):
        """
        Set stage dimensions from TCP message.

        Args:
            width: Stage width in meters
            height: Stage height in meters
        """
        self.stage_width = width
        self.stage_height = height
        self._update_stage_info()
        print(f"Stage dimensions updated: {width}m x {height}m")

    def set_fixtures(self, fixtures_data: list):
        """
        Set fixtures from TCP message.

        Args:
            fixtures_data: List of fixture dictionaries from protocol
        """
        self.fixtures = fixtures_data
        self._update_fixture_count()
        print(f"Loaded {len(fixtures_data)} fixtures")

    def set_groups(self, groups_data: list):
        """
        Set groups from TCP message.

        Args:
            groups_data: List of group dictionaries from protocol
        """
        self.groups = {g['name']: g for g in groups_data}
        print(f"Loaded {len(groups_data)} groups")

    # --- DMX Handling (will be called by ArtNet listener in Phase V3) ---

    def update_dmx(self, universe: int, channels: bytes):
        """
        Update DMX values from ArtNet packet.

        Args:
            universe: DMX universe number
            channels: 512 bytes of DMX channel data
        """
        # TODO: Phase V3 - Update fixture colors/positions from DMX
        self._update_artnet_indicator(True)

    def closeEvent(self, event):
        """Clean up on window close."""
        print("Closing Visualizer...")
        self.status_timer.stop()

        # Disconnect TCP client
        if self.tcp_client:
            self.tcp_client.disconnect()

        # TODO: Phase V3 - Stop ArtNet listener
        event.accept()


def main():
    """Entry point for the Visualizer application."""
    try:
        # Verify shared module imports work
        print("QLC+ Visualizer starting...")
        print(f"  - Shared modules imported successfully")
        print(f"  - Configuration model: {Configuration.__name__}")
        print(f"  - Fixture model: {Fixture.__name__}")
        print(f"  - fixture_utils: determine_fixture_type available")

        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("QLC+ Visualizer")

        # Create and show main window
        window = VisualizerWindow()
        window.show()

        print("Visualizer window opened")
        print("  - TCP client ready (click Connect to link with Show Creator)")
        print("  - ArtNet listener will be added in Phase V3")
        print("  - 3D rendering will be added in Phase V4-V6")

        sys.exit(app.exec())

    except Exception as e:
        print(f"Error starting Visualizer: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
