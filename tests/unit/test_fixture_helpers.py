# tests/unit/test_fixture_helpers.py
"""Unit tests for effects/fixture_helpers.py - per-fixture effect processing."""

import pytest
from config.models import Fixture, FixtureMode
from effects.fixture_helpers import (
    get_fixture_def, get_fixture_dimmer_channels, get_fixture_colour_channels,
    sort_fixtures_by_position, build_fixture_value_string, count_total_dimmer_channels,
)


@pytest.fixture
def fixture_defs(mock_fixture_def):
    """Fixture definitions dict keyed by manufacturer_model."""
    return {"TestMfr_TestModel": mock_fixture_def}


class TestGetFixtureDef:

    def test_found(self, sample_fixture, fixture_defs):
        result = get_fixture_def(sample_fixture, fixture_defs)
        assert result is not None
        assert result['manufacturer'] == "TestMfr"

    def test_not_found(self, sample_fixture):
        result = get_fixture_def(sample_fixture, {})
        assert result is None


class TestGetFixtureDimmerChannels:

    def test_finds_dimmer(self, sample_fixture, fixture_defs):
        channels = get_fixture_dimmer_channels(sample_fixture, fixture_defs)
        assert len(channels) > 0
        assert 'channel' in channels[0]

    def test_no_fixture_def(self, sample_fixture):
        channels = get_fixture_dimmer_channels(sample_fixture, {})
        assert channels == []


class TestGetFixtureColourChannels:

    def test_no_fixture_def(self, sample_fixture):
        result = get_fixture_colour_channels(sample_fixture, {})
        assert result == {}


class TestSortFixturesByPosition:

    def test_sort_by_x(self):
        f1 = Fixture(universe=0, address=1, manufacturer="M", model="Mo",
                     name="F1", group="G", current_mode="S",
                     available_modes=[], x=5.0, y=0.0, z=0.0)
        f2 = Fixture(universe=0, address=7, manufacturer="M", model="Mo",
                     name="F2", group="G", current_mode="S",
                     available_modes=[], x=1.0, y=0.0, z=0.0)
        f3 = Fixture(universe=0, address=13, manufacturer="M", model="Mo",
                     name="F3", group="G", current_mode="S",
                     available_modes=[], x=3.0, y=0.0, z=0.0)
        result = sort_fixtures_by_position([f1, f2, f3], axis='x')
        # Should be sorted: f2(1.0), f3(3.0), f1(5.0)
        assert result[0][1] is f2
        assert result[1][1] is f3
        assert result[2][1] is f1

    def test_sort_by_y(self):
        f1 = Fixture(universe=0, address=1, manufacturer="M", model="Mo",
                     name="F1", group="G", current_mode="S",
                     available_modes=[], x=0.0, y=10.0, z=0.0)
        f2 = Fixture(universe=0, address=7, manufacturer="M", model="Mo",
                     name="F2", group="G", current_mode="S",
                     available_modes=[], x=0.0, y=2.0, z=0.0)
        result = sort_fixtures_by_position([f1, f2], axis='y')
        assert result[0][1] is f2
        assert result[1][1] is f1

    def test_sort_reverse(self):
        f1 = Fixture(universe=0, address=1, manufacturer="M", model="Mo",
                     name="F1", group="G", current_mode="S",
                     available_modes=[], x=1.0, y=0.0, z=0.0)
        f2 = Fixture(universe=0, address=7, manufacturer="M", model="Mo",
                     name="F2", group="G", current_mode="S",
                     available_modes=[], x=5.0, y=0.0, z=0.0)
        result = sort_fixtures_by_position([f1, f2], axis='x', reverse=True)
        assert result[0][1] is f2  # Largest first

    def test_preserves_original_indices(self):
        f1 = Fixture(universe=0, address=1, manufacturer="M", model="Mo",
                     name="F1", group="G", current_mode="S",
                     available_modes=[], x=5.0, y=0.0, z=0.0)
        f2 = Fixture(universe=0, address=7, manufacturer="M", model="Mo",
                     name="F2", group="G", current_mode="S",
                     available_modes=[], x=1.0, y=0.0, z=0.0)
        result = sort_fixtures_by_position([f1, f2], axis='x')
        # f2 comes first but its original index is 1
        assert result[0][0] == 1  # original index of f2
        assert result[1][0] == 0  # original index of f1


class TestBuildFixtureValueString:

    def test_dimmer_value_string(self, sample_fixture, fixture_defs):
        result = build_fixture_value_string(
            sample_fixture, 0, fixture_defs, 'dimmer', 200
        )
        assert result.startswith("0:")
        assert "200" in result

    def test_unknown_channel_type(self, sample_fixture, fixture_defs):
        result = build_fixture_value_string(
            sample_fixture, 0, fixture_defs, 'nonexistent', 100
        )
        # Should return fixture_id with empty channels
        assert result == "0:"


class TestCountTotalDimmerChannels:

    def test_count(self, sample_fixture, fixture_defs):
        total = count_total_dimmer_channels([sample_fixture], fixture_defs)
        assert total >= 0

    def test_empty_fixtures(self, fixture_defs):
        total = count_total_dimmer_channels([], fixture_defs)
        assert total == 0