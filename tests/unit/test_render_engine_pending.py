"""
Pending-state buffering in :class:`visualizer.renderer.engine.RenderEngine`.

``QOpenGLWidget.initializeGL`` only fires the first time the widget is
shown — so an embedded visualizer hosted on an inactive tab silently
dropped fixture / grid / DMX updates pushed at config-load time. The
engine now buffers them and flushes them in ``initializeGL``.

This test pins the buffer-and-flush contract directly so it cannot
regress without breaking the test, regardless of which tab happens to
be visible at config-load time.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def engine(qapp):
    """A bare RenderEngine that has NOT had initializeGL fire yet — i.e.
    stage_renderer / fixture_manager are still ``None``. We never show
    the widget, so Qt won't call initializeGL on us."""
    from visualizer.renderer.engine import RenderEngine

    e = RenderEngine(parent=None)
    try:
        # Stop the 60 FPS render timer so it doesn't fire `update()` and
        # tickle GL initialisation underneath us mid-test.
        e.render_timer.stop()
        # Sanity: pre-init state should match what initializeGL guards.
        assert e.stage_renderer is None
        assert e.fixture_manager is None
        yield e
    finally:
        e.deleteLater()


def test_update_fixtures_before_init_is_buffered(engine):
    payload = [{"id": "f1", "x": 0, "y": 0, "z": 0}]
    engine.update_fixtures(payload)
    assert engine._pending_fixtures is payload


def test_set_grid_size_before_init_is_buffered(engine):
    engine.set_grid_size(0.5)
    assert engine._pending_grid_size == 0.5


def test_update_dmx_before_init_is_buffered_per_universe(engine):
    engine.update_dmx(0, b"\x01" * 512)
    engine.update_dmx(1, b"\x02" * 512)
    # Later push for universe 0 wins (we only need the latest frame).
    engine.update_dmx(0, b"\x03" * 512)
    assert set(engine._pending_dmx.keys()) == {0, 1}
    assert engine._pending_dmx[0] == b"\x03" * 512
    assert engine._pending_dmx[1] == b"\x02" * 512


def test_flush_pushes_buffered_state_to_renderers(engine):
    payload = [{"id": "f1"}]
    engine.update_fixtures(payload)
    engine.set_grid_size(0.25)
    engine.update_dmx(0, b"\x10" * 512)
    engine.update_dmx(1, b"\x20" * 512)

    # Simulate initializeGL having created the renderers without
    # actually creating a GL context — we only care about the flush.
    engine.stage_renderer = MagicMock()
    engine.fixture_manager = MagicMock()

    engine._flush_pending_state()

    engine.stage_renderer.set_grid_size.assert_called_once_with(0.25)
    engine.fixture_manager.update_fixtures.assert_called_once_with(payload)
    # Both universes flushed with their latest buffered frame.
    dmx_calls = engine.fixture_manager.update_dmx.call_args_list
    sent = {c.args[0]: c.args[1] for c in dmx_calls}
    assert sent == {0: b"\x10" * 512, 1: b"\x20" * 512}

    # Pending stores cleared so a second flush is a no-op.
    assert engine._pending_grid_size is None
    assert engine._pending_fixtures is None
    assert engine._pending_dmx == {}


def test_flush_with_no_pending_state_is_a_noop(engine):
    """Engines that received no updates before init shouldn't bother
    the renderers with empty calls during initializeGL."""
    engine.stage_renderer = MagicMock()
    engine.fixture_manager = MagicMock()

    engine._flush_pending_state()

    engine.stage_renderer.set_grid_size.assert_not_called()
    engine.fixture_manager.update_fixtures.assert_not_called()
    engine.fixture_manager.update_dmx.assert_not_called()


def test_post_init_calls_bypass_buffering(engine):
    """Once renderers exist, setters go straight through — they don't
    pile up in the pending stores."""
    engine.stage_renderer = MagicMock()
    engine.fixture_manager = MagicMock()
    # The setters call makeCurrent / doneCurrent on the widget; stub
    # them out so we don't trip over a missing GL context.
    engine.makeCurrent = MagicMock()
    engine.doneCurrent = MagicMock()

    engine.update_fixtures([{"id": "f"}])
    engine.set_grid_size(0.5)
    engine.update_dmx(0, b"\x00" * 512)

    assert engine._pending_fixtures is None
    assert engine._pending_grid_size is None
    assert engine._pending_dmx == {}
    engine.fixture_manager.update_fixtures.assert_called_once()
    engine.stage_renderer.set_grid_size.assert_called_once_with(0.5)
    engine.fixture_manager.update_dmx.assert_called_once()
