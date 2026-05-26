"""HDR offscreen pipeline + tonemap pass.

The visualizer's beam blending is additive (``SRC_ALPHA, ONE``), which
gives a bright beam over a fixture chassis an LDR output value
greater than 1.0 — the framebuffer then clamps to white and the
fixture appears to "vanish". Two beams crossing in space both clip
the same way, so the intersection looks identical to either beam
alone instead of brighter.

This module renders the scene to an RGBA16F framebuffer (so values
can exceed 1.0 without clipping), then runs a fullscreen tonemap
pass that copies the result into the Qt LDR framebuffer with a soft
knee: pixels at or below ``knee`` (default 0.8) pass through
unchanged, brighter pixels are smoothly compressed toward 1.0. The
net effect: chassis brightness is preserved, beam intersections
genuinely brighten without saturating to flat white.

Used only by :class:`visualizer.renderer.engine.RenderEngine`. The
parity tests in ``tests/visual/test_fixture_renderer_parity.py``
drive a ``FixtureManager`` directly against their own LDR FBO, so
they're unaffected.
"""

from __future__ import annotations

from typing import Optional, Tuple

import moderngl
import numpy as np

from visualizer.renderer.gl_state import set_depth_mask


# ---------------------------------------------------------------------------
# Shaders
# ---------------------------------------------------------------------------


_TONEMAP_VERTEX_SHADER = """
#version 330

in vec2 in_position;
in vec2 in_uv;

out vec2 v_uv;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    v_uv = in_uv;
}
"""

# Soft-knee tonemap: identity below `knee`, smooth roll toward 1.0 above.
#
# Below the knee a chassis grey (0.3) maps to itself; above the knee a
# beam overshoot (1.5) maps to ~0.94 instead of clipping to 1.0. Two
# overlapping beams at hdr=2.0 and hdr=4.0 remain distinguishable
# (~0.97 vs ~0.99) so intersections look brighter than single beams.
_TONEMAP_FRAGMENT_SHADER = """
#version 330

in vec2 v_uv;

out vec4 fragColor;

uniform sampler2D hdr_tex;
uniform float knee;

void main() {
    vec3 hdr = texture(hdr_tex, v_uv).rgb;
    vec3 k = vec3(knee);
    vec3 below = min(hdr, k);
    vec3 over = max(hdr - k, vec3(0.0));
    vec3 compressed = (1.0 - k) * over / (over + (1.0 - k));
    vec3 mapped = below + compressed;
    fragColor = vec4(mapped, 1.0);
}
"""


# ---------------------------------------------------------------------------
# HDRPipeline
# ---------------------------------------------------------------------------


class HDRPipeline:
    """Manages an HDR offscreen FBO + tonemap fullscreen pass.

    Usage:

        hdr = HDRPipeline(ctx)
        # each frame:
        hdr.resize(widget_w, widget_h)
        hdr.bind()
        hdr.clear(0.05, 0.05, 0.08)
        # ... render scene to hdr ...
        hdr.tonemap_to(qt_fbo)
        # ... render LDR-only overlays (gizmo) to qt_fbo ...
    """

    DEFAULT_KNEE = 0.8

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.knee: float = self.DEFAULT_KNEE

        self._color: Optional[moderngl.Texture] = None
        self._depth: Optional[moderngl.Renderbuffer] = None
        self._fbo: Optional[moderngl.Framebuffer] = None
        self._size: Tuple[int, int] = (0, 0)

        # Tonemap shader + fullscreen quad (TRIANGLE_STRIP, 4 verts).
        self._program = ctx.program(
            vertex_shader=_TONEMAP_VERTEX_SHADER,
            fragment_shader=_TONEMAP_FRAGMENT_SHADER,
        )
        self._program['hdr_tex'].value = 0
        self._program['knee'].value = self.knee

        # x, y, u, v interleaved.
        quad_verts = np.array(
            [
                -1.0, -1.0, 0.0, 0.0,
                 1.0, -1.0, 1.0, 0.0,
                -1.0,  1.0, 0.0, 1.0,
                 1.0,  1.0, 1.0, 1.0,
            ],
            dtype='f4',
        )
        self._quad_vbo = ctx.buffer(quad_verts.tobytes())
        self._quad_vao = ctx.vertex_array(
            self._program,
            [(self._quad_vbo, '2f 2f', 'in_position', 'in_uv')],
        )

    # --- Lifecycle ---

    def resize(self, width: int, height: int) -> None:
        """Recreate the HDR FBO at the new size when it has changed."""
        size = (max(1, int(width)), max(1, int(height)))
        if size == self._size and self._fbo is not None:
            return
        self._release_fbo()
        # 'f2' = half-float (RGBA16F). Plenty of headroom for additive beams
        # and a quarter the bandwidth of f4.
        self._color = self.ctx.texture(size, 4, dtype='f2')
        self._color.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self._color.repeat_x = False
        self._color.repeat_y = False
        self._depth = self.ctx.depth_renderbuffer(size)
        self._fbo = self.ctx.framebuffer(
            color_attachments=[self._color],
            depth_attachment=self._depth,
        )
        self._size = size

    def release(self) -> None:
        self._release_fbo()
        if self._quad_vao:
            self._quad_vao.release()
            self._quad_vao = None
        if self._quad_vbo:
            self._quad_vbo.release()
            self._quad_vbo = None
        if self._program:
            self._program.release()
            self._program = None

    def _release_fbo(self) -> None:
        if self._fbo:
            self._fbo.release()
            self._fbo = None
        if self._color:
            self._color.release()
            self._color = None
        if self._depth:
            self._depth.release()
            self._depth = None

    # --- Per-frame ---

    def bind(self) -> None:
        if self._fbo is None:
            raise RuntimeError("HDRPipeline.bind() called before resize()")
        self._fbo.use()

    def clear(self, r: float, g: float, b: float, a: float = 1.0) -> None:
        if self._fbo is None:
            return
        self._fbo.clear(r, g, b, a)

    def tonemap_to(
        self,
        target_fbo: moderngl.Framebuffer,
        *,
        knee: Optional[float] = None,
    ) -> None:
        """Run the tonemap fullscreen pass into ``target_fbo``.

        Disables blending + depth test for the pass and restores depth
        test (with depth_mask = True) on exit so subsequent LDR-only
        overlays (e.g. the gizmo) render with the expected state.
        """
        if self._color is None:
            return
        if knee is not None:
            self._program['knee'].value = float(knee)
        elif abs(self._program['knee'].value - self.knee) > 1e-6:
            self._program['knee'].value = self.knee

        target_fbo.use()

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)
        set_depth_mask(False)

        try:
            self._color.use(location=0)
            self._quad_vao.render(moderngl.TRIANGLE_STRIP)
        finally:
            self.ctx.enable(moderngl.DEPTH_TEST)
            set_depth_mask(True)
