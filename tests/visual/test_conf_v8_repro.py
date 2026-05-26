"""Direct reproduction of the user's reported bug, loading conf_v8.yaml.

The user has a front-wash PAR sitting on the floor at world (0, 0, 0) and
two moving heads mounted on the back wall. They report that when an MH beam
crosses the camera's line of sight to the front PAR, the PAR vanishes from
the embedded visualizer.

This test loads their actual config (read-only) and renders it under
synthetic DMX that puts the MHs in their typical groove orientation, then
checks the front PAR's chassis pixels are still red-dominated.
"""

from __future__ import annotations

import importlib
import os
import pathlib
from typing import Tuple

import glm
import moderngl
import numpy as np
import pytest

from config.models import Configuration
from utils.fixture_capabilities import clear_capabilities_cache
from utils.tcp.protocol import VisualizerProtocol
from visualizer.renderer.camera import OrbitCamera


FBO_SIZE = 768
# conf_v8.yaml lived in the tracked `showcreator_archive/` until v1.0; the
# directory was renamed to `archive/` and gitignored. This test still runs
# locally if the file is present and is skipped otherwise (fresh clones,
# CI without a local archive).
CONFIG_PATH = pathlib.Path(__file__).resolve().parents[2] / "archive" / "conf_v8.yaml"
pytestmark = pytest.mark.skipif(
    not CONFIG_PATH.exists(),
    reason=f"Requires local archive file: {CONFIG_PATH}"
)


@pytest.fixture(scope="module")
def gl_context():
    try:
        ctx = moderngl.create_standalone_context()
    except Exception as e:
        pytest.skip(f"Could not create standalone GL context: {e}")
    yield ctx
    ctx.release()


@pytest.fixture
def ldr_fbo(gl_context):
    color = gl_context.texture((FBO_SIZE, FBO_SIZE), 4)
    depth = gl_context.depth_renderbuffer((FBO_SIZE, FBO_SIZE))
    fbo = gl_context.framebuffer(color_attachments=[color], depth_attachment=depth)
    yield fbo
    fbo.release()
    color.release()
    depth.release()


@pytest.fixture
def hdr_fbo(gl_context):
    color = gl_context.texture((FBO_SIZE, FBO_SIZE), 4, dtype='f2')
    depth = gl_context.depth_renderbuffer((FBO_SIZE, FBO_SIZE))
    fbo = gl_context.framebuffer(color_attachments=[color], depth_attachment=depth)
    yield fbo
    fbo.release()
    color.release()
    depth.release()


def _maybe_save(image: np.ndarray, name: str) -> None:
    out = os.environ.get("BEAM_CHASSIS_DEBUG_OUT")
    if not out:
        return
    try:
        from PIL import Image
    except ImportError:
        return
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(os.path.join(out, f"{name}.png"))


def _load_conf_v8() -> Configuration:
    if not CONFIG_PATH.exists():
        pytest.skip(f"Config not present at {CONFIG_PATH}")
    return Configuration.load(str(CONFIG_PATH))


def _find_front_par(config: Configuration):
    """The front-wash fixture is the Retro Flat Par at the stage centre."""
    for f in config.fixtures:
        if f.model.strip() == "Retro Flat Par 18x12W RGBW" and abs(f.x) < 0.5 and abs(f.y) < 0.5:
            return f
    pytest.skip("Front Retro Flat Par not found in conf_v8.yaml")


def _find_mhs(config: Configuration):
    return [f for f in config.fixtures if f.model == "Hero Spot 60"]


def _project_world_to_screen(mvp: glm.mat4, world: glm.vec3, fbo_size: int) -> Tuple[int, int]:
    """Project a world-space point to integer pixel coordinates in the FBO.

    Returns (x, y) where y is measured from the bottom of the FBO (the
    same convention as ``moderngl.Framebuffer.read``). Negative values
    or values >= fbo_size mean off-screen.
    """
    clip = mvp * glm.vec4(world.x, world.y, world.z, 1.0)
    if abs(clip.w) < 1e-6:
        return -1, -1
    ndc_x = clip.x / clip.w
    ndc_y = clip.y / clip.w
    x = int((ndc_x * 0.5 + 0.5) * fbo_size)
    y = int((ndc_y * 0.5 + 0.5) * fbo_size)
    return x, y


def _camera_facing_back() -> OrbitCamera:
    """A camera roughly matching the screenshot: in front of the stage,
    slightly elevated, looking back."""
    cam = OrbitCamera()
    cam.set_aspect(1.0)
    cam.target = glm.vec3(0.0, 1.0, 0.0)
    cam.azimuth = 0.0
    cam.elevation = 25.0
    cam.distance = 10.0
    return cam


def _build_dmx_for_repro(config: Configuration) -> bytes:
    """Build a DMX buffer that:
    - Lights the front PAR red (distinctive colour for the chassis silhouette).
    - Aims both MHs at the front PAR with full white beams.
    """
    from utils.orientation import calculate_pan_tilt, pan_tilt_to_dmx

    dmx = bytearray(512)

    front_par = _find_front_par(config)
    par_addr = front_par.address - 1
    # Retro Flat Par 18x12W RGBW 8ch: dimmer, R, G, B, W, A, UV, strobe
    dmx[par_addr + 0] = 220   # dimmer
    dmx[par_addr + 1] = 255   # R
    dmx[par_addr + 2] = 0     # G
    dmx[par_addr + 3] = 0     # B

    # Hero Spot 60 ``14 Channel`` mode (per QXF <Mode>):
    # 0=Pan 1=PanFine 2=Tilt 3=TiltFine 4=MovingSpeed 5=Dimmer 6=Shutter
    # 7=Color 8=Gobo 9=GoboRot 10=Focus 11=Prism 12=MovingProg 13=AutoShows.
    for mh in _find_mhs(config):
        pan_deg, tilt_deg = calculate_pan_tilt(
            mh.x, mh.y, mh.z,
            front_par.x, front_par.y, front_par.z,
            mh.mounting, mh.yaw, mh.pitch, mh.roll,
            pan_range=540.0, tilt_range=190.0,
        )
        pan_dmx, tilt_dmx = pan_tilt_to_dmx(pan_deg, tilt_deg, 540.0, 190.0)
        print(f"  Aiming MH @({mh.x},{mh.y},{mh.z}) at PAR: "
              f"pan={pan_deg:.1f}° (dmx={pan_dmx}) tilt={tilt_deg:.1f}° (dmx={tilt_dmx})")

        a = mh.address - 1
        dmx[a + 0] = pan_dmx
        dmx[a + 2] = tilt_dmx
        dmx[a + 5] = 255   # dimmer full
        dmx[a + 6] = 255   # shutter open
        dmx[a + 7] = 0     # color: white macro

    return bytes(dmx)


def _render(ctx, fbo, config: Configuration, dmx: bytes, *, with_hdr: bool):
    os.environ["FIXTURE_RENDERER"] = "composable"
    from visualizer.renderer import fixtures as fixtures_module
    importlib.reload(fixtures_module)

    fm = fixtures_module.FixtureManager(ctx)
    clear_capabilities_cache()
    payload = VisualizerProtocol.build_fixtures_payload(config)
    fm.update_fixtures(payload)
    fm.update_dmx(universe=1, dmx_data=dmx)

    cam = _camera_facing_back()
    mvp = cam.get_view_projection_matrix()

    if with_hdr:
        from visualizer.renderer.hdr import HDRPipeline
        hdr_color = fbo.color_attachments[0]
        # Confirm we have an HDR framebuffer.
        assert hdr_color.dtype in ('f2', 'f4'), \
            f"Pass an HDR FBO when with_hdr=True (got dtype={hdr_color.dtype})"

        # Render scene to the HDR FBO, then create a temporary LDR FBO to
        # tonemap into so we can read it back as uint8.
        fbo.use()
        ctx.viewport = (0, 0, FBO_SIZE, FBO_SIZE)
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.depth_mask = True
        ctx.disable(moderngl.BLEND)
        fbo.clear(0.05, 0.05, 0.08, 1.0)
        fm.render(mvp)

        ldr_color = ctx.texture((FBO_SIZE, FBO_SIZE), 4)
        ldr_depth = ctx.depth_renderbuffer((FBO_SIZE, FBO_SIZE))
        ldr_fbo = ctx.framebuffer(color_attachments=[ldr_color], depth_attachment=ldr_depth)

        try:
            hdr = HDRPipeline(ctx)
            try:
                hdr._color = hdr_color
                hdr._size = (FBO_SIZE, FBO_SIZE)
                hdr.tonemap_to(ldr_fbo)
                raw = ldr_fbo.read(components=3, dtype='f1')
                image = np.frombuffer(raw, dtype='u1').reshape(FBO_SIZE, FBO_SIZE, 3)
            finally:
                hdr._color = None
                hdr.release()
        finally:
            ldr_fbo.release()
            ldr_color.release()
            ldr_depth.release()
    else:
        fbo.use()
        ctx.viewport = (0, 0, FBO_SIZE, FBO_SIZE)
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.depth_mask = True
        ctx.disable(moderngl.BLEND)
        ctx.clear(0.05, 0.05, 0.08, 1.0)
        fm.render(mvp)

        raw = fbo.read(components=3, dtype='f1')
        image = np.frombuffer(raw, dtype='u1').reshape(FBO_SIZE, FBO_SIZE, 3)

    fm.release()
    return image.copy(), mvp


def _front_par_world_pos(config: Configuration) -> glm.vec3:
    """Map the front PAR's stage (x,y,z) to world (x, z, y) — same convention
    used by ``FixtureRenderer.get_model_matrix``."""
    f = _find_front_par(config)
    return glm.vec3(f.x, f.z, f.y)


def _brightest_red_in_box(image: np.ndarray, cx: int, cy: int, half: int = 40) -> Tuple[int, int, int]:
    """Return the brightest red-dominant pixel within ±half of (cx, cy).

    The PAR with the new :class:`PARChassisGeometry` lights its lens slab,
    not the full chassis body, so the brightest pixel sits a bit above or
    around the projected origin (chassis local +Z → world +Y after the
    standing pitch). Searching a small box accommodates that.
    """
    h, w, _ = image.shape
    x0, x1 = max(0, cx - half), min(w, cx + half)
    y0, y1 = max(0, cy - half), min(h, cy + half)
    region = image[y0:y1, x0:x1]
    r = region[..., 0].astype(int)
    g = region[..., 1].astype(int)
    b = region[..., 2].astype(int)
    # Score: prefer red-dominant pixels. Zero out non-red ones.
    score = np.where((r > g + 20) & (r > b + 20), r, -1)
    if score.max() <= 0:
        return (0, 0, 0)
    idx = np.argmax(score)
    by, bx = np.unravel_index(idx, score.shape)
    return tuple(int(c) for c in region[by, bx])


def test_conf_v8_par_alone_baseline(gl_context, ldr_fbo):
    """Baseline: render conf_v8 with ONLY the front PAR lit (everything else dark).

    Verifies the PAR is visible and where in screen space the chassis lands.
    If this fails, the conf_v8 + chassis-on-top + projection chain is broken
    independently of the beam-occlusion question.
    """
    config = _load_conf_v8()
    # All-zero DMX except the PAR.
    dmx = bytearray(512)
    front_par = _find_front_par(config)
    a = front_par.address - 1
    dmx[a + 0] = 220
    dmx[a + 1] = 255
    img, mvp = _render(gl_context, ldr_fbo, config, bytes(dmx), with_hdr=False)
    _maybe_save(img, "conf_v8_par_alone")

    par_world = _front_par_world_pos(config)
    px, py = _project_world_to_screen(mvp, par_world, FBO_SIZE)
    print(f"[par_alone] front PAR world={tuple(par_world)} projected=({px},{py})")

    # Find the actual red-pixel centroid in the rendered image.
    r = img[..., 0].astype(int)
    g = img[..., 1].astype(int)
    b = img[..., 2].astype(int)
    red_mask = (r > 80) & (r > g + 30) & (r > b + 30)
    ys, xs = np.where(red_mask)
    if len(xs) == 0:
        pytest.fail("PAR not visible at all when rendered alone — basic rendering broken.")
    actual_cx = int(xs.mean())
    actual_cy = int(ys.mean())  # numpy row 0 = bottom of FBO
    print(f"[par_alone] actual red centroid in FBO coords=({actual_cx},{actual_cy})")
    print(f"[par_alone] difference: dx={actual_cx - px} dy={actual_cy - py}")


def test_conf_v8_front_par_stays_visible_ldr(gl_context, ldr_fbo):
    """Render conf_v8 with MHs on, check the front PAR's chassis stays red."""
    config = _load_conf_v8()
    dmx = _build_dmx_for_repro(config)
    img, mvp = _render(gl_context, ldr_fbo, config, dmx, with_hdr=False)
    _maybe_save(img, "conf_v8_ldr")

    par_world = _front_par_world_pos(config)
    px, py = _project_world_to_screen(mvp, par_world, FBO_SIZE)
    # numpy image row 0 = bottom of FBO. _project_world_to_screen returns y
    # from bottom too, so they align without a flip.
    print(f"[conf_v8_ldr] front PAR world={tuple(par_world)} screen=({px},{py})")
    if not (0 <= px < FBO_SIZE and 0 <= py < FBO_SIZE):
        pytest.skip(f"Front PAR projects off-screen at ({px},{py}); adjust camera.")

    # The new PARChassisGeometry lights only the lens slab (sitting on the
    # chassis +Z face) — search around the projected origin for the
    # brightest red-dominant pixel rather than averaging at the body centre.
    r, g, b = _brightest_red_in_box(img, px, py)
    print(f"[conf_v8_ldr] avg RGB near PAR: ({r}, {g}, {b})")

    assert r - g >= 30 and r - b >= 30, (
        f"Front PAR centre averaged ({r},{g},{b}) — lost red dominance. "
        f"Chassis-on-top isn't holding under conf_v8 + MH beams."
    )


def test_conf_v8_front_par_stays_visible_hdr(gl_context, hdr_fbo):
    """Same scene, full HDR + tonemap pipeline (the user's actual path)."""
    config = _load_conf_v8()
    dmx = _build_dmx_for_repro(config)
    img, mvp = _render(gl_context, hdr_fbo, config, dmx, with_hdr=True)
    _maybe_save(img, "conf_v8_hdr")

    par_world = _front_par_world_pos(config)
    px, py = _project_world_to_screen(mvp, par_world, FBO_SIZE)
    print(f"[conf_v8_hdr] front PAR world={tuple(par_world)} screen=({px},{py})")
    if not (0 <= px < FBO_SIZE and 0 <= py < FBO_SIZE):
        pytest.skip(f"Front PAR projects off-screen at ({px},{py}); adjust camera.")

    r, g, b = _brightest_red_in_box(img, px, py)
    print(f"[conf_v8_hdr] avg RGB near PAR: ({r}, {g}, {b})")

    assert r - g >= 30 and r - b >= 30, (
        f"Front PAR centre averaged ({r},{g},{b}) under HDR — lost red dominance."
    )
