import os
import sys
import xml.etree.ElementTree as ET

def load_fixture_definitions(models_in_config):
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
    if sys.platform.startswith('linux'):
        qlc_fixture_dirs.extend([
            '/usr/share/qlcplus/fixtures',
            os.path.expanduser('~/.qlcplus/')
        ])
    elif sys.platform == 'win32':
        qlc_fixture_dirs.extend([
            os.path.join(os.path.expanduser('~'), 'QLC+'),  # User fixtures
            'C:\\QLC+\\Fixtures'  # System-wide fixtures
        ])
    elif sys.platform == 'darwin':
        qlc_fixture_dirs.append(os.path.expanduser('~/Library/Application Support/QLC+/fixtures'))

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

    for dir_path in qlc_fixture_dirs:
        if not os.path.exists(dir_path):
            continue

        for manufacturer_dir in os.listdir(dir_path):
            manufacturer_path = os.path.join(dir_path, manufacturer_dir)
            if not os.path.isdir(manufacturer_path):
                continue

            for fixture_file in os.listdir(manufacturer_path):
                if not fixture_file.endswith('.qxf'):
                    continue

                fixture_path = os.path.join(manufacturer_path, fixture_file)
                try:
                    tree = ET.parse(fixture_path)
                    root = tree.getroot()

                    manufacturer = root.find('.//Manufacturer', ns).text
                    model = root.find('.//Model', ns).text

                    # Only process if this fixture is in our configuration
                    if (manufacturer, model) not in models_in_config:
                        continue

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
                                # Some newer QLC+ fixtures have direct color attributes
                                cap_data['color'] = capability.get('Color1')
                            elif capability.get('Res1'):
                                # Some fixtures store color information in Res1
                                cap_data['color'] = capability.get('Res1')
                            elif capability.text and any(color in capability.text for color in color_name_to_rgb):
                                # Extract color from capability text if it mentions a standard color
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

                        # Get channels for this mode
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
