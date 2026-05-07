"""
Persistence for Live Mode session state.

Stores ArtNet configuration, audio device choice, BPM/groove settings,
movement target, color override, per-group constraints, submasters, and
the visualiser-broadcast toggle in `~/.qlcautoshow/live_mode_settings.json`
so the operator does not have to reconfigure on every launch.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


_SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".qlcautoshow")
_SETTINGS_PATH = os.path.join(_SETTINGS_DIR, "live_mode_settings.json")


@dataclass
class LiveModeSettings:
    """All persisted Live Mode state. Sensible defaults match a fresh launch."""

    # ArtNet output
    target_ip: str = "192.168.1.151"
    universe_mapping: Dict[int, int] = field(default_factory=dict)  # config uid -> artnet uid
    mirror_to_visualizer: bool = True

    # Audio input — store device name (indices are unstable across reboots)
    input_device_name: Optional[str] = None

    # Engine controls
    bpm: int = 120
    groove_bars: int = 3
    energy_sensitivity: int = 70  # 0..100
    target_plane_name: str = "Front"
    max_movement_speed: int = 0  # degrees/sec, 0 = off

    # Color override
    color_override_active: bool = False
    color_override_hue: float = 0.0       # 0..360
    color_override_saturation: float = 1.0  # 0..1

    # Per-group state — empty/missing means AUTO / default
    group_constraints: Dict[str, List[str]] = field(default_factory=dict)
    group_submasters: Dict[str, int] = field(default_factory=dict)  # 0..100


def load() -> LiveModeSettings:
    """Read settings from disk. Returns defaults on missing/corrupt file."""
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return LiveModeSettings()

    defaults = LiveModeSettings()
    valid_keys = set(asdict(defaults).keys())
    filtered = {k: v for k, v in data.items() if k in valid_keys}

    # JSON turns int keys into strings — restore for universe_mapping.
    if "universe_mapping" in filtered:
        try:
            filtered["universe_mapping"] = {
                int(k): int(v) for k, v in filtered["universe_mapping"].items()
            }
        except (ValueError, AttributeError):
            filtered["universe_mapping"] = {}

    return LiveModeSettings(**{**asdict(defaults), **filtered})


def save(settings: LiveModeSettings) -> None:
    """Write settings to disk. Silently ignores I/O errors — never block window close."""
    try:
        os.makedirs(_SETTINGS_DIR, exist_ok=True)
        data = asdict(settings)
        # Stringify int keys for JSON.
        data["universe_mapping"] = {str(k): v for k, v in data["universe_mapping"].items()}
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        print(f"Failed to save Live Mode settings: {e}")
