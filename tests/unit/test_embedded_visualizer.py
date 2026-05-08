"""
Behavioural tests for :class:`gui.widgets.embedded_visualizer.EmbeddedVisualizer`.

The widget wraps :class:`visualizer.renderer.engine.RenderEngine` (a
``QOpenGLWidget``). For unit-testing we never trigger ``initializeGL``
— we just assert the widget's own dispatch rules around preview modes
and DMX forwarding. The underlying engine is exercised in
:mod:`tests.unit.test_render_engine_pending`.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def vis(qapp):
    """A bare EmbeddedVisualizer with the heavy GL engine swapped for a
    mock so we can introspect calls without a real OpenGL context."""
    from gui.widgets.embedded_visualizer import EmbeddedVisualizer

    v = EmbeddedVisualizer(parent=None)
    try:
        # Stop the FPS poll timer so we don't tick the real engine.
        v._fps_timer.stop()
        v._engine = MagicMock()
        yield v
    finally:
        v.cleanup()
        v.deleteLater()


def test_feed_dmx_forwards_in_live_mode(vis):
    vis._preview_mode = "live"
    vis.feed_dmx(1, b"\x10" * 512)
    vis._engine.update_dmx.assert_called_once_with(1, b"\x10" * 512)


def test_feed_dmx_also_forwards_in_build_mode(vis):
    """Earlier versions gated forwarding on ``preview_mode == "live"``,
    which made the Live (Auto) tab visualizer freeze on the synthetic
    full-on buffer if a frame fired before ``set_preview_mode("live")``
    had landed. Forwarding is now unconditional — build vs. live only
    governs what gets pushed when *no* live source is feeding."""
    vis._preview_mode = "build"
    vis.feed_dmx(1, b"\x42" * 512)
    vis._engine.update_dmx.assert_called_once_with(1, b"\x42" * 512)


def test_feed_dmx_drops_none_payload(vis):
    """A None payload is still ignored — the engine would just raise."""
    vis._preview_mode = "live"
    vis.feed_dmx(0, None)
    vis._engine.update_dmx.assert_not_called()


def test_set_preview_mode_build_pushes_synthetic_buffer(vis):
    """Switching to build mode while a config is loaded should push a
    synthetic full-on DMX buffer per universe so every fixture lights
    up. This is the "no live source" baseline."""
    from config.models import (Configuration, Fixture, FixtureGroup,
                               FixtureMode, Universe)

    f = Fixture(
        universe=1, address=1, manufacturer="M", model="X",
        name="A1", group="G", current_mode="m",
        available_modes=[FixtureMode(name="m", channels=4)],
        type="PAR",
    )
    cfg = Configuration(
        fixtures=[f],
        groups={"G": FixtureGroup(name="G", fixtures=[f])},
        universes={1: Universe(id=1, name="U1", output={})},
    )

    # Stub set_config's heavy dependencies so we don't need real QXF
    # data on disk for this test. We only care that the build-mode push
    # runs after switching back to build.
    vis.set_config(cfg)
    vis._engine.reset_mock()

    vis._preview_mode = "live"
    vis.set_preview_mode("build")
    # set_preview_mode flipped the flag and called _push_build_mode_dmx,
    # which iterates universes and calls engine.update_dmx for each.
    assert vis.preview_mode() == "build"
    assert vis._engine.update_dmx.called


def test_set_preview_mode_live_does_not_push(vis):
    """Switching TO live mode must not synthesise anything — whoever is
    feeding via :meth:`feed_dmx` is responsible for the next frame."""
    vis._preview_mode = "build"
    vis.set_preview_mode("live")
    vis._engine.update_dmx.assert_not_called()


def test_set_preview_mode_idempotent(vis):
    """Setting the mode to its current value must be a no-op (no
    spurious build-mode push when re-applying "build")."""
    vis._preview_mode = "build"
    vis.set_preview_mode("build")
    vis._engine.update_dmx.assert_not_called()
