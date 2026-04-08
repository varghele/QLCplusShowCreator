"""
Live Mode Window — main UI for real-time audio-reactive lighting.

Separate window launched from the main app menu. Captures live audio,
auto-generates riffs matching the sound, and sends DMX to configured
ArtNet target.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
    QLineEdit, QComboBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from config.models import Configuration
from audio.device_manager import DeviceManager
from audio.live_input import LiveAudioInput
from audio.realtime_spectral import RealtimeSpectralAnalyzer, LiveFeatureFrame
from audio.live_feature_bridge import LiveFeatureBridge
from live.engine import LiveShowEngine
from live.dmx_output import LiveDMXController
from live.bpm_detector import TapBPM, AutoBPMDetector
from live.widgets.color_wheel import HSVColorWheel
from live.widgets.group_submasters import GroupSubmasterPanel
from live.widgets.energy_fader import EnergySensitivityFader
from live.widgets.riff_palette import GroupRiffConstraintPanel
from live.widgets.metrics_tracker import LiveMetricsTracker
from autogen.spatial import ensure_default_spots, compute_stage_planes
from config.models import StagePlane


class LiveModeWindow(QMainWindow):
    """Main Live Mode window."""

    def __init__(self, config: Configuration, fixture_definitions: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.fixture_definitions = fixture_definitions

        self.setWindowTitle("Live Mode")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        # Components (created on start)
        self._device_manager = DeviceManager()
        self._live_input = None
        self._analyzer = None
        self._bridge = None
        self._engine = None
        self._dmx_controller = None
        self._tap_bpm = TapBPM()
        self._auto_bpm = AutoBPMDetector()
        self._is_running = False

        # UI update timer
        self._ui_timer = QTimer()
        self._ui_timer.setInterval(50)  # 20Hz UI updates
        self._ui_timer.timeout.connect(self._update_ui)

        # Latest feature frame for meters
        self._latest_frame: LiveFeatureFrame = None

        self._setup_ui()
        self._populate_devices()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ── Left Panel: Audio Meters + Energy ──
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        meters_label = QLabel("Audio Meters")
        meters_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(meters_label)

        self._meter_bars = {}
        for metric in ['flux', 'rms', 'transient', 'richness', 'vocal', 'centroid', 'contrast']:
            row = QHBoxLayout()
            lbl = QLabel(metric[:6])
            lbl.setFixedWidth(50)
            lbl.setStyleSheet("font-size: 10px;")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFixedHeight(16)
            bar.setTextVisible(False)
            row.addWidget(lbl)
            row.addWidget(bar)
            left_layout.addLayout(row)
            self._meter_bars[metric] = bar

        left_layout.addSpacing(10)

        # Energy fader
        self._energy_fader = EnergySensitivityFader()
        left_layout.addWidget(self._energy_fader)

        # BPM display
        left_layout.addSpacing(10)
        bpm_label = QLabel("BPM")
        bpm_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(bpm_label)
        self._bpm_display = QLabel("120")
        self._bpm_display.setFont(QFont("Monospace", 24, QFont.Weight.Bold))
        self._bpm_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self._bpm_display)

        left_layout.addStretch()
        left_panel.setFixedWidth(170)
        splitter.addWidget(left_panel)

        # ── Center Panel: Controls ──
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(4, 4, 4, 4)

        # Status bar
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #1a1a2e; border-radius: 4px; padding: 8px;")
        status_layout = QHBoxLayout(status_frame)
        self._status_riff = QLabel("Riff: ---")
        self._status_riff.setStyleSheet("color: #e0e0e0; font-size: 14px; font-weight: bold;")
        self._status_bar_counter = QLabel("Bar: -/-")
        self._status_bar_counter.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        self._status_phase = QLabel("STOPPED")
        self._status_phase.setStyleSheet("color: #ff6b6b; font-size: 12px; font-weight: bold;")
        status_layout.addWidget(self._status_riff)
        status_layout.addStretch()
        status_layout.addWidget(self._status_bar_counter)
        status_layout.addWidget(self._status_phase)
        center_layout.addWidget(status_frame)

        # BPM controls
        bpm_group = QGroupBox("BPM Control")
        bpm_layout = QHBoxLayout(bpm_group)

        self._tap_btn = QPushButton("TAP")
        self._tap_btn.setFixedSize(60, 40)
        self._tap_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self._tap_btn.clicked.connect(self._on_tap_bpm)
        bpm_layout.addWidget(self._tap_btn)

        self._auto_bpm_checkbox = QCheckBox("Auto")
        self._auto_bpm_checkbox.toggled.connect(self._on_auto_bpm_toggled)
        bpm_layout.addWidget(self._auto_bpm_checkbox)

        self._bpm_spinbox = QSpinBox()
        self._bpm_spinbox.setRange(30, 300)
        self._bpm_spinbox.setValue(120)
        self._bpm_spinbox.setSuffix(" BPM")
        self._bpm_spinbox.valueChanged.connect(self._on_bpm_spinbox_changed)
        bpm_layout.addWidget(self._bpm_spinbox)

        bpm_layout.addSpacing(20)

        groove_label = QLabel("Groove bars:")
        bpm_layout.addWidget(groove_label)
        self._groove_bars_spinbox = QSpinBox()
        self._groove_bars_spinbox.setRange(1, 16)
        self._groove_bars_spinbox.setValue(3)
        self._groove_bars_spinbox.valueChanged.connect(self._on_groove_bars_changed)
        bpm_layout.addWidget(self._groove_bars_spinbox)

        bpm_layout.addStretch()
        center_layout.addWidget(bpm_group)

        # Per-group riff constraints
        group_names = list(self.config.groups.keys())
        self._riff_constraints = GroupRiffConstraintPanel(group_names)
        self._riff_constraints.constraints_changed.connect(self._on_constraints_changed)
        center_layout.addWidget(self._riff_constraints)

        # Groove Now / Fill Now buttons
        groove_fill_row = QHBoxLayout()
        self._groove_btn = QPushButton("GROOVE NOW")
        self._groove_btn.setFixedHeight(50)
        self._groove_btn.setStyleSheet(
            "font-size: 16px; font-weight: bold; "
            "background-color: #27ae60; color: white; border-radius: 6px;"
        )
        self._groove_btn.clicked.connect(self._on_groove_now)
        groove_fill_row.addWidget(self._groove_btn)

        self._fill_btn = QPushButton("FILL NOW")
        self._fill_btn.setFixedHeight(50)
        self._fill_btn.setStyleSheet(
            "font-size: 16px; font-weight: bold; "
            "background-color: #e74c3c; color: white; border-radius: 6px;"
        )
        self._fill_btn.clicked.connect(self._on_fill_now)
        groove_fill_row.addWidget(self._fill_btn)
        center_layout.addLayout(groove_fill_row)

        # Movement speed limiter
        speed_row = QHBoxLayout()
        speed_label = QLabel("Max Speed:")
        speed_label.setStyleSheet("font-size: 10px;")
        speed_label.setFixedWidth(65)
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(0, 360)
        self._speed_slider.setValue(0)
        self._speed_slider.setFixedHeight(20)
        self._speed_value_label = QLabel("OFF")
        self._speed_value_label.setFixedWidth(40)
        self._speed_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._speed_value_label.setStyleSheet("font-size: 10px;")
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_row.addWidget(speed_label)
        speed_row.addWidget(self._speed_slider)
        speed_row.addWidget(self._speed_value_label)
        center_layout.addLayout(speed_row)

        # Color wheel
        center_layout.addSpacing(8)
        self._color_wheel = HSVColorWheel()
        self._color_wheel.color_changed.connect(self._on_color_changed)
        center_layout.addWidget(self._color_wheel)

        # Metrics tracker (30-second scrolling chart)
        self._metrics_tracker = LiveMetricsTracker()
        center_layout.addWidget(self._metrics_tracker)

        center_layout.addStretch()
        splitter.addWidget(center_panel)

        # ── Right Panel: Output + Submasters ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)

        # ArtNet config
        artnet_group = QGroupBox("ArtNet Output")
        artnet_layout = QVBoxLayout(artnet_group)

        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("Target IP:"))
        self._ip_input = QLineEdit("192.168.1.151")
        self._ip_input.setPlaceholderText("192.168.1.151")
        ip_row.addWidget(self._ip_input)
        artnet_layout.addLayout(ip_row)

        artnet_layout.addWidget(QLabel("Universe Mapping:"))
        self._universe_table = QTableWidget(0, 2)
        self._universe_table.setHorizontalHeaderLabels(["Config Univ", "ArtNet Univ"])
        self._universe_table.setFixedHeight(80)
        self._populate_universe_table()
        artnet_layout.addWidget(self._universe_table)

        right_layout.addWidget(artnet_group)

        # Input device
        input_group = QGroupBox("Audio Input")
        input_layout = QVBoxLayout(input_group)
        self._input_device_combo = QComboBox()
        input_layout.addWidget(self._input_device_combo)
        right_layout.addWidget(input_group)

        # Target plane selector
        plane_group = QGroupBox("Movement Target")
        plane_layout = QVBoxLayout(plane_group)
        self._plane_combo = QComboBox()
        self._stage_planes: dict = {}  # name -> StagePlane
        self._populate_plane_combo()
        self._plane_combo.currentTextChanged.connect(self._on_target_plane_changed)
        plane_layout.addWidget(self._plane_combo)
        right_layout.addWidget(plane_group)

        # Group submasters
        group_names = list(self.config.groups.keys())
        self._submasters = GroupSubmasterPanel(group_names)
        self._submasters.submaster_changed.connect(self._on_submaster_changed)
        right_layout.addWidget(self._submasters)

        right_layout.addStretch()

        # Start / Stop buttons
        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("START")
        self._start_btn.setFixedHeight(40)
        self._start_btn.setStyleSheet(
            "font-size: 14px; font-weight: bold; "
            "background-color: #27ae60; color: white; border-radius: 4px;"
        )
        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn = QPushButton("STOP")
        self._stop_btn.setFixedHeight(40)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "font-size: 14px; font-weight: bold; "
            "background-color: #555; color: white; border-radius: 4px;"
        )
        self._stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._stop_btn)
        right_layout.addLayout(btn_row)

        right_panel.setFixedWidth(220)
        splitter.addWidget(right_panel)

    def _populate_devices(self):
        """Populate input device combo."""
        devices = self._device_manager.enumerate_input_devices()
        self._input_device_combo.clear()
        for device in devices:
            self._input_device_combo.addItem(
                f"{device.name} ({device.host_api})", device.index
            )
        # Select default
        default = self._device_manager.get_default_input_device()
        if default:
            for i in range(self._input_device_combo.count()):
                if self._input_device_combo.itemData(i) == default.index:
                    self._input_device_combo.setCurrentIndex(i)
                    break

    def _populate_plane_combo(self):
        """Populate target plane combo from stage cuboid faces."""
        planes = compute_stage_planes(self.config)
        self._stage_planes = {p.name: p for p in planes}

        self._plane_combo.clear()
        self._plane_combo.addItem("None (manual)")
        for plane in planes:
            self._plane_combo.addItem(plane.name)

        # Default to Front (audience-facing)
        front_idx = self._plane_combo.findText("Front")
        if front_idx >= 0:
            self._plane_combo.setCurrentIndex(front_idx)

    def _populate_universe_table(self):
        """Fill universe mapping table from config."""
        universes = list(self.config.universes.keys())
        self._universe_table.setRowCount(len(universes))
        for row, uid in enumerate(universes):
            uid_int = int(uid)
            config_item = QTableWidgetItem(str(uid_int))
            config_item.setFlags(config_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            artnet_item = QTableWidgetItem(str(uid_int - 1))  # 1-based → 0-based default
            self._universe_table.setItem(row, 0, config_item)
            self._universe_table.setItem(row, 1, artnet_item)

    def _get_universe_mapping(self) -> dict:
        """Read universe mapping from table."""
        mapping = {}
        for row in range(self._universe_table.rowCount()):
            config_item = self._universe_table.item(row, 0)
            artnet_item = self._universe_table.item(row, 1)
            if config_item and artnet_item:
                try:
                    mapping[int(config_item.text())] = int(artnet_item.text())
                except ValueError:
                    pass
        return mapping

    # ── Start / Stop ──

    def _on_start(self):
        if self._is_running:
            return

        try:
            # Get input device
            device_index = self._input_device_combo.currentData()

            # Create audio input
            self._live_input = LiveAudioInput(sample_rate=44100, channels=1, buffer_size=512)
            if not self._live_input.initialize(device_index=device_index):
                print("Failed to initialize audio input")
                return

            # Create analyzer + bridge
            self._analyzer = RealtimeSpectralAnalyzer(sample_rate=44100)
            self._bridge = LiveFeatureBridge(self._analyzer)
            self._bridge.feature_updated.connect(self._on_feature_frame)

            # Create engine
            self._engine = LiveShowEngine(self.config, self.fixture_definitions)
            self._engine.set_bpm(self._bpm_spinbox.value())
            self._engine.set_groove_bars(self._groove_bars_spinbox.value())
            self._engine.set_energy_sensitivity(self._energy_fader.value())
            self._engine.set_on_riffs_updated(self._on_riffs_updated_from_engine)
            # Set initial target plane from combo
            plane_text = self._plane_combo.currentText()
            plane = self._stage_planes.get(plane_text) if plane_text != "None (manual)" else None
            self._engine.set_target_plane(plane)

            # Create DMX controller
            target_ip = self._ip_input.text().strip() or "192.168.1.151"
            self._dmx_controller = LiveDMXController(
                self.config, self.fixture_definitions, target_ip=target_ip,
            )
            self._dmx_controller.set_universe_mapping(self._get_universe_mapping())
            self._dmx_controller.set_engine(self._engine)
            # Pass stage planes to DMX manager for world-space movement
            self._dmx_controller.dmx_manager.set_stage_planes(self._stage_planes)

            # Start everything
            self._live_input.start()
            self._bridge.start(self._live_input.ring_buffer)
            self._dmx_controller.start()

            self._is_running = True
            self._ui_timer.start()

            # Update button states
            self._start_btn.setEnabled(False)
            self._start_btn.setStyleSheet(
                "font-size: 14px; font-weight: bold; "
                "background-color: #555; color: white; border-radius: 4px;"
            )
            self._stop_btn.setEnabled(True)
            self._stop_btn.setStyleSheet(
                "font-size: 14px; font-weight: bold; "
                "background-color: #e74c3c; color: white; border-radius: 4px;"
            )
            self._status_phase.setText("RUNNING")
            self._status_phase.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold;")

            print("Live Mode started")

        except Exception as e:
            print(f"Failed to start Live Mode: {e}")
            import traceback
            traceback.print_exc()
            self._cleanup()

    def _on_stop(self):
        if not self._is_running:
            return

        self._cleanup()

        self._start_btn.setEnabled(True)
        self._start_btn.setStyleSheet(
            "font-size: 14px; font-weight: bold; "
            "background-color: #27ae60; color: white; border-radius: 4px;"
        )
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "font-size: 14px; font-weight: bold; "
            "background-color: #555; color: white; border-radius: 4px;"
        )
        self._status_phase.setText("STOPPED")
        self._status_phase.setStyleSheet("color: #ff6b6b; font-size: 12px; font-weight: bold;")
        self._status_riff.setText("Riff: ---")
        self._status_bar_counter.setText("Bar: -/-")

        print("Live Mode stopped")

    def _cleanup(self):
        """Stop and release all resources."""
        self._is_running = False
        self._ui_timer.stop()

        if self._dmx_controller:
            self._dmx_controller.stop()
            self._dmx_controller = None

        if self._bridge:
            self._bridge.stop()
            self._bridge = None

        if self._analyzer:
            self._analyzer.stop()
            self._analyzer = None

        if self._live_input:
            self._live_input.cleanup()
            self._live_input = None

        self._engine = None

    # ── Event handlers ──

    def _on_feature_frame(self, frame: LiveFeatureFrame):
        """Receive feature frame from analyzer (via Qt signal, on main thread)."""
        self._latest_frame = frame

        # Feed to engine
        if self._engine:
            self._engine.on_feature_frame(frame)

        # Feed to auto BPM detector
        if self._auto_bpm_checkbox.isChecked():
            self._auto_bpm.on_feature(frame)

    def _on_tap_bpm(self):
        bpm = self._tap_bpm.tap()
        if bpm is not None:
            self._bpm_spinbox.blockSignals(True)
            self._bpm_spinbox.setValue(int(round(bpm)))
            self._bpm_spinbox.blockSignals(False)
            if self._engine:
                self._engine.set_bpm(bpm)

    def _on_auto_bpm_toggled(self, checked):
        if checked:
            self._auto_bpm.reset()

    def _on_bpm_spinbox_changed(self, value):
        if self._engine:
            self._engine.set_bpm(float(value))

    def _on_groove_bars_changed(self, value):
        if self._engine:
            self._engine.set_groove_bars(value)

    def _on_groove_now(self):
        if self._engine:
            self._engine.force_groove()

    def _on_fill_now(self):
        if self._engine:
            self._engine.force_fill()

    def _on_color_changed(self, r, g, b):
        if self._engine:
            if r < 0:  # Auto mode signal
                self._engine.set_color_override(None)
            else:
                self._engine.set_color_override((r, g, b))

    def _on_speed_changed(self, value):
        if value == 0:
            self._speed_value_label.setText("OFF")
        else:
            self._speed_value_label.setText(f"{value}°/s")
        if self._engine:
            self._engine.set_max_movement_speed(float(value))

    def _on_target_plane_changed(self, text):
        if self._engine:
            plane = self._stage_planes.get(text) if text != "None (manual)" else None
            self._engine.set_target_plane(plane)

    def _on_submaster_changed(self, group_name, value):
        if self._engine:
            self._engine.set_group_submaster(group_name, value)

    def _on_constraints_changed(self, group_name, allowed):
        if self._engine:
            self._engine.set_group_constraints(group_name, allowed)

    def _on_riffs_updated_from_engine(self, per_group_rudiments):
        """Called from engine (potentially from DMX thread) — schedule UI update."""
        # This is safe because we schedule it for the next UI tick
        self._pending_riff_update = per_group_rudiments

    # ── UI update ──

    def _update_ui(self):
        """Called at 20Hz to update meters, status, and auto BPM."""
        # Update meters
        frame = self._latest_frame
        if frame:
            self._meter_bars['flux'].setValue(int(frame.flux * 100))
            self._meter_bars['rms'].setValue(int(frame.rms * 100))
            self._meter_bars['transient'].setValue(int(frame.transient * 100))
            self._meter_bars['richness'].setValue(int(frame.richness * 100))
            self._meter_bars['vocal'].setValue(int(frame.vocal * 100))
            self._meter_bars['centroid'].setValue(int(frame.centroid * 100))
            self._metrics_tracker.append_frame(frame)
            self._meter_bars['contrast'].setValue(int(frame.contrast * 100))

        # Update status
        if self._engine and self._is_running:
            self._status_riff.setText(f"Riff: {self._engine.current_groove_name}")
            total = self._engine.groove_bars + 1
            bar = self._engine.current_bar + 1
            self._status_bar_counter.setText(f"Bar: {bar}/{total}")
            self._status_phase.setText("FILL" if self._engine.is_fill else "GROOVE")
            phase_color = "#ff9800" if self._engine.is_fill else "#4CAF50"
            self._status_phase.setStyleSheet(
                f"color: {phase_color}; font-size: 12px; font-weight: bold;"
            )
            self._bpm_display.setText(str(int(self._engine.bpm)))

        # Update riff constraint panel (active riff display only)
        if hasattr(self, '_pending_riff_update') and self._pending_riff_update:
            active = {g: r[0] for g, r in self._pending_riff_update.items()}
            self._riff_constraints.update_active_riffs(active)
            self._pending_riff_update = None

        # Auto BPM
        if self._auto_bpm_checkbox.isChecked() and self._is_running:
            auto_bpm = self._auto_bpm.get_bpm()
            if auto_bpm is not None:
                self._bpm_spinbox.blockSignals(True)
                self._bpm_spinbox.setValue(int(round(auto_bpm)))
                self._bpm_spinbox.blockSignals(False)
                if self._engine:
                    self._engine.set_bpm(auto_bpm)

    def closeEvent(self, event):
        """Ensure cleanup on window close."""
        self._cleanup()
        self._device_manager.cleanup()
        super().closeEvent(event)
