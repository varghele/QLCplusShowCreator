"""
MIDI Settings Dialog for QuickMIDI
Allows users to select MIDI output device
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QGroupBox,
                             QMessageBox)
from PyQt6.QtCore import Qt
from audio.midi_device_manager import MidiDeviceManager
from audio.midi_output_engine import MidiOutputEngine


class MidiSettingsDialog(QDialog):
    """Dialog for configuring MIDI output settings"""

    def __init__(self, midi_device_manager: MidiDeviceManager,
                 midi_output_engine: MidiOutputEngine, parent=None):
        super().__init__(parent)
        self.midi_device_manager = midi_device_manager
        self.midi_output_engine = midi_output_engine

        self.setWindowTitle("MIDI Settings")
        self.setModal(True)
        self.setMinimumWidth(500)

        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Device Selection Group
        device_group = QGroupBox("MIDI Output Device")
        device_layout = QVBoxLayout(device_group)

        # Device dropdown
        device_select_layout = QHBoxLayout()
        device_label = QLabel("Output Device:")
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(300)

        device_select_layout.addWidget(device_label)
        device_select_layout.addWidget(self.device_combo)
        device_select_layout.addStretch()

        device_layout.addLayout(device_select_layout)

        # Refresh button
        refresh_button = QPushButton("Refresh Devices")
        refresh_button.clicked.connect(self.refresh_devices)
        device_layout.addWidget(refresh_button)

        # Info label
        info_label = QLabel("MIDI messages will be sent to the selected device during playback.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        device_layout.addWidget(info_label)

        layout.addWidget(device_group)

        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        test_button = QPushButton("Test")
        test_button.clicked.connect(self.test_device)

        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.apply_settings)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(test_button)
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def load_current_settings(self):
        """Load current MIDI settings into the UI"""
        try:
            # Enumerate devices
            devices = self.midi_device_manager.enumerate_devices()

            # Clear and populate device combo
            self.device_combo.clear()

            if not devices:
                self.device_combo.addItem("No MIDI devices found", None)
                return

            for device in devices:
                self.device_combo.addItem(device.name, device.index)

        except Exception as e:
            print(f"Error loading MIDI devices: {e}")
            self.device_combo.clear()
            self.device_combo.addItem("Error loading devices", None)
            return

        try:
            # Set current device
            if self.midi_output_engine._current_device_index is not None:
                for i in range(self.device_combo.count()):
                    if self.device_combo.itemData(i) == self.midi_output_engine._current_device_index:
                        self.device_combo.setCurrentIndex(i)
                        break
            else:
                # Select first device by default
                if self.device_combo.count() > 0 and self.device_combo.itemData(0) is not None:
                    self.device_combo.setCurrentIndex(0)

        except Exception as e:
            print(f"Error setting current device: {e}")

    def refresh_devices(self):
        """Refresh the list of available devices"""
        try:
            devices = self.midi_device_manager.enumerate_devices(force_refresh=True)

            # Save current selection
            current_device_index = self.device_combo.currentData()

            # Clear and repopulate
            self.device_combo.clear()

            if not devices:
                self.device_combo.addItem("No MIDI devices found", None)
                QMessageBox.information(self, "No Devices", "No MIDI output devices found")
                return

            for device in devices:
                self.device_combo.addItem(device.name, device.index)

            # Restore selection if possible
            if current_device_index is not None:
                for i in range(self.device_combo.count()):
                    if self.device_combo.itemData(i) == current_device_index:
                        self.device_combo.setCurrentIndex(i)
                        break

            QMessageBox.information(self, "Success", f"Found {len(devices)} MIDI devices")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh devices: {str(e)}")

    def test_device(self):
        """Test the selected MIDI device by sending a test note"""
        device_index = self.device_combo.currentData()

        if device_index is None:
            QMessageBox.warning(self, "Warning", "Please select a device")
            return

        try:
            # Create temporary MIDI output for testing
            import rtmidi
            test_midi = rtmidi.MidiOut()
            test_midi.open_port(device_index)

            # Send test note (Middle C, channel 1)
            # Note On
            test_midi.send_message([0x90, 60, 100])

            # Wait a bit, then Note Off
            import time
            time.sleep(0.5)
            test_midi.send_message([0x80, 60, 0])

            test_midi.close_port()
            del test_midi

            QMessageBox.information(self, "Success",
                                    "Test note sent successfully!\nYou should have heard a brief note on channel 1.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Device test failed: {str(e)}")

    def apply_settings(self):
        """Apply the selected settings"""
        device_index = self.device_combo.currentData()

        if device_index is None:
            QMessageBox.warning(self, "Warning", "Please select a device")
            return

        try:
            # Cleanup current MIDI output
            self.midi_output_engine.cleanup()

            # Re-initialize with new device
            if self.midi_output_engine.initialize(device_index=device_index):
                # Save preferences
                self.midi_device_manager.save_preferences('midi_config.json', device_index)

                QMessageBox.information(self, "Success",
                                        "MIDI settings applied successfully")
                self.accept()
            else:
                QMessageBox.critical(self, "Error",
                                     "Failed to initialize MIDI with selected device")

        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to apply MIDI settings: {str(e)}")
