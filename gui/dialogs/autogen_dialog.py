# gui/dialogs/autogen_dialog.py
# Configuration dialog for automatic show generation

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QSpinBox, QLabel, QDialogButtonBox, QComboBox,
    QProgressBar, QFrame, QLineEdit,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from autogen.matcher import AutogenConfig


class AutogenWorker(QThread):
    """Background worker for show generation."""
    finished = pyqtSignal(list)  # Emits generated lanes
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # Status message

    def __init__(self, audio_path, song_structure, config, autogen_config, key_signature):
        super().__init__()
        self.audio_path = audio_path
        self.song_structure = song_structure
        self.config = config
        self.autogen_config = autogen_config
        self.key_signature = key_signature

    def run(self):
        try:
            from autogen.generator import generate_show
            self.progress.emit("Analyzing audio...")
            lanes = generate_show(
                self.audio_path,
                self.song_structure,
                self.config,
                self.autogen_config,
                self.key_signature,
            )
            self.progress.emit("Done!")
            self.finished.emit(lanes)
        except Exception as e:
            self.error.emit(str(e))


class AutogenDialog(QDialog):
    """Configuration dialog for automatic show generation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-Generate Show")
        self.setMinimumWidth(420)
        self.result_config = None
        self.result_key_signature = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Key signature
        key_group = QGroupBox("Song")
        key_layout = QFormLayout()

        self.key_combo = QComboBox()
        self.key_combo.addItems([
            "(Auto-detect)", "C major", "C minor",
            "D major", "D minor", "E major", "E minor",
            "F major", "F minor", "G major", "G minor",
            "A major", "A minor", "B major", "B minor",
            "Db major", "Eb major", "Eb minor",
            "Gb major", "Ab major", "Ab minor", "Bb major", "Bb minor",
        ])
        key_layout.addRow("Key Signature:", self.key_combo)

        key_group.setLayout(key_layout)
        layout.addWidget(key_group)

        # Phrase structure
        phrase_group = QGroupBox("Phrase Structure")
        phrase_layout = QFormLayout()

        self.phrase_length_spin = QSpinBox()
        self.phrase_length_spin.setRange(2, 8)
        self.phrase_length_spin.setValue(4)
        self.phrase_length_spin.setSuffix(" bars")
        phrase_layout.addRow("Phrase Length:", self.phrase_length_spin)

        self.groove_fill_spin = QDoubleSpinBox()
        self.groove_fill_spin.setRange(0.5, 0.9)
        self.groove_fill_spin.setSingleStep(0.05)
        self.groove_fill_spin.setValue(0.75)
        self.groove_fill_spin.setToolTip("Proportion of phrase as groove (rest is fill)")
        phrase_layout.addRow("Groove/Fill Ratio:", self.groove_fill_spin)

        phrase_group.setLayout(phrase_layout)
        layout.addWidget(phrase_group)

        # Matching parameters
        match_group = QGroupBox("Matching")
        match_layout = QFormLayout()

        self.fidelity_spin = QDoubleSpinBox()
        self.fidelity_spin.setRange(0.0, 1.0)
        self.fidelity_spin.setSingleStep(0.05)
        self.fidelity_spin.setValue(0.6)
        self.fidelity_spin.setToolTip("Weight of audio parameter fidelity in scoring")
        match_layout.addRow("Fidelity Weight:", self.fidelity_spin)

        self.coherence_spin = QDoubleSpinBox()
        self.coherence_spin.setRange(0.0, 1.0)
        self.coherence_spin.setSingleStep(0.05)
        self.coherence_spin.setValue(0.4)
        self.coherence_spin.setToolTip("Weight of musical coherence in scoring")
        match_layout.addRow("Coherence Weight:", self.coherence_spin)

        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0.05, 0.5)
        self.tolerance_spin.setSingleStep(0.05)
        self.tolerance_spin.setValue(0.2)
        self.tolerance_spin.setToolTip("Flux tolerance band width for candidate selection")
        match_layout.addRow("Tolerance Band:", self.tolerance_spin)

        match_group.setLayout(match_layout)
        layout.addWidget(match_group)

        # Special effects thresholds
        effects_group = QGroupBox("Special Effects")
        effects_layout = QFormLayout()

        self.gobo_threshold_spin = QDoubleSpinBox()
        self.gobo_threshold_spin.setRange(0.0, 1.0)
        self.gobo_threshold_spin.setSingleStep(0.05)
        self.gobo_threshold_spin.setValue(0.7)
        self.gobo_threshold_spin.setToolTip("Spectral richness threshold for gobo activation")
        effects_layout.addRow("Gobo Threshold:", self.gobo_threshold_spin)

        self.prism_threshold_spin = QDoubleSpinBox()
        self.prism_threshold_spin.setRange(0.0, 1.0)
        self.prism_threshold_spin.setSingleStep(0.05)
        self.prism_threshold_spin.setValue(0.8)
        self.prism_threshold_spin.setToolTip("Spectral richness threshold for prism activation")
        effects_layout.addRow("Prism Threshold:", self.prism_threshold_spin)

        effects_group.setLayout(effects_layout)
        layout.addWidget(effects_group)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accepted)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accepted(self):
        """Build config and accept."""
        self.result_config = AutogenConfig(
            groove_fill_ratio=self.groove_fill_spin.value(),
            phrase_length_bars=self.phrase_length_spin.value(),
            fidelity_weight=self.fidelity_spin.value(),
            coherence_weight=self.coherence_spin.value(),
            tolerance_band_width=self.tolerance_spin.value(),
            spectral_richness_gobo_threshold=self.gobo_threshold_spin.value(),
            spectral_richness_prism_threshold=self.prism_threshold_spin.value(),
        )

        key_text = self.key_combo.currentText()
        self.result_key_signature = None if key_text == "(Auto-detect)" else key_text

        self.accept()
