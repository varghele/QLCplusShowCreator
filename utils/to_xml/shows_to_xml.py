import os
import json
import xml.etree.ElementTree as ET

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

def load_fixture_definitions(json_path):
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
        return previous_time + int(milliseconds_per_bar * num_bars)

    elif transition == "gradual":
        total_time = 0
        for bar in range(num_bars):
            # Using a slightly curved interpolation instead of linear
            progress = (bar / num_bars) ** 0.52  # Adding slight curve to the transition
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
    ms_per_beat = 60000 / bpm

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


def create_tracks(function, root, effects, base_dir="../"):
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
    fixture_definitions = load_fixture_definitions(fixtures_file)

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


def create_shows(root, shows_dir='../shows', base_dir='../'):
    """
    Creates show function elements from show files in the shows folder
    Parameters:
        root: The root XML element to add the show functions to
        shows_dir: Directory containing show files
        base_dir: Base directory path
    Returns:
        int: Next available ID
    """
    show_id = 0  # Initialize show ID counter

    # Convert relative paths to absolute paths
    shows_dir = os.path.abspath(shows_dir)
    base_dir = os.path.abspath(base_dir)

    # Get all show folders
    for show_name in sorted(os.listdir(shows_dir)):
        show_path = os.path.join(shows_dir, show_name)

        if os.path.isdir(show_path):
            # Check if all required files exist
            required_files = [
                f"{show_name}_setup.json",
                f"{show_name}_structure.csv",  # Added file extension
                f"{show_name}_values.json"  # Added values file requirement
            ]

            missing_files = [f for f in required_files
                             if not os.path.exists(os.path.join(show_path, f))]

            if not missing_files:
                try:
                    # Create Function element for the show
                    function = ET.SubElement(root, "Function")
                    function.set("ID", str(show_id))
                    function.set("Type", "Show")
                    function.set("Name", show_name)

                    # Read show setup file for configuration
                    setup_file = os.path.join(show_path, f"{show_name}_setup.json")
                    with open(setup_file, 'r') as f:
                        setup_data = json.load(f)

                    # Create TimeDivision element with data from setup
                    time_division = ET.SubElement(function, "TimeDivision")
                    time_division.set("Type", setup_data.get("TimeType", "Time"))
                    time_division.set("BPM", str(setup_data.get("BPM", 120)))

                    # Load effects modules
                    effects_dir = os.path.join(base_dir, "effects")
                    effects = load_effects(effects_dir)

                    # Create tracks for this show and get next available ID
                    next_id = create_tracks(function, root, effects, base_dir)
                    show_id = next_id  # Update show_id for next iteration

                    print(f"Successfully created show: {show_name}")

                except json.JSONDecodeError as e:
                    print(f"Error reading setup file for show {show_name}: {e}")
                except Exception as e:
                    print(f"Error processing show {show_name}: {str(e)}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"Show {show_name} is missing required files: {missing_files}")

    return show_id




