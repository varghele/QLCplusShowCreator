import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
#import json
import os
from config.models import Configuration
from utils.to_xml.setup_to_xml import (create_universe_elements, create_fixture_elements,
                                       create_channels_groups)
from utils.to_xml.shows_to_xml import create_shows
#from utils.make.make_channel_groups import make_channel_groups_from_fixtures
from utils.fixture_utils import load_fixture_definitions

def create_qlc_workspace(config: Configuration):
    """
    Create QLC+ workspace file using Configuration data

    Args:
        config: Configuration object containing fixtures, groups, shows, and universes
    """
    # Set up base dir
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workspace_path = os.path.join(base_dir, 'workspace.qxw')

    # Get set of models we need definitions for
    models_in_config = {(fixture.manufacturer, fixture.model)
                        for group in config.groups.values()
                        for fixture in group.fixtures}

    # Load fixture definitions
    fixture_definitions = load_fixture_definitions(models_in_config)

    # Create the root element with namespace
    root = ET.Element("Workspace")
    root.set("xmlns", "http://www.qlcplus.org/Workspace")
    root.set("CurrentWindow", "VirtualConsole")

    # Create Creator section
    creator = ET.SubElement(root, "Creator")
    ET.SubElement(creator, "Name").text = "Q Light Controller Plus"
    ET.SubElement(creator, "Version").text = "4.12.4"
    ET.SubElement(creator, "Author").text = "Auto Generated"

    # Create Engine section
    engine = ET.SubElement(root, "Engine")

    # Create InputOutputMap and add universes
    input_output_map = ET.SubElement(engine, "InputOutputMap")
    create_universe_elements(input_output_map, config)

    # Create Fixtures and get fixture ID mapping
    fixture_id_map = create_fixture_elements(engine, config)

    # Create ChannelsGroups using Configuration data and fixture ID mapping
    create_channels_groups(engine, config, fixture_id_map)

    # Create Shows using Configuration data
    create_shows(engine, config, fixture_id_map, fixture_definitions)


    # Create VirtualConsole section
    vc = ET.SubElement(root, "VirtualConsole")
    frame = ET.SubElement(vc, "Frame")
    frame.set("Caption", "")

    # Add Appearance
    appearance = ET.SubElement(frame, "Appearance")
    ET.SubElement(appearance, "FrameStyle").text = "None"
    ET.SubElement(appearance, "ForegroundColor").text = "Default"
    ET.SubElement(appearance, "BackgroundColor").text = "Default"
    ET.SubElement(appearance, "BackgroundImage").text = "None"
    ET.SubElement(appearance, "Font").text = "Default"

    # Add Properties
    properties = ET.SubElement(vc, "Properties")
    size = ET.SubElement(properties, "Size")
    size.set("Width", "1920")
    size.set("Height", "1080")

    # Add GrandMaster properties
    grandmaster = ET.SubElement(properties, "GrandMaster")
    grandmaster.set("ChannelMode", "Intensity")
    grandmaster.set("ValueMode", "Reduce")
    grandmaster.set("SliderMode", "Normal")

    # Create SimpleDesk section
    simple_desk = ET.SubElement(engine, "SimpleDesk")
    ET.SubElement(simple_desk, "Engine")

    # Create the XML tree
    tree = ET.ElementTree(root)

    # Pretty print the XML
    rough_string = ET.tostring(root, encoding='UTF-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    # Write to file with proper formatting
    with open(workspace_path, "w", encoding='UTF-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE Workspace>\n')
        f.write('\n'.join(pretty_xml.split('\n')[1:]))
