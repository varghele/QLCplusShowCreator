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
        mode_name: Name of the mode to check ("8 Channel", "14 Channel", etc.)
        properties: List of properties to look for (["IntensityDimmer", "Shutter", etc.])
    Returns:
        dict: Dictionary of channel numbers by property
    """
    channels = {}

    # Find the specified mode
    mode = None
    for m in fixture_def['modes']:
        if m['name'] == mode_name:
            mode = m
            break

    if not mode:
        return channels

    # For each channel in the mode
    for channel_mapping in mode['channels']:
        channel_number = channel_mapping['number']
        channel_name = channel_mapping['name']

        # Find the channel definition
        channel_def = None
        for ch in fixture_def['channels']:
            if ch['name'] == channel_name:
                channel_def = ch
                break

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
                    'min': capability['min'],
                    'max': capability['max']
                })

    return channels

