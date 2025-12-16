# gui/audio_settings_dialog.py
# Audio Settings Dialog for QLCAutoShow
# Allows users to select audio output device and configure audio parameters

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QGroupBox, QSpinBox,
                             QMessageBox)
from PyQt6.QtCore import Qt

# Try to import audio components
try:
    from audio.device_manager import DeviceManager
    from audio.audio_engine import AudioEngine
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    DeviceManager = None
    AudioEngine = None


class AudioSettingsDialog(QDialog):
    """Dialog for configuring audio output settings."""

    def __init__(self, device_manager=None, audio_engine=None, parent=None):
        """Initialize audio settings dialog.

        Args:
            device_manager: DeviceManager instance (optional, will create if not provided)
            audio_engine: AudioEngine instance (optional)
            parent: Parent widget
        """
        super().__init__(parent)

        self.device_manager = device_manager
        self.audio_engine = audio_engine
        self._owns_device_manager = False

        # Create device manager if not provided
        if self.device_manager is None and AUDIO_AVAILABLE:
            self.device_manager = DeviceManager()
            self._owns_device_manager = True

        self.setWindowTitle("Audio Settings")
        self.setModal(True)
        self.setMinimumWidth(500)

        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        if not AUDIO_AVAILABLE:
            # Show error message if audio not available
            error_label = QLabel(
                "Audio support is not available.\n\n"
                "Please ensure the following packages are installed:\n"
                "- pyaudio\n"
                "- soundfile\n"
                "- librosa"
            )
            error_label.setStyleSheet("color: red; font-weight: bold;")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)

            # Close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(self.reject)
            layout.addWidget(close_button)
            return

        # Device Selection Group
        device_group = QGroupBox("Audio Output Device")
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

        layout.addWidget(device_group)

        # Audio Parameters Group
        params_group = QGroupBox("Audio Parameters")
        params_layout = QVBoxLayout(params_group)

        # Sample Rate
        sample_rate_layout = QHBoxLayout()
        sample_rate_label = QLabel("Sample Rate:")
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000", "96000"])
        self.sample_rate_combo.setCurrentText("44100")

        sample_rate_layout.addWidget(sample_rate_label)
        sample_rate_layout.addWidget(self.sample_rate_combo)
        sample_rate_layout.addStretch()

        params_layout.addLayout(sample_rate_layout)

        # Buffer Size
        buffer_size_layout = QHBoxLayout()
        buffer_size_label = QLabel("Buffer Size:")
        self.buffer_size_spinbox = QSpinBox()
        self.buffer_size_spinbox.setRange(256, 4096)
        self.buffer_size_spinbox.setSingleStep(256)
        self.buffer_size_spinbox.setValue(1024)

        buffer_size_layout.addWidget(buffer_size_label)
        buffer_size_layout.addWidget(self.buffer_size_spinbox)
        buffer_size_layout.addStretch()

        params_layout.addLayout(buffer_size_layout)

        # Info label
        info_label = QLabel("Note: Changing audio settings will restart the audio engine.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        params_layout.addWidget(info_label)

        layout.addWidget(params_group)

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
        """Load current audio settings into the UI."""
        if not AUDIO_AVAILABLE or not self.device_manager:
            return

        try:
            # Enumerate devices
            devices = self.device_manager.enumerate_devices()

            # Clear and populate device combo
            self.device_combo.clear()

            if not devices:
                self.device_combo.addItem("No audio devices found", None)
                return

            for device in devices:
                display_text = f"{device.name} ({device.host_api})"
                self.device_combo.addItem(display_text, device.index)

        except Exception as e:
            print(f"Error loading devices: {e}")
            self.device_combo.clear()
            self.device_combo.addItem("Error loading devices", None)
            return

        try:
            # Set current device
            default_device = self.device_manager.get_default_device()
            if default_device:
                for i in range(self.device_combo.count()):
                    if self.device_combo.itemData(i) == default_device.index:
                        self.device_combo.setCurrentIndex(i)
                        break

            # Set current sample rate and buffer size from engine if available
            if self.audio_engine:
                if hasattr(self.audio_engine, 'sample_rate'):
                    self.sample_rate_combo.setCurrentText(str(self.audio_engine.sample_rate))
                if hasattr(self.audio_engine, 'buffer_size'):
                    self.buffer_size_spinbox.setValue(self.audio_engine.buffer_size)

        except Exception as e:
            print(f"Error setting current device: {e}")

    def refresh_devices(self):
        """Refresh the list of available devices."""
        if not AUDIO_AVAILABLE or not self.device_manager:
            return

        try:
            devices = self.device_manager.enumerate_devices(force_refresh=True)

            # Save current selection
            current_device_index = self.device_combo.currentData()

            # Clear and repopulate
            self.device_combo.clear()
            for device in devices:
                display_text = f"{device.name} ({device.host_api})"
                self.device_combo.addItem(display_text, device.index)

            # Restore selection if possible
            if current_device_index is not None:
                for i in range(self.device_combo.count()):
                    if self.device_combo.itemData(i) == current_device_index:
                        self.device_combo.setCurrentIndex(i)
                        break

            QMessageBox.information(self, "Success", f"Found {len(devices)} audio devices")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh devices: {str(e)}")

    def test_device(self):
        """Test the selected audio device."""
        if not AUDIO_AVAILABLE or not self.device_manager:
            return

        device_index = self.device_combo.currentData()

        if device_index is None:
            QMessageBox.warning(self, "Warning", "Please select a device")
            return

        try:
            # Validate device
            if self.device_manager.validate_device(device_index):
                QMessageBox.information(self, "Success",
                                        "Audio device is valid and available")
            else:
                QMessageBox.warning(self, "Warning",
                                    "Selected device may not be available")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Device test failed: {str(e)}")

    def apply_settings(self):
        """Apply the selected settings."""
        if not AUDIO_AVAILABLE:
            self.reject()
            return

        device_index = self.device_combo.currentData()
        sample_rate = int(self.sample_rate_combo.currentText())
        buffer_size = self.buffer_size_spinbox.value()

        if device_index is None:
            QMessageBox.warning(self, "Warning", "Please select a device")
            return

        # Store settings for retrieval
        self.selected_device_index = device_index
        self.selected_sample_rate = sample_rate
        self.selected_buffer_size = buffer_size

        # If we have an audio engine, apply directly
        if self.audio_engine:
            try:
                # Stop current playback if running
                if hasattr(self.audio_engine, 'is_playing') and self.audio_engine.is_playing():
                    self.audio_engine.stop_playback()

                # Cleanup old engine
                if hasattr(self.audio_engine, 'cleanup'):
                    self.audio_engine.cleanup()

                # Update engine parameters
                self.audio_engine.sample_rate = sample_rate
                self.audio_engine.buffer_size = buffer_size

                # Re-initialize with new device
                if self.audio_engine.initialize(device_index=device_index):
                    QMessageBox.information(self, "Success",
                                            "Audio settings applied successfully")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error",
                                         "Failed to initialize audio with selected device")

            except Exception as e:
                QMessageBox.critical(self, "Error",
                                     f"Failed to apply audio settings: {str(e)}")
        else:
            # No engine provided, just store settings and accept
            QMessageBox.information(self, "Success",
                                    "Audio settings saved. They will be applied when playback starts.")
            self.accept()

    def get_settings(self):
        """Get the selected settings.

        Returns:
            dict with device_index, sample_rate, buffer_size or None if cancelled
        """
        if hasattr(self, 'selected_device_index'):
            return {
                'device_index': self.selected_device_index,
                'sample_rate': self.selected_sample_rate,
                'buffer_size': self.selected_buffer_size
            }
        return None

    def closeEvent(self, event):
        """Handle dialog close."""
        # Clean up device manager if we created it
        if self._owns_device_manager and self.device_manager:
            self.device_manager.cleanup()
        super().closeEvent(event)
