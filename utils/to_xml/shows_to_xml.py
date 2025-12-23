import os
import json
import xml.etree.ElementTree as ET
from config.models import Configuration
import pandas as pd
import importlib


def add_steps_to_sequence(sequence, steps):
    """Adds steps to a sequence"""
    for step in steps:
        sequence.append(step)

def load_show_values(values_file):
    """
    Load show values from JSON file
    Parameters:
        values_file: Path to the values JSON file
    Returns:
        dict: Dictionary of show values indexed by (show_part, fixture_group)
    """
    show_values = {}
    if os.path.exists(values_file):
        try:
            with open(values_file, 'r') as f:
                values = json.load(f)
                for item in values:
                    key = (item['show_part'], item['fixture_group'])
                    show_values[key] = item
        except Exception as e:
            print(f"Error loading values file: {e}")
    return show_values

def load_fixture_definitions_from_json(json_path):
    """
    Load fixture definitions from JSON file
    Parameters:
        json_path: Path to the fixtures.json file
    Returns:
        dict: Dictionary of fixture definitions
    """
    try:
        with open(json_path, 'r') as f:
            fixture_definitions = json.load(f)
        return fixture_definitions
    except Exception as e:
        print(f"Error loading fixture definitions from {json_path}: {e}")
        return {}


def load_effects(effects_dir="effects"):
    """
    Loads all effect modules from the effects directory
    Parameters:
        effects_dir: Directory containing effect modules (default: "effects")
    Returns:
        dict: Dictionary of loaded effect modules with category names as keys
    """
    effects = {}

    # Convert relative path to absolute path
    effects_dir = os.path.abspath(effects_dir)

    # Check if directory exists
    if not os.path.exists(effects_dir):
        print(f"Effects directory not found: {effects_dir}")
        return effects

    try:
        # Load each Python file in the effects directory
        for effect_file in os.listdir(effects_dir):
            if effect_file.endswith('.py') and not effect_file.startswith('__'):
                category = effect_file[:-3]  # Remove .py extension
                try:
                    # Import the module using importlib
                    module_path = f"effects.{category}"
                    effects[category] = importlib.import_module(module_path)
                    print(f"Loaded effects for category: {category}")
                except ImportError as e:
                    print(f"Error importing {effect_file}: {e}")
                except Exception as e:
                    print(f"Error loading {effect_file}: {e}")
                    import traceback
                    traceback.print_exc()

    except Exception as e:
        print(f"Error scanning effects directory: {e}")
        import traceback
        traceback.print_exc()

    return effects

def calculate_start_time(previous_time, signature, bpm, num_bars, transition, previous_bpm=None):
    """
    Calculate the start time in milliseconds with normalized beat calculations
    Parameters:
        previous_time: Previous start time in milliseconds
        signature: Time signature as string (e.g. "4/4")
        bpm: Target BPM for this section
        num_bars: Number of bars
        transition: Type of transition ("instant" or "gradual")
        previous_bpm: BPM of the previous section (needed for gradual transition)
    Returns:
        int: New start time in milliseconds
    """
    numerator, denominator = map(int, signature.split('/'))
    # Normalize to quarter notes for consistent calculation
    beats_per_bar = (numerator * 4) / denominator

    if transition == "instant" or previous_bpm is None:
        milliseconds_per_bar = (60000 / bpm) * beats_per_bar
        return previous_time + int(milliseconds_per_bar * int(num_bars))

    elif transition == "gradual":
        total_time = 0
        for bar in range(int(num_bars)):
            # Using a slightly curved interpolation instead of linear
            progress = (bar / int(num_bars)) ** 0.52  # Adding slight curve to the transition
            current_bpm = previous_bpm + (bpm - previous_bpm) * progress
            milliseconds_per_bar = (60000 / current_bpm) * beats_per_bar
            total_time += milliseconds_per_bar

        return previous_time + int(total_time)

    else:
        raise ValueError(f"Unknown transition type: {transition}")


def calculate_step_timing(signature, start_bpm, end_bpm, num_bars, speed="1", transition="gradual"):
    """
    Calculate step timings and count based on BPM transition
    Parameters:
        signature: Time signature as string (e.g. "4/4")
        start_bpm: Starting BPM
        end_bpm: Target BPM
        num_bars: Number of bars
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        transition: Type of transition ("instant" or "gradual")
    Returns:
        tuple: (step_timings, total_steps)
            step_timings: List of step durations in milliseconds
            total_steps: Total number of steps needed
    """
    # Convert speed fraction to float
    if isinstance(speed, str) and '/' in speed:
        num, denom = map(int, speed.split('/'))
        speed_multiplier = num / denom
    else:
        speed_multiplier = float(speed)

    # Make sure num_bars is integer
    num_bars = int(num_bars)
    try:
        start_bpm = float(start_bpm)
    except TypeError:
        # Start_bpm can be None Type object
        pass
    end_bpm = float(end_bpm)

    numerator, denominator = map(int, signature.split('/'))
    beats_per_bar = (numerator * 4) / denominator
    total_beats = num_bars * beats_per_bar
    steps_per_beat = speed_multiplier
    total_steps = int(total_beats * steps_per_beat)

    step_timings = []

    if transition == "instant" or start_bpm == end_bpm or start_bpm is None:
        ms_per_beat = 60000 / end_bpm
        ms_per_step = ms_per_beat / steps_per_beat
        step_timings = [ms_per_step] * total_steps


    elif transition == "gradual":
        for bar in range(num_bars):
            # Calculate current and next bar's BPM
            current_progress = (bar / num_bars) ** 0.52
            current_bpm = start_bpm + (end_bpm - start_bpm) * current_progress

            next_progress = ((bar + 1) / num_bars) ** 0.52
            next_bpm = start_bpm + (end_bpm - start_bpm) * next_progress if bar < num_bars - 1 else end_bpm

            # Calculate total time for this bar
            milliseconds_per_bar = (60000 / current_bpm) * beats_per_bar
            steps_in_bar = int(beats_per_bar * steps_per_beat)

            # Calculate step timings with linear decrease
            total_time = 0
            bar_steps = []

            for step in range(steps_in_bar):
                step_progress = step / (steps_in_bar - 1) if steps_in_bar > 1 else 0
                step_bpm = current_bpm + (next_bpm - current_bpm) * step_progress
                ms_per_step = (60000 / step_bpm) / steps_per_beat
                bar_steps.append(ms_per_step)
                total_time += ms_per_step

            # Normalize step timings to fit milliseconds_per_bar
            scaling_factor = milliseconds_per_bar / total_time
            normalized_steps = [step * scaling_factor for step in bar_steps]
            step_timings.extend(normalized_steps)


    else:
        raise ValueError(f"Unknown transition type: {transition}")

    return [int(timing) for timing in step_timings], total_steps


def create_sequence(root, sequence_id, sequence_name, bound_scene_id, bpm=120):
    """
    Creates a Sequence function element
    Parameters:
        root: The root XML element to add the sequence to
        sequence_id: ID of the sequence
        sequence_name: Name of the sequence
        bound_scene_id: ID of the bound scene
        bpm: Beats per minute for timing
    Returns:
        Element: The created sequence element
    """
    sequence = ET.SubElement(root, "Function")
    sequence.set("ID", str(sequence_id))
    sequence.set("Type", "Sequence")
    sequence.set("Name", sequence_name)
    sequence.set("BoundScene", str(bound_scene_id))

    # Calculate default timing based on BPM
    ms_per_beat = 60000 / float(bpm)

    speed = ET.SubElement(sequence, "Speed")
    speed.set("FadeIn", str(int(ms_per_beat * 0.1)))  # 10% of beat time
    speed.set("FadeOut", "0")
    speed.set("Duration", str(int(ms_per_beat)))

    direction = ET.SubElement(sequence, "Direction")
    direction.text = "Forward"

    run_order = ET.SubElement(sequence, "RunOrder")
    run_order.text = "SingleShot"

    speed_modes = ET.SubElement(sequence, "SpeedModes")
    speed_modes.set("FadeIn", "PerStep")
    speed_modes.set("FadeOut", "PerStep")
    speed_modes.set("Duration", "PerStep")

    return sequence


def create_tracks(show_function, engine, show, effects_by_group, config, fixture_id_map, function_id_counter, effects,
                  fixture_definitions):
    """
    Creates Track elements, Scenes, and Sequences for each channel group category

    Parameters:
        show_function: The show Function element to add tracks to
        engine: The engine element for adding scenes
        show: Show object containing show data
        effects_by_group: Dictionary of effects grouped by fixture group
        config: Configuration object
        fixture_id_map: Dictionary mapping fixture object IDs to their sequential IDs
        function_id_counter: Current function ID counter
        effects: dictionary containing effect names and link to module
        fixture_definitions: Dictionary of fixture definitions loaded from QLC+
    Returns:
        int: Next available function ID
    """
    track_id = 0
    fixture_start_id = 0

    for group_name, group_effects in effects_by_group.items():
        # Calculate number of fixtures in group
        fixture_num = len(config.groups[group_name].fixtures)

        # Create Track
        track = ET.SubElement(show_function, "Track")
        track.set("ID", str(track_id))
        track.set("Name", group_name.upper())
        track.set("SceneID", str(function_id_counter))
        track.set("isMute", "0")

        # Create Scene
        scene = ET.SubElement(engine, "Function")
        scene.set("ID", str(function_id_counter))
        scene.set("Type", "Scene")
        scene.set("Name", f"Scene for {show.name} - Track {track_id + 1}")
        scene.set("Hidden", "True")

        # Add Scene properties
        speed = ET.SubElement(scene, "Speed")
        speed.set("FadeIn", "0")
        speed.set("FadeOut", "0")
        speed.set("Duration", "0")

        # Add ChannelGroupsVal
        ET.SubElement(scene, "ChannelGroupsVal").text = f"{track_id},0"

        # Add FixtureVal for fixtures in the group
        for fixture in config.groups[group_name].fixtures:
            fixture_val = ET.SubElement(scene, "FixtureVal")
            fixture_val.set("ID", str(fixture_id_map[id(fixture)]))

            # Get number of channels
            num_channels = next((mode.channels for mode in fixture.available_modes
                                 if mode.name == fixture.current_mode), 0)

            # Create channel values string
            channel_values = ",".join([f"{i},0" for i in range(num_channels)])
            fixture_val.text = channel_values

        function_id_counter += 1

        # Create sequences for each show part
        start_time = 0
        previous_bpm = None

        for part in show.parts:
            # Find effect for this part and group
            part_effect = next((effect for effect in group_effects
                                if effect.show_part == part.name), None)

            if part_effect:
                # Create sequence
                sequence_name = f"{show.name}_{group_name}_{part.name}"
                sequence = create_sequence(engine, function_id_counter, sequence_name,
                                           scene.get("ID"), part.bpm)

                # Split effect name into module and function
                if part_effect.effect != "":
                    module_name, func_name = part_effect.effect.split('.')
                    effect_module = effects.get(module_name)

                    if effect_module and hasattr(effect_module, func_name):
                        effect_func = getattr(effect_module, func_name)

                        # Get fixture definition from the first fixture in the group
                        # (assuming all fixtures in a group are the same type)
                        first_fixture = config.groups[group_name].fixtures[0]
                        fixture_key = f"{first_fixture.manufacturer}_{first_fixture.model}"
                        fixture_def = fixture_definitions.get(fixture_key)

                        # Make sure that start_bpm is a float.
                        # If it is None, simply assume it is the same as the next bpm
                        if previous_bpm is None:
                            previous_bpm = part.bpm

                        if fixture_def and first_fixture.current_mode:
                            print(f"Creating effect steps with mode: {first_fixture.current_mode}")
                            steps = effect_func(
                                start_step=start_time,
                                fixture_def=fixture_def,
                                mode_name=first_fixture.current_mode,
                                start_bpm=previous_bpm,
                                end_bpm=part.bpm,
                                signature=part.signature,
                                transition=part.transition,
                                num_bars=part.num_bars,
                                speed=part_effect.speed,
                                color=part_effect.color,
                                fixture_conf=config.fixtures[fixture_start_id:fixture_start_id + fixture_num], # TODO: implement for all effects
                                fixture_start_id=fixture_start_id,
                                intensity=part_effect.intensity,
                                spot=None if part_effect.spot=='' else config.spots[part_effect.spot],
                            )
                            print(f"Steps created: {len(steps) if steps else 0}")
                            add_steps_to_sequence(sequence, steps)

                # Create ShowFunction
                show_func = ET.SubElement(track, "ShowFunction")
                show_func.set("ID", str(function_id_counter))
                show_func.set("StartTime", str(start_time))
                show_func.set("Color", part.color)

                function_id_counter += 1

            # Calculate next start time using existing function
            start_time = calculate_start_time(
                start_time,
                part.signature,
                float(part.bpm),
                part.num_bars,
                part.transition,
                previous_bpm
            )
            previous_bpm = float(part.bpm)

        fixture_start_id += fixture_num
        track_id += 1

    return function_id_counter


def create_tracks_old(function, root, effects, base_dir="../"):
    """
    Creates Track elements, Scenes, and Sequences for each channel group category
    Parameters:
        function: The Function XML element (show) to add tracks to
        root: The root XML element where scenes will be added
        base_dir: Base directory path
    Returns:
        int: Next available ID
    """
    # Convert relative paths to absolute paths
    base_dir = os.path.abspath(base_dir)
    groups_file = os.path.join(base_dir, 'setup', 'groups.csv')
    show_name = function.get('Name')
    structure_file = os.path.join(base_dir, 'shows', show_name, f"{show_name}_structure.csv")  # Added .csv extension
    values_file = os.path.join(base_dir, 'shows', show_name, f"{show_name}_values.json")
    fixtures_file = os.path.join(base_dir, 'setup', 'fixtures.json')

    # Check if required files exist
    if not os.path.exists(groups_file):
        print(f"Groups file not found: {groups_file}")
        return
    if not os.path.exists(structure_file):
        print(f"Structure file not found: {structure_file}")
        return

    # Load show values and fixture definitions
    show_values = load_show_values(values_file)
    fixture_definitions = load_fixture_definitions_from_json(fixtures_file)

    # Read the CSV files
    groups_df = pd.read_csv(groups_file)
    structure_df = pd.read_csv(structure_file)
    categories = groups_df['category'].unique()
    current_id = int(function.get("ID")) + 1

    track_id = 0
    fixture_start_id = 0
    for category in categories:
        if pd.isna(category) or category == 'None':
            continue

        # Calculate number of fixtures of same type fixture
        category_fixtures = groups_df[groups_df['category'] == category]
        fixture_num = len(category_fixtures)

        # Create Track
        track = ET.SubElement(function, "Track")
        track.set("ID", str(track_id))
        track.set("Name", str(category).upper())
        track.set("SceneID", str(current_id))
        track.set("isMute", "0")

        # Create Scene
        scene = ET.SubElement(root, "Function")
        scene.set("ID", str(current_id))
        scene.set("Type", "Scene")
        scene.set("Name", f"Scene for {show_name} - Track {track_id + 1}")
        scene.set("Hidden", "True")

        # Add Speed element
        speed = ET.SubElement(scene, "Speed")
        speed.set("FadeIn", "0")
        speed.set("FadeOut", "0")
        speed.set("Duration", "0")

        # Add ChannelGroupsVal element
        channel_groups = ET.SubElement(scene, "ChannelGroupsVal")
        channel_groups.text = "0,0"

        # Add fixture values
        category_fixtures = groups_df[groups_df['category'] == category]
        for _, fixture in category_fixtures.iterrows():
            fixture_val = ET.SubElement(scene, "FixtureVal")
            fixture_val.set("ID", str(fixture['id']))
            fixture_val.text = ','.join([f"{i},0" for i in range(int(fixture['Channels']))])

        current_id += 1

        # Create sequences for each show part
        start_time = 0
        previous_bpm = None

        for i, row in structure_df.iterrows():
            sequence_name = f"{show_name}_{category}_{row['showpart']}"
            sequence = create_sequence(root, current_id, sequence_name, scene.get("ID"), row['bpm'])

            # Get effect data for this show part and category
            key = (row['showpart'], category)
            print(f"Checking key: {key}")
            if key in show_values:
                effect_data = show_values[key]
                print(f"Effect data: {effect_data}")
                if effect_data.get('effect'):
                    print(f"Found effect: {effect_data['effect']}")
                    # Get unique fixture definitions and channels for this category
                    unique_fixtures = category_fixtures.drop_duplicates(subset=['Manufacturer', 'Model'])
                    for _, fixture in unique_fixtures.iterrows():
                        fixture_key = f"{fixture['Manufacturer']}_{fixture['Model']}"
                        print(f"Looking for fixture: {fixture_key}")
                        fixture_def = fixture_definitions.get(fixture_key)
                        print(f"Found fixture definition: {True if fixture_def else False}")

                        if fixture_def:
                            # Split module and function name
                            module_name, func_name = effect_data['effect'].split('.')
                            effect_module = effects.get(module_name)
                            print(f"Effect module: {effect_module}")
                            print(f"Effect function name: {func_name}")
                            print(f"Has attribute: {hasattr(effect_module, func_name)}")

                            # Get the first available mode if CurrentMode is not specified
                            available_modes = fixture_def.get('modes', [])
                            current_mode = (fixture.get('Mode') if 'Mode' in fixture
                                            else available_modes[0]['name'] if available_modes
                            else None)

                            if effect_module and hasattr(effect_module, func_name) and current_mode:
                                print(f"Creating effect steps with mode: {current_mode}")
                                effect_func = getattr(effect_module, func_name)
                                steps = effect_func(start_time,
                                                    fixture_def,
                                                    current_mode,
                                                    start_bpm=previous_bpm,
                                                    end_bpm=row['bpm'],
                                                    signature=row['signature'],
                                                    transition=row['transition'],
                                                    num_bars=row['num_bars'],
                                                    speed=effect_data.get('speed', '1'),
                                                    color=effect_data.get('color', ''),
                                                    fixture_num=fixture_num,
                                                    fixture_start_id=fixture_start_id)
                                print(f"Steps created: {len(steps) if steps else 0}")
                                add_steps_to_sequence(sequence, steps)

            show_function = ET.SubElement(track, "ShowFunction")
            show_function.set("ID", str(current_id))
            show_function.set("StartTime", str(start_time))
            show_function.set("Color", row['color'])

            start_time = calculate_start_time(
                start_time,
                row['signature'],
                row['bpm'],
                row['num_bars'],
                row['transition'],
                previous_bpm
            )
            previous_bpm = row['bpm']
            current_id += 1
        fixture_start_id += fixture_num
        track_id += 1


    return current_id


def _convert_dimmer_steps_to_rgb(steps, dimmer_block, colour_blocks, fixture_def, mode_name, fixture_num, fixture_start_id):
    """
    Convert dimmer intensity steps to RGB channel steps for fixtures without dimmer capability.

    Args:
        steps: List of Step XML elements with dimmer intensity values
        dimmer_block: The DimmerBlock being processed
        colour_blocks: List of ColourBlocks from the same light block
        fixture_def: Fixture definition dictionary
        mode_name: Current fixture mode name
        fixture_num: Number of fixtures in group
        fixture_start_id: Starting fixture ID

    Returns:
        List of Step XML elements with RGB channel values
    """
    from utils.effects_utils import get_channels_by_property

    # Get RGB channels from fixture definition (try different preset names)
    channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityRed", "IntensityGreen", "IntensityBlue"])

    if not channels_dict:
        print("Warning: No RGB channels found for fixture without dimmer")
        return steps

    # Verify we have all three RGB channels
    if 'IntensityRed' not in channels_dict or 'IntensityGreen' not in channels_dict or 'IntensityBlue' not in channels_dict:
        print(f"Warning: Missing some RGB channels. Found: {list(channels_dict.keys())}")
        return steps

    # Helper function to find overlapping colour block at a given time
    def get_rgb_at_time(time_seconds):
        """Get RGB values from overlapping colour block, or (0,0,0) if none."""
        for colour_block in colour_blocks:
            if colour_block.start_time <= time_seconds <= colour_block.end_time:
                # Found overlapping colour block
                r = getattr(colour_block, 'red', 0)
                g = getattr(colour_block, 'green', 0)
                b = getattr(colour_block, 'blue', 0)
                return (int(r), int(g), int(b))
        # No overlapping colour block
        return (0, 0, 0)

    # Convert each step
    converted_steps = []
    cumulative_time = 0

    for step in steps:
        # Calculate time of this step (in seconds)
        fade_in = int(step.get("FadeIn", 0))
        hold = int(step.get("Hold", 0))
        step_time = dimmer_block.start_time + (cumulative_time / 1000.0)
        cumulative_time += fade_in + hold

        # Parse intensity values from step
        step_text = step.text if step.text else ""
        # Format: "fixture_id:channel,value:fixture_id:channel,value..."

        # Parse to get intensity for each fixture
        fixture_intensities = {}
        if step_text:
            fixture_parts = step_text.split(':')
            for i in range(0, len(fixture_parts), 2):
                if i + 1 < len(fixture_parts):
                    fixture_id = int(fixture_parts[i])
                    channel_value_pairs = fixture_parts[i + 1].split(',')
                    if len(channel_value_pairs) >= 2:
                        intensity = int(channel_value_pairs[1])
                        fixture_intensities[fixture_id] = intensity

        # Get RGB values at this time
        base_rgb = get_rgb_at_time(step_time)

        # Create new step with RGB values
        new_step = ET.Element("Step")
        new_step.set("Number", step.get("Number"))
        new_step.set("FadeIn", step.get("FadeIn"))
        new_step.set("Hold", step.get("Hold"))
        new_step.set("FadeOut", step.get("FadeOut"))

        # Build RGB values for all fixtures
        values = []
        total_values = 0

        for i in range(fixture_num):
            fixture_id = fixture_start_id + i
            intensity = fixture_intensities.get(fixture_id, 0)

            # Apply RGB values to ALL channel sets (e.g., all 10 segments)
            num_rgb_sets = len(channels_dict['IntensityRed'])
            channel_value_pairs = []

            for seg_idx in range(num_rgb_sets):
                # Determine per-segment intensity based on effect type
                seg_intensity = intensity

                if dimmer_block.effect_type == "twinkle":
                    # Twinkle: Each segment independently randomized
                    # Use step number and segment index as seed for pseudo-random variation
                    import random
                    random.seed(int(step.get("Number")) * 1000 + seg_idx + fixture_id)
                    seg_intensity = random.randint(0, 255)

                elif dimmer_block.effect_type in ["ping_pong_smooth", "waterfall"]:
                    # Wave pattern: offset intensity based on segment index
                    # Create a wave that moves across segments
                    step_num = int(step.get("Number"))
                    wave_position = (step_num + seg_idx) % num_rgb_sets
                    wave_intensity = abs((wave_position - num_rgb_sets / 2) / (num_rgb_sets / 2))
                    seg_intensity = int(intensity * (1.0 - wave_intensity))

                # For static/strobe: use base intensity (uniform across segments)

                # Scale RGB by segment intensity
                intensity_ratio = seg_intensity / 255.0
                scaled_r = int(base_rgb[0] * intensity_ratio)
                scaled_g = int(base_rgb[1] * intensity_ratio)
                scaled_b = int(base_rgb[2] * intensity_ratio)

                r_ch = channels_dict['IntensityRed'][seg_idx]['channel']
                g_ch = channels_dict['IntensityGreen'][seg_idx]['channel']
                b_ch = channels_dict['IntensityBlue'][seg_idx]['channel']
                channel_value_pairs.extend([f"{r_ch},{scaled_r}", f"{g_ch},{scaled_g}", f"{b_ch},{scaled_b}"])

            channel_values = ",".join(channel_value_pairs)
            total_values += num_rgb_sets * 3

            values.append(f"{fixture_id}:{channel_values}")

        new_step.set("Values", str(total_values))
        new_step.text = ":".join(values)
        converted_steps.append(new_step)

    return converted_steps


def _generate_movement_shape_steps(movement_block, fixture_def, mode_name, fixture_conf,
                                    fixture_start_id, bpm, signature, num_bars):
    """
    Generate movement shape steps for a movement block.

    Supports static positioning and dynamic shapes (circle, diamond, lissajous, etc.)
    with clipping to boundary limits.

    Step density is kept constant per shape cycle (minimum 32 steps per cycle) for
    smooth motion. The speed setting controls how many times the shape is traced,
    not the step count.

    Parameters:
        movement_block: MovementBlock with effect parameters
        fixture_def: Fixture definition dictionary
        mode_name: Current fixture mode name
        fixture_conf: List of fixture configurations
        fixture_start_id: Starting fixture ID for value assignment
        bpm: Beats per minute
        signature: Time signature (e.g., "4/4")
        num_bars: Number of bars for the effect

    Returns:
        List of Step elements for QLC+ sequence
    """
    import math
    from utils.effects_utils import get_channels_by_property

    # Get pan/tilt channels
    channels_dict = get_channels_by_property(fixture_def, mode_name, ["PositionPan", "PositionTilt"])
    if not channels_dict:
        return []

    # Get effect parameters
    effect_type = movement_block.effect_type
    center_pan = movement_block.pan
    center_tilt = movement_block.tilt
    pan_amplitude = movement_block.pan_amplitude
    tilt_amplitude = movement_block.tilt_amplitude
    pan_min = movement_block.pan_min
    pan_max = movement_block.pan_max
    tilt_min = movement_block.tilt_min
    tilt_max = movement_block.tilt_max
    lissajous_ratio = getattr(movement_block, 'lissajous_ratio', '1:2')
    phase_offset_enabled = getattr(movement_block, 'phase_offset_enabled', False)
    phase_offset_degrees = getattr(movement_block, 'phase_offset_degrees', 0.0)
    effect_speed = movement_block.effect_speed

    # Convert speed to multiplier
    if '/' in effect_speed:
        num, denom = map(int, effect_speed.split('/'))
        speed_multiplier = num / denom
    else:
        speed_multiplier = float(effect_speed)

    # Calculate timing
    numerator, denominator = map(int, signature.split('/'))
    beats_per_bar = (numerator * 4) / denominator
    seconds_per_beat = 60.0 / bpm
    seconds_per_bar = beats_per_bar * seconds_per_beat

    # Calculate block duration
    block_duration = movement_block.end_time - movement_block.start_time
    block_duration_ms = int(block_duration * 1000)

    # Calculate number of shape cycles based on speed
    # Speed "1" = 1 cycle per bar, Speed "2" = 2 cycles per bar, etc.
    total_cycles = (block_duration / seconds_per_bar) * speed_multiplier

    # Minimum steps per cycle for smooth motion (32 gives smooth curves)
    STEPS_PER_CYCLE = 32

    # Calculate total steps needed
    # For static, we only need 1 step
    if effect_type == "static":
        total_steps = 1
    else:
        # Ensure at least STEPS_PER_CYCLE steps, scaled by number of cycles
        total_steps = max(STEPS_PER_CYCLE, int(total_cycles * STEPS_PER_CYCLE))
        # Cap at a reasonable maximum to avoid too many steps
        total_steps = min(total_steps, 256)

    # Calculate step duration
    if total_steps > 0:
        step_duration_ms = block_duration_ms // total_steps
    else:
        step_duration_ms = block_duration_ms

    # Ensure minimum step duration of 20ms
    if step_duration_ms < 20 and total_steps > 1:
        total_steps = block_duration_ms // 20
        step_duration_ms = block_duration_ms // max(1, total_steps)

    # Parse lissajous ratio
    try:
        ratio_parts = lissajous_ratio.split(':')
        freq_pan = int(ratio_parts[0])
        freq_tilt = int(ratio_parts[1])
    except (ValueError, IndexError):
        freq_pan, freq_tilt = 1, 2

    fixture_num = len(fixture_conf) if fixture_conf else 1
    steps = []

    # Count channels per fixture
    pan_channels = channels_dict.get('PositionPan', [])
    tilt_channels = channels_dict.get('PositionTilt', [])
    channels_per_fixture = len(pan_channels) + len(tilt_channels)

    for step_idx in range(total_steps):
        step = ET.Element("Step")
        step.set("Number", str(step_idx))
        step.set("FadeIn", "0")
        step.set("Hold", str(step_duration_ms))
        step.set("FadeOut", "0")
        step.set("Values", str(channels_per_fixture * fixture_num))

        values = []

        for fixture_idx in range(fixture_num):
            fixture_id = fixture_start_id + fixture_idx

            # Calculate phase offset for this fixture
            if phase_offset_enabled:
                fixture_phase = (fixture_idx * phase_offset_degrees) * math.pi / 180.0
            else:
                fixture_phase = 0.0

            # Calculate position based on effect type
            # t represents the angle in radians, scaled by total_cycles to trace the shape multiple times
            t = 2 * math.pi * total_cycles * step_idx / max(1, total_steps) + fixture_phase

            if effect_type == "static":
                pan = center_pan
                tilt = center_tilt
            elif effect_type == "circle":
                pan = center_pan + pan_amplitude * math.cos(t)
                tilt = center_tilt + tilt_amplitude * math.sin(t)
            elif effect_type == "diamond":
                # Diamond: 4 corners, scaled by total_cycles for multiple traces
                phase = (step_idx / max(1, total_steps)) * 4 * total_cycles
                corner = int(phase) % 4
                local_t = phase - int(phase)
                corners = [
                    (center_pan, center_tilt - tilt_amplitude),
                    (center_pan + pan_amplitude, center_tilt),
                    (center_pan, center_tilt + tilt_amplitude),
                    (center_pan - pan_amplitude, center_tilt),
                ]
                start = corners[corner]
                end = corners[(corner + 1) % 4]
                pan = start[0] + local_t * (end[0] - start[0])
                tilt = start[1] + local_t * (end[1] - start[1])
            elif effect_type == "square":
                # Square: 4 corners, scaled by total_cycles for multiple traces
                phase = (step_idx / max(1, total_steps)) * 4 * total_cycles
                corner = int(phase) % 4
                local_t = phase - int(phase)
                corners = [
                    (center_pan - pan_amplitude, center_tilt - tilt_amplitude),
                    (center_pan + pan_amplitude, center_tilt - tilt_amplitude),
                    (center_pan + pan_amplitude, center_tilt + tilt_amplitude),
                    (center_pan - pan_amplitude, center_tilt + tilt_amplitude),
                ]
                start = corners[corner]
                end = corners[(corner + 1) % 4]
                pan = start[0] + local_t * (end[0] - start[0])
                tilt = start[1] + local_t * (end[1] - start[1])
            elif effect_type == "triangle":
                # Triangle: 3 corners, scaled by total_cycles for multiple traces
                phase = (step_idx / max(1, total_steps)) * 3 * total_cycles
                corner = int(phase) % 3
                local_t = phase - int(phase)
                corners = [
                    (center_pan, center_tilt - tilt_amplitude),
                    (center_pan + pan_amplitude * 0.866, center_tilt + tilt_amplitude * 0.5),
                    (center_pan - pan_amplitude * 0.866, center_tilt + tilt_amplitude * 0.5),
                ]
                start = corners[corner]
                end = corners[(corner + 1) % 3]
                pan = start[0] + local_t * (end[0] - start[0])
                tilt = start[1] + local_t * (end[1] - start[1])
            elif effect_type == "figure_8":
                pan = center_pan + pan_amplitude * math.sin(t)
                tilt = center_tilt + tilt_amplitude * math.sin(2 * t)
            elif effect_type == "lissajous":
                pan = center_pan + pan_amplitude * math.sin(freq_pan * t)
                tilt = center_tilt + tilt_amplitude * math.sin(freq_tilt * t)
            elif effect_type == "random":
                # Pseudo-random smooth motion using multiple sine waves
                pan = center_pan + pan_amplitude * (
                    0.5 * math.sin(3 * t) + 0.3 * math.sin(7 * t) + 0.2 * math.sin(11 * t)
                )
                tilt = center_tilt + tilt_amplitude * (
                    0.5 * math.sin(5 * t) + 0.3 * math.sin(11 * t) + 0.2 * math.sin(13 * t)
                )
            elif effect_type == "bounce":
                # Bouncing pattern using triangle waves, scaled by total_cycles
                bounce_t = (step_idx / max(1, total_steps)) * 4 * total_cycles
                pan_t = abs((bounce_t % 2) - 1)
                tilt_t = abs(((bounce_t + 0.5) % 2) - 1)
                pan = center_pan - pan_amplitude + 2 * pan_amplitude * pan_t
                tilt = center_tilt - tilt_amplitude + 2 * tilt_amplitude * tilt_t
            else:
                # Default to static
                pan = center_pan
                tilt = center_tilt

            # Apply clipping to boundaries
            pan = max(pan_min, min(pan_max, pan))
            tilt = max(tilt_min, min(tilt_max, tilt))

            # Build channel values for this fixture
            channel_value_pairs = []
            for pan_ch in pan_channels:
                channel_value_pairs.append(f"{pan_ch['channel']},{int(pan)}")
            for tilt_ch in tilt_channels:
                channel_value_pairs.append(f"{tilt_ch['channel']},{int(tilt)}")

            channel_values = ",".join(channel_value_pairs)
            values.append(f"{fixture_id}:{channel_values}")

        step.text = ":".join(values)
        steps.append(step)

    return steps


def create_tracks_from_timeline(show_function, engine, show, config, fixture_id_map,
                                function_id_counter, effects, fixture_definitions):
    """
    Creates Track elements from timeline_data (new timeline-based format).

    Parameters:
        show_function: The show Function element to add tracks to
        engine: The engine element for adding scenes
        show: Show object containing show data with timeline_data
        config: Configuration object
        fixture_id_map: Dictionary mapping fixture object IDs to their sequential IDs
        function_id_counter: Current function ID counter
        effects: dictionary containing effect names and link to module
        fixture_definitions: Dictionary of fixture definitions loaded from QLC+
    Returns:
        int: Next available function ID
    """
    from timeline.song_structure import SongStructure

    # Build song structure for timing calculations
    song_structure = SongStructure()
    song_structure.load_from_show_parts(show.parts)

    track_id = 0
    fixture_start_id = 0

    for lane in show.timeline_data.lanes:
        group_name = lane.fixture_group

        if group_name not in config.groups:
            print(f"Warning: Fixture group '{group_name}' not found, skipping lane")
            continue

        # Calculate number of fixtures in group
        fixture_num = len(config.groups[group_name].fixtures)

        # Create Track
        track = ET.SubElement(show_function, "Track")
        track.set("ID", str(track_id))
        track.set("Name", group_name.upper())
        track.set("SceneID", str(function_id_counter))
        track.set("isMute", "1" if lane.muted else "0")

        # Create Scene
        scene = ET.SubElement(engine, "Function")
        scene.set("ID", str(function_id_counter))
        scene.set("Type", "Scene")
        scene.set("Name", f"Scene for {show.name} - {group_name}")
        scene.set("Hidden", "True")

        # Add Scene properties
        speed = ET.SubElement(scene, "Speed")
        speed.set("FadeIn", "0")
        speed.set("FadeOut", "0")
        speed.set("Duration", "0")

        # Add ChannelGroupsVal
        ET.SubElement(scene, "ChannelGroupsVal").text = f"{track_id},0"

        # Add FixtureVal for fixtures in the group
        for fixture in config.groups[group_name].fixtures:
            fixture_val = ET.SubElement(scene, "FixtureVal")
            fixture_val.set("ID", str(fixture_id_map[id(fixture)]))

            num_channels = next((mode.channels for mode in fixture.available_modes
                                if mode.name == fixture.current_mode), 0)
            channel_values = ",".join([f"{i},0" for i in range(num_channels)])
            fixture_val.text = channel_values

        function_id_counter += 1

        # Create sequences for each light block
        for block in lane.light_blocks:
            if not block.effect_name:
                continue

            # Convert start_time from seconds to milliseconds
            start_time_ms = int(block.start_time * 1000)

            # Create sequence
            sequence_name = f"{show.name}_{group_name}_{start_time_ms}"

            # Find BPM at block start
            part_at_block = song_structure.get_part_at_time(block.start_time)
            block_bpm = part_at_block.bpm if part_at_block else 120

            sequence = create_sequence(engine, function_id_counter, sequence_name,
                                       scene.get("ID"), block_bpm)

            # Split effect name into module and function
            try:
                module_name, func_name = block.effect_name.split('.')
            except ValueError:
                print(f"Invalid effect name format: {block.effect_name}")
                continue

            effect_module = effects.get(module_name)

            if effect_module and hasattr(effect_module, func_name):
                effect_func = getattr(effect_module, func_name)

                # Get fixture definition from the first fixture in the group
                first_fixture = config.groups[group_name].fixtures[0]
                fixture_key = f"{first_fixture.manufacturer}_{first_fixture.model}"
                fixture_def = fixture_definitions.get(fixture_key)

                if fixture_def and first_fixture.current_mode and part_at_block:
                    # Calculate number of bars from block duration
                    numerator, denominator = map(int, part_at_block.signature.split('/'))
                    beats_per_bar = (numerator * 4) / denominator
                    seconds_per_bar = beats_per_bar * (60.0 / block_bpm)
                    num_bars = max(1, int(block.duration / seconds_per_bar))

                    # Get parameters
                    params = block.parameters or {}

                    try:
                        steps = effect_func(
                            start_step=0,
                            fixture_def=fixture_def,
                            mode_name=first_fixture.current_mode,
                            start_bpm=block_bpm,
                            end_bpm=block_bpm,
                            signature=part_at_block.signature,
                            transition="instant",
                            num_bars=num_bars,
                            speed=params.get('speed', '1'),
                            color=params.get('color', ''),
                            fixture_conf=config.groups[group_name].fixtures,
                            fixture_start_id=fixture_start_id,
                            intensity=params.get('intensity', 200),
                            spot=config.spots.get(params.get('spot')) if params.get('spot') else None,
                        )
                        add_steps_to_sequence(sequence, steps)
                    except Exception as e:
                        print(f"Error creating effect steps: {e}")
                        import traceback
                        traceback.print_exc()

            # Create ShowFunction
            show_func = ET.SubElement(track, "ShowFunction")
            show_func.set("ID", str(function_id_counter))
            show_func.set("StartTime", str(start_time_ms))

            # Use color from parameters or default
            color = block.parameters.get('color', '#808080') if block.parameters else '#808080'
            show_func.set("Color", color)

            function_id_counter += 1

        # Check if this fixture group has dimmer capability
        group_capabilities = config.groups[group_name].capabilities if hasattr(config.groups[group_name], 'capabilities') else None
        has_dimmer = group_capabilities.has_dimmer if group_capabilities else True
        has_colour = group_capabilities.has_colour if group_capabilities else False

        # Process dimmer blocks for this lane
        for block in lane.light_blocks:
            for dimmer_block in block.dimmer_blocks:
                # Get effect module
                effect_module = effects.get("dimmers")
                if not effect_module:
                    continue

                # Get effect function based on effect_type
                effect_func_name = dimmer_block.effect_type
                if not hasattr(effect_module, effect_func_name):
                    print(f"Warning: Effect function '{effect_func_name}' not found in dimmers module")
                    continue

                effect_func = getattr(effect_module, effect_func_name)

                # Convert start_time from seconds to milliseconds
                dimmer_start_time_ms = int(dimmer_block.start_time * 1000)

                # Create sequence for this dimmer block
                sequence_name = f"{show.name}_{group_name}_dimmer_{dimmer_start_time_ms}"

                # Find BPM and song part at dimmer block start
                part_at_dimmer = song_structure.get_part_at_time(dimmer_block.start_time)
                dimmer_bpm = part_at_dimmer.bpm if part_at_dimmer else 120

                sequence = create_sequence(engine, function_id_counter, sequence_name,
                                          scene.get("ID"), dimmer_bpm)

                # Get fixture definition
                first_fixture = config.groups[group_name].fixtures[0]
                fixture_key = f"{first_fixture.manufacturer}_{first_fixture.model}"
                fixture_def = fixture_definitions.get(fixture_key)

                if fixture_def and first_fixture.current_mode and part_at_dimmer:
                    # Calculate number of bars from dimmer block duration
                    dimmer_duration = dimmer_block.end_time - dimmer_block.start_time
                    numerator, denominator = map(int, part_at_dimmer.signature.split('/'))
                    beats_per_bar = (numerator * 4) / denominator
                    seconds_per_bar = beats_per_bar * (60.0 / dimmer_bpm)
                    num_bars = max(1, int(dimmer_duration / seconds_per_bar))

                    try:
                        # Call the effect function with dimmer block parameters
                        steps = effect_func(
                            start_step=0,
                            fixture_def=fixture_def,
                            mode_name=first_fixture.current_mode,
                            start_bpm=dimmer_bpm,
                            end_bpm=dimmer_bpm,
                            signature=part_at_dimmer.signature,
                            transition="instant",
                            num_bars=num_bars,
                            speed=dimmer_block.effect_speed,
                            color=None,
                            fixture_conf=config.groups[group_name].fixtures,
                            fixture_start_id=fixture_start_id,
                            intensity=int(dimmer_block.intensity),
                            spot=None,
                        )

                        # If fixture has no dimmer, convert intensity steps to RGB steps
                        if not has_dimmer and has_colour:
                            steps = _convert_dimmer_steps_to_rgb(
                                steps=steps,
                                dimmer_block=dimmer_block,
                                colour_blocks=block.colour_blocks,
                                fixture_def=fixture_def,
                                mode_name=first_fixture.current_mode,
                                fixture_num=fixture_num,
                                fixture_start_id=fixture_start_id
                            )

                        add_steps_to_sequence(sequence, steps)
                    except Exception as e:
                        print(f"Error creating dimmer effect steps: {e}")
                        import traceback
                        traceback.print_exc()

                # Create ShowFunction for this dimmer block
                show_func = ET.SubElement(track, "ShowFunction")
                show_func.set("ID", str(function_id_counter))
                show_func.set("StartTime", str(dimmer_start_time_ms))

                # Use color from song part for easy identification
                color = part_at_dimmer.color if part_at_dimmer else '#808080'
                show_func.set("Color", color)

                function_id_counter += 1

        # Process movement blocks for this lane
        for block in lane.light_blocks:
            for movement_block in block.movement_blocks:
                # Get fixture definition first - skip if not available
                first_fixture = config.groups[group_name].fixtures[0]
                fixture_key = f"{first_fixture.manufacturer}_{first_fixture.model}"
                fixture_def = fixture_definitions.get(fixture_key)

                # Find BPM and song part at movement block start
                part_at_movement = song_structure.get_part_at_time(movement_block.start_time)

                if not fixture_def or not first_fixture.current_mode or not part_at_movement:
                    print(f"Warning: Skipping movement block - missing fixture_def, mode, or part")
                    continue

                # Convert start_time from seconds to milliseconds
                movement_start_time_ms = int(movement_block.start_time * 1000)

                # Calculate movement block duration in milliseconds
                movement_duration = movement_block.end_time - movement_block.start_time
                movement_duration_ms = int(movement_duration * 1000)

                # Calculate number of bars from movement block duration
                movement_bpm = part_at_movement.bpm if part_at_movement else 120
                numerator, denominator = map(int, part_at_movement.signature.split('/'))
                beats_per_bar = (numerator * 4) / denominator
                seconds_per_bar = beats_per_bar * (60.0 / movement_bpm)
                num_bars = max(1, int(movement_duration / seconds_per_bar))

                # Generate movement shape steps FIRST, before creating sequence
                try:
                    steps = _generate_movement_shape_steps(
                        movement_block=movement_block,
                        fixture_def=fixture_def,
                        mode_name=first_fixture.current_mode,
                        fixture_conf=config.groups[group_name].fixtures,
                        fixture_start_id=fixture_start_id,
                        bpm=movement_bpm,
                        signature=part_at_movement.signature,
                        num_bars=num_bars
                    )

                    if not steps:
                        print(f"Warning: No steps generated for movement block at {movement_start_time_ms}ms")
                        continue

                except Exception as e:
                    print(f"Error creating movement effect steps: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

                # Only create sequence and ShowFunction if we have valid steps
                sequence_name = f"{show.name}_{group_name}_movement_{movement_start_time_ms}"
                sequence = create_sequence(engine, function_id_counter, sequence_name,
                                          scene.get("ID"), movement_bpm)
                add_steps_to_sequence(sequence, steps)

                # Create ShowFunction for this movement block
                show_func = ET.SubElement(track, "ShowFunction")
                show_func.set("ID", str(function_id_counter))
                show_func.set("StartTime", str(movement_start_time_ms))
                show_func.set("Duration", str(movement_duration_ms))

                # Use blue color for movement blocks
                show_func.set("Color", "#6496FF")

                function_id_counter += 1

        fixture_start_id += fixture_num
        track_id += 1

    return function_id_counter


def create_shows(engine, config: Configuration, fixture_id_map: dict, fixture_definitions: dict):
    """
    Creates show function elements from Configuration data

    Parameters:
        engine: The engine XML element to add the show functions to
        config: Configuration object containing show data
        fixture_id_map: Dictionary mapping fixture object IDs to their sequential IDs
        fixture_definitions: Dictionary of fixture definitions loaded from QLC+
    Returns:
        int: Next available function ID
    """
    function_id_counter = 0

    # Load effects modules from effects directory
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    effects_dir = os.path.join(project_root, "effects")
    effects = load_effects(effects_dir)

    # Process each show in the configuration
    for show_name, show in config.shows.items():
        # Create Function element for the show
        show_function = ET.SubElement(engine, "Function")
        show_function.set("ID", str(function_id_counter))
        show_function.set("Type", "Show")
        show_function.set("Name", show_name)
        function_id_counter += 1

        # Create TimeDivision element
        time_division = ET.SubElement(show_function, "TimeDivision")
        time_division.set("Type", "Time")
        # Use BPM from first show part, or default to 120
        time_division.set("BPM", str(show.parts[0].bpm if show.parts else 120))

        # Check if show has timeline_data (new format) or effects (legacy format)
        if show.timeline_data and show.timeline_data.lanes:
            # Use new timeline-based export
            function_id_counter = create_tracks_from_timeline(
                show_function,
                engine,
                show,
                config,
                fixture_id_map,
                function_id_counter,
                effects,
                fixture_definitions
            )
            print(f"Successfully created show from timeline: {show_name}")
        else:
            # Use legacy effects-based export
            # Group effects by fixture group
            effects_by_group = {}
            for effect in show.effects:
                if effect.fixture_group not in effects_by_group:
                    effects_by_group[effect.fixture_group] = []
                effects_by_group[effect.fixture_group].append(effect)

            # Create tracks for this show
            function_id_counter = create_tracks(
                show_function,
                engine,
                show,
                effects_by_group,
                config,
                fixture_id_map,
                function_id_counter,
                effects,
                fixture_definitions
            )
            print(f"Successfully created show from effects: {show_name}")

    return function_id_counter




