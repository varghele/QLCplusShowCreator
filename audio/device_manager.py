"""
Audio device management for QLCAutoShow.
Handles device enumeration, selection, and configuration.
Uses sounddevice for cross-platform ASIO (Windows) / JACK (Linux) support.
"""

import sounddevice as sd
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class AudioDevice:
    """Represents an audio device"""
    index: int
    name: str
    max_output_channels: int
    max_input_channels: int
    default_sample_rate: float
    host_api: str
    host_api_index: int

    def __str__(self):
        return f"{self.name} ({self.max_output_channels}out/{self.max_input_channels}in @ {int(self.default_sample_rate)} Hz, {self.host_api})"


class DeviceManager:
    """Manages audio device enumeration and selection"""

    def __init__(self):
        self._devices_cache = None

    def initialize(self) -> bool:
        """Initialize device manager (no-op for sounddevice, kept for API compat)"""
        return True

    def cleanup(self):
        """Cleanup resources (no-op for sounddevice, kept for API compat)"""
        self._devices_cache = None

    def enumerate_devices(self, force_refresh: bool = False,
                          host_api_filter: Optional[str] = None,
                          include_inputs: bool = False) -> List[AudioDevice]:
        """Enumerate available audio devices.

        Args:
            force_refresh: Force re-enumeration
            host_api_filter: Filter by host API name (e.g. "ASIO", "JACK", "Windows WASAPI")
            include_inputs: If True, include input-only devices. If False, only output-capable devices.

        Returns:
            List of AudioDevice objects
        """
        if self._devices_cache is not None and not force_refresh and host_api_filter is None and not include_inputs:
            return self._devices_cache

        devices = []

        try:
            all_devices = sd.query_devices()
            host_apis = sd.query_hostapis()

            for i, info in enumerate(all_devices):
                has_output = info['max_output_channels'] > 0
                has_input = info['max_input_channels'] > 0

                if not has_output and not (include_inputs and has_input):
                    continue

                # Get host API name
                api_index = info.get('hostapi', 0)
                try:
                    api_name = host_apis[api_index]['name']
                except (IndexError, KeyError):
                    api_name = "Unknown"

                if host_api_filter and api_name != host_api_filter:
                    continue

                device = AudioDevice(
                    index=i,
                    name=info['name'],
                    max_output_channels=info['max_output_channels'],
                    max_input_channels=info['max_input_channels'],
                    default_sample_rate=info['default_samplerate'],
                    host_api=api_name,
                    host_api_index=api_index,
                )
                devices.append(device)

        except Exception as e:
            print(f"Error enumerating devices: {e}")

        # Cache only the default (output-only, no filter) query
        if host_api_filter is None and not include_inputs:
            self._devices_cache = devices

        return devices

    def enumerate_input_devices(self, host_api_filter: Optional[str] = None) -> List[AudioDevice]:
        """Enumerate audio input devices.

        Args:
            host_api_filter: Filter by host API name

        Returns:
            List of AudioDevice objects with input channels
        """
        try:
            all_devices = sd.query_devices()
            host_apis = sd.query_hostapis()
            devices = []

            for i, info in enumerate(all_devices):
                if info['max_input_channels'] <= 0:
                    continue

                api_index = info.get('hostapi', 0)
                try:
                    api_name = host_apis[api_index]['name']
                except (IndexError, KeyError):
                    api_name = "Unknown"

                if host_api_filter and api_name != host_api_filter:
                    continue

                device = AudioDevice(
                    index=i,
                    name=info['name'],
                    max_output_channels=info['max_output_channels'],
                    max_input_channels=info['max_input_channels'],
                    default_sample_rate=info['default_samplerate'],
                    host_api=api_name,
                    host_api_index=api_index,
                )
                devices.append(device)

            return devices

        except Exception as e:
            print(f"Error enumerating input devices: {e}")
            return []

    def get_default_device(self) -> Optional[AudioDevice]:
        """Get the system default output device"""
        try:
            default_output_index = sd.default.device[1]
            if default_output_index is None or default_output_index < 0:
                return None

            info = sd.query_devices(default_output_index)
            host_apis = sd.query_hostapis()

            api_index = info.get('hostapi', 0)
            try:
                api_name = host_apis[api_index]['name']
            except (IndexError, KeyError):
                api_name = "Unknown"

            return AudioDevice(
                index=default_output_index,
                name=info['name'],
                max_output_channels=info['max_output_channels'],
                max_input_channels=info['max_input_channels'],
                default_sample_rate=info['default_samplerate'],
                host_api=api_name,
                host_api_index=api_index,
            )
        except Exception as e:
            print(f"Error getting default device: {e}")
            return None

    def get_default_input_device(self) -> Optional[AudioDevice]:
        """Get the system default input device"""
        try:
            default_input_index = sd.default.device[0]
            if default_input_index is None or default_input_index < 0:
                return None

            info = sd.query_devices(default_input_index)
            host_apis = sd.query_hostapis()

            api_index = info.get('hostapi', 0)
            try:
                api_name = host_apis[api_index]['name']
            except (IndexError, KeyError):
                api_name = "Unknown"

            return AudioDevice(
                index=default_input_index,
                name=info['name'],
                max_output_channels=info['max_output_channels'],
                max_input_channels=info['max_input_channels'],
                default_sample_rate=info['default_samplerate'],
                host_api=api_name,
                host_api_index=api_index,
            )
        except Exception as e:
            print(f"Error getting default input device: {e}")
            return None

    def get_device_by_index(self, index: int) -> Optional[AudioDevice]:
        """Get device by its index"""
        try:
            info = sd.query_devices(index)
            host_apis = sd.query_hostapis()

            api_index = info.get('hostapi', 0)
            try:
                api_name = host_apis[api_index]['name']
            except (IndexError, KeyError):
                api_name = "Unknown"

            return AudioDevice(
                index=index,
                name=info['name'],
                max_output_channels=info['max_output_channels'],
                max_input_channels=info['max_input_channels'],
                default_sample_rate=info['default_samplerate'],
                host_api=api_name,
                host_api_index=api_index,
            )
        except Exception as e:
            print(f"Error getting device {index}: {e}")
            return None

    def get_available_host_apis(self) -> List[Tuple[int, str]]:
        """Get all available host APIs.

        Returns:
            List of (index, name) tuples, e.g. [(0, "MME"), (1, "Windows WASAPI"), (2, "ASIO")]
        """
        try:
            apis = sd.query_hostapis()
            return [(i, api['name']) for i, api in enumerate(apis)]
        except Exception as e:
            print(f"Error querying host APIs: {e}")
            return []

    def validate_device(self, device_index: int) -> bool:
        """Check if a device index is valid and available"""
        try:
            info = sd.query_devices(device_index)
            return info['max_output_channels'] > 0
        except Exception:
            return False

    def validate_input_device(self, device_index: int) -> bool:
        """Check if an input device index is valid and available"""
        try:
            info = sd.query_devices(device_index)
            return info['max_input_channels'] > 0
        except Exception:
            return False

    def save_preferences(self, config_path: str, device_index: Optional[int],
                         sample_rate: int, buffer_size: int,
                         input_device_index: Optional[int] = None):
        """Save audio preferences to config file"""
        config = {
            'device_index': device_index,
            'sample_rate': sample_rate,
            'buffer_size': buffer_size,
            'input_device_index': input_device_index,
        }

        # Store device name for relocation if index changes across sessions
        if device_index is not None:
            device = self.get_device_by_index(device_index)
            if device:
                config['device_name'] = device.name
                config['device_host_api'] = device.host_api

        if input_device_index is not None:
            device = self.get_device_by_index(input_device_index)
            if device:
                config['input_device_name'] = device.name
                config['input_device_host_api'] = device.host_api

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
            'device_index': None,
            'sample_rate': 44100,
            'buffer_size': 512,
            'input_device_index': None,
        }

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Validate output device — try by index first, then relocate by name
            if config.get('device_index') is not None:
                if not self.validate_device(config['device_index']):
                    relocated = self._find_device_by_name(
                        config.get('device_name'), config.get('device_host_api'))
                    if relocated is not None:
                        print(f"Output device index changed, relocated to {relocated}")
                        config['device_index'] = relocated
                    else:
                        print(f"Configured output device not available, using default")
                        config['device_index'] = None

            # Validate input device
            if config.get('input_device_index') is not None:
                if not self.validate_input_device(config['input_device_index']):
                    relocated = self._find_device_by_name(
                        config.get('input_device_name'), config.get('input_device_host_api'))
                    if relocated is not None:
                        print(f"Input device index changed, relocated to {relocated}")
                        config['input_device_index'] = relocated
                    else:
                        print(f"Configured input device not available, using default")
                        config['input_device_index'] = None

            return {**default_config, **config}
        except FileNotFoundError:
            return default_config
        except Exception as e:
            print(f"Error loading audio config: {e}")
            return default_config

    def _find_device_by_name(self, name: Optional[str],
                             host_api: Optional[str]) -> Optional[int]:
        """Try to find a device by name and host API (for index relocation)."""
        if not name:
            return None

        try:
            all_devices = sd.query_devices()
            host_apis = sd.query_hostapis()

            for i, info in enumerate(all_devices):
                if info['name'] == name:
                    if host_api:
                        api_index = info.get('hostapi', 0)
                        try:
                            api_name = host_apis[api_index]['name']
                        except (IndexError, KeyError):
                            api_name = ""
                        if api_name == host_api:
                            return i
                    else:
                        return i
        except Exception:
            pass

        return None
