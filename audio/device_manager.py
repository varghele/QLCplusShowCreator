"""
Audio device management for QLCAutoShow.
Handles device enumeration, selection, and configuration.
"""

import pyaudio
import json
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class AudioDevice:
    """Represents an audio output device"""
    index: int
    name: str
    max_output_channels: int
    default_sample_rate: float
    host_api: str

    def __str__(self):
        return f"{self.name} ({self.max_output_channels} channels @ {int(self.default_sample_rate)} Hz)"


class DeviceManager:
    """Manages audio device enumeration and selection"""

    def __init__(self):
        self.py_audio = None
        self._devices_cache = None

    def initialize(self) -> bool:
        """Initialize PyAudio"""
        try:
            if not self.py_audio:
                self.py_audio = pyaudio.PyAudio()
            return True
        except Exception as e:
            print(f"Failed to initialize PyAudio: {e}")
            return False

    def cleanup(self):
        """Cleanup PyAudio resources"""
        if self.py_audio:
            self.py_audio.terminate()
            self.py_audio = None
            self._devices_cache = None

    def enumerate_devices(self, force_refresh: bool = False) -> List[AudioDevice]:
        """Enumerate all available audio output devices"""
        if self._devices_cache and not force_refresh:
            return self._devices_cache

        if not self.initialize():
            return []

        devices = []
        device_count = self.py_audio.get_device_count()

        for i in range(device_count):
            try:
                info = self.py_audio.get_device_info_by_index(i)

                # Only include devices with output channels
                if info['maxOutputChannels'] > 0:
                    # Get host API name
                    host_api_index = info.get('hostApi', 0)
                    try:
                        host_api_info = self.py_audio.get_host_api_info_by_index(host_api_index)
                        host_api_name = host_api_info['name']
                    except:
                        host_api_name = "Unknown"

                    device = AudioDevice(
                        index=i,
                        name=info['name'],
                        max_output_channels=info['maxOutputChannels'],
                        default_sample_rate=info['defaultSampleRate'],
                        host_api=host_api_name
                    )
                    devices.append(device)
            except Exception as e:
                print(f"Error reading device {i}: {e}")
                continue

        self._devices_cache = devices
        return devices

    def get_default_device(self) -> Optional[AudioDevice]:
        """Get the system default output device"""
        if not self.initialize():
            return None

        try:
            default_info = self.py_audio.get_default_output_device_info()
            device_index = default_info['index']

            # Get full device info
            devices = self.enumerate_devices()
            for device in devices:
                if device.index == device_index:
                    return device

            return None
        except Exception as e:
            print(f"Error getting default device: {e}")
            return None

    def get_device_by_index(self, index: int) -> Optional[AudioDevice]:
        """Get device by its index"""
        devices = self.enumerate_devices()
        for device in devices:
            if device.index == index:
                return device
        return None

    def validate_device(self, device_index: int) -> bool:
        """Check if a device index is valid and available"""
        devices = self.enumerate_devices()
        return any(d.index == device_index for d in devices)

    def save_preferences(self, config_path: str, device_index: Optional[int],
                        sample_rate: int, buffer_size: int):
        """Save audio preferences to config file"""
        config = {
            'device_index': device_index,
            'sample_rate': sample_rate,
            'buffer_size': buffer_size
        }

        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving audio config: {e}")
            return False

    def load_preferences(self, config_path: str) -> Dict:
        """Load audio preferences from config file"""
        default_config = {
            'device_index': None,  # None means use system default
            'sample_rate': 44100,
            'buffer_size': 1024
        }

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Validate loaded config
            if config.get('device_index') is not None:
                if not self.validate_device(config['device_index']):
                    print(f"Configured device {config['device_index']} not available, using default")
                    config['device_index'] = None

            return {**default_config, **config}
        except FileNotFoundError:
            return default_config
        except Exception as e:
            print(f"Error loading audio config: {e}")
            return default_config
