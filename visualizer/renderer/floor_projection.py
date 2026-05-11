"""Floor projection component for the composable fixture renderer (Phase D Stage 2).

Renders a gobo-pattern + focus-blur ellipse where a moving-head beam hits the
floor (Y=0 in world). Mirrors :meth:`MovingHeadRenderer._render_floor_projection`.

The intersection math is split out as a pure function (:func:`compute_floor_intersection`)
so it can be unit-tested without an OpenGL context.

Phase D Stage 4 (visual tuning) may revisit lens-position / beam-direction
computation to match legacy output exactly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import glm
import moderngl
import numpy as np

from utils.geometry import GeometryBuilder
from visualizer.renderer.shaders import (
    FLOOR_PROJECTION_VERTEX_SHADER,
    GOBO_FLOOR_PROJECTION_FRAGMENT_SHADER,
)


DEFAULT_BEAM_LENGTH_M = 5.0


@dataclass
class FloorIntersection:
    """Result of projecting a beam onto the Y=0 floor plane.

    All values are in world coordinates (Y-up). ``rotation_angle_deg``
    aligns the ellipse's major axis with the beam's XZ-plane projection.
    """
    hit_pos: glm.vec3       # world position of the spot center
    major_radius: float     # along beam direction (stretched at shallow angles)
    minor_radius: float     # perpendicular to beam direction
    rotation_angle_deg: float


def compute_floor_intersection(
    lens_world_pos: glm.vec3,
    beam_dir_world: glm.vec3,
    beam_angle_deg: float,
    beam_length_m: float = DEFAULT_BEAM_LENGTH_M,
) -> Optional[FloorIntersection]:
    """Project a beam onto Y=0 and return the resulting ellipse.

    Returns ``None`` if the beam doesn't point downward, hits the floor
    behind the lens, or hits past the maximum beam length.
    """
    # Beam must point down (negative Y in world Y-up).
    if beam_dir_world.y >= 0:
        return None

    # Ray-plane intersection with Y=0.
    t = -lens_world_pos.y / beam_dir_world.y
    if t <= 0 or t > beam_length_m:
        return None

    hit_pos = lens_world_pos + beam_dir_world * t

    # Beam radius at intersection distance (half-angle of the cone).
    beam_radius = t * math.tan(math.radians(beam_angle_deg / 2.0))

    # Ellipse from oblique incidence: minor axis = beam radius, major axis
    # = beam_radius / cos(angle from vertical), capped at 5× to avoid
    # extreme stretching at shallow angles.
    cos_angle = abs(beam_dir_world.y)
    minor_radius = beam_radius
    major_radius = min(beam_radius / max(cos_angle, 0.1), beam_radius * 5.0)

    # Major axis aligns with the beam's XZ-plane direction.
    beam_xz = glm.vec2(beam_dir_world.x, beam_dir_world.z)
    if glm.length(beam_xz) > 0.01:
        beam_xz = glm.normalize(beam_xz)
        rotation_angle_deg = math.degrees(math.atan2(beam_xz.x, beam_xz.y))
    else:
        rotation_angle_deg = 0.0

    return FloorIntersection(
        hit_pos=hit_pos,
        major_radius=major_radius,
        minor_radius=minor_radius,
        rotation_angle_deg=rotation_angle_deg,
    )


def compute_distance_falloff(
    lens_world_pos: glm.vec3,
    beam_dir_world: glm.vec3,
    beam_length_m: float = DEFAULT_BEAM_LENGTH_M,
) -> float:
    """Distance-based intensity falloff for the floor projection.

    Mirrors the legacy formula: at the lens, falloff=1.0; at the max beam
    length, ~0.7; never below 0.5. Used as a uniform on the projection
    fragment shader to attenuate spotlight brightness with distance.
    """
    if beam_dir_world.y < 0:
        distance = abs(lens_world_pos.y / beam_dir_world.y)
    else:
        distance = beam_length_m
    return max(1.0 - (distance / beam_length_m) * 0.3, 0.5)


def _mat4_bytes(m: glm.mat4) -> bytes:
    return np.array([x for col in m.to_list() for x in col], dtype='f4').tobytes()


class FloorProjectionComponent:
    """Renders a gobo+focus-modulated ellipse on the floor under a moving head.

    Owns one program (gobo floor projection fragment shader) + one floor
    disk VAO. Caller invokes :meth:`render` once per facet (so prism
    fixtures call it N times with different ``beam_dir_world`` per facet).
    """

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.program: moderngl.Program = ctx.program(
            vertex_shader=FLOOR_PROJECTION_VERTEX_SHADER,
            fragment_shader=GOBO_FLOOR_PROJECTION_FRAGMENT_SHADER,
        )
        verts, uvs = GeometryBuilder.create_floor_projection_disk(segments=32)
        self.vbo = ctx.buffer(verts.tobytes())
        self.ubo = ctx.buffer(uvs.tobytes())
        self.vao = ctx.vertex_array(
            self.program,
            [
                (self.vbo, '3f', 'in_position'),
                (self.ubo, '2f', 'in_uv'),
            ],
        )

    def render(
        self,
        mvp: glm.mat4,
        *,
        lens_world_pos: glm.vec3,
        beam_dir_world: glm.vec3,
        beam_angle_deg: float,
        color: Tuple[float, float, float],
        dimmer: float,
        beam_length_m: float = DEFAULT_BEAM_LENGTH_M,
        gobo_pattern: int = 0,
        gobo_rotation_rad: float = 0.0,
        focus_sharpness: float = 1.0,
        brightness_scale: float = 1.0,
        intensity_scale: float = 1.0,
    ) -> None:
        """Render the floor projection. No-op if the beam doesn't hit the floor."""
        if dimmer < 0.01:
            return

        intersection = compute_floor_intersection(
            lens_world_pos=lens_world_pos,
            beam_dir_world=beam_dir_world,
            beam_angle_deg=beam_angle_deg,
            beam_length_m=beam_length_m,
        )
        if intersection is None:
            return

        falloff = compute_distance_falloff(
            lens_world_pos, beam_dir_world, beam_length_m,
        )

        # Build the ellipse model matrix:
        # - translate to hit position (slightly above floor to avoid z-fighting)
        # - rotate around Y so major axis aligns with the beam's XZ direction
        # - scale to (major_radius, 1, minor_radius)
        proj_model = glm.mat4(1.0)
        proj_model = glm.translate(
            proj_model,
            glm.vec3(intersection.hit_pos.x, 0.03, intersection.hit_pos.z),
        )
        proj_model = glm.rotate(
            proj_model,
            glm.radians(intersection.rotation_angle_deg),
            glm.vec3(0, 1, 0),
        )
        proj_model = glm.scale(
            proj_model,
            glm.vec3(intersection.major_radius, 1.0, intersection.minor_radius),
        )

        # Additive blend with depth TEST on but depth WRITE off: the
        # projection plane sits just above the stage floor (y=0.03), so
        # depth-test still lets it draw over the stage; meanwhile any
        # fixture chassis already drawn at the same screen pixels (which
        # is closer to the camera than the floor plane) correctly occludes
        # the projection. Without the depth-test the projection drew over
        # floor PARs that happened to sit under a moving head's spot.
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE)
        self.ctx.depth_mask = False

        try:
            self.program['mvp'].write(_mat4_bytes(mvp * proj_model))
            self.program['projection_color'].value = color
            self.program['projection_intensity'].value = (
                dimmer * brightness_scale * intensity_scale
            )
            self.program['distance_falloff'].value = falloff
            self.program['gobo_pattern'].value = gobo_pattern
            self.program['gobo_rotation'].value = gobo_rotation_rad
            self.program['focus_sharpness'].value = focus_sharpness
            self.vao.render(moderngl.TRIANGLES)
        finally:
            self.ctx.depth_mask = True
            self.ctx.disable(moderngl.BLEND)

    def release(self) -> None:
        if self.vao:
            self.vao.release()
        if self.vbo:
            self.vbo.release()
        if self.ubo:
            self.ubo.release()
        if self.program:
            self.program.release()
