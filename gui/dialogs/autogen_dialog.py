# gui/dialogs/autogen_dialog.py
# Configuration dialog for automatic show generation

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QSpinBox, QLabel, QDialogButtonBox, QComboBox,
    QFrame, QPushButton, QCheckBox, QColorDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from autogen.matcher import AutogenConfig
from autogen.color_generator import SongPalette, get_preset_names, get_preset_palette


class AutogenWorker(QThread):
    """Background worker for show generation."""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, audio_path, song_structure, config, autogen_config,
                 key_signature, song_palette):
        super().__init__()
        self.audio_path = audio_path
        self.song_structure = song_structure
        self.config = config
        self.autogen_config = autogen_config
        self.key_signature = key_signature
        self.song_palette = song_palette

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
                self.song_palette,
            )
            self.progress.emit("Done!")
            self.finished.emit(lanes)
        except Exception as e:
            self.error.emit(str(e))


class _ColorButton(QPushButton):
    """Button that shows a color swatch and opens a color picker on click."""

    def __init__(self, initial_color=(128, 128, 128), parent=None):
        super().__init__(parent)
        self.color = initial_color
        self.setFixedSize(40, 25)
        self._update_style()
        self.clicked.connect(self._pick_color)

    def _update_style(self):
        r, g, b = self.color
        text_color = "white" if (r + g + b) / 3 < 128 else "black"
        self.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); color: {text_color}; "
            f"border: 1px solid #888; border-radius: 3px;"
        )

    def _pick_color(self):
        r, g, b = self.color
        color = QColorDialog.getColor(QColor(r, g, b), self, "Pick Color")
        if color.isValid():
            self.color = (color.red(), color.green(), color.blue())
            self._update_style()


class AutogenDialog(QDialog):
    """Configuration dialog for automatic show generation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-Generate Show")
        self.setMinimumWidth(450)
        self.result_config = None
        self.result_key_signature = None
        self.result_palette = None
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

        # Color scheme
        color_group = QGroupBox("Color Scheme")
        color_layout = QFormLayout()

        self.color_preset_combo = QComboBox()
        self.color_preset_combo.addItem("(Auto from audio)")
        for name in get_preset_names():
            self.color_preset_combo.addItem(name)
        self.color_preset_combo.addItem("Custom")
        self.color_preset_combo.currentTextChanged.connect(self._on_color_preset_changed)
        color_layout.addRow("Palette:", self.color_preset_combo)

        # Custom color pickers
        custom_row = QHBoxLayout()
        self.color_btn_1 = _ColorButton((255, 0, 0))
        self.color_btn_2 = _ColorButton((0, 0, 255))
        self.color_btn_3 = _ColorButton((128, 128, 128))
        self.color_label_1 = QLabel("Primary:")
        self.color_label_2 = QLabel("Secondary:")
        self.color_label_3 = QLabel("Tertiary:")
        custom_row.addWidget(self.color_label_1)
        custom_row.addWidget(self.color_btn_1)
        custom_row.addSpacing(8)
        custom_row.addWidget(self.color_label_2)
        custom_row.addWidget(self.color_btn_2)
        custom_row.addSpacing(8)
        custom_row.addWidget(self.color_label_3)
        custom_row.addWidget(self.color_btn_3)
        custom_row.addStretch()
        color_layout.addRow("Colors:", custom_row)

        self.num_colors_combo = QComboBox()
        self.num_colors_combo.addItems(["1 color", "2 colors", "3 colors"])
        self.num_colors_combo.setCurrentIndex(1)  # Default: 2 colors
        self.num_colors_combo.currentIndexChanged.connect(self._on_num_colors_changed)
        color_layout.addRow("Num Colors:", self.num_colors_combo)

        self.include_white_check = QCheckBox("Include white")
        self.include_white_check.setChecked(True)
        color_layout.addRow("", self.include_white_check)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # Initially hide custom controls
        self._set_custom_visible(False)

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
        match_layout.addRow("Fidelity Weight:", self.fidelity_spin)

        self.coherence_spin = QDoubleSpinBox()
        self.coherence_spin.setRange(0.0, 1.0)
        self.coherence_spin.setSingleStep(0.05)
        self.coherence_spin.setValue(0.4)
        match_layout.addRow("Coherence Weight:", self.coherence_spin)

        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0.05, 0.5)
        self.tolerance_spin.setSingleStep(0.05)
        self.tolerance_spin.setValue(0.2)
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
        effects_layout.addRow("Gobo Threshold:", self.gobo_threshold_spin)

        self.prism_threshold_spin = QDoubleSpinBox()
        self.prism_threshold_spin.setRange(0.0, 1.0)
        self.prism_threshold_spin.setSingleStep(0.05)
        self.prism_threshold_spin.setValue(0.8)
        effects_layout.addRow("Prism Threshold:", self.prism_threshold_spin)

        effects_group.setLayout(effects_layout)
        layout.addWidget(effects_group)

        # Buttons
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accepted)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _set_custom_visible(self, visible):
        """Show/hide custom color pickers."""
        for w in [self.color_label_1, self.color_btn_1,
                   self.color_label_2, self.color_btn_2,
                   self.color_label_3, self.color_btn_3,
                   self.num_colors_combo, self.include_white_check]:
            w.setVisible(visible)
        # Also hide the labels in form layout
        if visible:
            self._on_num_colors_changed(self.num_colors_combo.currentIndex())

    def _on_color_preset_changed(self, text):
        """Handle color preset selection."""
        is_custom = (text == "Custom")
        self._set_custom_visible(is_custom)

        # Update color buttons from preset for preview
        preset = get_preset_palette(text)
        if preset:
            self.color_btn_1.color = preset.primary
            self.color_btn_1._update_style()
            if preset.secondary:
                self.color_btn_2.color = preset.secondary
                self.color_btn_2._update_style()
            self.include_white_check.setChecked(preset.include_white)

    def _on_num_colors_changed(self, index):
        """Show/hide color buttons based on num colors."""
        num = index + 1
        self.color_label_2.setVisible(num >= 2)
        self.color_btn_2.setVisible(num >= 2)
        self.color_label_3.setVisible(num >= 3)
        self.color_btn_3.setVisible(num >= 3)

    def _build_palette(self) -> SongPalette:
        """Build SongPalette from dialog state."""
        preset_text = self.color_preset_combo.currentText()

        if preset_text == "(Auto from audio)":
            return None  # Generator will auto-derive

        preset = get_preset_palette(preset_text)
        if preset and preset_text != "Custom":
            return preset

        # Custom
        num = self.num_colors_combo.currentIndex() + 1
        primary = self.color_btn_1.color
        secondary = self.color_btn_2.color if num >= 2 else None
        tertiary = self.color_btn_3.color if num >= 3 else None

        return SongPalette(
            primary=primary,
            secondary=secondary,
            tertiary=tertiary,
            include_white=self.include_white_check.isChecked(),
        )

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
        self.result_palette = self._build_palette()

        self.accept()
