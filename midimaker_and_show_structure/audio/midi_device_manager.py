"""
MIDI device management for QuickMIDI.
Handles MIDI device enumeration, selection, and configuration.
"""

import rtmidi
import json
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class MidiDevice:
    """Represents a MIDI output device"""
    index: int
    name: str

    def __str__(self):
        return self.name


class MidiDeviceManager:
    """Manages MIDI device enumeration and selection"""

    def __init__(self):
        self._midi_out = None
        self._devices_cache = None

    def initialize(self) -> bool:
        """Initialize MIDI output"""
        try:
            if not self._midi_out:
                self._midi_out = rtmidi.MidiOut()
            return True
        except Exception as e:
            print(f"Failed to initialize MIDI output: {e}")
            return False

    def cleanup(self):
        """Cleanup MIDI resources"""
        if self._midi_out:
            if self._midi_out.is_port_open():
                self._midi_out.close_port()
            del self._midi_out
            self._midi_out = None
            self._devices_cache = None

    def enumerate_devices(self, force_refresh: bool = False) -> List[MidiDevice]:
        """Enumerate all available MIDI output devices"""
        if self._devices_cache and not force_refresh:
            return self._devices_cache

        if not self.initialize():
            return []

        devices = []
        port_names = self._midi_out.get_ports()

        for i, name in enumerate(port_names):
            device = MidiDevice(index=i, name=name)
            devices.append(device)

        self._devices_cache = devices
        return devices

    def get_default_device(self) -> Optional[MidiDevice]:
        """Get the first available MIDI output device"""
        devices = self.enumerate_devices()
        if devices:
            return devices[0]
        return None

    def get_device_by_index(self, index: int) -> Optional[MidiDevice]:
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

    def save_preferences(self, config_path: str, device_index: Optional[int]):
        """Save MIDI preferences to config file"""
        config = {
            'device_index': device_index
        }

        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving MIDI config: {e}")
            return False

    def load_preferences(self, config_path: str) -> Dict:
        """Load MIDI preferences from config file"""
        default_config = {
            'device_index': None  # None means use first available device
        }

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Validate loaded config
            if config.get('device_index') is not None:
                if not self.validate_device(config['device_index']):
                    print(f"Configured MIDI device {config['device_index']} not available, using default")
                    config['device_index'] = None

            return {**default_config, **config}
        except FileNotFoundError:
            return default_config
        except Exception as e:
            print(f"Error loading MIDI config: {e}")
            return default_config
