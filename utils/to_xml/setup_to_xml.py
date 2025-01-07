# setup_to_xml.py
import xml.etree.ElementTree as ET
import csv
import os
import json
import pandas as pd


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


def create_universe_elements(root, universes_json_pth = '../setup/universes.json'):
    """
    Creates universe elements from JSON data and adds them to the root
    """
    with open(universes_json_pth, 'r') as file:
        config = json.load(file)

    for universe in config['universes']:
        # Create Universe element
        universe_elem = ET.SubElement(root, "Universe")
        universe_elem.set("Name", universe['name'])
        universe_elem.set("ID", str(universe['id']))

        # Add Output if specified
        if 'output' in universe:
            output = ET.SubElement(universe_elem, "Output")
            output.set("Plugin", universe['output']['plugin'])
            output.set("Line", universe['output']['line'])

            # Add plugin parameters
            plugin_params = ET.SubElement(output, "PluginParameters")
            for param_name, param_value in universe['output']['parameters'].items():
                plugin_params.set(param_name, str(param_value))


def create_fixture_elements(root, setup_fixtures_dir='../setup', id_start=0):
    """
    Creates fixture elements from CSV data and adds them to the root
    Parameters:
        root: The root XML element to add fixtures to
        id_start: Starting ID number for fixtures (default 0)
        :param id_start:
        :param root:
        :param setup_fixtures_dir:
    """
    fixtures = read_fixtures_from_csv(setup_fixtures_dir)

    for index, fixture in enumerate(fixtures):
        fixture_elem = ET.SubElement(root, "Fixture")
        ET.SubElement(fixture_elem, "Manufacturer").text = fixture['Manufacturer']
        ET.SubElement(fixture_elem, "Model").text = fixture['Model']
        ET.SubElement(fixture_elem, "Mode").text = f"{fixture['Mode']}"
        ET.SubElement(fixture_elem, "ID").text = str(index + id_start)  # Add ID element with incremental value
        ET.SubElement(fixture_elem, "Name").text = f"{fixture['Name']}"  # Add Name element
        ET.SubElement(fixture_elem, "Universe").text = str(int(fixture['Universe']) - 1)  # Convert to 0-based index
        ET.SubElement(fixture_elem, "Address").text = str(int(fixture['Address']) - 1)  # Convert to 0-based index
        ET.SubElement(fixture_elem, "Channels").text = str(int(fixture['Channels']))


def create_channels_groups(root):
    """
    Creates ChannelsGroup elements from groups.csv
    Parameters:
        root: The root XML element to add the ChannelsGroups to
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    groups_file = os.path.join(base_dir, 'setup', 'groups.csv')

    if not os.path.exists(groups_file):
        print("Groups file not found in setup directory")
        return

    # Read groups data
    groups_df = pd.read_csv(groups_file)

    # Group fixtures by category
    categories = groups_df.groupby('category')

    # Create channel groups for each category
    group_id = 0
    for category_name, group in categories:
        # Skip None/empty categories
        if pd.isna(category_name) or category_name == 'None':
            continue

        channels_list = []
        for _, fixture in group.iterrows():
            # Get fixture ID and number of channels
            fixture_id = fixture['id'] #wrong
            #fixture_id =
            num_channels = int(fixture['Channels'])

            # Add each channel to the list
            for channel in range(num_channels):
                channels_list.extend([str(fixture_id), str(channel)])

        # Only create group if there are channels
        if channels_list:
            # Create ChannelsGroup element
            channels_group = ET.SubElement(root, "ChannelsGroup")
            channels_group.set("ID", str(group_id))
            channels_group.set("Name", str(category_name))
            channels_group.set("Value", "0")
            channels_group.text = ",".join(channels_list)

            group_id += 1

    return root
