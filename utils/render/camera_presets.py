# utils/render/camera_presets.py
# Predefined camera positions for offline rendering

import math


# Each preset is a function that takes (stage_width, stage_depth) and returns
# (azimuth_deg, elevation_deg, distance, target_x, target_y, target_z)
# matching OrbitCamera's spherical coordinate system

def _compute_distance(stage_width, stage_depth, fov_deg=45.0):
    """Compute camera distance to fit the full stage in frame."""
    diagonal = math.sqrt(stage_width ** 2 + stage_depth ** 2)
    # Distance = half-diagonal / tan(fov/2), with padding
    distance = (diagonal / 2) / math.tan(math.radians(fov_deg / 2)) * 1.05
    return max(distance, 5.0)


CAMERA_PRESETS = {
    "Front": {
        "description": "Audience view, centered front",
        "get_params": lambda w, d: {
            "azimuth": 0.0,
            "elevation": 25.0,
            "distance": _compute_distance(w, d),
            "target": (0.0, 1.5, 0.0),  # Look at ~head height
        }
    },
    "Front-Left 45": {
        "description": "Angled view from house left",
        "get_params": lambda w, d: {
            "azimuth": -45.0,
            "elevation": 25.0,
            "distance": _compute_distance(w, d),
            "target": (0.0, 1.5, 0.0),
        }
    },
    "Front-Right 45": {
        "description": "Angled view from house right",
        "get_params": lambda w, d: {
            "azimuth": 45.0,
            "elevation": 25.0,
            "distance": _compute_distance(w, d),
            "target": (0.0, 1.5, 0.0),
        }
    },
    "Top-Down": {
        "description": "Bird's eye view straight down",
        "get_params": lambda w, d: {
            "azimuth": 0.0,
            "elevation": 85.0,
            "distance": _compute_distance(w, d) * 0.8,
            "target": (0.0, 0.0, 0.0),
        }
    },
    "Wide": {
        "description": "Pulled back wide shot",
        "get_params": lambda w, d: {
            "azimuth": -15.0,
            "elevation": 20.0,
            "distance": _compute_distance(w, d) * 1.5,
            "target": (0.0, 1.0, 0.0),
        }
    },
}
