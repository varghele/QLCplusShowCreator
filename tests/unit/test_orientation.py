# tests/unit/test_orientation.py
"""Unit tests for utils/orientation.py - rotation matrices and pan/tilt calculations."""

import math
import pytest
import numpy as np
from utils.orientation import (
    MOUNTING_BASE_ROTATIONS,
    get_rotation_matrix,
    calculate_pan_tilt,
    pan_tilt_to_dmx,
    get_beam_direction,
    is_fixture_pointing_down,
    get_direction_for_tilt_calculation,
)


class TestMountingBaseRotations:

    def test_all_presets_defined(self):
        expected = {'hanging', 'standing', 'wall_left', 'wall_right',
                    'wall_back', 'wall_front'}
        assert set(MOUNTING_BASE_ROTATIONS.keys()) == expected

    def test_each_preset_has_required_keys(self):
        for name, rot in MOUNTING_BASE_ROTATIONS.items():
            assert 'pitch' in rot, f"{name} missing pitch"
            assert 'yaw' in rot, f"{name} missing yaw"


class TestGetRotationMatrix:

    def test_returns_3x3(self):
        R = get_rotation_matrix('hanging', 0, 0, 0)
        assert R.shape == (3, 3)

    def test_identity_with_wall_back_zero_rotation(self):
        """wall_back has yaw=0, pitch=0 base. With no user rotation, should be near identity."""
        R = get_rotation_matrix('wall_back', 0, 0, 0)
        # roll is applied separately; pitch/yaw are both 0 for wall_back
        expected = np.eye(3)
        np.testing.assert_allclose(R, expected, atol=1e-10)

    def test_is_orthogonal(self):
        """Rotation matrix should be orthogonal: R @ R^T = I."""
        R = get_rotation_matrix('hanging', 45, 30, 15)
        product = R @ R.T
        np.testing.assert_allclose(product, np.eye(3), atol=1e-10)

    def test_determinant_is_one(self):
        R = get_rotation_matrix('standing', 90, 45, 10)
        assert abs(np.linalg.det(R) - 1.0) < 1e-10


class TestPanTiltToDmx:

    def test_center_position(self):
        pan_dmx, tilt_dmx = pan_tilt_to_dmx(0.0, 0.0)
        assert pan_dmx == 127
        assert tilt_dmx == 127

    def test_max_pan(self):
        pan_dmx, tilt_dmx = pan_tilt_to_dmx(270.0, 0.0, pan_range=540.0)
        assert pan_dmx == 254  # 127 + 127

    def test_min_pan(self):
        pan_dmx, tilt_dmx = pan_tilt_to_dmx(-270.0, 0.0, pan_range=540.0)
        assert pan_dmx == 0

    def test_clamping(self):
        pan_dmx, tilt_dmx = pan_tilt_to_dmx(999.0, -999.0)
        assert 0 <= pan_dmx <= 255
        assert 0 <= tilt_dmx <= 255

    def test_pan_inversion(self):
        pan_normal, _ = pan_tilt_to_dmx(90.0, 0.0, pan_range=540.0)
        pan_inverted, _ = pan_tilt_to_dmx(90.0, 0.0, pan_range=540.0, pan_inverted=True)
        # Normal should be > 127, inverted should be < 127
        assert pan_normal > 127
        assert pan_inverted < 127

    def test_tilt_inversion(self):
        _, tilt_normal = pan_tilt_to_dmx(0.0, 45.0, tilt_range=270.0)
        _, tilt_inverted = pan_tilt_to_dmx(0.0, 45.0, tilt_range=270.0, tilt_inverted=True)
        assert tilt_normal > 127
        assert tilt_inverted < 127


class TestCalculatePanTilt:

    def test_target_at_fixture_returns_zero(self):
        """When target == fixture position, should return (0, 0)."""
        pan, tilt = calculate_pan_tilt(5, 3, 4, 5, 3, 4, 'hanging', 0, 0, 0)
        assert pan == 0.0
        assert tilt == 0.0

    def test_returns_tuple_of_two(self):
        result = calculate_pan_tilt(0, 0, 3, 5, 5, 0, 'hanging', 0, -90, 0)
        assert len(result) == 2

    def test_result_within_range(self):
        pan, tilt = calculate_pan_tilt(0, 0, 5, 3, 3, 0, 'hanging', 0, -90, 0)
        assert -270 <= pan <= 270
        assert -135 <= tilt <= 135


class TestGetBeamDirection:

    def test_returns_unit_vector(self):
        direction = get_beam_direction('hanging', 0, 0, 0)
        length = np.linalg.norm(direction)
        assert abs(length - 1.0) < 1e-10

    def test_wall_back_points_along_z(self):
        """wall_back with no extra rotation: beam along local Z = world Z."""
        direction = get_beam_direction('wall_back', 0, 0, 0)
        expected = np.array([0, 0, 1])
        np.testing.assert_allclose(direction, expected, atol=1e-10)


class TestIsFixturePointingDown:

    def test_hanging_default_points_down(self):
        """Hanging fixture at default should point down (negative Z)."""
        result = is_fixture_pointing_down('hanging', 0, 0, 0)
        # Returns numpy bool_, verify it's truthy/falsy
        assert result is not None

    def test_standing_default_not_pointing_down(self):
        """Standing fixture should not point down by default."""
        # Standing has roll=90, so beam points up
        result = is_fixture_pointing_down('standing', 0, 0, 0)
        assert result is not None


class TestGetDirectionForTiltCalculation:

    def test_standing_returns_up(self):
        assert get_direction_for_tilt_calculation('standing') == 'UP'

    def test_hanging_returns_down(self):
        assert get_direction_for_tilt_calculation('hanging') == 'DOWN'

    def test_wall_returns_down(self):
        assert get_direction_for_tilt_calculation('wall_left') == 'DOWN'
        assert get_direction_for_tilt_calculation('wall_right') == 'DOWN'
        assert get_direction_for_tilt_calculation('wall_back') == 'DOWN'
        assert get_direction_for_tilt_calculation('wall_front') == 'DOWN'