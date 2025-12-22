import os
import sys
import xml.etree.ElementTree as ET

def load_fixture_definitions_from_qlc(models_in_config):
    """
    Loads fixture definitions from QLC+ fixture directories

    Parameters:
        models_in_config: Set of (manufacturer, model) tuples to load
    Returns:
        dict: Dictionary of fixture definitions
    """
    fixture_definitions = {}
    ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

    # Get QLC+ fixture directories based on OS
    qlc_fixture_dirs = []

    # Always include the project's custom_fixtures folder first (for development/testing)
    project_custom_fixtures = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'custom_fixtures')
    if os.path.exists(project_custom_fixtures):
        qlc_fixture_dirs.append(project_custom_fixtures)

    if sys.platform.startswith('linux'):
        # Linux paths
        # User fixtures: ~/.qlcplus/Fixtures
        qlc_fixture_dirs.append(os.path.expanduser('~/.qlcplus/Fixtures'))
        # System fixtures: /usr/share/qlcplus/Fixtures
        qlc_fixture_dirs.append('/usr/share/qlcplus/Fixtures')

    elif sys.platform == 'win32':
        # Windows paths
        # User fixtures: C:\Users\{Username}\QLC+\Fixtures
        qlc_fixture_dirs.append(os.path.join(os.path.expanduser('~'), 'QLC+', 'Fixtures'))
        # System fixtures: C:\QLC+\Fixtures (QLC+ 4 default install location)
        qlc_fixture_dirs.append('C:\\QLC+\\Fixtures')
        # System fixtures: C:\QLC+5\Fixtures (QLC+ 5 install location)
        qlc_fixture_dirs.append('C:\\QLC+5\\Fixtures')

    elif sys.platform == 'darwin':
        # macOS paths
        # User fixtures: ~/Library/Application Support/QLC+/Fixtures
        qlc_fixture_dirs.append(os.path.expanduser('~/Library/Application Support/QLC+/Fixtures'))
        # System fixtures: /Applications/QLC+.app/Contents/Resources/Fixtures
        qlc_fixture_dirs.append('/Applications/QLC+.app/Contents/Resources/Fixtures')

    # Color name to RGB mapping for standard colors
    color_name_to_rgb = {
        "White": "#FFFFFF",
        "Red": "#FF0000",
        "Green": "#00FF00",
        "Blue": "#0000FF",
        "Cyan": "#00FFFF",
        "Magenta": "#FF00FF",
        "Yellow": "#FFFF00",
        "Amber": "#FFBF00",
        "Orange": "#FF7F00",
        "Purple": "#7F00FF",
        "Pink": "#FF007F",
        "UV": "#8000FF",
        "Lime": "#BFFF00"
    }

    def _parse_fixture_file(fixture_path, ns, models_in_config, color_name_to_rgb, fixture_definitions):
        """Parse a single fixture file and add to definitions if in config."""
        try:
            tree = ET.parse(fixture_path)
            root = tree.getroot()

            manufacturer = root.find('.//Manufacturer', ns).text
            model = root.find('.//Model', ns).text

            # Only process if this fixture is in our configuration
            if (manufacturer, model) not in models_in_config:
                return

            # Get channels information
            channels_info = []
            for channel in root.findall('.//Channel', ns):
                channel_data = {
                    'name': channel.get('Name'),
                    'preset': channel.get('Preset'),
                    'group': channel.find('Group', ns).text if channel.find('Group', ns) is not None else None,
                    'capabilities': []
                }

                # Get capabilities
                for capability in channel.findall('Capability', ns):
                    cap_data = {
                        'min': int(capability.get('Min')),
                        'max': int(capability.get('Max')),
                        'preset': capability.get('Preset'),
                        'name': capability.text
                    }

                    # Extract color information if present
                    if capability.get('Color1') or capability.get('Color2'):
                        cap_data['color'] = capability.get('Color1')
                    elif capability.get('Res1'):
                        cap_data['color'] = capability.get('Res1')
                    elif capability.text and any(color in capability.text for color in color_name_to_rgb):
                        for color_name, hex_value in color_name_to_rgb.items():
                            if color_name.lower() in capability.text.lower():
                                cap_data['color'] = hex_value
                                break

                    channel_data['capabilities'].append(cap_data)

                channels_info.append(channel_data)

            # Get modes information
            modes_info = []
            for mode in root.findall('.//Mode', ns):
                mode_data = {
                    'name': mode.get('Name'),
                    'channels': []
                }
                for channel in mode.findall('Channel', ns):
                    mode_data['channels'].append({
                        'number': int(channel.get('Number')),
                        'name': channel.text
                    })
                modes_info.append(mode_data)

            # Store the fixture definition
            key = f"{manufacturer}_{model}"
            fixture_definitions[key] = {
                'manufacturer': manufacturer,
                'model': model,
                'channels': channels_info,
                'modes': modes_info
            }

        except ET.ParseError as e:
            print(f"Error parsing fixture file {fixture_path}: {e}")
        except Exception as e:
            print(f"Error processing fixture file {fixture_path}: {e}")

    for dir_path in qlc_fixture_dirs:
        if not os.path.exists(dir_path):
            continue

        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)

            # Check if it's a .qxf file directly in the directory
            if item.endswith('.qxf') and os.path.isfile(item_path):
                _parse_fixture_file(item_path, ns, models_in_config, color_name_to_rgb, fixture_definitions)

            # Check if it's a manufacturer subdirectory
            elif os.path.isdir(item_path):
                for fixture_file in os.listdir(item_path):
                    if fixture_file.endswith('.qxf'):
                        fixture_path = os.path.join(item_path, fixture_file)
                        _parse_fixture_file(fixture_path, ns, models_in_config, color_name_to_rgb, fixture_definitions)

    return fixture_definitions


def determine_fixture_type(fixture_def):
    """
    Determine fixture type based on its channels across all modes
    Parameters:
        fixture_def: The fixture definition root element
    """
    ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

    # Initialize sets for channel types
    movement_channels = set()
    color_channels = set()
    dimmer_channels = set()

    # Get all channels and their properties
    for channel in fixture_def.findall('.//Channel', ns):
        channel_name = channel.get('Name', '')

        # Check for movement channels
        if 'Pan' in channel_name or 'Tilt' in channel_name:
            movement_channels.add(channel_name)

        # Check for color channels
        if any(color in channel_name for color in ['Red', 'Green', 'Blue', 'White']):
            color_channels.add(channel_name)

        # Check for dimmer
        if 'Dimmer' in channel_name:
            dimmer_channels.add(channel_name)

    # Determine fixture type based on capabilities
    has_movement = len(movement_channels) > 0
    has_rgbw = all(any(color in ch for ch in color_channels)
                   for color in ['Red', 'Green', 'Blue', 'White'])
    has_rgb = all(any(color in ch for ch in color_channels)
                  for color in ['Red', 'Green', 'Blue'])
    has_dimmer = len(dimmer_channels) > 0

    # Return fixture type
    if has_movement:
        return "MH"  # Moving Head
    elif has_rgbw or has_rgb:
        if has_dimmer:
            return "WASH"
        else:
            return "BAR"
    else:
        return "PAR"  # Default type


def detect_fixture_group_capabilities(fixtures, fixture_definitions=None):
    """
    Detect sublane capabilities for a fixture group by analyzing fixture definitions.

    Args:
        fixtures: List of Fixture objects in the group
        fixture_definitions: Optional dict of pre-loaded fixture definitions.
                           If None, will scan from QLC+ directories.

    Returns:
        FixtureGroupCapabilities object with detected capabilities
    """
    from config.models import FixtureGroupCapabilities
    from utils.sublane_presets import (
        categorize_preset, SublaneType,
        DIMMER_PRESETS, COLOUR_PRESETS, MOVEMENT_PRESETS, SPECIAL_PRESETS
    )

    capabilities = FixtureGroupCapabilities()

    # If no fixture definitions provided, scan them
    if fixture_definitions is None:
        models_in_config = {(f.manufacturer, f.model) for f in fixtures}
        fixture_definitions = load_fixture_definitions_from_qlc(models_in_config)

    # Analyze each fixture in the group
    for fixture in fixtures:
        fixture_key = f"{fixture.manufacturer}_{fixture.model}"

        if fixture_key not in fixture_definitions:
            # Try alternate key format
            fixture_key = f"{fixture.manufacturer}_{fixture.model.replace(' ', '_')}"

        if fixture_key in fixture_definitions:
            fixture_def = fixture_definitions[fixture_key]

            # Check all channels for their presets
            for channel in fixture_def.get('channels', []):
                preset = channel.get('preset')

                if preset:
                    sublane_type = categorize_preset(preset)

                    if sublane_type == SublaneType.DIMMER:
                        capabilities.has_dimmer = True
                    elif sublane_type == SublaneType.COLOUR:
                        capabilities.has_colour = True
                    elif sublane_type == SublaneType.MOVEMENT:
                        capabilities.has_movement = True
                    elif sublane_type == SublaneType.SPECIAL:
                        capabilities.has_special = True

                # Fallback: check channel name if no preset
                elif not preset:
                    channel_name = channel.get('name', '') or ''

                    # Simple heuristics based on channel name
                    if channel_name and any(word in channel_name for word in ['Dimmer', 'Intensity', 'Master', 'Strobe', 'Shutter']):
                        capabilities.has_dimmer = True
                    elif channel_name and any(word in channel_name for word in ['Red', 'Green', 'Blue', 'White', 'Cyan', 'Magenta', 'Yellow', 'Color', 'Hue', 'Saturation']):
                        capabilities.has_colour = True
                    elif channel_name and any(word in channel_name for word in ['Pan', 'Tilt', 'X-Axis', 'Y-Axis']):
                        capabilities.has_movement = True
                    elif channel_name and any(word in channel_name for word in ['Gobo', 'Prism', 'Focus', 'Zoom', 'Beam']):
                        capabilities.has_special = True

    return capabilities


def get_color_wheel_options(fixtures, fixture_definitions=None):
    """
    Extract color wheel options from fixtures that have a color wheel channel.

    Args:
        fixtures: List of Fixture objects in the group
        fixture_definitions: Optional dict of pre-loaded fixture definitions.

    Returns:
        List of (name, dmx_value, hex_color) tuples, or empty list if no color wheel
    """
    # If no fixture definitions provided, scan them
    if fixture_definitions is None:
        models_in_config = {(f.manufacturer, f.model) for f in fixtures}
        fixture_definitions = load_fixture_definitions_from_qlc(models_in_config)

    color_wheel_options = []

    # Check all fixtures - use the first one that has a color wheel
    for fixture in fixtures:
        fixture_key = f"{fixture.manufacturer}_{fixture.model}"

        if fixture_key not in fixture_definitions:
            fixture_key = f"{fixture.manufacturer}_{fixture.model.replace(' ', '_')}"

        if fixture_key in fixture_definitions:
            fixture_def = fixture_definitions[fixture_key]

            # Look for color wheel channels
            for channel in fixture_def.get('channels', []):
                channel_name = channel.get('name', '') or ''
                group = channel.get('group', '') or ''

                # Check if this is a color wheel/macro channel
                is_color_channel = (
                    group == 'Colour' or
                    'Color' in channel_name or
                    'Colour' in channel_name
                )

                if is_color_channel and channel.get('capabilities'):
                    # Extract color options from capabilities
                    for cap in channel['capabilities']:
                        preset = cap.get('preset', '')
                        name = cap.get('name', '') or ''
                        color = cap.get('color')

                        # Skip rotation/rainbow effects
                        if 'Rainbow' in name or 'Rotation' in name:
                            continue

                        # Skip if no meaningful name
                        if not name or name.lower() in ['no function', 'blackout']:
                            continue

                        # Use the middle of the DMX range
                        dmx_value = (cap.get('min', 0) + cap.get('max', 0)) // 2

                        # Ensure we have a hex color
                        if not color or not color.startswith('#'):
                            # Try to infer from name
                            color = _infer_color_from_name(name)

                        if color:
                            color_wheel_options.append((name, dmx_value, color))

                    # Found a color wheel, return options
                    if color_wheel_options:
                        return color_wheel_options

    return color_wheel_options


def _infer_color_from_name(name):
    """Infer hex color from a color name."""
    color_map = {
        'white': '#FFFFFF',
        'red': '#FF0000',
        'green': '#00FF00',
        'blue': '#0000FF',
        'cyan': '#00FFFF',
        'magenta': '#FF00FF',
        'yellow': '#FFFF00',
        'amber': '#FFBF00',
        'orange': '#FF7F00',
        'purple': '#7F00FF',
        'violet': '#EE82EE',
        'pink': '#FF69B4',
        'uv': '#8000FF',
        'lime': '#BFFF00',
        'light blue': '#ADD8E6',
        'aqua': '#00FFFF',
    }

    name_lower = name.lower()
    for color_name, hex_value in color_map.items():
        if color_name in name_lower:
            return hex_value

    return None
