"""
LiveTab — real-time audio-reactive lighting embedded as the sixth tab.

Ported from ``live/window.py::LiveModeWindow`` per UI_MODERNIZATION_PLAN
step 9. The standalone ``QMainWindow`` shell is gone; the tab itself owns
the engine lifecycle. Two behavioural deltas vs. the old window:

- **Lazy fixture-definition load.** ``on_tab_activated`` parses the QXF
  files on the first activation rather than blocking app startup.
- **UI timer pauses when the tab isn't visible.** ``on_tab_deactivated``
  stops the 20 Hz UI tick to save cycles. The engine itself keeps
  running — Live Mode is performance-oriented and shouldn't auto-stop
  when the user peeks at another tab.

Cleanup runs from ``MainWindow.closeEvent`` via :meth:`cleanup`, which
replaces the old window's ``closeEvent``.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QSpinBox, QCheckBox, QSlider,
    QLineEdit, QComboBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QFrame,
)
from PyQt6.QtCore import Qt, QTimer
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
from live import settings as live_settings
from autogen.spatial import compute_stage_planes

from .base_tab import BaseTab


class LiveTab(BaseTab):
    """Real-time audio-reactive lighting embedded as a tab."""

    def __init__(self, config: Configuration, parent=None):
        # All the non-UI state must be set before super().__init__ — that
        # call invokes setup_ui() which references several of these.
        self.fixture_definitions: dict = {}
        self._fixtures_loaded = False

        self._settings = live_settings.load()

        self._device_manager = DeviceManager()
        self._live_input = None
        self._analyzer = None
        self._bridge = None
        self._engine = None
        self._dmx_controller = None
        self._tap_bpm = TapBPM()
        self._auto_bpm = AutoBPMDetector()
        self._is_running = False

        # 20 Hz UI tick — paused when the tab isn't visible (see
        # on_tab_deactivated) so it doesn't burn cycles in the background.
        self._ui_timer = QTimer()
        self._ui_timer.setInterval(50)
        self._ui_timer.timeout.connect(self._update_ui)

        # Latest feature frame for meters; replaced on each analyzer tick.
        self._latest_frame: LiveFeatureFrame = None

        # Cached riffs payload — set from the engine callback (which may
        # arrive on a worker thread); applied on the next UI tick.
        self._pending_riff_update = None

        super().__init__(config, parent)

        # Device list depends on the audio host being initialised; build
        # it after the UI exists so the combo is ready to receive items.
        self._populate_devices()

    # ── BaseTab overrides ─────────────────────────────────────────────

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ── Left panel: meters + energy + BPM display ──────────────
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        meters_label = QLabel("Audio Meters")
        meters_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(meters_label)

        self._meter_bars = {}
        for metric in ['flux', 'rms', 'transient', 'richness',
                       'vocal', 'centroid', 'contrast']:
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

        self._energy_fader = EnergySensitivityFader()
        self._energy_fader.set_value(self._settings.energy_sensitivity / 100.0)
        self._energy_fader.sensitivity_changed.connect(self._on_energy_sensitivity_changed)
        left_layout.addWidget(self._energy_fader)

        left_layout.addSpacing(10)
        bpm_label = QLabel("BPM")
        bpm_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(bpm_label)
        self._bpm_display = QLabel("120")
        self._bpm_display.setObjectName("LiveBpmDisplay")
        self._bpm_display.setFont(QFont("Monospace", 24, QFont.Weight.Bold))
        self._bpm_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self._bpm_display)

        left_layout.addStretch()
        left_panel.setFixedWidth(170)
        splitter.addWidget(left_panel)

        # ── Center panel: status + BPM + groove/fill + color wheel ──
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(4, 4, 4, 4)

        # Status frame — dark bar with three labels, theme-styled via QSS.
        status_frame = QFrame()
        status_frame.setObjectName("LiveStatusFrame")
        status_layout = QHBoxLayout(status_frame)
        self._status_riff = QLabel("Riff: ---")
        self._status_riff.setObjectName("LiveStatusRiff")
        self._status_bar_counter = QLabel("Bar: -/-")
        self._status_bar_counter.setObjectName("LiveStatusBarCounter")
        self._status_phase = QLabel("STOPPED")
        self._status_phase.setObjectName("LiveStatusPhase")
        # `phase` is a dynamic property the QSS reads — we re-polish on
        # change so the colour follows engine state without inline CSS.
        self._status_phase.setProperty("phase", "stopped")
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
        self._bpm_spinbox.setValue(self._settings.bpm)
        self._bpm_spinbox.setSuffix(" BPM")
        self._bpm_spinbox.valueChanged.connect(self._on_bpm_spinbox_changed)
        bpm_layout.addWidget(self._bpm_spinbox)

        bpm_layout.addSpacing(20)

        bpm_layout.addWidget(QLabel("Groove bars:"))
        self._groove_bars_spinbox = QSpinBox()
        self._groove_bars_spinbox.setRange(1, 16)
        self._groove_bars_spinbox.setValue(self._settings.groove_bars)
        self._groove_bars_spinbox.valueChanged.connect(self._on_groove_bars_changed)
        bpm_layout.addWidget(self._groove_bars_spinbox)

        bpm_layout.addStretch()
        center_layout.addWidget(bpm_group)

        # Per-group riff constraints
        group_names = list(self.config.groups.keys())
        self._riff_constraints = GroupRiffConstraintPanel(group_names)
        for g, allowed in self._settings.group_constraints.items():
            if g in group_names:
                self._riff_constraints.set_constraint(g, set(allowed))
        self._riff_constraints.constraints_changed.connect(self._on_constraints_changed)
        center_layout.addWidget(self._riff_constraints)

        # GROOVE NOW / FILL NOW big buttons — themed via role properties.
        groove_fill_row = QHBoxLayout()
        self._groove_btn = QPushButton("GROOVE NOW")
        self._groove_btn.setFixedHeight(50)
        self._groove_btn.setProperty("role", "success")
        self._groove_btn.setStyleSheet("font-size: 16px;")
        self._groove_btn.clicked.connect(self._on_groove_now)
        groove_fill_row.addWidget(self._groove_btn)

        self._fill_btn = QPushButton("FILL NOW")
        self._fill_btn.setFixedHeight(50)
        self._fill_btn.setProperty("role", "destructive")
        self._fill_btn.setStyleSheet("font-size: 16px;")
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
        self._speed_slider.setValue(self._settings.max_movement_speed)
        self._speed_slider.setFixedHeight(20)
        self._speed_value_label = QLabel(
            "OFF" if self._settings.max_movement_speed == 0
            else f"{self._settings.max_movement_speed}°/s"
        )
        self._speed_value_label.setFixedWidth(40)
        self._speed_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._speed_value_label.setStyleSheet("font-size: 10px;")
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_row.addWidget(speed_label)
        speed_row.addWidget(self._speed_slider)
        speed_row.addWidget(self._speed_value_label)
        center_layout.addLayout(speed_row)

        center_layout.addSpacing(8)
        self._color_wheel = HSVColorWheel()
        self._color_wheel.set_state(
            self._settings.color_override_active,
            self._settings.color_override_hue,
            self._settings.color_override_saturation,
        )
        self._color_wheel.color_changed.connect(self._on_color_changed)
        center_layout.addWidget(self._color_wheel)

        self._metrics_tracker = LiveMetricsTracker()
        center_layout.addWidget(self._metrics_tracker)

        center_layout.addStretch()
        splitter.addWidget(center_panel)

        # ── Right panel: ArtNet + input + plane + submasters + START/STOP ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)

        artnet_group = QGroupBox("ArtNet Output")
        artnet_layout = QVBoxLayout(artnet_group)

        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("Target IP:"))
        self._ip_input = QLineEdit(self._settings.target_ip)
        self._ip_input.setPlaceholderText("192.168.1.151")
        self._ip_input.editingFinished.connect(self._on_ip_changed)
        ip_row.addWidget(self._ip_input)
        artnet_layout.addLayout(ip_row)

        artnet_layout.addWidget(QLabel("Universe Mapping:"))
        self._universe_table = QTableWidget(0, 2)
        self._universe_table.setHorizontalHeaderLabels(["Config Univ", "ArtNet Univ"])
        self._universe_table.setFixedHeight(80)
        self._populate_universe_table()
        artnet_layout.addWidget(self._universe_table)

        # Mirror to broadcast — useful for the on-screen visualiser at home;
        # leave off at venues to keep DMX off the LAN.
        self._mirror_checkbox = QCheckBox("Mirror to visualiser broadcast")
        self._mirror_checkbox.setChecked(self._settings.mirror_to_visualizer)
        self._mirror_checkbox.toggled.connect(self._on_mirror_toggled)
        artnet_layout.addWidget(self._mirror_checkbox)

        right_layout.addWidget(artnet_group)

        input_group = QGroupBox("Audio Input")
        input_layout = QVBoxLayout(input_group)
        self._input_device_combo = QComboBox()
        input_layout.addWidget(self._input_device_combo)
        right_layout.addWidget(input_group)

        plane_group = QGroupBox("Movement Target")
        plane_layout = QVBoxLayout(plane_group)
        self._plane_combo = QComboBox()
        self._stage_planes: dict = {}
        self._populate_plane_combo()
        self._plane_combo.currentTextChanged.connect(self._on_target_plane_changed)
        plane_layout.addWidget(self._plane_combo)
        right_layout.addWidget(plane_group)

        # Group submasters — per-group dimmer trim faders.
        self._submasters = GroupSubmasterPanel(group_names)
        for g, val in self._settings.group_submasters.items():
            if g in group_names:
                self._submasters.set_value(g, val / 100.0)
        self._submasters.submaster_changed.connect(self._on_submaster_changed)
        right_layout.addWidget(self._submasters)

        right_layout.addStretch()

        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("START")
        self._start_btn.setFixedHeight(40)
        self._start_btn.setProperty("role", "success")
        self._start_btn.setStyleSheet("font-size: 14px;")
        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn = QPushButton("STOP")
        self._stop_btn.setFixedHeight(40)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setProperty("role", "destructive")
        self._stop_btn.setStyleSheet("font-size: 14px;")
        self._stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._stop_btn)
        right_layout.addLayout(btn_row)

        right_panel.setFixedWidth(220)
        splitter.addWidget(right_panel)

    def on_tab_activated(self):
        # Lazy fixture-definitions load — first time the user opens the
        # tab, parse the QXF files for every (manufacturer, model) the
        # config references. Skipping this on app startup keeps cold
        # start cheap.
        if not self._fixtures_loaded:
            self._load_fixture_definitions()
            self._fixtures_loaded = True

        # If the engine is still running (e.g. the user peeked at another
        # tab during a gig), restart the UI tick so meters update again.
        if self._is_running:
            self._ui_timer.start()

    def on_tab_deactivated(self):
        # Stop the 20 Hz UI poll while we're invisible — the engine and
        # DMX threads keep running so a peek at another tab doesn't
        # interrupt the show.
        self._ui_timer.stop()
        try:
            self._save_settings()
        except Exception as e:
            print(f"Error saving Live Mode settings: {e}")

    # BaseTab calls update_from_config / save_to_config on activate /
    # deactivate by default. We override those hooks above instead, so
    # the auto-save behaviour from BaseTab is replaced — the engine /
    # DMX state lives in self, not in self.config.
    def update_from_config(self):
        # Refresh the plane combo when stage geometry changes; harmless
        # to call repeatedly because _populate_plane_combo restores the
        # selection.
        if hasattr(self, "_plane_combo"):
            self._populate_plane_combo()

    # ── Lazy fixture definitions ──────────────────────────────────────

    def _load_fixture_definitions(self):
        """Parse QXF files for every (manufacturer, model) in the config.

        Run once on first tab activation. If parsing fails we leave
        ``fixture_definitions`` empty — START will then refuse to spin
        up the engine, but the rest of the tab UI stays interactive.
        """
        try:
            models_in_config = {(f.manufacturer, f.model)
                                for g in self.config.groups.values()
                                for f in g.fixtures}
            from utils.fixture_utils import load_fixture_definitions_from_qlc
            self.fixture_definitions = load_fixture_definitions_from_qlc(
                models_in_config
            )
        except Exception as e:
            print(f"LiveTab: failed to load fixture definitions: {e}")
            self.fixture_definitions = {}

    # ── Population helpers ────────────────────────────────────────────

    def _populate_devices(self):
        devices = self._device_manager.enumerate_input_devices()
        self._input_device_combo.clear()
        for device in devices:
            self._input_device_combo.addItem(
                f"{device.name} ({device.host_api})", device.index
            )

        saved_name = self._settings.input_device_name
        if saved_name:
            for i, device in enumerate(devices):
                if device.name == saved_name:
                    self._input_device_combo.setCurrentIndex(i)
                    return

        default = self._device_manager.get_default_input_device()
        if default:
            for i in range(self._input_device_combo.count()):
                if self._input_device_combo.itemData(i) == default.index:
                    self._input_device_combo.setCurrentIndex(i)
                    break

    def _populate_plane_combo(self):
        planes = compute_stage_planes(self.config)
        self._stage_planes = {p.name: p for p in planes}

        self._plane_combo.clear()
        self._plane_combo.addItem("None (manual)")
        for plane in planes:
            self._plane_combo.addItem(plane.name)

        saved = self._settings.target_plane_name
        idx = self._plane_combo.findText(saved) if saved else -1
        if idx < 0:
            idx = self._plane_combo.findText("Front")
        if idx >= 0:
            self._plane_combo.setCurrentIndex(idx)

    def _populate_universe_table(self):
        universes = list(self.config.universes.keys())
        saved = self._settings.universe_mapping
        self._universe_table.setRowCount(len(universes))
        for row, uid in enumerate(universes):
            uid_int = int(uid)
            config_item = QTableWidgetItem(str(uid_int))
            config_item.setFlags(config_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            artnet_uid = saved.get(uid_int, uid_int - 1)
            artnet_item = QTableWidgetItem(str(artnet_uid))
            self._universe_table.setItem(row, 0, config_item)
            self._universe_table.setItem(row, 1, artnet_item)

    def _get_universe_mapping(self) -> dict:
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

    # ── Start / Stop ──────────────────────────────────────────────────

    def _on_start(self):
        if self._is_running:
            return

        # Make sure fixture definitions are loaded — usually done by
        # on_tab_activated, but if the user clicked START during the
        # very first activation race we still want to not crash.
        if not self._fixtures_loaded:
            self._load_fixture_definitions()
            self._fixtures_loaded = True

        try:
            device_index = self._input_device_combo.currentData()

            self._live_input = LiveAudioInput(
                sample_rate=44100, channels=1, buffer_size=512
            )
            if not self._live_input.initialize(device_index=device_index):
                print("Failed to initialize audio input")
                return

            self._analyzer = RealtimeSpectralAnalyzer(sample_rate=44100)
            self._bridge = LiveFeatureBridge(self._analyzer)
            self._bridge.feature_updated.connect(self._on_feature_frame)

            self._engine = LiveShowEngine(self.config, self.fixture_definitions)
            self._engine.set_bpm(self._bpm_spinbox.value())
            self._engine.set_groove_bars(self._groove_bars_spinbox.value())
            self._engine.set_energy_sensitivity(self._energy_fader.value())
            self._engine.set_on_riffs_updated(self._on_riffs_updated_from_engine)
            plane_text = self._plane_combo.currentText()
            plane = (self._stage_planes.get(plane_text)
                     if plane_text != "None (manual)" else None)
            self._engine.set_target_plane(plane)

            target_ip = self._ip_input.text().strip() or "192.168.1.151"
            self._dmx_controller = LiveDMXController(
                self.config, self.fixture_definitions, target_ip=target_ip,
            )
            self._dmx_controller.set_universe_mapping(self._get_universe_mapping())
            self._dmx_controller.set_mirror_to_visualizer(self._mirror_checkbox.isChecked())
            self._dmx_controller.set_engine(self._engine)
            self._dmx_controller.dmx_manager.set_stage_planes(self._stage_planes)

            self._live_input.start()
            self._bridge.start(self._live_input.ring_buffer)
            self._dmx_controller.start()

            self._is_running = True
            self._ui_timer.start()

            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            self._set_phase("running")

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
        self._stop_btn.setEnabled(False)
        self._set_phase("stopped")
        self._status_riff.setText("Riff: ---")
        self._status_bar_counter.setText("Bar: -/-")

        print("Live Mode stopped")

    def _cleanup(self):
        """Tear down audio + engine + DMX threads. Idempotent."""
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

    def cleanup(self):
        """Called from MainWindow.closeEvent on app shutdown.

        Replaces the old ``LiveModeWindow.closeEvent`` — saves user
        settings, tears down running threads, releases the audio host.
        """
        try:
            self._save_settings()
        except Exception as e:
            print(f"Error saving Live Mode settings: {e}")
        self._cleanup()
        try:
            self._device_manager.cleanup()
        except Exception:
            pass

    # ── Engine event handlers ─────────────────────────────────────────

    def _on_feature_frame(self, frame: LiveFeatureFrame):
        """Receive feature frame from analyzer (Qt signal, main thread)."""
        self._latest_frame = frame
        if self._engine:
            self._engine.on_feature_frame(frame)
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
            if r < 0:
                self._engine.set_color_override(None)
            else:
                self._engine.set_color_override((r, g, b))

    def _on_energy_sensitivity_changed(self, value: float):
        if self._engine:
            self._engine.set_energy_sensitivity(value)

    def _on_ip_changed(self):
        if self._dmx_controller:
            self._dmx_controller.set_target_ip(
                self._ip_input.text().strip() or "192.168.1.151"
            )

    def _on_mirror_toggled(self, checked: bool):
        if self._dmx_controller:
            self._dmx_controller.set_mirror_to_visualizer(checked)

    def _on_speed_changed(self, value):
        if value == 0:
            self._speed_value_label.setText("OFF")
        else:
            self._speed_value_label.setText(f"{value}°/s")
        if self._engine:
            self._engine.set_max_movement_speed(float(value))

    def _on_target_plane_changed(self, text):
        if self._engine:
            plane = (self._stage_planes.get(text)
                     if text != "None (manual)" else None)
            self._engine.set_target_plane(plane)

    def _on_submaster_changed(self, group_name, value):
        if self._engine:
            self._engine.set_group_submaster(group_name, value)

    def _on_constraints_changed(self, group_name, allowed):
        if self._engine:
            self._engine.set_group_constraints(group_name, allowed)

    def _on_riffs_updated_from_engine(self, per_group_rudiments):
        # Engine may invoke this from the DMX worker thread — defer the
        # widget update to the next UI tick instead of touching widgets
        # off-thread.
        self._pending_riff_update = per_group_rudiments

    # ── UI tick (20 Hz) ───────────────────────────────────────────────

    def _update_ui(self):
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

        if self._engine and self._is_running:
            self._status_riff.setText(f"Riff: {self._engine.current_groove_name}")
            total = self._engine.groove_bars + 1
            bar = self._engine.current_bar + 1
            self._status_bar_counter.setText(f"Bar: {bar}/{total}")
            phase = "fill" if self._engine.is_fill else "groove"
            self._status_phase.setText("FILL" if self._engine.is_fill else "GROOVE")
            self._set_phase(phase)
            self._bpm_display.setText(str(int(self._engine.bpm)))

        if self._pending_riff_update:
            active = {g: r[0] for g, r in self._pending_riff_update.items()}
            self._riff_constraints.update_active_riffs(active)
            self._pending_riff_update = None

        if self._auto_bpm_checkbox.isChecked() and self._is_running:
            auto_bpm = self._auto_bpm.get_bpm()
            if auto_bpm is not None:
                self._bpm_spinbox.blockSignals(True)
                self._bpm_spinbox.setValue(int(round(auto_bpm)))
                self._bpm_spinbox.blockSignals(False)
                if self._engine:
                    self._engine.set_bpm(auto_bpm)

    # ── Phase property + theme ────────────────────────────────────────

    def _set_phase(self, phase: str):
        """Set the ``phase`` dynamic property + re-polish so the theme's
        ``QLabel#LiveStatusPhase[phase="..."]`` rule re-evaluates."""
        if self._status_phase.property("phase") == phase:
            return
        self._status_phase.setProperty("phase", phase)
        style = self._status_phase.style()
        if style is not None:
            style.unpolish(self._status_phase)
            style.polish(self._status_phase)

    # ── Settings persistence ──────────────────────────────────────────

    def _save_settings(self):
        hue, sat = self._color_wheel.get_hue_saturation()
        override_active = self._color_wheel.is_override_active()

        constraints = {
            g: sorted(allowed)
            for g, allowed in self._riff_constraints.get_constraints().items()
        }
        submasters = self._submasters.get_values()

        device_name = None
        idx = self._input_device_combo.currentIndex()
        if idx >= 0:
            label = self._input_device_combo.itemText(idx)
            paren = label.rfind(" (")
            device_name = label[:paren] if paren > 0 else label

        plane_text = self._plane_combo.currentText()
        target_plane = plane_text if plane_text != "None (manual)" else ""

        self._settings = live_settings.LiveModeSettings(
            target_ip=self._ip_input.text().strip() or "192.168.1.151",
            universe_mapping=self._get_universe_mapping(),
            mirror_to_visualizer=self._mirror_checkbox.isChecked(),
            input_device_name=device_name,
            bpm=self._bpm_spinbox.value(),
            groove_bars=self._groove_bars_spinbox.value(),
            energy_sensitivity=int(round(self._energy_fader.value() * 100)),
            target_plane_name=target_plane,
            max_movement_speed=self._speed_slider.value(),
            color_override_active=override_active,
            color_override_hue=hue,
            color_override_saturation=sat,
            group_constraints=constraints,
            group_submasters=submasters,
        )
        live_settings.save(self._settings)
