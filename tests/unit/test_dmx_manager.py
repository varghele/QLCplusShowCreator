# tests/unit/test_dmx_manager.py
"""Unit tests for utils/artnet/dmx_manager.py - DMX state management."""

import pytest
from config.models import (
    Configuration, Fixture, FixtureMode, FixtureGroup, Universe,
    FixtureGroupCapabilities,
)
from utils.artnet.dmx_manager import FixtureChannelMap, DMXManager


@pytest.fixture
def fixture_def(mock_fixture_def):
    """Use the shared mock fixture definition."""
    return mock_fixture_def


@pytest.fixture
def fixture_defs(fixture_def):
    return {"TestMfr_TestModel": fixture_def}


@pytest.fixture
def test_fixture():
    return Fixture(
        universe=0, address=1, manufacturer="TestMfr", model="TestModel",
        name="MH1", group="TestGroup", current_mode="Standard",
        available_modes=[FixtureMode(name="Standard", channels=10)],
        type="MH", x=1.0, y=2.0, z=3.0,
    )


@pytest.fixture
def test_config(test_fixture):
    group = FixtureGroup(
        name="TestGroup", fixtures=[test_fixture],
        capabilities=FixtureGroupCapabilities(
            has_dimmer=True, has_colour=True, has_movement=True,
        ),
    )
    return Configuration(
        fixtures=[test_fixture],
        groups={"TestGroup": group},
        universes={0: Universe(id=0, name="Universe 0", output={})},
    )


class TestFixtureChannelMap:

    def test_creation(self, test_fixture, fixture_def, test_config):
        fcm = FixtureChannelMap(test_fixture, fixture_def, test_config)
        assert fcm.universe == 0
        assert fcm.base_address == 0  # address 1 -> 0-indexed

    def test_dimmer_channels_found(self, test_fixture, fixture_def, test_config):
        fcm = FixtureChannelMap(test_fixture, fixture_def, test_config)
        assert len(fcm.dimmer_channels) > 0

    def test_colour_channels_found(self, test_fixture, fixture_def, test_config):
        fcm = FixtureChannelMap(test_fixture, fixture_def, test_config)
        assert len(fcm.red_channels) > 0 or len(fcm.green_channels) > 0

    def test_pan_tilt_channels_found(self, test_fixture, fixture_def, test_config):
        fcm = FixtureChannelMap(test_fixture, fixture_def, test_config)
        assert len(fcm.pan_channels) > 0 or len(fcm.tilt_channels) > 0

    def test_get_absolute_address(self, test_fixture, fixture_def, test_config):
        fcm = FixtureChannelMap(test_fixture, fixture_def, test_config)
        universe, channel = fcm.get_absolute_address(3)
        assert universe == 0
        assert channel == 3  # base_address(0) + offset(3)


class TestDMXManagerInit:

    def test_creation(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        assert 0 in mgr.dmx_state
        assert len(mgr.dmx_state[0]) == 512

    def test_universe_initialized(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        assert all(v == 0 for v in mgr.dmx_state[0])

    def test_fixture_maps_built(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        assert "MH1" in mgr.fixture_maps


class TestDMXManagerOperations:

    def test_set_dmx_value(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        mgr.set_dmx_value(0, 5, 200)
        assert mgr.dmx_state[0][5] == 200

    def test_set_dmx_value_clamps(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        mgr.set_dmx_value(0, 5, 300)
        assert mgr.dmx_state[0][5] == 255
        mgr.set_dmx_value(0, 5, -10)
        assert mgr.dmx_state[0][5] == 0

    def test_set_dmx_value_invalid_universe(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        mgr.set_dmx_value(99, 0, 100)  # Should not raise

    def test_get_dmx_data(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        mgr.set_dmx_value(0, 10, 128)
        data = mgr.get_dmx_data(0)
        assert isinstance(data, bytes)
        assert len(data) == 512
        assert data[10] == 128

    def test_get_dmx_data_missing_universe(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        data = mgr.get_dmx_data(99)
        assert data == bytes(512)

    def test_clear_all_dmx(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        mgr.set_dmx_value(0, 10, 200)
        mgr.clear_all_dmx()
        assert all(v == 0 for v in mgr.dmx_state[0])

    def test_clear_active_blocks(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        mgr.active_blocks["lane1"] = {"dimmer": "something"}
        mgr.clear_active_blocks()
        assert mgr.active_blocks == {}

    def test_rebuild_fixture_maps(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        mgr.rebuild_fixture_maps()
        assert "MH1" in mgr.fixture_maps


class TestDMXManagerFixturesVisible:

    def test_set_fixtures_visible(self, test_config, fixture_defs):
        mgr = DMXManager(test_config, fixture_defs)
        mgr.set_fixtures_visible()
        # Dimmer channel (0) should be set to 255
        fcm = mgr.fixture_maps["MH1"]
        if fcm.dimmer_channels:
            ch = fcm.dimmer_channels[0]
            assert mgr.dmx_state[0][ch] == 255