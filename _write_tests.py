import os

base_dir = r"C:\Users\varghele\PycharmProjects\QLCplusShowCreator\tests\unit"

# File 1: test_orientation.py
with open(os.path.join(base_dir, "test_orientation.py"), "w", encoding="utf-8") as f:
    f.write('''# tests/unit/test_orientation.py
"""Unit tests for utils/orientation.py - rotation matrices, pan/tilt, beam direction."""

import math
import pytest
import numpy as np
from numpy.testing import assert_allclose

from utils.orientation import (
    get_rotation_matrix,
    calculate_pan_tilt,
    pan_tilt_to_dmx,
    get_beam_direction,
    MOUNTING_BASE_ROTATIONS,
)

class TestGetRotationMatrix:
    """Tests for get_rotation_matrix."""

    def test_wall_back_zero_angles_is_identity(self):
        R = get_rotation_matrix("wall_back", yaw=0, pitch=0, roll=0)
        assert R.shape == (3, 3)
        assert_allclose(R, np.eye(3), atol=1e-12)

    def test_result_shape_is_3x3(self):
        R = get_rotation_matrix("hanging", yaw=0, pitch=0, roll=0)
        assert R.shape == (3, 3)
''')
print("Written test_orientation.py (partial test)")