# utils/to_xml/preset_scenes_to_xml.py
# Generates preset Scene and EFX functions for Virtual Console

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Any, Optional
from config.models import Configuration, FixtureGroup, FixtureGroupCapabilities
from utils.effects_utils import get_channels_by_property
from utils.sublane_presets import COLOUR_PRESETS, DIMMER_PRESETS, MOVEMENT_PRESETS
from utils.orientation import calculate_pan_tilt, pan_tilt_to_dmx


# Helper functions for fixture channel detection
def get_fixture_channels_for_preset(
    fixture,
    fixture_definitions: Dict[str, Any],
    preset_names: List[str]
) -> Tuple[Dict[str, List[int]], int]:
    """Get channels matching specific presets for a fixture.

    Returns:
        Tuple of (channels_dict, total_channels)
        channels_dict maps preset names to lists of channel numbers
    """
    fixture_key = f"{fixture.manufacturer}_{fixture.model}"
    fixture_def = fixture_definitions.get(fixture_key)

    if not fixture_def:
        return {}, 0

    mode = next((m for m in fixture_def.get('modes', [])
                 if m['name'] == fixture.current_mode), None)
    if not mode:
        return {}, 0

    total_channels = len(mode.get('channels', []))
    channels_info = get_channels_by_property(fixture_def, fixture.current_mode, preset_names)

    # Convert to simple dict
    channels_dict = {}
    for preset, channel_list in channels_info.items():
        channels_dict[preset] = [c['channel'] for c in channel_list]

    return channels_dict, total_channels


def get_color_wheel_channel(fixture, fixture_definitions: Dict[str, Any]) -> Optional[int]:
    """Get the color wheel channel number for a fixture, if it has one."""
    fixture_key = f"{fixture.manufacturer}_{fixture.model}"
    fixture_def = fixture_definitions.get(fixture_key)

    if not fixture_def:
        return None

    mode = next((m for m in fixture_def.get('modes', [])
                 if m['name'] == fixture.current_mode), None)
    if not mode:
        return None

    # Find a channel with group="Colour" or group="Color"
    for channel_mapping in mode.get('channels', []):
        channel_number = channel_mapping.get('number')
        channel_name = channel_mapping.get('name')

        # Find the channel definition
        channel_def = next((ch for ch in fixture_def.get('channels', [])
                           if ch.get('name') == channel_name), None)

        if channel_def:
            group = channel_def.get('group', '')
            if group and group.lower() in ['colour', 'color']:
                return channel_number

    return None


# Color preset definitions (RGB values for RGB fixtures)
COLOR_PRESETS_RGB = {
    "Red": {"IntensityRed": 255, "IntensityGreen": 0, "IntensityBlue": 0},
    "Green": {"IntensityRed": 0, "IntensityGreen": 255, "IntensityBlue": 0},
    "Blue": {"IntensityRed": 0, "IntensityGreen": 0, "IntensityBlue": 255},
    "White": {"IntensityRed": 255, "IntensityGreen": 255, "IntensityBlue": 255, "IntensityWhite": 255},
    "Amber": {"IntensityRed": 255, "IntensityGreen": 176, "IntensityBlue": 0, "IntensityAmber": 255},
    "Cyan": {"IntensityRed": 0, "IntensityGreen": 255, "IntensityBlue": 255, "IntensityCyan": 255},
    "Magenta": {"IntensityRed": 255, "IntensityGreen": 0, "IntensityBlue": 255, "IntensityMagenta": 255},
    "Yellow": {"IntensityRed": 255, "IntensityGreen": 255, "IntensityBlue": 0, "IntensityYellow": 255},
    "UV": {"IntensityUV": 255},
    "Blackout": {},  # All channels to 0
}

# Color preset hex values (for matching to color wheel)
COLOR_PRESETS_HEX = {
    "Red": "#FF0000",
    "Green": "#00FF00",
    "Blue": "#0000FF",
    "White": "#FFFFFF",
    "Amber": "#FFAA00",
    "Cyan": "#00FFFF",
    "Magenta": "#FF00FF",
    "Yellow": "#FFFF00",
    "UV": "#8000FF",
    "Blackout": None,  # Special case
}

# Intensity preset values (0-255)
INTENSITY_PRESETS = {
    "25%": 64,
    "50%": 128,
    "75%": 191,
    "100%": 255,
}

# Movement preset positions (world coordinates in meters)
# Stage coordinate system: +X = stage right, +Y = upstage (back), +Z = up
# Origin (0,0,0) = center of stage floor
MOVEMENT_PRESETS_POS = {
    "Center": {"x": 0.0, "y": 0.0, "z": 2.0},     # Center of stage, at head height
    "Front": {"x": 0.0, "y": -4.0, "z": 2.0},     # Front of stage (toward audience)
    "Up": {"x": 0.0, "y": 0.0, "z": 5.0},         # Straight up toward ceiling
    "Left": {"x": -4.0, "y": 0.0, "z": 2.0},      # Stage left
    "Right": {"x": 4.0, "y": 0.0, "z": 2.0},      # Stage right
}


def create_scene_function(
    engine: ET.Element,
    function_id: int,
    name: str,
    fixture_values: List[Tuple[int, str]],  # [(fixture_id, "ch,val,ch,val,..."), ...]
    hidden: bool = False
) -> ET.Element:
    """Create a Scene function element.

    Args:
        engine: Engine XML element to append to
        function_id: Unique function ID
        name: Scene name
        fixture_values: List of (fixture_id, channel_values_string) tuples
        hidden: Whether to hide the scene in QLC+ function list

    Returns:
        Scene function element
    """
    scene = ET.SubElement(engine, "Function")
    scene.set("ID", str(function_id))
    scene.set("Type", "Scene")
    scene.set("Name", name)
    if hidden:
        scene.set("Hidden", "True")

    # Add Speed element
    speed = ET.SubElement(scene, "Speed")
    speed.set("FadeIn", "0")
    speed.set("FadeOut", "0")
    speed.set("Duration", "0")

    # Add FixtureVal for each fixture
    for fixture_id, channel_values in fixture_values:
        fixture_val = ET.SubElement(scene, "FixtureVal")
        fixture_val.set("ID", str(fixture_id))
        fixture_val.text = channel_values

    return scene


def create_efx_function(
    engine: ET.Element,
    function_id: int,
    name: str,
    pattern: str,  # "Circle", "Eight", "Line", etc.
    fixtures: List[Tuple[int, int, int]],  # [(fixture_id, pan_channel, tilt_channel), ...]
    width: int = 127,
    height: int = 127,
    x_offset: int = 127,
    y_offset: int = 127,
    speed: int = 4000  # Duration in ms
) -> ET.Element:
    """Create an EFX (effect) function element for movement patterns.

    Args:
        engine: Engine XML element to append to
        function_id: Unique function ID
        name: EFX name
        pattern: Movement pattern type
        fixtures: List of (fixture_id, pan_channel, tilt_channel) tuples
        width, height: Pattern dimensions (0-255)
        x_offset, y_offset: Pattern center position (0-255)
        speed: Pattern speed in milliseconds

    Returns:
        EFX function element
    """
    efx = ET.SubElement(engine, "Function")
    efx.set("ID", str(function_id))
    efx.set("Type", "EFX")
    efx.set("Name", name)

    # Add fixtures first (per QLC+ format)
    for i, (fixture_id, pan_ch, tilt_ch) in enumerate(fixtures):
        fixture_elem = ET.SubElement(efx, "Fixture")
        ET.SubElement(fixture_elem, "ID").text = str(fixture_id)
        ET.SubElement(fixture_elem, "Head").text = "0"
        ET.SubElement(fixture_elem, "Mode").text = "0"  # Position mode
        ET.SubElement(fixture_elem, "Direction").text = "Forward"
        ET.SubElement(fixture_elem, "StartOffset").text = "0"

    # Propagation mode
    ET.SubElement(efx, "PropagationMode").text = "Parallel"

    # Speed settings
    speed_elem = ET.SubElement(efx, "Speed")
    speed_elem.set("FadeIn", "0")
    speed_elem.set("FadeOut", "0")
    speed_elem.set("Duration", str(speed))

    # Direction and run order
    ET.SubElement(efx, "Direction").text = "Forward"
    ET.SubElement(efx, "RunOrder").text = "Loop"

    # Algorithm (pattern type)
    ET.SubElement(efx, "Algorithm").text = pattern

    # Pattern dimensions
    ET.SubElement(efx, "Width").text = str(width)
    ET.SubElement(efx, "Height").text = str(height)
    ET.SubElement(efx, "Rotation").text = "0"
    ET.SubElement(efx, "StartOffset").text = "0"
    ET.SubElement(efx, "IsRelative").text = "0"

    # Axis elements (new format instead of XOffset/YOffset)
    x_axis = ET.SubElement(efx, "Axis")
    x_axis.set("Name", "X")
    ET.SubElement(x_axis, "Offset").text = str(x_offset)
    ET.SubElement(x_axis, "Frequency").text = "2"
    ET.SubElement(x_axis, "Phase").text = "90"

    y_axis = ET.SubElement(efx, "Axis")
    y_axis.set("Name", "Y")
    ET.SubElement(y_axis, "Offset").text = str(y_offset)
    ET.SubElement(y_axis, "Frequency").text = "3"
    ET.SubElement(y_axis, "Phase").text = "0"

    return efx


def get_fixture_channel_info(
    fixture,
    fixture_definitions: Dict[str, Any]
) -> Tuple[Dict[str, List[int]], int]:
    """Get channel information for a fixture.

    Args:
        fixture: Fixture object
        fixture_definitions: Dictionary of fixture definitions

    Returns:
        Tuple of (channels_by_preset, total_channels)
        channels_by_preset: Dict mapping preset names to list of channel numbers
    """
    fixture_key = f"{fixture.manufacturer}_{fixture.model}"
    fixture_def = fixture_definitions.get(fixture_key)

    if not fixture_def:
        return {}, 0

    # Get total channel count
    mode = next((m for m in fixture_def.get('modes', [])
                 if m['name'] == fixture.current_mode), None)
    if not mode:
        return {}, 0

    total_channels = len(mode.get('channels', []))

    # Get channels by property
    all_presets = list(COLOUR_PRESETS) + list(DIMMER_PRESETS) + list(MOVEMENT_PRESETS)
    channels_info = get_channels_by_property(fixture_def, fixture.current_mode, all_presets)

    # Convert to simple dict of preset -> [channel_numbers]
    channels_by_preset = {}
    for preset, channel_list in channels_info.items():
        channels_by_preset[preset] = [c['channel'] for c in channel_list]

    return channels_by_preset, total_channels


def get_color_wheel_info(
    fixture,
    fixture_definitions: Dict[str, Any]
) -> Tuple[int, List[Dict[str, Any]]]:
    """Get color wheel channel and available colors for a fixture.

    Args:
        fixture: Fixture object
        fixture_definitions: Dictionary of fixture definitions

    Returns:
        Tuple of (color_wheel_channel, color_options)
        color_wheel_channel: Channel number for color wheel, or None
        color_options: List of dicts with 'name', 'dmx_value', 'hex_color'
    """
    fixture_key = f"{fixture.manufacturer}_{fixture.model}"
    fixture_def = fixture_definitions.get(fixture_key)

    if not fixture_def:
        return None, []

    mode = next((m for m in fixture_def.get('modes', [])
                 if m['name'] == fixture.current_mode), None)
    if not mode:
        return None, []

    # Find color wheel channel
    color_wheel_channel = None
    color_options = []

    for channel_mapping in mode.get('channels', []):
        channel_number = channel_mapping.get('number')
        channel_name = channel_mapping.get('name')

        # Find the channel definition
        channel_def = next((ch for ch in fixture_def.get('channels', [])
                           if ch.get('name') == channel_name), None)

        if not channel_def:
            continue

        # Check if this is a color wheel channel
        group = channel_def.get('group', '')
        if group and group.lower() in ['colour', 'color']:
            color_wheel_channel = channel_number

            # Extract color options from capabilities
            for cap in channel_def.get('capabilities', []):
                preset = cap.get('preset', '')
                name = cap.get('name', '')
                hex_color = cap.get('color')  # May be in 'color' key from parsing

                # Get hex color from Res1 if available
                if not hex_color:
                    res1 = cap.get('res1', '')
                    if res1 and res1.startswith('#'):
                        hex_color = res1

                # Skip rotation/rainbow effects
                if 'Rainbow' in name or 'Rotation' in name:
                    continue

                # Calculate middle of DMX range
                dmx_value = (cap.get('min', 0) + cap.get('max', 0)) // 2

                if name:
                    color_options.append({
                        'name': name.lower(),
                        'dmx_value': dmx_value,
                        'hex_color': hex_color
                    })

            break  # Found color wheel

    return color_wheel_channel, color_options


def find_color_wheel_dmx(color_name: str, color_options: List[Dict[str, Any]], target_hex: str = None) -> int:
    """Find DMX value for a color name or hex in color wheel options.

    Args:
        color_name: Color name to search for (e.g., "Red")
        color_options: List of color options from get_color_wheel_info
        target_hex: Optional hex color to match against

    Returns:
        DMX value for the color, or None if not found
    """
    color_name_lower = color_name.lower()

    # First try exact name match
    for option in color_options:
        if option['name'] == color_name_lower:
            return option['dmx_value']

    # Try partial name match (but prefer shorter matches to avoid "blue" matching "light blue")
    best_name_match = None
    best_name_length = float('inf')
    for option in color_options:
        if color_name_lower in option['name']:
            if len(option['name']) < best_name_length:
                best_name_length = len(option['name'])
                best_name_match = option['dmx_value']

    if best_name_match is not None:
        return best_name_match

    # Try matching by hex color if provided
    if target_hex:
        target_hex = target_hex.upper()
        best_match = None
        min_distance = float('inf')

        for option in color_options:
            opt_hex = option.get('hex_color', '')
            if not opt_hex or not opt_hex.startswith('#'):
                continue

            opt_hex = opt_hex.upper()

            # Calculate color distance
            try:
                tr = int(target_hex[1:3], 16)
                tg = int(target_hex[3:5], 16)
                tb = int(target_hex[5:7], 16)

                or_ = int(opt_hex[1:3], 16)
                og = int(opt_hex[3:5], 16)
                ob = int(opt_hex[5:7], 16)

                distance = ((tr - or_) ** 2 + (tg - og) ** 2 + (tb - ob) ** 2) ** 0.5

                if distance < min_distance:
                    min_distance = distance
                    best_match = option['dmx_value']
            except (ValueError, IndexError):
                continue

        if best_match is not None:
            return best_match

    return None


def create_color_preset_scene(
    engine: ET.Element,
    function_id: int,
    group_name: str,
    color_name: str,
    color_values: Dict[str, int],
    group: FixtureGroup,
    fixture_id_map: Dict[int, int],
    fixture_definitions: Dict[str, Any]
) -> ET.Element:
    """Create a color preset scene for a fixture group.

    Handles both RGB fixtures and color wheel fixtures.

    Args:
        engine: Engine XML element
        function_id: Unique function ID
        group_name: Name of the fixture group
        color_name: Name of the color preset
        color_values: Dict mapping preset names to values (for RGB fixtures)
        group: FixtureGroup object
        fixture_id_map: Mapping of fixture object IDs to QLC+ fixture IDs
        fixture_definitions: Dictionary of fixture definitions

    Returns:
        Scene function element
    """
    scene_name = f"{group_name} - {color_name}"
    fixture_values = []

    # Get target hex color for color wheel matching
    target_hex = COLOR_PRESETS_HEX.get(color_name)

    for fixture in group.fixtures:
        fixture_id = fixture_id_map.get(id(fixture))
        if fixture_id is None:
            continue

        channels_by_preset, total_channels = get_fixture_channel_info(
            fixture, fixture_definitions
        )

        # Check for color wheel
        color_wheel_ch, color_options = get_color_wheel_info(fixture, fixture_definitions)

        # Check if this fixture has RGB channels
        has_rgb = any(preset in channels_by_preset for preset in
                     ["IntensityRed", "IntensityGreen", "IntensityBlue"])

        # Build channel values - only set the channels we're controlling
        channel_vals = {}

        if color_name == "Blackout":
            # Blackout: set dimmer to 0
            for preset in ["IntensityMasterDimmer", "IntensityDimmer"]:
                if preset in channels_by_preset:
                    for ch in channels_by_preset[preset]:
                        channel_vals[ch] = 0
        elif has_rgb:
            # RGB fixture: set RGB channels
            for preset_name, value in color_values.items():
                if preset_name in channels_by_preset:
                    for ch in channels_by_preset[preset_name]:
                        channel_vals[ch] = value

            # Set dimmer to full
            for preset in ["IntensityMasterDimmer", "IntensityDimmer"]:
                if preset in channels_by_preset:
                    for ch in channels_by_preset[preset]:
                        channel_vals[ch] = 255
        elif color_wheel_ch is not None and color_options:
            # Color wheel fixture: find matching color DMX value
            dmx_value = find_color_wheel_dmx(color_name, color_options, target_hex)
            if dmx_value is not None:
                channel_vals[color_wheel_ch] = dmx_value

            # Set dimmer to full
            for preset in ["IntensityMasterDimmer", "IntensityDimmer"]:
                if preset in channels_by_preset:
                    for ch in channels_by_preset[preset]:
                        channel_vals[ch] = 255

        # Only add fixture if we have channel values to set
        if channel_vals:
            channel_str = ",".join(f"{ch},{val}" for ch, val in sorted(channel_vals.items()))
            fixture_values.append((fixture_id, channel_str))

    return create_scene_function(engine, function_id, scene_name, fixture_values)


def create_intensity_preset_scene(
    engine: ET.Element,
    function_id: int,
    group_name: str,
    intensity_name: str,
    intensity_value: int,
    group: FixtureGroup,
    fixture_id_map: Dict[int, int],
    fixture_definitions: Dict[str, Any]
) -> ET.Element:
    """Create an intensity preset scene for a fixture group.

    Args:
        engine: Engine XML element
        function_id: Unique function ID
        group_name: Name of the fixture group
        intensity_name: Name of the intensity preset (e.g., "50%")
        intensity_value: DMX value (0-255)
        group: FixtureGroup object
        fixture_id_map: Mapping of fixture object IDs to QLC+ fixture IDs
        fixture_definitions: Dictionary of fixture definitions

    Returns:
        Scene function element
    """
    scene_name = f"{group_name} - {intensity_name}"
    fixture_values = []

    for fixture in group.fixtures:
        fixture_id = fixture_id_map.get(id(fixture))
        if fixture_id is None:
            continue

        channels_by_preset, total_channels = get_fixture_channel_info(
            fixture, fixture_definitions
        )

        # Build channel values - only set dimmer channels
        channel_vals = {}

        # Set dimmer channels
        for preset in ["IntensityMasterDimmer", "IntensityDimmer"]:
            if preset in channels_by_preset:
                for ch in channels_by_preset[preset]:
                    channel_vals[ch] = intensity_value

        # If fixture has no dedicated dimmer, try setting RGB all to same value
        if not channel_vals:
            for preset in ["IntensityRed", "IntensityGreen", "IntensityBlue"]:
                if preset in channels_by_preset:
                    for ch in channels_by_preset[preset]:
                        channel_vals[ch] = intensity_value

        # Convert to string format
        channel_str = ",".join(f"{ch},{val}" for ch, val in sorted(channel_vals.items()))
        fixture_values.append((fixture_id, channel_str))

    return create_scene_function(engine, function_id, scene_name, fixture_values)


def create_movement_preset_scene(
    engine: ET.Element,
    function_id: int,
    group_name: str,
    position_name: str,
    position: Dict[str, float],
    group: FixtureGroup,
    fixture_id_map: Dict[int, int],
    fixture_definitions: Dict[str, Any]
) -> ET.Element:
    """Create a movement position preset scene for a fixture group.

    Args:
        engine: Engine XML element
        function_id: Unique function ID
        group_name: Name of the fixture group
        position_name: Name of the position preset
        position: Dict with 'x', 'y', 'z' world coordinates (meters)
        group: FixtureGroup object
        fixture_id_map: Mapping of fixture object IDs to QLC+ fixture IDs
        fixture_definitions: Dictionary of fixture definitions

    Returns:
        Scene function element
    """
    scene_name = f"{group_name} - {position_name}"
    fixture_values = []

    # Get target position from preset
    target_x = position.get("x", 0.0)
    target_y = position.get("y", 0.0)
    target_z = position.get("z", 2.0)

    for fixture in group.fixtures:
        fixture_id = fixture_id_map.get(id(fixture))
        if fixture_id is None:
            continue

        channels_by_preset, total_channels = get_fixture_channel_info(
            fixture, fixture_definitions
        )

        # Get fixture orientation
        mounting = getattr(fixture, 'mounting', 'hanging')
        yaw = getattr(fixture, 'yaw', 0.0)
        pitch = getattr(fixture, 'pitch', 0.0)
        roll = getattr(fixture, 'roll', 0.0)

        # Get fixture position
        fixture_x = getattr(fixture, 'x', 0.0)
        fixture_y = getattr(fixture, 'y', 0.0)
        fixture_z = getattr(fixture, 'z', 3.0)

        # Calculate pan/tilt angles to point at target
        pan_deg, tilt_deg = calculate_pan_tilt(
            fixture_x, fixture_y, fixture_z,
            target_x, target_y, target_z,
            mounting, yaw, pitch, roll
        )

        # Convert to DMX values
        pan_dmx, tilt_dmx = pan_tilt_to_dmx(pan_deg, tilt_deg)

        channel_vals = {}

        # Set pan channel
        if "PositionPan" in channels_by_preset:
            for ch in channels_by_preset["PositionPan"]:
                channel_vals[ch] = pan_dmx

        # Set tilt channel
        if "PositionTilt" in channels_by_preset:
            for ch in channels_by_preset["PositionTilt"]:
                channel_vals[ch] = tilt_dmx

        # Convert to string format
        if channel_vals:
            channel_str = ",".join(f"{ch},{val}" for ch, val in sorted(channel_vals.items()))
            fixture_values.append((fixture_id, channel_str))

    return create_scene_function(engine, function_id, scene_name, fixture_values)


def create_movement_efx_pattern(
    engine: ET.Element,
    function_id: int,
    group_name: str,
    pattern_name: str,
    group: FixtureGroup,
    fixture_id_map: Dict[int, int],
    fixture_definitions: Dict[str, Any]
) -> ET.Element:
    """Create a movement EFX pattern for a fixture group.

    Args:
        engine: Engine XML element
        function_id: Unique function ID
        group_name: Name of the fixture group
        pattern_name: Pattern type ("Circle", "Eight", "Line", etc.)
        group: FixtureGroup object
        fixture_id_map: Mapping of fixture object IDs to QLC+ fixture IDs
        fixture_definitions: Dictionary of fixture definitions

    Returns:
        EFX function element
    """
    efx_name = f"{group_name} - {pattern_name}"
    fixtures = []

    for fixture in group.fixtures:
        fixture_id = fixture_id_map.get(id(fixture))
        if fixture_id is None:
            continue

        channels_by_preset, _ = get_fixture_channel_info(fixture, fixture_definitions)

        # Get pan and tilt channels
        pan_ch = channels_by_preset.get("PositionPan", [None])[0]
        tilt_ch = channels_by_preset.get("PositionTilt", [None])[0]

        if pan_ch is not None and tilt_ch is not None:
            fixtures.append((fixture_id, pan_ch, tilt_ch))

    if not fixtures:
        return None

    return create_efx_function(
        engine, function_id, efx_name, pattern_name, fixtures
    )


def generate_all_preset_functions(
    engine: ET.Element,
    config: Configuration,
    fixture_id_map: Dict[int, int],
    fixture_definitions: Dict[str, Any],
    capabilities_map: Dict[str, FixtureGroupCapabilities],
    function_id_start: int,
    include_color: bool = True,
    include_intensity: bool = True,
    include_movement: bool = True
) -> Tuple[Dict[str, Dict[str, int]], int]:
    """Generate all preset functions for all groups.

    Args:
        engine: Engine XML element
        config: Configuration object
        fixture_id_map: Mapping of fixture object IDs to QLC+ fixture IDs
        fixture_definitions: Dictionary of fixture definitions
        capabilities_map: Dict mapping group names to FixtureGroupCapabilities
        function_id_start: Starting function ID
        include_color: Generate color presets
        include_intensity: Generate intensity presets
        include_movement: Generate movement presets/EFX

    Returns:
        Tuple of (preset_function_map, next_function_id)
        preset_function_map: {group_name: {preset_name: function_id, ...}, ...}
    """
    preset_function_map = {}
    function_id = function_id_start

    for group_name, group in config.groups.items():
        if not group.fixtures:
            continue

        group_presets = {}
        capabilities = capabilities_map.get(group_name, FixtureGroupCapabilities())

        # Color presets (if group has colour capability)
        if include_color and capabilities.has_colour:
            for color_name, color_values in COLOR_PRESETS_RGB.items():
                create_color_preset_scene(
                    engine, function_id, group_name, color_name,
                    color_values, group, fixture_id_map, fixture_definitions
                )
                group_presets[f"Color_{color_name}"] = function_id
                function_id += 1

        # Intensity presets (if group has dimmer or colour)
        if include_intensity and (capabilities.has_dimmer or capabilities.has_colour):
            for intensity_name, intensity_value in INTENSITY_PRESETS.items():
                create_intensity_preset_scene(
                    engine, function_id, group_name, intensity_name,
                    intensity_value, group, fixture_id_map, fixture_definitions
                )
                group_presets[f"Intensity_{intensity_name}"] = function_id
                function_id += 1

        # Movement presets (if group has movement capability)
        if include_movement and capabilities.has_movement:
            # Position presets (as scenes)
            for pos_name, position in MOVEMENT_PRESETS_POS.items():
                create_movement_preset_scene(
                    engine, function_id, group_name, pos_name,
                    position, group, fixture_id_map, fixture_definitions
                )
                group_presets[f"Position_{pos_name}"] = function_id
                function_id += 1

            # Movement patterns (as EFX)
            for pattern in ["Circle", "Eight", "Line", "Lissajous", "Triangle"]:
                efx = create_movement_efx_pattern(
                    engine, function_id, group_name, pattern,
                    group, fixture_id_map, fixture_definitions
                )
                if efx is not None:
                    group_presets[f"Pattern_{pattern}"] = function_id
                    function_id += 1

        preset_function_map[group_name] = group_presets

    return preset_function_map, function_id


def create_master_presets(
    engine: ET.Element,
    function_id: int,
    config: Configuration,
    fixture_id_map: Dict[int, int],
    fixture_definitions: Dict[str, Any]
) -> Tuple[Dict[str, int], int]:
    """Create master preset scenes and chasers that control all fixture groups.

    Returns:
        Tuple of (master_presets_map, next_function_id)
    """
    master_presets = {}

    # Get all fixtures across all groups
    all_fixtures = []
    rgb_fixtures = []  # Fixtures with RGB capability
    color_wheel_fixtures = []  # Fixtures with color wheel
    moving_head_fixtures = []  # Fixtures with pan/tilt

    for group_name, group in config.groups.items():
        for fixture in group.fixtures:
            fixture_id = fixture_id_map.get(id(fixture))
            if fixture_id is not None:
                all_fixtures.append((fixture_id, fixture))

                # Categorize by capability
                channels_dict, _ = get_fixture_channels_for_preset(
                    fixture, fixture_definitions,
                    list(COLOUR_PRESETS) + list(MOVEMENT_PRESETS)
                )

                # Check if RGB or color wheel
                if channels_dict.get("ColourRed") or channels_dict.get("ColourGreen") or channels_dict.get("ColourBlue"):
                    rgb_fixtures.append((fixture_id, fixture, channels_dict))
                elif get_color_wheel_channel(fixture, fixture_definitions) is not None:
                    color_wheel_fixtures.append((fixture_id, fixture))

                # Check if moving head
                if channels_dict.get("PositionPan") and channels_dict.get("PositionTilt"):
                    moving_head_fixtures.append((fixture_id, fixture, channels_dict))

    # Master Scene 1: All Warm White
    function_id = create_master_warm_white_scene(
        engine, function_id, all_fixtures, rgb_fixtures,
        color_wheel_fixtures, fixture_definitions, master_presets
    )

    # Master Scene 2: Red Wash
    function_id = create_master_color_wash_scene(
        engine, function_id, "Red", all_fixtures, rgb_fixtures,
        color_wheel_fixtures, fixture_definitions, master_presets
    )

    # Master Scene 3: Blue Wash
    function_id = create_master_color_wash_scene(
        engine, function_id, "Blue", all_fixtures, rgb_fixtures,
        color_wheel_fixtures, fixture_definitions, master_presets
    )

    # Master Scene 4: Purple Wash
    function_id = create_master_color_wash_scene(
        engine, function_id, "Purple", all_fixtures, rgb_fixtures,
        color_wheel_fixtures, fixture_definitions, master_presets
    )

    # Master Scene 5: Rainbow (static - different colors per group)
    function_id = create_master_rainbow_scene(
        engine, function_id, config, fixture_id_map,
        fixture_definitions, master_presets
    )

    # Chaser 1: Party (cycles through colors)
    function_id = create_party_chaser(
        engine, function_id, rgb_fixtures, color_wheel_fixtures,
        fixture_definitions, master_presets
    )

    # Chaser 2: Pulse (wave breathing effect)
    function_id = create_pulse_chaser(
        engine, function_id, all_fixtures, fixture_definitions, master_presets
    )

    # Chaser 3: Sparkle (random flashes)
    function_id = create_sparkle_chaser(
        engine, function_id, all_fixtures, fixture_definitions, master_presets
    )

    # Movement Pattern 1: Sweep All
    if moving_head_fixtures:
        function_id = create_sweep_all_efx(
            engine, function_id, moving_head_fixtures, master_presets
        )

    # Movement Pattern 2: Circle All
    if moving_head_fixtures:
        function_id = create_circle_all_efx(
            engine, function_id, moving_head_fixtures, master_presets
        )

    return master_presets, function_id


def create_master_warm_white_scene(
    engine: ET.Element,
    function_id: int,
    all_fixtures: List[Tuple[int, Any]],
    rgb_fixtures: List[Tuple[int, Any, Dict]],
    color_wheel_fixtures: List[Tuple[int, Any]],
    fixture_definitions: Dict[str, Any],
    master_presets: Dict[str, int]
) -> int:
    """Create All Warm White master scene."""
    fixture_values = []

    for fixture_id, fixture in all_fixtures:
        channels_dict, _ = get_fixture_channels_for_preset(
            fixture, fixture_definitions,
            list(DIMMER_PRESETS) + list(COLOUR_PRESETS)
        )

        channel_vals = {}

        # Set dimmer to full
        for ch in channels_dict.get("IntensityDimmer", []):
            channel_vals[ch] = 255

        # Set RGB to warm white (high red, high green, low blue)
        for ch in channels_dict.get("ColourRed", []):
            channel_vals[ch] = 255
        for ch in channels_dict.get("ColourGreen", []):
            channel_vals[ch] = 200
        for ch in channels_dict.get("ColourBlue", []):
            channel_vals[ch] = 150
        for ch in channels_dict.get("ColourWhite", []):
            channel_vals[ch] = 255

        # Color wheel: try to find white/warm white
        color_ch = get_color_wheel_channel(fixture, fixture_definitions)
        if color_ch is not None and not channel_vals:
            # Set to white (typically around value 12)
            channel_vals[color_ch] = 12

        if channel_vals:
            channel_str = ",".join(f"{ch},{val}" for ch, val in sorted(channel_vals.items()))
            fixture_values.append((fixture_id, channel_str))

    if fixture_values:
        create_scene_function(engine, function_id, "Master - All Warm White", fixture_values)
        master_presets["All_Warm_White"] = function_id
        return function_id + 1

    return function_id


def create_master_color_wash_scene(
    engine: ET.Element,
    function_id: int,
    color_name: str,
    all_fixtures: List[Tuple[int, Any]],
    rgb_fixtures: List[Tuple[int, Any, Dict]],
    color_wheel_fixtures: List[Tuple[int, Any]],
    fixture_definitions: Dict[str, Any],
    master_presets: Dict[str, int]
) -> int:
    """Create a master color wash scene."""
    # Color values for RGB fixtures
    color_rgb = {
        "Red": (255, 0, 0),
        "Blue": (0, 0, 255),
        "Purple": (255, 0, 255),
    }

    # Color wheel values (approximate)
    color_wheel_values = {
        "Red": 37,
        "Blue": 188,
        "Purple": 163,
    }

    rgb_val = color_rgb.get(color_name, (255, 255, 255))
    wheel_val = color_wheel_values.get(color_name, 12)

    fixture_values = []

    for fixture_id, fixture in all_fixtures:
        channels_dict, _ = get_fixture_channels_for_preset(
            fixture, fixture_definitions,
            list(DIMMER_PRESETS) + list(COLOUR_PRESETS)
        )

        channel_vals = {}

        # Set dimmer to full
        for ch in channels_dict.get("IntensityDimmer", []):
            channel_vals[ch] = 255

        # Set RGB
        for ch in channels_dict.get("ColourRed", []):
            channel_vals[ch] = rgb_val[0]
        for ch in channels_dict.get("ColourGreen", []):
            channel_vals[ch] = rgb_val[1]
        for ch in channels_dict.get("ColourBlue", []):
            channel_vals[ch] = rgb_val[2]

        # Color wheel
        color_ch = get_color_wheel_channel(fixture, fixture_definitions)
        if color_ch is not None and not (channels_dict.get("ColourRed") or channels_dict.get("ColourGreen") or channels_dict.get("ColourBlue")):
            channel_vals[color_ch] = wheel_val

        if channel_vals:
            channel_str = ",".join(f"{ch},{val}" for ch, val in sorted(channel_vals.items()))
            fixture_values.append((fixture_id, channel_str))

    if fixture_values:
        create_scene_function(engine, function_id, f"Master - {color_name} Wash", fixture_values)
        master_presets[f"{color_name}_Wash"] = function_id
        return function_id + 1

    return function_id


def create_master_rainbow_scene(
    engine: ET.Element,
    function_id: int,
    config: Configuration,
    fixture_id_map: Dict[int, int],
    fixture_definitions: Dict[str, Any],
    master_presets: Dict[str, int]
) -> int:
    """Create rainbow static scene with different colors per group."""
    rainbow_colors_rgb = [
        (255, 0, 0),      # Red
        (255, 127, 0),    # Orange
        (255, 255, 0),    # Yellow
        (0, 255, 0),      # Green
        (0, 255, 255),    # Cyan
        (0, 0, 255),      # Blue
        (255, 0, 255),    # Purple
    ]

    rainbow_colors_wheel = [37, 63, 88, 113, 138, 163, 188]

    fixture_values = []
    group_idx = 0

    for group_name, group in config.groups.items():
        color_idx = group_idx % len(rainbow_colors_rgb)
        rgb_val = rainbow_colors_rgb[color_idx]
        wheel_val = rainbow_colors_wheel[color_idx]

        for fixture in group.fixtures:
            fixture_id = fixture_id_map.get(id(fixture))
            if fixture_id is None:
                continue

            channels_dict, _ = get_fixture_channels_for_preset(
                fixture, fixture_definitions,
                list(DIMMER_PRESETS) + list(COLOUR_PRESETS)
            )

            channel_vals = {}

            # Set dimmer
            for ch in channels_dict.get("IntensityDimmer", []):
                channel_vals[ch] = 255

            # Set RGB
            for ch in channels_dict.get("ColourRed", []):
                channel_vals[ch] = rgb_val[0]
            for ch in channels_dict.get("ColourGreen", []):
                channel_vals[ch] = rgb_val[1]
            for ch in channels_dict.get("ColourBlue", []):
                channel_vals[ch] = rgb_val[2]

            # Color wheel
            color_ch = get_color_wheel_channel(fixture, fixture_definitions)
            if color_ch is not None and not (channels_dict.get("ColourRed") or channels_dict.get("ColourGreen") or channels_dict.get("ColourBlue")):
                channel_vals[color_ch] = wheel_val

            if channel_vals:
                channel_str = ",".join(f"{ch},{val}" for ch, val in sorted(channel_vals.items()))
                fixture_values.append((fixture_id, channel_str))

        group_idx += 1

    if fixture_values:
        create_scene_function(engine, function_id, "Master - Rainbow", fixture_values)
        master_presets["Rainbow"] = function_id
        return function_id + 1

    return function_id


def create_party_chaser(
    engine: ET.Element,
    function_id: int,
    rgb_fixtures: List[Tuple[int, Any, Dict]],
    color_wheel_fixtures: List[Tuple[int, Any]],
    fixture_definitions: Dict[str, Any],
    master_presets: Dict[str, int]
) -> int:
    """Create Party chaser that cycles through colors (16 beats per color)."""
    # Define color cycle
    party_colors_rgb = [
        (255, 0, 0),      # Red
        (255, 127, 0),    # Orange
        (255, 255, 0),    # Yellow
        (0, 255, 0),      # Green
        (0, 255, 255),    # Cyan
        (0, 0, 255),      # Blue
        (255, 0, 255),    # Purple
    ]

    party_colors_wheel = [37, 63, 88, 113, 138, 163, 188]

    # Create scene for each color
    step_scene_ids = []

    for i, (rgb_val, wheel_val) in enumerate(zip(party_colors_rgb, party_colors_wheel)):
        fixture_values = []

        # RGB fixtures
        for fixture_id, fixture, channels_dict in rgb_fixtures:
            channel_vals = {}
            for ch in channels_dict.get("IntensityDimmer", []):
                channel_vals[ch] = 255
            for ch in channels_dict.get("ColourRed", []):
                channel_vals[ch] = rgb_val[0]
            for ch in channels_dict.get("ColourGreen", []):
                channel_vals[ch] = rgb_val[1]
            for ch in channels_dict.get("ColourBlue", []):
                channel_vals[ch] = rgb_val[2]

            if channel_vals:
                channel_str = ",".join(f"{ch},{val}" for ch, val in sorted(channel_vals.items()))
                fixture_values.append((fixture_id, channel_str))

        # Color wheel fixtures
        for fixture_id, fixture in color_wheel_fixtures:
            channels_dict, _ = get_fixture_channels_for_preset(
                fixture, fixture_definitions, list(DIMMER_PRESETS) + list(COLOUR_PRESETS)
            )
            channel_vals = {}
            for ch in channels_dict.get("IntensityDimmer", []):
                channel_vals[ch] = 255
            color_ch = get_color_wheel_channel(fixture, fixture_definitions)
            if color_ch is not None:
                channel_vals[color_ch] = wheel_val

            if channel_vals:
                channel_str = ",".join(f"{ch},{val}" for ch, val in sorted(channel_vals.items()))
                fixture_values.append((fixture_id, channel_str))

        if fixture_values:
            create_scene_function(engine, function_id, f"Party Step {i+1}", fixture_values)
            step_scene_ids.append(function_id)
            function_id += 1

    # Create chaser from scenes
    if step_scene_ids:
        chaser = ET.SubElement(engine, "Function")
        chaser.set("ID", str(function_id))
        chaser.set("Type", "Chaser")
        chaser.set("Name", "Master - Party")

        # Speed: 16 beats per step at 120 BPM = 8000ms per step
        # Duration will be controlled by speed dial, so we set a default
        speed = ET.SubElement(chaser, "Speed")
        speed.set("FadeIn", "0")
        speed.set("FadeOut", "0")
        speed.set("Duration", "8000")  # 16 beats at 120 BPM

        ET.SubElement(chaser, "Direction").text = "Forward"
        ET.SubElement(chaser, "RunOrder").text = "Loop"
        speed_modes = ET.SubElement(chaser, "SpeedModes")
        speed_modes.set("FadeIn", "Default")
        speed_modes.set("FadeOut", "Default")
        speed_modes.set("Duration", "Common")

        # Add steps
        for step_id in step_scene_ids:
            step = ET.SubElement(chaser, "Step")
            step.set("Number", str(step_scene_ids.index(step_id)))
            step.set("FadeIn", "0")
            step.set("Hold", "0")
            step.set("FadeOut", "0")
            step.set("Duration", "0")
            step.text = str(step_id)

        master_presets["Party"] = function_id
        return function_id + 1

    return function_id


def create_pulse_chaser(
    engine: ET.Element,
    function_id: int,
    all_fixtures: List[Tuple[int, Any]],
    fixture_definitions: Dict[str, Any],
    master_presets: Dict[str, int]
) -> int:
    """Create Pulse chaser with wave breathing effect (4 beats per cycle)."""
    # Create scenes for pulse wave (dim → bright → dim)
    pulse_steps = [0, 64, 128, 192, 255, 192, 128, 64]  # 8 steps for smooth wave

    step_scene_ids = []

    for i, intensity in enumerate(pulse_steps):
        fixture_values = []

        for fixture_id, fixture in all_fixtures:
            channels_dict, _ = get_fixture_channels_for_preset(
                fixture, fixture_definitions, list(DIMMER_PRESETS)
            )

            channel_vals = {}
            for ch in channels_dict.get("IntensityDimmer", []):
                channel_vals[ch] = intensity

            if channel_vals:
                channel_str = ",".join(f"{ch},{val}" for ch, val in sorted(channel_vals.items()))
                fixture_values.append((fixture_id, channel_str))

        if fixture_values:
            create_scene_function(engine, function_id, f"Pulse Step {i+1}", fixture_values)
            step_scene_ids.append(function_id)
            function_id += 1

    # Create chaser
    if step_scene_ids:
        chaser = ET.SubElement(engine, "Function")
        chaser.set("ID", str(function_id))
        chaser.set("Type", "Chaser")
        chaser.set("Name", "Master - Pulse")

        # Speed: 4 beats total / 8 steps = 0.5 beats per step at 120 BPM = 250ms per step
        speed = ET.SubElement(chaser, "Speed")
        speed.set("FadeIn", "0")
        speed.set("FadeOut", "0")
        speed.set("Duration", "250")

        ET.SubElement(chaser, "Direction").text = "Forward"
        ET.SubElement(chaser, "RunOrder").text = "Loop"
        speed_modes = ET.SubElement(chaser, "SpeedModes")
        speed_modes.set("FadeIn", "Default")
        speed_modes.set("FadeOut", "Default")
        speed_modes.set("Duration", "Common")

        for step_id in step_scene_ids:
            step = ET.SubElement(chaser, "Step")
            step.set("Number", str(step_scene_ids.index(step_id)))
            step.set("FadeIn", "0")
            step.set("Hold", "0")
            step.set("FadeOut", "0")
            step.set("Duration", "0")
            step.text = str(step_id)

        master_presets["Pulse"] = function_id
        return function_id + 1

    return function_id


def create_sparkle_chaser(
    engine: ET.Element,
    function_id: int,
    all_fixtures: List[Tuple[int, Any]],
    fixture_definitions: Dict[str, Any],
    master_presets: Dict[str, int]
) -> int:
    """Create Sparkle chaser with random flashes (1 beat per flash)."""
    import random

    # Create scenes for random sparkle (randomly select a few fixtures to flash)
    num_sparkle_steps = 8
    step_scene_ids = []

    for i in range(num_sparkle_steps):
        fixture_values = []

        # Randomly select 20-30% of fixtures to be bright
        num_bright = max(1, len(all_fixtures) // 4)
        bright_fixtures = random.sample(all_fixtures, min(num_bright, len(all_fixtures)))

        for fixture_id, fixture in all_fixtures:
            channels_dict, _ = get_fixture_channels_for_preset(
                fixture, fixture_definitions, list(DIMMER_PRESETS)
            )

            channel_vals = {}
            # Set bright or dim based on selection
            intensity = 255 if (fixture_id, fixture) in bright_fixtures else 0

            for ch in channels_dict.get("IntensityDimmer", []):
                channel_vals[ch] = intensity

            if channel_vals:
                channel_str = ",".join(f"{ch},{val}" for ch, val in sorted(channel_vals.items()))
                fixture_values.append((fixture_id, channel_str))

        if fixture_values:
            create_scene_function(engine, function_id, f"Sparkle Step {i+1}", fixture_values)
            step_scene_ids.append(function_id)
            function_id += 1

    # Create chaser
    if step_scene_ids:
        chaser = ET.SubElement(engine, "Function")
        chaser.set("ID", str(function_id))
        chaser.set("Type", "Chaser")
        chaser.set("Name", "Master - Sparkle")

        # Speed: 1 beat per flash at 120 BPM = 500ms
        speed = ET.SubElement(chaser, "Speed")
        speed.set("FadeIn", "0")
        speed.set("FadeOut", "0")
        speed.set("Duration", "500")

        ET.SubElement(chaser, "Direction").text = "Forward"
        ET.SubElement(chaser, "RunOrder").text = "Loop"
        speed_modes = ET.SubElement(chaser, "SpeedModes")
        speed_modes.set("FadeIn", "Default")
        speed_modes.set("FadeOut", "Default")
        speed_modes.set("Duration", "Common")

        for step_id in step_scene_ids:
            step = ET.SubElement(chaser, "Step")
            step.set("Number", str(step_scene_ids.index(step_id)))
            step.set("FadeIn", "0")
            step.set("Hold", "0")
            step.set("FadeOut", "0")
            step.set("Duration", "0")
            step.text = str(step_id)

        master_presets["Sparkle"] = function_id
        return function_id + 1

    return function_id


def create_sweep_all_efx(
    engine: ET.Element,
    function_id: int,
    moving_head_fixtures: List[Tuple[int, Any, Dict]],
    master_presets: Dict[str, int]
) -> int:
    """Create Sweep All EFX (8 beats per cycle)."""
    if not moving_head_fixtures:
        return function_id

    efx = ET.SubElement(engine, "Function")
    efx.set("ID", str(function_id))
    efx.set("Type", "EFX")
    efx.set("Name", "Master - Sweep All")

    # Add all moving heads to EFX
    for fixture_id, fixture, channels_dict in moving_head_fixtures:
        fixture_elem = ET.SubElement(efx, "Fixture")
        ET.SubElement(fixture_elem, "ID").text = str(fixture_id)
        ET.SubElement(fixture_elem, "Head").text = "0"
        ET.SubElement(fixture_elem, "Mode").text = "0"
        ET.SubElement(fixture_elem, "Direction").text = "Forward"
        ET.SubElement(fixture_elem, "StartOffset").text = "0"

    ET.SubElement(efx, "PropagationMode").text = "Parallel"

    # Speed: 8 beats at 120 BPM = 4000ms
    speed = ET.SubElement(efx, "Speed")
    speed.set("FadeIn", "0")
    speed.set("FadeOut", "0")
    speed.set("Duration", "4000")

    ET.SubElement(efx, "Direction").text = "Forward"
    ET.SubElement(efx, "RunOrder").text = "Loop"
    ET.SubElement(efx, "Algorithm").text = "Line"
    ET.SubElement(efx, "Width").text = "100"
    ET.SubElement(efx, "Height").text = "0"
    ET.SubElement(efx, "Rotation").text = "0"
    ET.SubElement(efx, "StartOffset").text = "0"
    ET.SubElement(efx, "IsRelative").text = "1"

    # X axis (pan - left to right sweep)
    x_axis = ET.SubElement(efx, "Axis")
    x_axis.set("Name", "X")
    ET.SubElement(x_axis, "Offset").text = "127"
    ET.SubElement(x_axis, "Frequency").text = "2"
    ET.SubElement(x_axis, "Phase").text = "0"

    # Y axis (tilt - stationary)
    y_axis = ET.SubElement(efx, "Axis")
    y_axis.set("Name", "Y")
    ET.SubElement(y_axis, "Offset").text = "127"
    ET.SubElement(y_axis, "Frequency").text = "0"
    ET.SubElement(y_axis, "Phase").text = "0"

    master_presets["Sweep_All"] = function_id
    return function_id + 1


def create_circle_all_efx(
    engine: ET.Element,
    function_id: int,
    moving_head_fixtures: List[Tuple[int, Any, Dict]],
    master_presets: Dict[str, int]
) -> int:
    """Create Circle All EFX (8 beats per cycle)."""
    if not moving_head_fixtures:
        return function_id

    efx = ET.SubElement(engine, "Function")
    efx.set("ID", str(function_id))
    efx.set("Type", "EFX")
    efx.set("Name", "Master - Circle All")

    # Add all moving heads to EFX
    for fixture_id, fixture, channels_dict in moving_head_fixtures:
        fixture_elem = ET.SubElement(efx, "Fixture")
        ET.SubElement(fixture_elem, "ID").text = str(fixture_id)
        ET.SubElement(fixture_elem, "Head").text = "0"
        ET.SubElement(fixture_elem, "Mode").text = "0"
        ET.SubElement(fixture_elem, "Direction").text = "Forward"
        ET.SubElement(fixture_elem, "StartOffset").text = "0"

    ET.SubElement(efx, "PropagationMode").text = "Parallel"

    # Speed: 8 beats at 120 BPM = 4000ms
    speed = ET.SubElement(efx, "Speed")
    speed.set("FadeIn", "0")
    speed.set("FadeOut", "0")
    speed.set("Duration", "4000")

    ET.SubElement(efx, "Direction").text = "Forward"
    ET.SubElement(efx, "RunOrder").text = "Loop"
    ET.SubElement(efx, "Algorithm").text = "Circle"
    ET.SubElement(efx, "Width").text = "100"
    ET.SubElement(efx, "Height").text = "100"
    ET.SubElement(efx, "Rotation").text = "0"
    ET.SubElement(efx, "StartOffset").text = "0"
    ET.SubElement(efx, "IsRelative").text = "1"

    # X axis (pan)
    x_axis = ET.SubElement(efx, "Axis")
    x_axis.set("Name", "X")
    ET.SubElement(x_axis, "Offset").text = "127"
    ET.SubElement(x_axis, "Frequency").text = "2"
    ET.SubElement(x_axis, "Phase").text = "90"

    # Y axis (tilt)
    y_axis = ET.SubElement(efx, "Axis")
    y_axis.set("Name", "Y")
    ET.SubElement(y_axis, "Offset").text = "127"
    ET.SubElement(y_axis, "Frequency").text = "3"
    ET.SubElement(y_axis, "Phase").text = "0"

    master_presets["Circle_All"] = function_id
    return function_id + 1
