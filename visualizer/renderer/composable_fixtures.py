"""Composable FixtureRenderer (Phase B).

Composes :class:`utils.fixture_capabilities.FixtureCapabilities` into a
:class:`ChassisGeometry` + a list of :class:`FixtureComponent`s + a
:class:`BeamComponent` + an :class:`EmitterRunner`.

The renderer is not yet wired into ``FixtureManager`` — Phase D does
that. Phase B's job is just to make sure the composition produces a
correct, callable renderer for every supported fixture archetype.

Layout (rendered per frame in ``render(mvp)``):

1. ``get_model_matrix()`` — chassis position + yaw/pitch/roll
2. ``chassis.render(mvp, model)`` — body mesh
3. ``emitter_runner.emissions()`` → list of :class:`Emission`s
4. for each emission: ``beam.render_emission(mvp, model, emission, modifiers)``
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import glm
import moderngl

from utils.fixture_capabilities import (
    CellArray,
    Chassis,
    FixtureCapabilities,
    MultiHead,
    PointEmitter,
)
from visualizer.renderer.beams import (
    BeamComponent,
    BeamModifiers,
    ConeBeam,
    CylindricalBeam,
    GlowBeam,
    RectangularBeam,
    SegmentedBeam,
)
from visualizer.renderer.chassis import (
    ChassisGeometry,
    ChassisRenderState,
    make_chassis_geometry,
)
from visualizer.renderer.components import (
    ColorComponent,
    DimmerComponent,
    FixtureComponent,
    FocusComponent,
    FrostComponent,
    GoboComponent,
    IrisComponent,
    MovementComponent,
    PrismComponent,
    StrobeComponent,
    ZoomComponent,
)
from visualizer.renderer.emitters import EmitterRunner, create_emitter_runner


# ---------------------------------------------------------------------------
# Beam selection
# ---------------------------------------------------------------------------


def _select_beam(
    ctx: moderngl.Context,
    capabilities: FixtureCapabilities,
) -> BeamComponent:
    """Pick the right BeamComponent variant for a fixture's capabilities.

    Decision tree (see FIXTURE_TAXONOMY.md §6 for context):
    - MultiHead emitter → ConeBeam (one cone per head in the emission loop)
    - Movement present (single moving head) → ConeBeam
    - Chassis BAR/PANEL with cells → SegmentedBeam
    - Chassis BAR/PANEL without cells, no optics → RectangularBeam (wash bar)
    - Chassis PAR with optics → CylindricalBeam
    - Otherwise → GlowBeam (cheap fallback)
    """
    chassis = capabilities.chassis
    emitter = capabilities.emitter
    has_movement = capabilities.movement is not None
    has_optics = capabilities.beam.has_optics
    has_cells = isinstance(emitter, CellArray)

    if isinstance(emitter, MultiHead) or has_movement:
        # Tune cone to fixture's lens range; fall back to a sensible default.
        cone_angle = capabilities.beam.max_deg if has_optics else 15.0
        return ConeBeam(ctx, cone_angle_deg=cone_angle)

    if has_cells and chassis in (Chassis.BAR, Chassis.PANEL):
        return SegmentedBeam(ctx)

    if chassis in (Chassis.BAR, Chassis.PANEL) and not has_optics:
        # Wash bar / video panel — wide rectangular volume.
        w = capabilities.body_dims_m[0] * 0.6
        h = max(capabilities.body_dims_m[1] * 0.6, 0.3)
        return RectangularBeam(ctx, width_m=w, height_m=h)

    if chassis is Chassis.PAR and has_optics:
        return CylindricalBeam(ctx)

    return GlowBeam(ctx)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class FixtureRenderer:
    """Composable per-fixture renderer.

    Built from a :class:`FixtureCapabilities` plus runtime placement
    (position, orientation, universe/address) from ``fixture_data``.
    Owns its chassis mesh, beam GL resources, and a list of components
    that consume DMX.
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        fixture_data: Dict[str, Any],
        capabilities: FixtureCapabilities,
    ):
        self.ctx = ctx
        self.capabilities = capabilities

        # --- placement / identity (same fields as legacy FixtureRenderer) ---
        self.name = fixture_data.get('name', 'Unknown')
        self.position = fixture_data.get('position', {'x': 0.0, 'y': 0.0, 'z': 0.0})

        orientation = fixture_data.get('orientation', {})
        self.mounting = orientation.get('mounting', 'hanging')
        self.yaw = orientation.get('yaw', 0.0)
        self.pitch = orientation.get('pitch', 0.0)
        self.roll = orientation.get('roll', 0.0)

        self.universe = fixture_data.get('universe', 1)
        self.address = fixture_data.get('address', 1)
        self.brightness_scale = 1.0

        # --- chassis geometry ---
        self.chassis_geom: ChassisGeometry = make_chassis_geometry(
            ctx, capabilities.chassis, capabilities.body_dims_m
        )

        # --- state-only components (built only when the capability exists) ---
        self.movement: Optional[MovementComponent] = (
            MovementComponent(capabilities.movement) if capabilities.movement else None
        )
        self.color: Optional[ColorComponent] = (
            ColorComponent(mixing=capabilities.color_mixing, wheel=capabilities.color_wheel)
            if (capabilities.color_mixing or capabilities.color_wheel)
            else None
        )
        self.dimmer: Optional[DimmerComponent] = (
            DimmerComponent(capabilities.dimmer_channel)
            if capabilities.dimmer_channel is not None
            else None
        )
        self.strobe: Optional[StrobeComponent] = (
            StrobeComponent(capabilities.strobe_channel)
            if capabilities.strobe_channel is not None
            else None
        )
        self.gobo: Optional[GoboComponent] = (
            GoboComponent(capabilities.gobo_wheel) if capabilities.gobo_wheel else None
        )
        self.prism: Optional[PrismComponent] = (
            PrismComponent(capabilities.prism) if capabilities.prism else None
        )
        self.focus: Optional[FocusComponent] = (
            FocusComponent(capabilities.focus_channel)
            if capabilities.focus_channel is not None
            else None
        )
        self.iris: Optional[IrisComponent] = (
            IrisComponent(capabilities.iris_channel)
            if capabilities.iris_channel is not None
            else None
        )
        self.frost: Optional[FrostComponent] = (
            FrostComponent(capabilities.frost_channel)
            if capabilities.frost_channel is not None
            else None
        )
        self.zoom: Optional[ZoomComponent] = (
            ZoomComponent(capabilities.zoom_channel, capabilities.beam)
            if capabilities.zoom_channel is not None
            else None
        )

        # --- emitter runner ---
        self.emitter_runner: EmitterRunner = create_emitter_runner(
            capabilities.emitter,
            body_dims_m=capabilities.body_dims_m,
            chassis_movement=self.movement,
        )

        # --- beam ---
        self.beam: BeamComponent = _select_beam(ctx, capabilities)

    # --- public API ---

    @property
    def components(self) -> List[FixtureComponent]:
        """Ordered list of non-None components. Useful for batch DMX updates / introspection."""
        result: List[FixtureComponent] = []
        for c in (
            self.movement,
            self.color,
            self.dimmer,
            self.strobe,
            self.gobo,
            self.prism,
            self.focus,
            self.iris,
            self.frost,
            self.zoom,
        ):
            if c is not None:
                result.append(c)
        result.append(self.emitter_runner)
        return result

    def get_model_matrix(self) -> glm.mat4:
        """Chassis model matrix from position + yaw/pitch/roll.

        Uses the same convention as the legacy renderer: stage X→3D X,
        stage Y→3D Z, stage Z (height)→3D Y. Rotation order YXZ.
        """
        m = glm.mat4(1.0)
        p = self.position
        m = glm.translate(m, glm.vec3(p['x'], p['z'], p['y']))
        m = glm.rotate(m, glm.radians(self.yaw), glm.vec3(0, 1, 0))
        m = glm.rotate(m, glm.radians(self.pitch), glm.vec3(1, 0, 0))
        m = glm.rotate(m, glm.radians(self.roll), glm.vec3(0, 0, 1))
        return m

    def update_dmx(self, dmx_data: bytes) -> None:
        """Fan-out the DMX universe buffer to every component."""
        for c in self.components:
            c.update_dmx(dmx_data, self.address)

    def render(self, mvp: glm.mat4) -> None:
        model = self.get_model_matrix()

        # 1. Body chassis. Pass pan/tilt so an animated chassis (moving yoke)
        #    can rotate its yoke + head; static chassis ignore both. Lens
        #    emissive follows beam color × dimmer for moving heads.
        chassis_state = self._build_chassis_state()
        self.chassis_geom.render(mvp, model, chassis_state)

        # 2. Build modifier bundle once per frame; beam variants ignore unused fields.
        modifiers = self._build_modifiers()

        # 3. Iterate emissions × beam.
        for emission in self.emitter_runner.emissions(self.color, self.dimmer):
            self.beam.render_emission(mvp, model, emission, modifiers)

    def release(self) -> None:
        self.chassis_geom.release()
        self.beam.release()

    # --- internal ---

    def _build_chassis_state(self) -> ChassisRenderState:
        """Build per-frame chassis inputs: pan/tilt for animated chassis,
        emissive for the lens (color × dimmer)."""
        pan = self.movement.pan_deg if self.movement is not None else 0.0
        tilt = self.movement.tilt_deg if self.movement is not None else 0.0

        if self.color is not None and self.dimmer is not None:
            d = self.dimmer.normalized
            r, g, b = self.color.rgb
            emissive = (r * d, g * d, b * d)
            strength = self.brightness_scale
        elif self.color is not None:
            emissive = self.color.rgb
            strength = self.brightness_scale
        else:
            emissive = (0.0, 0.0, 0.0)
            strength = 0.0

        return ChassisRenderState(
            pan_deg=pan,
            tilt_deg=tilt,
            emissive_color=emissive,
            emissive_strength=strength,
        )

    def _build_modifiers(self) -> BeamModifiers:
        """Bundle component state into the modifier struct passed to the beam.

        Focus sharpness uses the fixture's mounting height (Z position)
        as a rough projection distance — the legacy MovingHeadRenderer
        does the same as a fallback when the floor intersection isn't
        computed.
        """
        if self.focus is not None:
            projection_dist = max(0.5, float(self.position.get('z', 3.0)))
            focus_sharpness = self.focus.sharpness(projection_dist)
        else:
            focus_sharpness = 1.0

        return BeamModifiers(
            brightness_scale=self.brightness_scale,
            gobo_pattern=self.gobo.pattern_id if self.gobo is not None else 0,
            gobo_rotation_rad=self.gobo.rotation_rad if self.gobo is not None else 0.0,
            focus_sharpness=focus_sharpness,
            iris_opening=self.iris.opening if self.iris is not None else 1.0,
            frost=self.frost.diffusion if self.frost is not None else 0.0,
            zoom_angle_deg=(self.zoom.current_angle_deg if self.zoom is not None else None),
            prism_active=self.prism.is_active if self.prism is not None else False,
            prism_facets=self.prism.facets if self.prism is not None else 3,
        )
