# tests/unit/test_sublane_presets.py
"""Unit tests for utils/sublane_presets.py - preset categorization."""

import pytest
from utils.sublane_presets import (
    SublaneType, categorize_preset, get_all_presets_for_sublane,
    get_preset_display_name,
    DIMMER_PRESETS, COLOUR_PRESETS, MOVEMENT_PRESETS, SPECIAL_PRESETS,
    IGNORED_PRESETS,
)


class TestSublaneType:

    def test_enum_values(self):
        assert SublaneType.DIMMER.value == "dimmer"
        assert SublaneType.COLOUR.value == "colour"
        assert SublaneType.MOVEMENT.value == "movement"
        assert SublaneType.SPECIAL.value == "special"


class TestCategorizePreset:

    @pytest.mark.parametrize("preset", [
        "IntensityMasterDimmer", "IntensityDimmer", "ShutterStrobeSlowFast",
    ])
    def test_dimmer_presets(self, preset):
        assert categorize_preset(preset) == SublaneType.DIMMER

    @pytest.mark.parametrize("preset", [
        "IntensityRed", "IntensityGreen", "IntensityBlue", "IntensityWhite",
        "IntensityAmber", "IntensityUV", "ColorWheel", "ColorMacro",
        "IntensityHue", "IntensitySaturation",
    ])
    def test_colour_presets(self, preset):
        assert categorize_preset(preset) == SublaneType.COLOUR

    @pytest.mark.parametrize("preset", [
        "PositionPan", "PositionTilt", "PositionPanFine", "SpeedPanTiltSlowFast",
    ])
    def test_movement_presets(self, preset):
        assert categorize_preset(preset) == SublaneType.MOVEMENT

    @pytest.mark.parametrize("preset", [
        "GoboWheel", "GoboIndex", "BeamFocusNearFar", "BeamZoomSmallBig",
        "PrismRotationSlowFast",
    ])
    def test_special_presets(self, preset):
        assert categorize_preset(preset) == SublaneType.SPECIAL

    @pytest.mark.parametrize("preset", ["Custom", "NoFunction"])
    def test_ignored_presets(self, preset):
        assert categorize_preset(preset) is None

    def test_unknown_preset(self):
        assert categorize_preset("SomethingNew") is None


class TestGetAllPresetsForSublane:

    def test_dimmer(self):
        result = get_all_presets_for_sublane(SublaneType.DIMMER)
        assert result is DIMMER_PRESETS
        assert "IntensityMasterDimmer" in result

    def test_colour(self):
        result = get_all_presets_for_sublane(SublaneType.COLOUR)
        assert result is COLOUR_PRESETS
        assert "IntensityRed" in result

    def test_movement(self):
        result = get_all_presets_for_sublane(SublaneType.MOVEMENT)
        assert result is MOVEMENT_PRESETS
        assert "PositionPan" in result

    def test_special(self):
        result = get_all_presets_for_sublane(SublaneType.SPECIAL)
        assert result is SPECIAL_PRESETS
        assert "GoboWheel" in result


class TestPresetSetsNoOverlap:
    """Ensure no preset appears in multiple categories."""

    def test_no_overlap(self):
        all_sets = [DIMMER_PRESETS, COLOUR_PRESETS, MOVEMENT_PRESETS,
                    SPECIAL_PRESETS, IGNORED_PRESETS]
        for i, a in enumerate(all_sets):
            for j, b in enumerate(all_sets):
                if i < j:
                    overlap = a & b
                    assert overlap == set(), f"Overlap between sets {i} and {j}: {overlap}"


class TestGetPresetDisplayName:

    def test_known_preset(self):
        assert get_preset_display_name("IntensityRed") == "Red"
        assert get_preset_display_name("PositionPan") == "Pan"
        assert get_preset_display_name("GoboWheel") == "Gobo Wheel"

    def test_unknown_preset_returns_itself(self):
        assert get_preset_display_name("UnknownPreset") == "UnknownPreset"