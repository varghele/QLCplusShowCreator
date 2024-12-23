# setup_to_xml.py
import xml.etree.ElementTree as ET
import csv
import os


def read_universes_from_csv():
    universes = []
    csv_path = os.path.join('setup', 'universes.csv')
    with open(csv_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            universes.append(row)
    return universes

def read_fixtures_from_csv():
    fixtures = []
    csv_path = os.path.join('setup', 'fixtures.csv')
    with open(csv_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            fixtures.append(row)
    return fixtures


def create_universe_elements(input_output_map):
    """
    Creates universe elements from CSV data and adds them to the input_output_map
    """
    universes = read_universes_from_csv()

    for universe in universes:
        universe_elem = ET.SubElement(input_output_map, "Universe")
        universe_elem.set("Name", universe['name'])
        universe_elem.set("ID", universe['ID'])

        # Add Output if specified
        if universe['output']:
            output = ET.SubElement(universe_elem, "Output")
            output.set("Plugin", universe['output'])
            output.set("Line", universe['line'])
            plugin_params = ET.SubElement(output, "PluginParameters")
            plugin_params.set("outputIP", universe['outputIP'])


def create_fixture_elements(engine):
    """
    Creates fixture elements from CSV data and adds them to the engine
    """
    fixtures = read_fixtures_from_csv()

    for fixture in fixtures:
        fixture_elem = ET.SubElement(engine, "Fixture")
        ET.SubElement(fixture_elem, "Manufacturer").text = fixture['Manufacturer']
        ET.SubElement(fixture_elem, "Model").text = fixture['Model']
        ET.SubElement(fixture_elem, "Mode").text = f"{int(fixture['Mode'])} Channels Mode"
        ET.SubElement(fixture_elem, "Universe").text = str(int(fixture['Universe']) - 1)  # Convert to 0-based index
        ET.SubElement(fixture_elem, "Address").text = fixture['Address']
        ET.SubElement(fixture_elem, "Channels").text = str(int(fixture['Channels']))