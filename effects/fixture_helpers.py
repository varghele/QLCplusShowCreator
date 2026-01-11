# effects/fixture_helpers.py
# Helper functions for per-fixture effect processing

from typing import List, Dict, Any, Tuple, Optional
from utils.effects_utils import get_channels_by_property


def get_fixture_def(fixture, fixture_definitions: Dict[str, Any]) -> Optional[Dict]:
    """Get the fixture definition for a specific fixture.

    Args:
        fixture: Fixture object with manufacturer and model attributes
        fixture_definitions: Dict mapping "manufacturer_model" to fixture definitions

    Returns:
        Fixture definition dict or None if not found
    """
    fixture_key = f"{fixture.manufacturer}_{fixture.model}"
    return fixture_definitions.get(fixture_key)


def get_fixture_dimmer_channels(fixture, fixture_definitions: Dict[str, Any]) -> List[Dict]:
    """Get dimmer channel info for a specific fixture.

    Args:
        fixture: Fixture object
        fixture_definitions: Dict of fixture definitions

    Returns:
        List of channel info dicts with 'channel' key, or dummy [{'channel': 0}] if none found
    """
    fixture_def = get_fixture_def(fixture, fixture_definitions)
    if not fixture_def:
        return [{'channel': 0}]

    channels_dict = get_channels_by_property(
        fixture_def, fixture.current_mode, ["IntensityDimmer"]
    )

    if not channels_dict or 'IntensityDimmer' not in channels_dict:
        # No dimmer channels - return dummy for RGB-only fixtures
        return [{'channel': 0}]

    return channels_dict['IntensityDimmer']


def get_fixture_colour_channels(fixture, fixture_definitions: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """Get colour channel info for a specific fixture.

    Args:
        fixture: Fixture object
        fixture_definitions: Dict of fixture definitions

    Returns:
        Dict mapping colour type to list of channel info dicts
    """
    fixture_def = get_fixture_def(fixture, fixture_definitions)
    if not fixture_def:
        return {}

    return get_channels_by_property(
        fixture_def, fixture.current_mode,
        ["ColorIntensityRed", "ColorIntensityGreen", "ColorIntensityBlue",
         "ColorIntensityWhite", "ColorIntensityAmber", "ColorIntensityUV"]
    ) or {}


def sort_fixtures_by_position(fixtures: List, axis: str = 'x', reverse: bool = False) -> List[Tuple[int, Any]]:
    """Sort fixtures by position and return with original indices.

    Args:
        fixtures: List of fixture objects with x, y, z attributes
        axis: Which axis to sort by ('x', 'y', or 'z')
        reverse: Whether to reverse the sort order

    Returns:
        List of (original_index, fixture) tuples sorted by position
    """
    indexed_fixtures = list(enumerate(fixtures))

    if axis == 'x':
        indexed_fixtures.sort(key=lambda item: item[1].x, reverse=reverse)
    elif axis == 'y':
        indexed_fixtures.sort(key=lambda item: item[1].y, reverse=reverse)
    elif axis == 'z':
        indexed_fixtures.sort(key=lambda item: item[1].z, reverse=reverse)

    return indexed_fixtures


def build_fixture_value_string(
    fixture,
    fixture_id: int,
    fixture_definitions: Dict[str, Any],
    channel_type: str,
    value: int
) -> str:
    """Build a QLC+ value string for a fixture's channels.

    Args:
        fixture: Fixture object
        fixture_id: QLC+ fixture ID
        fixture_definitions: Dict of fixture definitions
        channel_type: Type of channels ('dimmer', 'red', 'green', 'blue', etc.)
        value: Value to set (0-255)

    Returns:
        Value string like "5:0,200" (fixture_id:channel,value,channel,value,...)
    """
    if channel_type == 'dimmer':
        channels = get_fixture_dimmer_channels(fixture, fixture_definitions)
        channel_values = []
        for ch_info in channels:
            channel_values.extend([str(ch_info['channel']), str(value)])
        return f"{fixture_id}:{','.join(channel_values)}"

    # For colour channels
    colour_channels = get_fixture_colour_channels(fixture, fixture_definitions)

    property_map = {
        'red': 'ColorIntensityRed',
        'green': 'ColorIntensityGreen',
        'blue': 'ColorIntensityBlue',
        'white': 'ColorIntensityWhite',
        'amber': 'ColorIntensityAmber',
        'uv': 'ColorIntensityUV',
    }

    prop = property_map.get(channel_type)
    if prop and prop in colour_channels:
        channel_values = []
        for ch_info in colour_channels[prop]:
            channel_values.extend([str(ch_info['channel']), str(value)])
        return f"{fixture_id}:{','.join(channel_values)}"

    return f"{fixture_id}:"


def build_dimmer_values_for_fixtures(
    fixtures: List,
    fixture_id_map: Dict[int, int],
    fixture_definitions: Dict[str, Any],
    intensity_per_fixture: List[int]
) -> str:
    """Build combined value string for all fixtures with per-fixture intensities.

    Args:
        fixtures: List of fixture objects
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID
        fixture_definitions: Dict of fixture definitions
        intensity_per_fixture: List of intensity values (0-255) per fixture

    Returns:
        Combined value string for QLC+ step
    """
    values = []
    for i, fixture in enumerate(fixtures):
        fixture_id = fixture_id_map[id(fixture)]
        intensity = intensity_per_fixture[i] if i < len(intensity_per_fixture) else 0
        channels = get_fixture_dimmer_channels(fixture, fixture_definitions)

        channel_values = []
        for ch_info in channels:
            channel_values.extend([str(ch_info['channel']), str(intensity)])

        values.append(f"{fixture_id}:{','.join(channel_values)}")

    return ":".join(values)


def count_total_dimmer_channels(
    fixtures: List,
    fixture_definitions: Dict[str, Any]
) -> int:
    """Count total dimmer channels across all fixtures.

    Args:
        fixtures: List of fixture objects
        fixture_definitions: Dict of fixture definitions

    Returns:
        Total number of dimmer channels
    """
    total = 0
    for fixture in fixtures:
        channels = get_fixture_dimmer_channels(fixture, fixture_definitions)
        total += len(channels)
    return total
