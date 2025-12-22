# utils/sublane_presets.py
# Categorization of QLC+ fixture presets into sublanes

"""
This module maps QLC+ channel presets to sublane categories.
Used for automatic fixture capability detection.

Reference: SUBLANE_FEATURE_PLAN.md - QLC+ Preset Categorization
"""

from typing import Set
from enum import Enum


class SublaneType(Enum):
    """Sublane type enumeration."""
    DIMMER = "dimmer"
    COLOUR = "colour"
    MOVEMENT = "movement"
    SPECIAL = "special"


# Dimmer Sublane Presets
DIMMER_PRESETS: Set[str] = {
    "IntensityMasterDimmer",
    "IntensityMasterDimmerFine",
    "IntensityDimmer",
    "IntensityDimmerFine",
    "ShutterStrobeSlowFast",
    "ShutterStrobeFastSlow",
    "ShutterIrisMinToMax",
    "ShutterIrisMaxToMin",
    "ShutterIrisFine",
}

# Colour Sublane Presets
COLOUR_PRESETS: Set[str] = {
    # RGB Components
    "IntensityRed",
    "IntensityRedFine",
    "IntensityGreen",
    "IntensityGreenFine",
    "IntensityBlue",
    "IntensityBlueFine",

    # CMY Components
    "IntensityCyan",
    "IntensityCyanFine",
    "IntensityMagenta",
    "IntensityMagentaFine",
    "IntensityYellow",
    "IntensityYellowFine",

    # Additional Colors
    "IntensityAmber",
    "IntensityAmberFine",
    "IntensityWhite",
    "IntensityWhiteFine",
    "IntensityUV",
    "IntensityUVFine",
    "IntensityIndigo",
    "IntensityIndigoFine",
    "IntensityLime",
    "IntensityLimeFine",

    # HSV/HSL
    "IntensityHue",
    "IntensityHueFine",
    "IntensitySaturation",
    "IntensitySaturationFine",
    "IntensityLightness",
    "IntensityLightnessFine",
    "IntensityValue",
    "IntensityValueFine",

    # Color Selection
    "ColorMacro",
    "ColorWheel",
    "ColorWheelFine",
    "ColorRGBMixer",
    "ColorCTOMixer",
    "ColorCTCMixer",
    "ColorCTBMixer",
}

# Movement Sublane Presets
MOVEMENT_PRESETS: Set[str] = {
    # Position
    "PositionPan",
    "PositionPanFine",
    "PositionTilt",
    "PositionTiltFine",
    "PositionXAxis",
    "PositionYAxis",

    # Speed
    "SpeedPanSlowFast",
    "SpeedPanFastSlow",
    "SpeedTiltSlowFast",
    "SpeedTiltFastSlow",
    "SpeedPanTiltSlowFast",
    "SpeedPanTiltFastSlow",
}

# Special Sublane Presets
SPECIAL_PRESETS: Set[str] = {
    # Gobo
    "GoboWheel",
    "GoboWheelFine",
    "GoboIndex",
    "GoboIndexFine",

    # Beam
    "BeamFocusNearFar",
    "BeamFocusFarNear",
    "BeamFocusFine",
    "BeamZoomSmallBig",
    "BeamZoomBigSmall",
    "BeamZoomFine",

    # Prism
    "PrismRotationSlowFast",
    "PrismRotationFastSlow",
}

# Uncategorized/Ignored Presets
IGNORED_PRESETS: Set[str] = {
    "Custom",
    "NoFunction",
}


def categorize_preset(preset: str) -> SublaneType | None:
    """
    Categorize a QLC+ channel preset into a sublane type.

    Args:
        preset: The preset string from a fixture channel (e.g., "IntensityRed")

    Returns:
        SublaneType if the preset is categorized, None if uncategorized/ignored

    Examples:
        >>> categorize_preset("IntensityRed")
        SublaneType.COLOUR

        >>> categorize_preset("PositionPan")
        SublaneType.MOVEMENT

        >>> categorize_preset("NoFunction")
        None
    """
    if preset in DIMMER_PRESETS:
        return SublaneType.DIMMER
    elif preset in COLOUR_PRESETS:
        return SublaneType.COLOUR
    elif preset in MOVEMENT_PRESETS:
        return SublaneType.MOVEMENT
    elif preset in SPECIAL_PRESETS:
        return SublaneType.SPECIAL
    elif preset in IGNORED_PRESETS:
        return None
    else:
        # Unknown preset - could log a warning
        return None


def get_all_presets_for_sublane(sublane_type: SublaneType) -> Set[str]:
    """
    Get all presets for a given sublane type.

    Args:
        sublane_type: The sublane type

    Returns:
        Set of preset strings for that sublane
    """
    if sublane_type == SublaneType.DIMMER:
        return DIMMER_PRESETS
    elif sublane_type == SublaneType.COLOUR:
        return COLOUR_PRESETS
    elif sublane_type == SublaneType.MOVEMENT:
        return MOVEMENT_PRESETS
    elif sublane_type == SublaneType.SPECIAL:
        return SPECIAL_PRESETS
    else:
        return set()


# Preset to human-readable name mapping (for UI display)
PRESET_DISPLAY_NAMES = {
    # Dimmer
    "IntensityMasterDimmer": "Master Dimmer",
    "IntensityDimmer": "Dimmer",
    "ShutterStrobeSlowFast": "Strobe",
    "ShutterIrisMinToMax": "Iris",

    # Colour - RGB
    "IntensityRed": "Red",
    "IntensityGreen": "Green",
    "IntensityBlue": "Blue",
    "IntensityWhite": "White",

    # Colour - CMY
    "IntensityCyan": "Cyan",
    "IntensityMagenta": "Magenta",
    "IntensityYellow": "Yellow",

    # Colour - Other
    "IntensityAmber": "Amber",
    "IntensityUV": "UV",
    "IntensityLime": "Lime",
    "IntensityIndigo": "Indigo",

    # Colour - HSV
    "IntensityHue": "Hue",
    "IntensitySaturation": "Saturation",
    "IntensityValue": "Value",
    "IntensityLightness": "Lightness",

    # Colour - Wheel
    "ColorWheel": "Color Wheel",
    "ColorMacro": "Color Macro",

    # Movement
    "PositionPan": "Pan",
    "PositionTilt": "Tilt",
    "PositionXAxis": "X-Axis",
    "PositionYAxis": "Y-Axis",
    "SpeedPanTiltSlowFast": "Pan/Tilt Speed",

    # Special
    "GoboWheel": "Gobo Wheel",
    "GoboIndex": "Gobo Index",
    "BeamFocusNearFar": "Focus",
    "BeamZoomSmallBig": "Zoom",
    "PrismRotationSlowFast": "Prism",
}


def get_preset_display_name(preset: str) -> str:
    """
    Get human-readable display name for a preset.

    Args:
        preset: The preset string

    Returns:
        Display name, or the preset itself if no mapping exists
    """
    return PRESET_DISPLAY_NAMES.get(preset, preset)
