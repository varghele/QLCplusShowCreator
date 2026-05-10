"""Chassis geometry registry for the composable fixture renderer (Phase B).

One :class:`ChassisGeometry` per :class:`utils.fixture_capabilities.Chassis`
value. Each owns a body mesh + GL resources and exposes ``render(mvp, model)``.

Phase B uses simple primitives (boxes, cylinders) for all nine chassis values.
Phase D / Phase E can refine MOVING_YOKE into a compound base+yoke+head mesh,
add a scanner mirror, etc., without changing the component/emitter contracts.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

import glm
import moderngl
import numpy as np

from utils.fixture_capabilities import Chassis
from utils.geometry import GeometryBuilder
from visualizer.renderer.shaders import (
    FIXTURE_FRAGMENT_SHADER,
    FIXTURE_VERTEX_SHADER,
)


def _mat4_bytes(m: glm.mat4) -> bytes:
    return np.array([x for col in m.to_list() for x in col], dtype='f4').tobytes()


# Body color presets — keep the look consistent with existing renderers.
DARK_METAL = (0.15, 0.15, 0.18)
LIGHT_METAL = (0.25, 0.25, 0.28)
PLACEHOLDER = (0.35, 0.30, 0.30)  # OTHER chassis — slightly warm-grey to flag "unknown"


# A mesh builder takes (width, height, depth) in meters and returns
# (vertices, normals) as flat numpy float32 arrays of triangle data.
MeshBuilder = Callable[[float, float, float], Tuple[np.ndarray, np.ndarray]]


def _build_par(width: float, height: float, depth: float):
    """Stubby cylinder — short and wide. PAR can / wash can."""
    radius = max(width, height) / 2.0
    verts, norms = GeometryBuilder.create_cylinder(radius=radius, height=depth, segments=24)
    return verts, norms


def _build_bar(width: float, height: float, depth: float):
    """Long thin box. LED bar / sunstrip / pixel bar."""
    return GeometryBuilder.create_box(width, height, depth)


def _build_panel(width: float, height: float, depth: float):
    """Flat box — wide+tall, shallow. LED matrix / video panel."""
    return GeometryBuilder.create_box(width, height, max(depth, 0.05))


def _build_moving_yoke(width: float, height: float, depth: float):
    """Box (Phase B placeholder).

    The existing MovingHeadRenderer renders a compound base+yoke+head;
    that compound will move into Phase D once the chassis abstraction is
    proven. For now, a single box keeps the renderer composable.
    """
    return GeometryBuilder.create_box(width, height, depth)


def _build_scanner(width: float, height: float, depth: float):
    """Box for v2 — scanner mirror geometry is deferred."""
    return GeometryBuilder.create_box(width, height, depth)


def _build_effect(width: float, height: float, depth: float):
    """Box for v2 — effect / centipede / flower geometry is deferred."""
    return GeometryBuilder.create_box(width, height, depth)


def _build_particle(width: float, height: float, depth: float):
    """Box for v2 — particle plume geometry is deferred."""
    return GeometryBuilder.create_box(width, height, depth)


def _build_laser(width: float, height: float, depth: float):
    """Box for v2 — laser projector geometry is deferred."""
    return GeometryBuilder.create_box(width, height, depth)


def _build_other(width: float, height: float, depth: float):
    """Placeholder box for unknown / dimmer-pack / fan fixtures."""
    return GeometryBuilder.create_box(width, height, depth)


# Public registry — keep in lock-step with the Chassis enum.
_BUILDERS: Dict[Chassis, MeshBuilder] = {
    Chassis.PAR: _build_par,
    Chassis.BAR: _build_bar,
    Chassis.PANEL: _build_panel,
    Chassis.MOVING_YOKE: _build_moving_yoke,
    Chassis.SCANNER: _build_scanner,
    Chassis.EFFECT: _build_effect,
    Chassis.PARTICLE: _build_particle,
    Chassis.LASER: _build_laser,
    Chassis.OTHER: _build_other,
}


_BODY_COLORS: Dict[Chassis, Tuple[float, float, float]] = {
    Chassis.PAR: DARK_METAL,
    Chassis.BAR: DARK_METAL,
    Chassis.PANEL: DARK_METAL,
    Chassis.MOVING_YOKE: DARK_METAL,
    Chassis.SCANNER: DARK_METAL,
    Chassis.EFFECT: DARK_METAL,
    Chassis.PARTICLE: LIGHT_METAL,
    Chassis.LASER: LIGHT_METAL,
    Chassis.OTHER: PLACEHOLDER,
}


def get_body_color(chassis: Chassis) -> Tuple[float, float, float]:
    return _BODY_COLORS.get(chassis, DARK_METAL)


def build_chassis_mesh(
    chassis: Chassis,
    body_dims_m: Tuple[float, float, float],
) -> Tuple[np.ndarray, np.ndarray]:
    """Build the body mesh for a chassis value (no GL — pure numpy)."""
    builder = _BUILDERS.get(chassis, _build_other)
    return builder(*body_dims_m)


# ---------------------------------------------------------------------------
# GL wrapper
# ---------------------------------------------------------------------------


class ChassisGeometry:
    """Wraps a chassis mesh + GL program/VAO/VBO into a renderable unit."""

    def __init__(
        self,
        ctx: moderngl.Context,
        chassis: Chassis,
        body_dims_m: Tuple[float, float, float],
    ):
        self.ctx = ctx
        self.chassis = chassis
        self.body_dims_m = body_dims_m

        verts, norms = build_chassis_mesh(chassis, body_dims_m)
        self._vertex_count = len(verts) // 3

        self.program: moderngl.Program = ctx.program(
            vertex_shader=FIXTURE_VERTEX_SHADER,
            fragment_shader=FIXTURE_FRAGMENT_SHADER,
        )
        self.vbo = ctx.buffer(verts.tobytes())
        self.nbo = ctx.buffer(norms.tobytes())
        self.vao = ctx.vertex_array(
            self.program,
            [
                (self.vbo, '3f', 'in_position'),
                (self.nbo, '3f', 'in_normal'),
            ],
        )

    def render(
        self,
        mvp: glm.mat4,
        model: glm.mat4,
        emissive_color: Optional[Tuple[float, float, float]] = None,
        emissive_strength: float = 0.0,
    ) -> None:
        """Render the chassis body.

        Args:
            mvp: full model-view-projection matrix.
            model: fixture model matrix (passed separately so the body
                shader can transform normals to world space).
            emissive_color: optional emissive RGB (e.g. a tinted halo around the lens).
            emissive_strength: 0..1 emissive multiplier.
        """
        self.program['mvp'].write(_mat4_bytes(mvp * model))
        self.program['model'].write(_mat4_bytes(model))
        self.program['base_color'].value = get_body_color(self.chassis)
        self.program['emissive_color'].value = emissive_color or (0.0, 0.0, 0.0)
        self.program['emissive_strength'].value = float(emissive_strength)
        self.vao.render(moderngl.TRIANGLES)

    def release(self) -> None:
        if self.vao:
            self.vao.release()
        if self.vbo:
            self.vbo.release()
        if self.nbo:
            self.nbo.release()
        if self.program:
            self.program.release()
