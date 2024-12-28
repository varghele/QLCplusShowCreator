import os
import json
import xml.etree.ElementTree as ET
import pandas as pd

import importlib
from utils.step_utils import create_step

def load_effects(effects_dir="effects"):
    """Loads all effect modules"""
    effects = {}
    for effect_file in os.listdir(effects_dir):
        if effect_file.endswith('.py') and not effect_file.startswith('__'):
            module_name = effect_file[:-3]
            module_path = f"effects.{module_name}"
            effects[module_name] = importlib.import_module(module_path)
    return effects

def add_steps_to_sequence(sequence, steps):
    """Adds steps to a sequence"""
    for step in steps:
        sequence.append(step)

# LOAD EFFECTS
effects = load_effects()


# Create a sequence with effects
def create_sequence_with_effects(sequence, start_step=0):
    # Get blinder channels from your configuration
    blinder_channels = [199, 173, 196]

    # Add a strobe effect
    strobe_steps = effects['blinders'].strobe(start_step, blinder_channels, speed="fast")
    add_steps_to_sequence(sequence, strobe_steps)

    # Add a flash effect after the strobe
    flash_steps = effects['blinders'].flash(start_step + len(strobe_steps), blinder_channels)
    add_steps_to_sequence(sequence, flash_steps)

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


def create_sequence(root, sequence_id, sequence_name, bound_scene_id):
    """
    Creates a Sequence function element
    Parameters:
        root: The root XML element to add the sequence to
        sequence_id: ID of the sequence
        sequence_name: Name of the sequence
        bound_scene_id: ID of the bound scene
    Returns:
        Element: The created sequence element
    """
    sequence = ET.SubElement(root, "Function")
    sequence.set("ID", str(sequence_id))
    sequence.set("Type", "Sequence")
    sequence.set("Name", sequence_name)
    sequence.set("BoundScene", str(bound_scene_id))

    speed = ET.SubElement(sequence, "Speed")
    speed.set("FadeIn", "0")
    speed.set("FadeOut", "0")
    speed.set("Duration", "0")

    direction = ET.SubElement(sequence, "Direction")
    direction.text = "Forward"

    run_order = ET.SubElement(sequence, "RunOrder")
    run_order.text = "SingleShot"

    speed_modes = ET.SubElement(sequence, "SpeedModes")
    speed_modes.set("FadeIn", "PerStep")
    speed_modes.set("FadeOut", "PerStep")
    speed_modes.set("Duration", "PerStep")

    return sequence


def create_tracks(function, root, base_dir="../"):
    """
    Creates Track elements, Scenes, and Sequences for each channel group category
    Parameters:
        function: The Function XML element (show) to add tracks to
        root: The root XML element where scenes will be added
        base_dir: Base directory path
    Returns:
        int: Next available ID
    """
    groups_file = os.path.join(base_dir, 'setup', 'groups.csv')
    show_name = function.get('Name')
    structure_file = os.path.join(base_dir, 'shows', show_name, f"{show_name}_structure")

    if not os.path.exists(groups_file) or not os.path.exists(structure_file):
        print("Required files not found")
        return

    groups_df = pd.read_csv(groups_file)
    structure_df = pd.read_csv(structure_file)
    categories = groups_df['category'].unique()
    current_id = int(function.get("ID")) + 1

    track_id = 0
    for category in categories:
        if pd.isna(category) or category == 'None':
            continue

        track = ET.SubElement(function, "Track")
        track.set("ID", str(track_id))
        track.set("Name", str(category).upper())
        track.set("SceneID", str(current_id))
        track.set("isMute", "0")

        # Create Scene
        scene = ET.SubElement(root, "Function")
        scene.set("ID", str(current_id))
        scene.set("Type", "Scene")
        scene.set("Name", f"Szene für {show_name} - Track {track_id + 1}")
        scene.set("Hidden", "True")

        speed = ET.SubElement(scene, "Speed")
        speed.set("FadeIn", "0")
        speed.set("FadeOut", "0")
        speed.set("Duration", "0")

        channel_groups = ET.SubElement(scene, "ChannelGroupsVal")
        channel_groups.text = "0,0"

        category_fixtures = groups_df[groups_df['category'] == category]
        for _, fixture in category_fixtures.iterrows():
            fixture_val = ET.SubElement(scene, "FixtureVal")
            fixture_val.set("ID", str(fixture['id']))
            fixture_val.text = ','.join([f"{i},0" for i in range(int(fixture['Channels']))])

        current_id += 1

        start_time = 0
        previous_bpm = None

        for _, row in structure_df.iterrows():
            sequence_name = f"{show_name}_{category}_{row['name']}"
            sequence = create_sequence(root, current_id, sequence_name, scene.get("ID"))

            show_function = ET.SubElement(track, "ShowFunction")
            show_function.set("ID", str(current_id))
            show_function.set("StartTime", str(start_time))
            show_function.set("Color", row['color'])

            # Calculate next start time with transition
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

        track_id += 1

    return current_id


def create_shows(root, shows_dir='../shows', base_dir='../'):
    """
    Creates show function elements from show files in the shows folder
    Parameters:
        root: The root XML element to add the show functions to
    """
    show_id = 0  # Initialize show ID counter

    # Get all show folders
    for show_name in os.listdir(shows_dir):
        show_path = os.path.join(shows_dir, show_name)

        if os.path.isdir(show_path):
            # Check if all required files exist
            required_files = [
                f"{show_name}_events",
                f"{show_name}_setup.json",
                f"{show_name}_structure"
            ]

            if all(os.path.exists(os.path.join(show_path, f)) for f in required_files):
                # Create Function element for the show
                function = ET.SubElement(root, "Function")
                function.set("ID", str(show_id))
                function.set("Type", "Show")
                function.set("Name", show_name)

                # Read show setup file for configuration
                setup_file = os.path.join(show_path, f"{show_name}_setup.json")
                try:
                    with open(setup_file, 'r') as f:
                        setup_data = json.load(f)

                    # Create TimeDivision element with data from setup
                    time_division = ET.SubElement(function, "TimeDivision")
                    time_division.set("Type", setup_data.get("TimeType", "Time"))
                    time_division.set("BPM", str(setup_data.get("BPM", 120)))

                    # Create tracks for this show
                    create_tracks(function, root, base_dir)

                except json.JSONDecodeError:
                    print(f"Error reading setup file for show: {show_name}")
                except Exception as e:
                    print(f"Error processing show {show_name}: {str(e)}")

                show_id += 1  # Increment show ID counter


