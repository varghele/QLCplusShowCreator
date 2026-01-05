# setup_to_xml.py
import xml.etree.ElementTree as ET
import csv
import os
import json
import pandas as pd
from config.models import Configuration


def read_universes_from_csv():
    universes = []
    csv_path = os.path.join('../../setup', 'universes.json')
    with open(csv_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            universes.append(row)
    return universes


def read_fixtures_from_csv(setup_fixtures_dir):
    fixtures = []
    csv_path = os.path.join(setup_fixtures_dir, 'fixtures.csv')
    with open(csv_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            fixtures.append(row)
    return fixtures


def create_universe_elements(input_output_map, config: Configuration):
    """
    Creates universe elements from Configuration data and adds them to the InputOutputMap

    Parameters:
        input_output_map: The InputOutputMap XML element to add universes to
        config: Configuration object containing universe data

    Note:
        QLC+ network interfaces (Lines) 0 and 1 are hardcoded and not used.
        We start from Line 2 with corresponding UIDs (network interface IPs).
        Universe 1 → Line 2, Universe 2 → Line 3, etc.

        UID (network interface IP) is mapped to Line number:
        Line 2 → 169.254.148.219
        Line 3 → 169.254.163.190
        Line 4 → 169.254.22.59
        Line 5 → 169.254.31.82
        Line 6 → 192.168.178.30

        Universe/subnet/IP settings must be configured manually in QLC+.
        QLC+ stores these in separate plugin configuration files, not the workspace.
    """
    # Fixed mapping of Line numbers to UIDs (network interface IPs)
    LINE_TO_UID = {
        2: "169.254.148.219",
        3: "169.254.163.190",
        4: "169.254.22.59",
        5: "169.254.31.82",
        6: "192.168.178.30"
    }

    for universe_id, universe in config.universes.items():
        # Create Universe element
        universe_elem = ET.SubElement(input_output_map, "Universe")
        universe_elem.set("Name", universe.name)
        universe_elem.set("ID", str(universe_id - 1))  # Convert to 0-based index

        # Add Output
        output = ET.SubElement(universe_elem, "Output")
        output.set("Plugin", universe.output['plugin'])

        # Calculate Line number (skip Lines 0 and 1)
        line_number = universe_id + 1
        output.set("Line", str(line_number))

        # Add UID (network interface IP) if available for this Line
        if line_number in LINE_TO_UID:
            output.set("UID", LINE_TO_UID[line_number])

    return input_output_map


def create_fixture_elements(engine, config: Configuration, id_start=0):
    """
    Creates fixture elements from Configuration data and adds them to the engine element

    Parameters:
        engine: The engine XML element to add fixtures to
        config: Configuration object containing fixture data
        id_start: Starting ID number for fixtures (default 0)
    """
    fixture_id_map = {}  # To store mapping of fixture objects to their IDs

    for index, fixture in enumerate(config.fixtures):
        fixture_elem = ET.SubElement(engine, "Fixture")
        ET.SubElement(fixture_elem, "Manufacturer").text = fixture.manufacturer
        ET.SubElement(fixture_elem, "Model").text = fixture.model
        ET.SubElement(fixture_elem, "Mode").text = fixture.current_mode
        ET.SubElement(fixture_elem, "ID").text = str(index + id_start)
        ET.SubElement(fixture_elem, "Name").text = fixture.name
        ET.SubElement(fixture_elem, "Universe").text = str(fixture.universe - 1)  # Convert to 0-based index
        ET.SubElement(fixture_elem, "Address").text = str(fixture.address - 1)  # Convert to 0-based index

        # Get channels from current mode
        channels = next((mode.channels for mode in fixture.available_modes
                         if mode.name == fixture.current_mode), 0)
        ET.SubElement(fixture_elem, "Channels").text = str(channels)

        # Store the mapping
        fixture_id_map[id(fixture)] = index + id_start

    return fixture_id_map


def create_channels_groups(engine, config: Configuration, fixture_id_map: dict, fixture_definitions: dict = None):
    """
    Creates individual ChannelsGroup elements for each capability (Pan, Tilt, Dimmer, Color, etc.)

    Parameters:
        engine: The engine XML element to add the ChannelsGroups to
        config: Configuration object containing groups and fixtures data
        fixture_id_map: Dictionary mapping fixture object IDs to their sequential IDs
        fixture_definitions: Dictionary of fixture definitions (optional, for better channel detection)
    """
    from utils.effects_utils import get_channels_by_property
    from utils.sublane_presets import DIMMER_PRESETS, COLOUR_PRESETS, MOVEMENT_PRESETS, SPECIAL_PRESETS

    group_id = 0

    # Define capability mappings: (preset_name, display_name)
    capability_mappings = [
        ("PositionPan", "Pan"),
        ("PositionTilt", "Tilt"),
        ("IntensityMasterDimmer", "Dimmer"),
        ("IntensityDimmer", "Dimmer"),
        ("IntensityRed", "Red"),
        ("IntensityGreen", "Green"),
        ("IntensityBlue", "Blue"),
        ("IntensityWhite", "White"),
        ("IntensityAmber", "Amber"),
        ("ColorMacro", "Color"),  # Color wheel
        ("GoboIndex", "Gobo"),
        ("GoboWheelIndex", "Gobo"),
        ("GoboRotation", "Gobo Rotation"),
        ("PrismRotation", "Prism"),
        ("ShutterStrobeSlowFast", "Shutter"),
        ("ShutterStrobeFastSlow", "Shutter"),
        ("BeamFocusNearFar", "Focus"),
        ("BeamFocusFarNear", "Focus"),
        ("BeamZoomSmallBig", "Zoom"),
        ("BeamZoomBigSmall", "Zoom"),
    ]

    for group_name, group in config.groups.items():
        if not group.fixtures:
            continue

        # Collect all channels for each capability across all fixtures in the group
        capability_channels = {}  # capability_name -> [(fixture_id, channel), ...]

        for fixture in group.fixtures:
            fixture_id = fixture_id_map.get(id(fixture))
            if fixture_id is None:
                continue

            # Get channels by property if we have fixture definitions
            if fixture_definitions:
                fixture_key = f"{fixture.manufacturer}_{fixture.model}"
                fixture_def = fixture_definitions.get(fixture_key)

                if fixture_def:
                    all_presets = list(DIMMER_PRESETS) + list(COLOUR_PRESETS) + list(MOVEMENT_PRESETS) + list(SPECIAL_PRESETS)
                    channels_dict = get_channels_by_property(fixture_def, fixture.current_mode, all_presets)

                    # Map each preset to its display name
                    for preset_name, display_name in capability_mappings:
                        if preset_name in channels_dict:
                            channel_list = channels_dict[preset_name]
                            # Get the first channel for each capability
                            if channel_list and isinstance(channel_list, list) and len(channel_list) > 0:
                                channel_num = channel_list[0].get('channel') if isinstance(channel_list[0], dict) else channel_list[0]

                                if display_name not in capability_channels:
                                    capability_channels[display_name] = []
                                capability_channels[display_name].append((fixture_id, channel_num))

        # Create a ChannelsGroup for each capability
        for capability_name, channels in capability_channels.items():
            if not channels:
                continue

            channels_group = ET.SubElement(engine, "ChannelsGroup")
            channels_group.set("ID", str(group_id))
            channels_group.set("Name", f"{group_name} - {capability_name}")
            channels_group.set("Value", "0")

            # Format: fixture_id,channel,fixture_id,channel,...
            channels_list = []
            for fixture_id, channel_num in channels:
                channels_list.extend([str(fixture_id), str(channel_num)])

            channels_group.text = ",".join(channels_list)
            group_id += 1

    return engine
