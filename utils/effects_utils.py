import os
import ast


def list_effects_in_directory(directory):
    effects_dict = {}

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())

                    # Get module name without .py extension
                    module_name = os.path.splitext(file)[0]

                    # Get all function definitions
                    functions = [node.name for node in ast.walk(tree)
                                 if isinstance(node, ast.FunctionDef)]

                    if functions:
                        effects_dict[module_name] = functions

                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")

    return effects_dict


# To load and use the effects later:
def load_effect(module_name, effect_name):
    try:
        # Import the module dynamically
        import importlib
        module = importlib.import_module(f"effects.{module_name}")

        # Get the function from the module
        if hasattr(module, effect_name):
            return getattr(module, effect_name)
        else:
            print(f"Effect {effect_name} not found in {module_name}")
            return None

    except ImportError as e:
        print(f"Error importing module {module_name}: {e}")
        return None


# Set up effects combo box for GUI:
def setup_effects_combo(self, combo_box):
    effects = list_effects_in_directory("path/to/effects/directory")

    # Add empty option first
    combo_box.addItem("")

    # Add effects organized by module
    for module, functions in effects.items():
        for func in functions:
            combo_box.addItem(f"{module}.{func}")


def get_channels_by_property(fixture_def, mode_name, properties):
    """
    Extracts channels with specific properties from a fixture definition
    Parameters:
        fixture_def: Dictionary containing fixture definition
        mode_name: Name of the mode to check
        properties: List of properties to look for
    Returns:
        dict: Dictionary of channel numbers by property
    """
    channels = {}

    # Find the specified mode from modes list
    mode = next((m for m in fixture_def['modes'] if m['name'] == mode_name), None)

    if not mode:
        return channels

    # For each channel in the mode
    for channel_mapping in mode['channels']:
        channel_number = channel_mapping['number']
        channel_name = channel_mapping['name']

        # Find the channel definition
        channel_def = next((ch for ch in fixture_def['channels'] if ch['name'] == channel_name), None)

        if not channel_def:
            continue

        # Check preset property
        if channel_def.get('preset') in properties:
            if channel_def['preset'] not in channels:
                channels[channel_def['preset']] = []
            channels[channel_def['preset']].append({
                'channel': channel_number
            })

        # Check group property
        if channel_def.get('group') in properties:
            if channel_def['group'] not in channels:
                channels[channel_def['group']] = []
            channels[channel_def['group']].append({
                'channel': channel_number
            })

        # Check capabilities for properties
        for capability in channel_def.get('capabilities', []):
            if capability.get('preset') in properties:
                if capability['preset'] not in channels:
                    channels[capability['preset']] = []
                channels[capability['preset']].append({
                    'channel': channel_number,
                    'min': capability.get('min'),
                    'max': capability.get('max')
                })

    return channels


def find_closest_color_dmx(channels_dict, hex_color, fixture_def=None):
    """
    Find the closest color match in the fixture's ColorMacro channel

    Parameters:
        channels_dict: Dictionary of channels by property
        hex_color: Target color as hex string (e.g. "#FF0000")
        fixture_def: Full fixture definition to search if colors not in channels_dict
    Returns:
        int: DMX value for the closest matching color
    """
    if not hex_color:
        return None

    # Remove '#' if present and normalize
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    hex_color = hex_color.upper()

    # Convert the target hex color to RGB
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except (ValueError, IndexError):
        return None

    # Find all color capabilities across all relevant channels
    color_capabilities = []

    # First check ColorMacro channels from channels_dict
    if 'ColorMacro' in channels_dict:
        for channel in channels_dict['ColorMacro']:
            for capability in channel.get('capabilities', []):
                if 'color' in capability and capability['color']:
                    color_capabilities.append(capability)

    # If no colors found in ColorMacro, search through all channels in fixture_def
    if not color_capabilities and fixture_def:
        for channel in fixture_def.get('channels', []):
            # Look for any channel in the Color group or with color capabilities
            if channel.get('group') == 'Colour' or channel.get('name') == 'Color':
                for capability in channel.get('capabilities', []):
                    if 'color' in capability:
                        color_capabilities.append(capability)

    # If still no colors found, try searching all channels for any color information
    if not color_capabilities and fixture_def:
        for channel in fixture_def.get('channels', []):
            for capability in channel.get('capabilities', []):
                if 'color' in capability:
                    color_capabilities.append(capability)

    # Find the closest color match
    best_match = None
    min_distance = float('inf')

    for capability in color_capabilities:
        color_val = capability.get('color', '')

        # Skip SVG files and non-hex values
        if color_val.endswith('.svg') or not color_val.startswith('#'):
            continue

        # Remove '#' if present
        if color_val.startswith('#'):
            color_val = color_val[1:]

        # Convert fixture color to RGB
        try:
            c_r = int(color_val[0:2], 16)
            c_g = int(color_val[2:4], 16)
            c_b = int(color_val[4:6], 16)
        except (ValueError, IndexError):
            continue

        # Calculate color distance (Euclidean distance in RGB space)
        distance = ((r - c_r) ** 2 + (g - c_g) ** 2 + (b - c_b) ** 2) ** 0.5

        if distance < min_distance:
            min_distance = distance
            # Get the middle of the DMX range for this color
            dmx_value = (int(capability['min']) + int(capability['max'])) // 2
            best_match = dmx_value
            print(f"Found color match: {capability.get('name')} (distance: {distance:.2f}) - DMX: {dmx_value}")

    return best_match


def find_gobo_dmx_value(channels_dict, gobo_index, fixture_def=None):
    """
    Find the DMX value for the specified gobo index

    Parameters:
        channels_dict: Dictionary of channels by property
        gobo_index: Index of the gobo to use (typically 1-5)
        fixture_def: Full fixture definition to search if gobos not in channels_dict
    Returns:
        int: DMX value for the selected gobo
    """
    # Look for gobo channel in channels_dict
    for channel_type in ['GoboMacro', 'GoboWheel']:
        if channel_type in channels_dict:
            for channel in channels_dict[channel_type]:
                # Find non-rotating gobos (skip "Rainbow" or "shake" capabilities)
                static_gobos = []
                for capability in channel.get('capabilities', []):
                    if ('name' in capability and
                            'gobo' in capability['name'].lower() and
                            'shake' not in capability['name'].lower() and
                            'rainbow' not in capability['name'].lower()):
                        static_gobos.append(capability)

                # Select the requested gobo by index
                if static_gobos and gobo_index <= len(static_gobos):
                    selected_gobo = static_gobos[gobo_index - 1]  # -1 because indices start at 1
                    return (selected_gobo['min'] + selected_gobo['max']) // 2

    # If we haven't found a gobo yet, search through the full fixture definition
    if fixture_def:
        for channel in fixture_def.get('channels', []):
            if channel.get('name') == 'Gobo':
                # Find non-rotating gobos
                static_gobos = []
                for capability in channel.get('capabilities', []):
                    name = capability.get('name', '').lower()
                    if ('gobo' in name and
                            'shake' not in name and
                            'rainbow' not in name and
                            'open' not in name):
                        static_gobos.append(capability)

                # Select the requested gobo by index
                if static_gobos and gobo_index <= len(static_gobos):
                    selected_gobo = static_gobos[gobo_index - 1]  # -1 because indices start at 1
                    return (int(selected_gobo['min']) + int(selected_gobo['max'])) // 2

    # Default gobo DMX value if no matching gobo found
    return 20  # Common value for first gobo pattern


def find_gobo_rotation_value(fixture_def, direction="cw", speed="fast"):
    """
    Find the DMX channel and value for gobo rotation

    Parameters:
        fixture_def: Full fixture definition
        direction: "cw" for clockwise or "ccw" for counterclockwise
        speed: "slow", "medium", or "fast"
    Returns:
        tuple: (channel_number, dmx_value) for gobo rotation
    """
    rotation_channel = None
    rotation_value = None

    # Find the Gobo Rotation channel
    for channel in fixture_def.get('channels', []):
        if channel.get('name') == 'Gobo Rotation':
            rotation_channel = channel
            break

    if not rotation_channel:
        return None

    # Find the appropriate preset based on direction
    rotation_preset = None
    if direction.lower() == "cw":
        rotation_preset = "RotationClockwiseFastToSlow"
    else:  # counterclockwise
        rotation_preset = "RotationCounterClockwiseSlowToFast"

    # Find capability with matching preset
    for capability in rotation_channel.get('capabilities', []):
        if capability.get('preset') == rotation_preset:
            min_val = int(capability['min'])
            max_val = int(capability['max'])

            # Calculate value based on speed
            range_size = max_val - min_val
            if speed.lower() == "fast":
                if direction.lower() == "cw":
                    rotation_value = min_val + int(range_size * 0.2)  # Fast is closer to min for CW
                else:
                    rotation_value = max_val - int(range_size * 0.2)  # Fast is closer to max for CCW
            elif speed.lower() == "medium":
                rotation_value = (min_val + max_val) // 2  # Medium speed is middle of range
            else:  # slow
                if direction.lower() == "cw":
                    rotation_value = max_val - int(range_size * 0.2)  # Slow is closer to max for CW
                else:
                    rotation_value = min_val + int(range_size * 0.2)  # Slow is closer to min for CCW

            # Find the channel number for this mode
            for mode in fixture_def.get('modes', []):
                for channel_entry in mode.get('channels', []):
                    if channel_entry.get('name') == 'Gobo Rotation':
                        return (channel_entry.get('number'), rotation_value)

    return None
