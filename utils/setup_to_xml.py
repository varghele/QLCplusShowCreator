# setup_to_xml.py
import xml.etree.ElementTree as ET
import csv
import os
import json


def read_universes_from_csv():
    universes = []
    csv_path = os.path.join('../setup', 'universes.json')
    with open(csv_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            universes.append(row)
    return universes

def read_fixtures_from_csv():
    fixtures = []
    csv_path = os.path.join('../setup', 'fixtures.csv')
    with open(csv_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            fixtures.append(row)
    return fixtures


def create_universe_elements(input_output_map):
    """
    Creates universe elements from JSON data and adds them to the input_output_map
    """
    with open('../setup/universes.json', 'r') as file:
        config = json.load(file)

    for universe in config['universes']:
        # Create Universe element
        universe_elem = ET.SubElement(input_output_map, "Universe")
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


def create_fixture_elements(root, id_start=0):
    """
    Creates fixture elements from CSV data and adds them to the root
    Parameters:
        root: The root XML element to add fixtures to
        id_start: Starting ID number for fixtures (default 0)
    """
    fixtures = read_fixtures_from_csv()

    for index, fixture in enumerate(fixtures):
        fixture_elem = ET.SubElement(root, "Fixture")
        ET.SubElement(fixture_elem, "Manufacturer").text = fixture['Manufacturer']
        ET.SubElement(fixture_elem, "Model").text = fixture['Model']
        ET.SubElement(fixture_elem, "Mode").text = f"{int(fixture['Mode'])} Channels Mode"
        ET.SubElement(fixture_elem, "ID").text = str(index + id_start)  # Add ID element with incremental value
        ET.SubElement(fixture_elem, "Name").text = f"{fixture['Model']}"  # Add Name element
        ET.SubElement(fixture_elem, "Universe").text = str(int(fixture['Universe']) - 1)  # Convert to 0-based index
        ET.SubElement(fixture_elem, "Address").text = fixture['Address']
        ET.SubElement(fixture_elem, "Channels").text = str(int(fixture['Channels']))