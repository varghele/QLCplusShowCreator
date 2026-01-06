import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import os
from typing import Dict, Optional
from config.models import Configuration, FixtureGroupCapabilities
from utils.to_xml.setup_to_xml import (create_universe_elements, create_fixture_elements,
                                       create_channels_groups)
from utils.to_xml.shows_to_xml import create_shows
from utils.to_xml.preset_scenes_to_xml import generate_all_preset_functions, create_master_presets
from utils.to_xml.virtual_console_to_xml import build_virtual_console
from utils.fixture_utils import load_fixture_definitions_from_qlc, detect_fixture_group_capabilities


def create_qlc_workspace(config: Configuration, vc_options: Optional[Dict[str, bool]] = None):
    """
    Create QLC+ workspace file using Configuration data

    Args:
        config: Configuration object containing fixtures, groups, shows, and universes
        vc_options: Optional dict with Virtual Console generation options:
            - generate_vc: bool - Master toggle for VC generation
            - group_controls: bool - Include fixture group controls (sliders, XY pads)
            - scene_presets: bool - Include color/intensity preset scenes
            - movement_presets: bool - Include movement EFX patterns
            - show_buttons: bool - Include show trigger buttons in SoloFrame
            - speed_dial: bool - Include tap BPM SpeedDial
            - dark_mode: bool - Use dark/black background
    """
    # Set up base dir
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workspace_path = os.path.join(base_dir, 'workspace.qxw')

    # Get set of models we need definitions for
    models_in_config = {(fixture.manufacturer, fixture.model)
                        for group in config.groups.values()
                        for fixture in group.fixtures}

    # Load fixture definitions
    fixture_definitions = load_fixture_definitions_from_qlc(models_in_config)

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
    create_channels_groups(engine, config, fixture_id_map, fixture_definitions)

    # Create Shows using Configuration data and collect show function IDs
    function_id_counter = create_shows(engine, config, fixture_id_map, fixture_definitions)

    # Detect fixture group capabilities for VC generation
    capabilities_map = {}
    for group_name, group in config.groups.items():
        if group.fixtures:
            capabilities_map[group_name] = detect_fixture_group_capabilities(
                group.fixtures, fixture_definitions
            )

    # Collect show function IDs for show buttons
    show_function_ids = {}
    # Find show functions in the engine
    for func in engine.findall("Function"):
        if func.get("Type") == "Show":
            show_function_ids[func.get("Name")] = int(func.get("ID"))

    # Generate preset functions if requested
    preset_function_map = {}
    master_presets = {}
    if vc_options and vc_options.get('generate_vc') and vc_options.get('scene_presets'):
        preset_function_map, function_id_counter = generate_all_preset_functions(
            engine, config, fixture_id_map, fixture_definitions,
            capabilities_map, function_id_counter,
            include_color=True,
            include_intensity=False,  # Intensity controlled via dimmer slider
            include_movement=vc_options.get('movement_presets', True)
        )

        # Generate master presets (scenes and chasers for all fixtures)
        master_presets, function_id_counter = create_master_presets(
            engine, function_id_counter, config, fixture_id_map, fixture_definitions
        )

    # Create VirtualConsole section
    if vc_options and vc_options.get('generate_vc'):
        # Use the new VC builder
        build_virtual_console(
            root, engine, config, fixture_id_map, fixture_definitions,
            capabilities_map, vc_options, show_function_ids, preset_function_map, master_presets
        )
    else:
        # Create minimal VirtualConsole section (backwards compatibility)
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
