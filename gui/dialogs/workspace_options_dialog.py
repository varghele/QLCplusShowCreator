# gui/dialogs/workspace_options_dialog.py
# Dialog for configuring QLC+ workspace export options

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QGroupBox,
    QDialogButtonBox, QLabel
)
from PyQt6.QtCore import Qt


class WorkspaceOptionsDialog(QDialog):
    """Dialog for configuring Virtual Console generation options when exporting workspace."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workspace Export Options")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Description
        desc_label = QLabel(
            "Configure what to include in the exported QLC+ workspace.\n"
            "The Virtual Console provides live control of your fixtures."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # Virtual Console group
        vc_group = QGroupBox("Virtual Console")
        vc_layout = QVBoxLayout(vc_group)

        # Main toggle
        self.generate_vc_checkbox = QCheckBox("Generate Virtual Console controls")
        self.generate_vc_checkbox.setChecked(True)
        self.generate_vc_checkbox.setToolTip(
            "Creates sliders, XY pads, and buttons for each fixture group\n"
            "based on their capabilities (dimmer, color, movement, special)"
        )
        self.generate_vc_checkbox.toggled.connect(self._on_vc_toggled)
        vc_layout.addWidget(self.generate_vc_checkbox)

        # Sub-options container
        self.sub_options_widget = QGroupBox()
        self.sub_options_widget.setFlat(True)
        self.sub_options_widget.setStyleSheet("QGroupBox { border: none; margin-left: 20px; }")
        sub_layout = QVBoxLayout(self.sub_options_widget)
        sub_layout.setContentsMargins(20, 5, 0, 5)

        # Group controls
        self.group_controls_checkbox = QCheckBox("Fixture group controls (sliders, XY pads)")
        self.group_controls_checkbox.setChecked(True)
        self.group_controls_checkbox.setToolTip(
            "Creates control widgets for each fixture group:\n"
            "- Master dimmer slider\n"
            "- RGB/Color sliders (if group has color capability)\n"
            "- XY Pad for pan/tilt (if group has movement capability)\n"
            "- Focus/Zoom sliders (if group has special capability)"
        )
        sub_layout.addWidget(self.group_controls_checkbox)

        # Scene presets
        self.scene_presets_checkbox = QCheckBox("Color and intensity preset scenes")
        self.scene_presets_checkbox.setChecked(True)
        self.scene_presets_checkbox.setToolTip(
            "Creates preset scenes for each fixture group:\n"
            "- Colors: Red, Green, Blue, White, Amber, Blackout\n"
            "- Intensities: 25%, 50%, 75%, 100%"
        )
        sub_layout.addWidget(self.scene_presets_checkbox)

        # Movement presets
        self.movement_presets_checkbox = QCheckBox("Movement preset patterns (for moving heads)")
        self.movement_presets_checkbox.setChecked(True)
        self.movement_presets_checkbox.setToolTip(
            "Creates movement EFX functions for moving head groups:\n"
            "- Center position\n"
            "- Circle pattern\n"
            "- Sweep pattern"
        )
        sub_layout.addWidget(self.movement_presets_checkbox)

        # Show buttons
        self.show_buttons_checkbox = QCheckBox("Show trigger buttons (in SoloFrame)")
        self.show_buttons_checkbox.setChecked(True)
        self.show_buttons_checkbox.setToolTip(
            "Creates a SoloFrame with buttons to trigger each show.\n"
            "Only one show can play at a time (solo/exclusive mode)."
        )
        sub_layout.addWidget(self.show_buttons_checkbox)

        # Speed dial
        self.speed_dial_checkbox = QCheckBox("Tap BPM SpeedDial")
        self.speed_dial_checkbox.setChecked(True)
        self.speed_dial_checkbox.setToolTip(
            "Creates a SpeedDial widget for tap tempo BPM control."
        )
        sub_layout.addWidget(self.speed_dial_checkbox)

        vc_layout.addWidget(self.sub_options_widget)
        layout.addWidget(vc_group)

        # Dark mode option
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout(appearance_group)

        self.dark_mode_checkbox = QCheckBox("Dark mode (black background)")
        self.dark_mode_checkbox.setChecked(True)
        self.dark_mode_checkbox.setToolTip(
            "Sets the Virtual Console background to black.\n"
            "Recommended for live performance to reduce distraction."
        )
        appearance_layout.addWidget(self.dark_mode_checkbox)

        layout.addWidget(appearance_group)

        # Spacer
        layout.addStretch()

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_vc_toggled(self, checked: bool):
        """Enable/disable sub-options when main VC checkbox is toggled."""
        self.sub_options_widget.setEnabled(checked)
        self.dark_mode_checkbox.setEnabled(checked)

    def get_options(self) -> dict:
        """Get the selected export options.

        Returns:
            Dict with keys:
                - generate_vc: bool - Master toggle for VC generation
                - group_controls: bool - Include fixture group controls
                - scene_presets: bool - Include color/intensity scenes
                - movement_presets: bool - Include movement EFX patterns
                - show_buttons: bool - Include show trigger buttons
                - speed_dial: bool - Include tap BPM SpeedDial
                - dark_mode: bool - Use dark/black background
        """
        return {
            'generate_vc': self.generate_vc_checkbox.isChecked(),
            'group_controls': self.group_controls_checkbox.isChecked(),
            'scene_presets': self.scene_presets_checkbox.isChecked(),
            'movement_presets': self.movement_presets_checkbox.isChecked(),
            'show_buttons': self.show_buttons_checkbox.isChecked(),
            'speed_dial': self.speed_dial_checkbox.isChecked(),
            'dark_mode': self.dark_mode_checkbox.isChecked(),
        }
