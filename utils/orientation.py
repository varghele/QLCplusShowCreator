# utils/orientation.py
# Orientation utilities for fixture rotation matrices and pan/tilt calculations

import math
import numpy as np
from typing import Tuple, Optional


# Base rotations for each mounting preset
MOUNTING_BASE_ROTATIONS = {
    'hanging': {'pitch': 90.0, 'yaw': 0.0},       # Fixture hanging from truss, beam down (base up)
    'standing': {'pitch': -90.0, 'yaw': 0.0},     # Fixture on floor, beam up (base down)
    'wall_left': {'pitch': 0.0, 'yaw': -90.0},    # Base against stage-right wall
    'wall_right': {'pitch': 0.0, 'yaw': 90.0},    # Base against stage-left wall
    'wall_back': {'pitch': 0.0, 'yaw': 0.0},      # Base against back wall, beam toward audience
    'wall_front': {'pitch': 0.0, 'yaw': 180.0},   # Base toward audience, beam toward back
}


def get_rotation_matrix(mounting: str, yaw: float, pitch: float, roll: float) -> np.ndarray:
    """
    Build a 3x3 rotation matrix from mounting preset and Euler angles.

    Uses ZYX (yaw-pitch-roll) convention:
    1. First apply yaw (rotation around world Z/up axis)
    2. Then apply pitch (rotation around local Y axis)
    3. Finally apply roll (rotation around local X axis)

    Args:
        mounting: Mounting preset name ('hanging', 'standing', 'wall_left', etc.)
        yaw: Yaw angle in degrees (-180 to 180)
        pitch: Pitch angle in degrees (-90 to 90)
        roll: Roll angle in degrees (-180 to 180)

    Returns:
        3x3 numpy rotation matrix that transforms from fixture-local to world space
    """
    # Get base rotation from mounting preset
    base = MOUNTING_BASE_ROTATIONS.get(mounting, {'pitch': 0.0, 'yaw': 0.0})
    base_pitch = base['pitch']
    base_yaw = base['yaw']

    # Add user adjustments to base rotation
    total_yaw = math.radians(base_yaw + yaw)
    total_pitch = math.radians(base_pitch + pitch)
    total_roll = math.radians(roll)

    # Build rotation matrices
    # Rz (yaw) - rotation around Z axis (world up)
    cos_yaw, sin_yaw = math.cos(total_yaw), math.sin(total_yaw)
    Rz = np.array([
        [cos_yaw, -sin_yaw, 0],
        [sin_yaw, cos_yaw, 0],
        [0, 0, 1]
    ])

    # Ry (pitch) - rotation around Y axis
    cos_pitch, sin_pitch = math.cos(total_pitch), math.sin(total_pitch)
    Ry = np.array([
        [cos_pitch, 0, sin_pitch],
        [0, 1, 0],
        [-sin_pitch, 0, cos_pitch]
    ])

    # Rx (roll) - rotation around X axis
    cos_roll, sin_roll = math.cos(total_roll), math.sin(total_roll)
    Rx = np.array([
        [1, 0, 0],
        [0, cos_roll, -sin_roll],
        [0, sin_roll, cos_roll]
    ])

    # Combined rotation: Rz * Ry * Rx
    return Rz @ Ry @ Rx


def calculate_pan_tilt(
    fixture_x: float, fixture_y: float, fixture_z: float,
    target_x: float, target_y: float, target_z: float,
    mounting: str, yaw: float, pitch: float, roll: float,
    pan_range: float = 540.0, tilt_range: float = 270.0
) -> Tuple[float, float]:
    """
    Calculate pan and tilt angles for a fixture to point at a world position.

    Args:
        fixture_x, fixture_y, fixture_z: Fixture position in world space (meters)
        target_x, target_y, target_z: Target position in world space (meters)
        mounting: Mounting preset name
        yaw, pitch, roll: Fixture orientation angles (degrees)
        pan_range: Total pan range in degrees (default 540)
        tilt_range: Total tilt range in degrees (default 270)

    Returns:
        Tuple of (pan_degrees, tilt_degrees) where:
        - pan_degrees: Pan angle in degrees (0 = center)
        - tilt_degrees: Tilt angle in degrees (0 = center)
    """
    # Calculate direction vector from fixture to target in world space
    direction_world = np.array([
        target_x - fixture_x,
        target_y - fixture_y,
        target_z - fixture_z
    ])

    # Normalize the direction
    length = np.linalg.norm(direction_world)
    if length < 0.001:  # Target is at fixture position
        return 0.0, 0.0
    direction_world = direction_world / length

    # Get fixture's rotation matrix (local to world)
    R = get_rotation_matrix(mounting, yaw, pitch, roll)

    # Transform direction to fixture-local space (world to local is R.T)
    direction_local = R.T @ direction_world

    # In fixture local space:
    # - X axis is typically the pan=0 reference direction
    # - Y axis is perpendicular in the horizontal plane
    # - Z axis is the beam direction at home position

    # Calculate pan angle (rotation around Y axis to align X with target direction)
    # pan = atan2(local_y, local_x) - but we need to project to XZ plane first
    pan_rad = math.atan2(direction_local[1], direction_local[0])
    pan_degrees = math.degrees(pan_rad)

    # Calculate tilt angle (elevation from horizontal)
    # Project direction onto XY plane for horizontal component
    horizontal_dist = math.sqrt(direction_local[0]**2 + direction_local[1]**2)
    tilt_rad = math.atan2(direction_local[2], horizontal_dist)
    tilt_degrees = math.degrees(tilt_rad)

    # Clamp to fixture's range
    half_pan = pan_range / 2
    half_tilt = tilt_range / 2
    pan_degrees = max(-half_pan, min(half_pan, pan_degrees))
    tilt_degrees = max(-half_tilt, min(half_tilt, tilt_degrees))

    return pan_degrees, tilt_degrees


def pan_tilt_to_dmx(
    pan_degrees: float, tilt_degrees: float,
    pan_range: float = 540.0, tilt_range: float = 270.0,
    pan_inverted: bool = False, tilt_inverted: bool = False
) -> Tuple[int, int]:
    """
    Convert pan/tilt angles to DMX values (0-255).

    Args:
        pan_degrees: Pan angle in degrees (0 = center)
        tilt_degrees: Tilt angle in degrees (0 = center)
        pan_range: Total pan range in degrees
        tilt_range: Total tilt range in degrees
        pan_inverted: Whether pan direction is inverted
        tilt_inverted: Whether tilt direction is inverted

    Returns:
        Tuple of (pan_dmx, tilt_dmx) values in range 0-255
    """
    # Convert from degrees to 0-255 DMX range
    # 0 degrees = 127 (center), -half_range = 0, +half_range = 255
    half_pan = pan_range / 2
    half_tilt = tilt_range / 2

    # Normalize to -1 to 1 range
    pan_normalized = pan_degrees / half_pan if half_pan > 0 else 0
    tilt_normalized = tilt_degrees / half_tilt if half_tilt > 0 else 0

    # Apply inversion if needed
    if pan_inverted:
        pan_normalized = -pan_normalized
    if tilt_inverted:
        tilt_normalized = -tilt_normalized

    # Convert to 0-255 (127 = center)
    pan_dmx = int(127 + pan_normalized * 127)
    tilt_dmx = int(127 + tilt_normalized * 127)

    # Clamp to valid range
    pan_dmx = max(0, min(255, pan_dmx))
    tilt_dmx = max(0, min(255, tilt_dmx))

    return pan_dmx, tilt_dmx


def get_beam_direction(mounting: str, yaw: float, pitch: float, roll: float) -> np.ndarray:
    """
    Get the beam direction vector in world space for a fixture.

    In fixture local space, the beam points along the positive Z axis.
    This function transforms that to world space.

    Args:
        mounting: Mounting preset name
        yaw, pitch, roll: Fixture orientation angles (degrees)

    Returns:
        Unit vector (3,) pointing in the beam direction in world space
    """
    R = get_rotation_matrix(mounting, yaw, pitch, roll)
    local_z = np.array([0, 0, 1])
    return R @ local_z


def get_fill_direction(mounting: str, yaw: float, pitch: float, roll: float) -> np.ndarray:
    """
    Get the fill direction for strip fixtures in world space.

    For strip fixtures, the fill direction is along the local X axis
    (from pixel 1 to pixel N).

    Args:
        mounting: Mounting preset name
        yaw, pitch, roll: Fixture orientation angles (degrees)

    Returns:
        Unit vector (3,) pointing in the fill direction in world space
    """
    R = get_rotation_matrix(mounting, yaw, pitch, roll)
    local_x = np.array([1, 0, 0])
    return R @ local_x


def is_fixture_pointing_down(mounting: str, yaw: float, pitch: float, roll: float) -> bool:
    """
    Check if the fixture's beam is primarily pointing downward.

    Useful for determining tilt direction conventions.

    Args:
        mounting: Mounting preset name
        yaw, pitch, roll: Fixture orientation angles (degrees)

    Returns:
        True if beam Z component is negative (pointing down in world space)
    """
    beam_dir = get_beam_direction(mounting, yaw, pitch, roll)
    return beam_dir[2] < 0


def get_direction_for_tilt_calculation(mounting: str) -> str:
    """
    Get the legacy direction value ('UP' or 'DOWN') for tilt calculations.

    This is used for backwards compatibility with existing effect code
    that uses 'UP'/'DOWN' direction values.

    Args:
        mounting: Mounting preset name

    Returns:
        'UP' or 'DOWN' based on mounting preset
    """
    # Standing fixtures point up, everything else points down
    if mounting == 'standing':
        return 'UP'
    return 'DOWN'
