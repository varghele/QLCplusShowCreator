# visualizer/renderer/camera.py
# Orbit camera for 3D stage visualization

import math
import glm


class OrbitCamera:
    """
    Orbiting camera that rotates around a target point.

    Controls:
    - Left mouse drag: Orbit (rotate around target)
    - Right mouse drag: Pan (move target point)
    - Scroll wheel: Zoom (change distance to target)
    - Home key: Reset to default view
    """

    def __init__(self):
        # Target point (center of stage)
        self.target = glm.vec3(0.0, 0.0, 0.0)

        # Spherical coordinates relative to target
        self.distance = 15.0  # Distance from target
        self.azimuth = 45.0   # Horizontal angle (degrees)
        self.elevation = 30.0  # Vertical angle (degrees)

        # Limits
        self.min_distance = 2.0
        self.max_distance = 100.0
        self.min_elevation = 5.0
        self.max_elevation = 89.0

        # Sensitivity
        self.orbit_sensitivity = 0.3
        self.pan_sensitivity = 0.01
        self.zoom_sensitivity = 0.1

        # Projection parameters
        self.fov = 45.0  # Field of view (degrees)
        self.aspect = 16.0 / 9.0
        self.near = 0.1
        self.far = 500.0

        # Default values for reset
        self._default_target = glm.vec3(0.0, 0.0, 0.0)
        self._default_distance = 15.0
        self._default_azimuth = 45.0
        self._default_elevation = 30.0

    def reset(self):
        """Reset camera to default position."""
        self.target = glm.vec3(self._default_target)
        self.distance = self._default_distance
        self.azimuth = self._default_azimuth
        self.elevation = self._default_elevation

    def set_stage_size(self, width: float, depth: float):
        """
        Adjust camera to fit stage.

        Args:
            width: Stage width in meters
            depth: Stage depth in meters
        """
        # Center target on stage
        self.target = glm.vec3(0.0, 0.0, 0.0)
        self._default_target = glm.vec3(0.0, 0.0, 0.0)

        # Adjust distance to see entire stage
        max_dim = max(width, depth)
        self.distance = max_dim * 1.5
        self._default_distance = self.distance

    def orbit(self, delta_x: float, delta_y: float):
        """
        Rotate camera around target.

        Args:
            delta_x: Horizontal mouse movement
            delta_y: Vertical mouse movement
        """
        self.azimuth -= delta_x * self.orbit_sensitivity
        self.elevation += delta_y * self.orbit_sensitivity

        # Wrap azimuth
        self.azimuth = self.azimuth % 360.0

        # Clamp elevation
        self.elevation = max(self.min_elevation, min(self.max_elevation, self.elevation))

    def pan(self, delta_x: float, delta_y: float):
        """
        Move target point (pan camera).

        Args:
            delta_x: Horizontal mouse movement
            delta_y: Vertical mouse movement
        """
        # Get camera right and up vectors
        right = self._get_right_vector()
        up = glm.vec3(0.0, 1.0, 0.0)  # World up for horizontal panning

        # Calculate pan amount based on distance
        pan_scale = self.distance * self.pan_sensitivity

        # Apply pan
        self.target += right * (-delta_x * pan_scale)
        self.target += up * (delta_y * pan_scale)

    def zoom(self, delta: float):
        """
        Zoom camera (change distance to target).

        Args:
            delta: Scroll wheel delta (positive = zoom in)
        """
        zoom_factor = 1.0 - delta * self.zoom_sensitivity
        self.distance *= zoom_factor
        self.distance = max(self.min_distance, min(self.max_distance, self.distance))

    def set_aspect(self, aspect: float):
        """Set aspect ratio for projection matrix."""
        self.aspect = aspect

    def get_position(self) -> glm.vec3:
        """Get camera position in world space."""
        # Convert spherical to Cartesian
        azimuth_rad = math.radians(self.azimuth)
        elevation_rad = math.radians(self.elevation)

        x = self.distance * math.cos(elevation_rad) * math.sin(azimuth_rad)
        y = self.distance * math.sin(elevation_rad)
        z = self.distance * math.cos(elevation_rad) * math.cos(azimuth_rad)

        return self.target + glm.vec3(x, y, z)

    def get_view_matrix(self) -> glm.mat4:
        """Get view matrix for rendering."""
        position = self.get_position()
        return glm.lookAt(position, self.target, glm.vec3(0.0, 1.0, 0.0))

    def get_projection_matrix(self) -> glm.mat4:
        """Get projection matrix for rendering."""
        return glm.perspective(
            glm.radians(self.fov),
            self.aspect,
            self.near,
            self.far
        )

    def get_view_projection_matrix(self) -> glm.mat4:
        """Get combined view-projection matrix."""
        return self.get_projection_matrix() * self.get_view_matrix()

    def _get_right_vector(self) -> glm.vec3:
        """Get camera right vector for panning."""
        azimuth_rad = math.radians(self.azimuth)
        return glm.vec3(
            math.cos(azimuth_rad),
            0.0,
            -math.sin(azimuth_rad)
        )

    def _get_forward_vector(self) -> glm.vec3:
        """Get camera forward vector."""
        azimuth_rad = math.radians(self.azimuth)
        elevation_rad = math.radians(self.elevation)

        return glm.vec3(
            -math.cos(elevation_rad) * math.sin(azimuth_rad),
            -math.sin(elevation_rad),
            -math.cos(elevation_rad) * math.cos(azimuth_rad)
        )
