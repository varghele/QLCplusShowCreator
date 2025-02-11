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
    """
    for universe_id, universe in config.universes.items():
        # Create Universe element
        universe_elem = ET.SubElement(input_output_map, "Universe")
        universe_elem.set("Name", universe.name)
        universe_elem.set("ID", str(universe_id - 1))  # Convert to 0-based index

        # Add Output
        output = ET.SubElement(universe_elem, "Output")
        output.set("Plugin", universe.output['plugin'])
        output.set("Line", str(universe_id - 1))  # Line should match universe ID

        # Add plugin parameters based on plugin type
        if universe.output['plugin'] == 'ArtNet':
            plugin_params = ET.SubElement(output, "PluginParameters")
            for param_name, param_value in universe.output['parameters'].items():
                plugin_params.set(param_name, str(param_value))

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


def create_channels_groups(engine, config: Configuration, fixture_id_map: dict):
    """
    Creates ChannelsGroup elements from Configuration data

    Parameters:
        engine: The engine XML element to add the ChannelsGroups to
        config: Configuration object containing groups and fixtures data
        fixture_id_map: Dictionary mapping fixture object IDs to their sequential IDs
    """
    group_id = 0
    for group_name, group in config.groups.items():
        # Create ChannelsGroup element
        channels_group = ET.SubElement(engine, "ChannelsGroup")
        channels_group.set("ID", str(group_id))
        channels_group.set("Name", group_name)
        channels_group.set("Value", "0")

        # Create channel list for all fixtures in group
        channels_list = []
        for fixture in group.fixtures:
            # Get number of channels from fixture's current mode
            num_channels = next((mode.channels for mode in fixture.available_modes
                                 if mode.name == fixture.current_mode), 0)

            # Get fixture ID from mapping
            fixture_id = fixture_id_map[id(fixture)]

            # Add each channel to the list
            for channel in range(num_channels):
                channels_list.extend([str(fixture_id), str(channel)])

        # Only create group if there are channels
        if channels_list:
            channels_group.text = ",".join(channels_list)
            group_id += 1

    return engine
