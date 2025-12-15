from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSpinBox, QDialogButtonBox,
                             QFormLayout, QComboBox, QTextEdit)
from PyQt6.QtCore import Qt


class ProjectSettingsDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project

        self.setWindowTitle("Project Settings")
        self.setModal(True)
        self.resize(400, 300)

        self.setup_ui()
        self.load_values()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        # Project name
        self.name_edit = QLineEdit()
        form_layout.addRow("Project Name:", self.name_edit)

        # BPM
        self.bpm_spinbox = QSpinBox()
        self.bpm_spinbox.setRange(60, 200)
        form_layout.addRow("BPM:", self.bpm_spinbox)

        layout.addLayout(form_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_values(self):
        self.name_edit.setText(self.project.project_name)
        self.bpm_spinbox.setValue(int(self.project.bpm))

    def accept(self):
        self.project.project_name = self.name_edit.text()
        self.project.bpm = float(self.bpm_spinbox.value())
        super().accept()


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("About MIDI Track Creator")
        self.setModal(True)
        self.resize(300, 200)

        layout = QVBoxLayout(self)

        title_label = QLabel("MIDI Track Creator")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info_label = QLabel("A modular MIDI track creation tool\nfor audio and light equipment control.")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title_label)
        layout.addWidget(info_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
