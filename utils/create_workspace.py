import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import json
import os
from utils.to_xml.setup_to_xml import (create_universe_elements, create_fixture_elements,
                                       create_channels_groups)
from utils.to_xml.shows_to_xml import create_shows
from utils.make.make_channel_groups import make_channel_groups_from_fixtures




def create_qlc_workspace():
    # Set up base dir
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Load configuration from JSON
    with open(os.path.join(base_dir, 'config.json'), 'r') as config_file:
        config = json.load(config_file)

    # Update other file paths to use base_dir
    universes_json_path = os.path.join(base_dir, 'setup', 'universes.json')
    setup_fixtures_dir = os.path.join(base_dir, 'setup')
    shows_dir = os.path.join(base_dir, 'shows')
    workspace_path = os.path.join(base_dir, 'workspace.qxw')

    # Create the root element with namespace
    root = ET.Element("Workspace")
    root.set("xmlns", "http://www.qlcplus.org/Workspace")
    root.set("CurrentWindow", config['base']['Workspace']['CurrentWindow'])

    # Create Creator section
    creator = ET.SubElement(root, "Creator")
    ET.SubElement(creator, "Name").text = "Q Light Controller Plus"
    ET.SubElement(creator, "Version").text = "4.12.4"
    ET.SubElement(creator, "Author").text = config['base']['Workspace']['author']

    # Create Engine section
    engine = ET.SubElement(root, "Engine")

    # Create InputOutputMap
    input_output_map = ET.SubElement(engine, "InputOutputMap")

    # Call the function from setup_to_xml.py to create universe elements
    create_universe_elements(input_output_map, universes_json_pth=universes_json_path)

    # Create Fixtures
    create_fixture_elements(engine, setup_fixtures_dir=setup_fixtures_dir)

    # Make channel groups from fixtures - Do before implanting channel groups
    make_channel_groups_from_fixtures()

    # Create ChannelsGroups from groups.csv
    create_channels_groups(engine)

    # Create Show
    create_shows(engine, shows_dir=shows_dir, base_dir=base_dir)


    # Create VirtualConsole section
    vc = ET.SubElement(root, "VirtualConsole")
    frame = ET.SubElement(vc, "Frame")
    frame.set("Caption", "")

    # Add Appearance with values from config
    appearance = ET.SubElement(frame, "Appearance")
    ET.SubElement(appearance, "FrameStyle").text = "None"
    ET.SubElement(appearance, "ForegroundColor").text = "Default"
    ET.SubElement(appearance, "BackgroundColor").text = str(
        config['base']['VirtualConsole']['Appearance']['BackgroundColor'])
    ET.SubElement(appearance, "BackgroundImage").text = "None"
    ET.SubElement(appearance, "Font").text = "Default"

    # Add Properties from config
    properties = ET.SubElement(vc, "Properties")
    size = ET.SubElement(properties, "Size")
    size.set("Width", str(config['base']['Properties']['Size']['Width']))
    size.set("Height", str(config['base']['Properties']['Size']['Height']))

    # Add GrandMaster properties from config
    grandmaster = ET.SubElement(properties, "GrandMaster")
    grandmaster.set("ChannelMode", config['base']['Properties']['GrandMaster']['ChannelMode'])
    grandmaster.set("ValueMode", config['base']['Properties']['GrandMaster']['ValueMode'])
    grandmaster.set("SliderMode", config['base']['Properties']['GrandMaster']['SliderMode'])

    # Create SimpleDesk section
    simple_desk = ET.SubElement(root, "SimpleDesk")
    ET.SubElement(simple_desk, "Engine")

    # Create the XML tree
    tree = ET.ElementTree(root)

    # Instead of writing directly, we'll use minidom to pretty print
    rough_string = ET.tostring(root, encoding='UTF-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")  # 2 spaces for indentation

    # Write to file with proper formatting
    with open(workspace_path, "w", encoding='UTF-8') as f:
        # Write the XML declaration and DOCTYPE
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE Workspace>\n')
        # Write the rest of the pretty-printed XML, but skip the first line (xml declaration)
        f.write('\n'.join(pretty_xml.split('\n')[1:]))
