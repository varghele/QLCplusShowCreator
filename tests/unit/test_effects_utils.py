# tests/unit/test_effects_utils.py
"""Unit tests for utils/effects_utils.py - channel lookup and color matching."""

import pytest
from utils.effects_utils import (
    get_channels_by_property,
    find_closest_color_dmx,
    find_gobo_dmx_value,
    find_gobo_rotation_value,
    add_reset_step,
)


@pytest.fixture
def fixture_def(mock_fixture_def):
    return mock_fixture_def


class TestGetChannelsByProperty:

    def test_finds_dimmer(self, fixture_def):
        result = get_channels_by_property(
            fixture_def, "Standard", ["IntensityMasterDimmer"]
        )
        assert "IntensityMasterDimmer" in result
        assert len(result["IntensityMasterDimmer"]) == 1
        assert result["IntensityMasterDimmer"][0]["channel"] == 0

    def test_finds_colour_channels(self, fixture_def):
        result = get_channels_by_property(
            fixture_def, "Standard", ["IntensityRed", "IntensityGreen", "IntensityBlue"]
        )
        assert "IntensityRed" in result
        assert "IntensityGreen" in result
        assert "IntensityBlue" in result

    def test_finds_position_channels_by_group(self, fixture_def):
        result = get_channels_by_property(
            fixture_def, "Standard", ["Pan", "Tilt"]
        )
        assert "Pan" in result
        assert "Tilt" in result

    def test_nonexistent_mode_returns_empty(self, fixture_def):
        result = get_channels_by_property(fixture_def, "NonexistentMode", ["IntensityRed"])
        assert result == {}

    def test_nonexistent_property_returns_empty(self, fixture_def):
        result = get_channels_by_property(fixture_def, "Standard", ["SomethingFake"])
        assert result == {}


class TestFindClosestColorDmx:

    def test_no_hex_returns_none(self):
        assert find_closest_color_dmx({}, None) is None
        assert find_closest_color_dmx({}, "") is None

    def test_invalid_hex_returns_none(self):
        assert find_closest_color_dmx({}, "#ZZZZZZ") is None

    def test_with_color_capabilities(self):
        channels_dict = {
            "ColorMacro": [{
                "capabilities": [
                    {"min": 0, "max": 10, "color": "#FF0000", "name": "Red"},
                    {"min": 11, "max": 20, "color": "#00FF00", "name": "Green"},
                    {"min": 21, "max": 30, "color": "#0000FF", "name": "Blue"},
                ]
            }]
        }
        # Closest to pure red should be the Red entry
        result = find_closest_color_dmx(channels_dict, "#FF0000")
        assert result == 5  # (0 + 10) // 2

    def test_closest_match(self):
        channels_dict = {
            "ColorMacro": [{
                "capabilities": [
                    {"min": 0, "max": 10, "color": "#FF0000", "name": "Red"},
                    {"min": 20, "max": 30, "color": "#FFFF00", "name": "Yellow"},
                ]
            }]
        }
        # Orange (#FF8000) should be closer to Yellow or Red
        result = find_closest_color_dmx(channels_dict, "#FF8000")
        assert result is not None


class TestFindGoboDmxValue:

    def test_with_gobo_capabilities(self):
        fixture_def = {
            "channels": [
                {
                    "name": "Gobo",
                    "capabilities": [
                        {"min": 0, "max": 7, "name": "Open", "preset": None},
                        {"min": 8, "max": 15, "name": "Gobo 1", "preset": None},
                        {"min": 16, "max": 23, "name": "Gobo 2", "preset": None},
                    ]
                }
            ]
        }
        # gobo_index=1 -> first non-open gobo
        result = find_gobo_dmx_value({}, 1, fixture_def)
        assert result == (8 + 15) // 2

    def test_default_value_when_no_gobos(self):
        result = find_gobo_dmx_value({}, 1, {"channels": []})
        assert result == 20  # Default


class TestFindGoboRotationValue:

    def test_no_rotation_channel(self):
        fixture_def = {"channels": [], "modes": []}
        result = find_gobo_rotation_value(fixture_def)
        assert result is None

    def test_with_rotation_channel(self):
        fixture_def = {
            "channels": [
                {
                    "name": "Gobo Rotation",
                    "capabilities": [
                        {
                            "min": 0, "max": 127,
                            "preset": "RotationClockwiseFastToSlow",
                            "name": "CW rotation"
                        },
                        {
                            "min": 128, "max": 255,
                            "preset": "RotationCounterClockwiseSlowToFast",
                            "name": "CCW rotation"
                        }
                    ]
                }
            ],
            "modes": [
                {
                    "name": "Standard",
                    "channels": [
                        {"number": 5, "name": "Gobo Rotation"}
                    ]
                }
            ]
        }
        result = find_gobo_rotation_value(fixture_def, direction="cw", speed="fast")
        assert result is not None
        channel, value = result
        assert channel == 5
        assert 0 <= value <= 127


class TestAddResetStep:

    def test_creates_reset_step(self):
        fixture_def = {
            "modes": [
                {
                    "name": "Standard",
                    "channels": [
                        {"channel": 0, "name": "Dimmer"},
                        {"channel": 1, "name": "Red"},
                    ]
                }
            ]
        }
        fixture_conf = [{"name": "Fix1"}]
        step = add_reset_step(fixture_def, "Standard", fixture_conf, 0, 0)
        assert step is not None
        assert step.tag == "Step"
        assert step.get("Number") == "0"
        assert step.get("FadeIn") == "0"

    def test_no_channels_returns_none(self):
        fixture_def = {"modes": [{"name": "Standard", "channels": []}]}
        step = add_reset_step(fixture_def, "Standard", [], 0, 0)
        assert step is None

    def test_wrong_mode_returns_none(self):
        fixture_def = {"modes": [{"name": "Other", "channels": [{"channel": 0}]}]}
        step = add_reset_step(fixture_def, "Standard", [], 0, 0)
        assert step is None