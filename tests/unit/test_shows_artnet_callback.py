"""
Regression test for ``ShowsArtNetController.local_dmx_callback`` — the
in-process bridge that lets the embedded visualizer mirror the show
without a TCP/ArtNet round-trip.

Each call to ``_send_all_universes`` should:
- still hand the DMX bytes to the ArtNet sender (the wire path stays
  intact for the standalone visualizer), AND
- invoke the local callback once per configured universe with the
  1-based universe id and the raw 512-byte DMX buffer.

A misbehaving callback must not poison the DMX thread, so an exception
inside the callback is swallowed without breaking the ArtNet send.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from config.models import Configuration, Fixture, FixtureMode, Universe
from utils.artnet.shows_artnet_controller import ShowsArtNetController


@pytest.fixture
def two_universe_config():
    """Configuration with one fixture per universe across two universes."""
    fixtures = [
        Fixture(
            universe=1, address=1, manufacturer="Mfr", model="A",
            name="A1", group="G", current_mode="Mode",
            available_modes=[FixtureMode(name="Mode", channels=4)],
            type="PAR",
        ),
        Fixture(
            universe=2, address=1, manufacturer="Mfr", model="B",
            name="B1", group="G", current_mode="Mode",
            available_modes=[FixtureMode(name="Mode", channels=4)],
            type="PAR",
        ),
    ]
    return Configuration(
        fixtures=fixtures,
        universes={
            1: Universe(id=1, name="Universe 1", output={}),
            2: Universe(id=2, name="Universe 2", output={}),
        },
    )


def _make_controller(config, callback=None):
    """Build a ShowsArtNetController with a mocked ArtNet sender so the
    test never actually opens a UDP socket. ``fixture_definitions`` is
    empty — DMXManager handles missing defs by leaving the universe at
    zeros, which is fine for the callback wire-up assertion."""
    controller = ShowsArtNetController(
        config=config,
        fixture_definitions={},
        local_dmx_callback=callback,
    )
    controller.artnet_sender = MagicMock()
    return controller


def test_callback_fires_once_per_universe(two_universe_config):
    received: list[tuple[int, bytes]] = []

    def callback(universe: int, dmx_bytes: bytes) -> None:
        received.append((universe, dmx_bytes))

    controller = _make_controller(two_universe_config, callback=callback)
    controller._send_all_universes()

    universes_seen = [u for u, _ in received]
    assert sorted(universes_seen) == [1, 2], (
        f"Expected callback for universes [1, 2], got {universes_seen}"
    )
    for _, payload in received:
        assert isinstance(payload, bytes), (
            f"Callback got {type(payload).__name__} instead of bytes"
        )
        assert len(payload) == 512, (
            f"Expected 512-byte DMX buffer, got {len(payload)}"
        )

    # ArtNet sender still gets called per-universe — this is the
    # belt-and-braces guarantee that the wire path is unaffected.
    assert controller.artnet_sender.send_dmx.call_count == 2


def test_callback_exception_does_not_break_send(two_universe_config):
    def bad_callback(universe: int, dmx_bytes: bytes) -> None:
        raise RuntimeError("visualizer is unhappy")

    controller = _make_controller(two_universe_config, callback=bad_callback)
    # Should not raise — the controller swallows callback exceptions so
    # a misbehaving visualizer can't kill the DMX thread mid-show.
    controller._send_all_universes()

    # ArtNet sender still got both packets.
    assert controller.artnet_sender.send_dmx.call_count == 2


def test_set_local_dmx_callback_swaps_in_place(two_universe_config):
    controller = _make_controller(two_universe_config, callback=None)

    received: list[int] = []
    controller.set_local_dmx_callback(lambda u, _: received.append(u))
    controller._send_all_universes()
    assert sorted(received) == [1, 2]

    # Clearing the callback stops further dispatch immediately.
    controller.set_local_dmx_callback(None)
    received.clear()
    controller._send_all_universes()
    assert received == []


def test_no_callback_means_zero_overhead(two_universe_config):
    """When no callback is wired, the controller should not raise and
    must still send via ArtNet."""
    controller = _make_controller(two_universe_config, callback=None)
    controller._send_all_universes()
    assert controller.artnet_sender.send_dmx.call_count == 2
