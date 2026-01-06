# utils/to_xml/virtual_console_to_xml.py
# Generates Virtual Console XML for QLC+ workspace

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Any, Optional
from config.models import Configuration, FixtureGroup, FixtureGroupCapabilities
from utils.effects_utils import get_channels_by_property
from utils.sublane_presets import COLOUR_PRESETS, DIMMER_PRESETS, MOVEMENT_PRESETS, SPECIAL_PRESETS
from utils.orientation import calculate_pan_tilt, pan_tilt_to_dmx
from utils.to_xml.preset_scenes_to_xml import MOVEMENT_PRESETS_POS


# Constants
VC_BLACK_BACKGROUND = "4278190080"  # ARGB 0xFF000000
VC_WHITE_FOREGROUND = "4294967295"  # ARGB 0xFFFFFFFF
VC_BLACK_FOREGROUND = "4278190080"  # ARGB 0xFF000000 (black text for colored buttons)
VC_DARK_GREY_BACKGROUND = "4282664004"  # ARGB 0xFF404044 (dark grey for sliders)
VC_INVALID_FUNCTION = "4294967295"  # ID for no function

# Layout constants
SLIDER_WIDTH = 60
SLIDER_HEIGHT = 200
XYPAD_SIZE = 200
BUTTON_SIZE = 75
BUTTON_SPACING = 10
GROUP_PADDING = 20
SECTION_SPACING = 30
FRAME_HEADER_HEIGHT = 30
SPEED_DIAL_WIDTH = 200
SPEED_DIAL_HEIGHT = 175


def create_appearance(
    parent: ET.Element,
    frame_style: str = "None",
    fg_color: str = "Default",
    bg_color: str = "Default",
    bg_image: str = "None",
    font: str = "Default"
) -> ET.Element:
    """Create standard Appearance element for VC widgets."""
    appearance = ET.SubElement(parent, "Appearance")
    ET.SubElement(appearance, "FrameStyle").text = frame_style
    ET.SubElement(appearance, "ForegroundColor").text = fg_color
    ET.SubElement(appearance, "BackgroundColor").text = bg_color
    ET.SubElement(appearance, "BackgroundImage").text = bg_image
    ET.SubElement(appearance, "Font").text = font
    return appearance


def create_window_state(
    parent: ET.Element,
    visible: bool = True,
    x: int = 0,
    y: int = 0,
    width: int = 100,
    height: int = 100
) -> ET.Element:
    """Create WindowState element for positioning."""
    window_state = ET.SubElement(parent, "WindowState")
    window_state.set("Visible", "True" if visible else "False")
    window_state.set("X", str(x))
    window_state.set("Y", str(y))
    window_state.set("Width", str(width))
    window_state.set("Height", str(height))
    return window_state


def create_vc_button(
    parent: ET.Element,
    widget_id: int,
    caption: str,
    function_id: int,
    x: int,
    y: int,
    width: int = BUTTON_SIZE,
    height: int = BUTTON_SIZE,
    action: str = "Toggle",
    bg_color: str = "Default",
    fg_color: str = "Default",
    font: str = "Default"
) -> ET.Element:
    """Create a Virtual Console Button widget."""
    button = ET.SubElement(parent, "Button")
    button.set("Caption", caption)
    button.set("ID", str(widget_id))
    button.set("Icon", "")

    create_window_state(button, True, x, y, width, height)
    create_appearance(button, "None", fg_color, bg_color, "None", font)

    func = ET.SubElement(button, "Function")
    func.set("ID", str(function_id))

    ET.SubElement(button, "Action").text = action

    intensity = ET.SubElement(button, "Intensity")
    intensity.set("Adjust", "False")
    intensity.text = "100"

    return button


def create_vc_slider(
    parent: ET.Element,
    widget_id: int,
    caption: str,
    x: int,
    y: int,
    width: int = SLIDER_WIDTH,
    height: int = SLIDER_HEIGHT,
    slider_mode: str = "Level",
    channels: List[Tuple[int, int]] = None,  # [(fixture_id, channel_num), ...]
    playback_function_id: int = None,
    bg_color: str = "Default"
) -> ET.Element:
    """Create a Virtual Console Slider widget."""
    slider = ET.SubElement(parent, "Slider")
    slider.set("Caption", caption)
    slider.set("ID", str(widget_id))
    slider.set("WidgetStyle", "Slider")
    slider.set("InvertedAppearance", "false")
    slider.set("CatchValues", "true")

    create_window_state(slider, True, x, y, width, height)
    create_appearance(slider, "Sunken", "Default", bg_color)

    mode = ET.SubElement(slider, "SliderMode")
    mode.set("ValueDisplayStyle", "Exact")
    mode.set("ClickAndGoType", "None")
    mode.set("Monitor", "false")
    mode.text = slider_mode

    if slider_mode == "Level" and channels:
        level = ET.SubElement(slider, "Level")
        level.set("LowLimit", "0")
        level.set("HighLimit", "255")
        level.set("Value", "0")

        for fixture_id, channel in channels:
            ch = ET.SubElement(level, "Channel")
            ch.set("Fixture", str(fixture_id))
            ch.text = str(channel)

    playback = ET.SubElement(slider, "Playback")
    func = ET.SubElement(playback, "Function")
    if playback_function_id is not None:
        func.text = str(playback_function_id)
    else:
        func.text = VC_INVALID_FUNCTION

    return slider


def create_vc_xypad(
    parent: ET.Element,
    widget_id: int,
    caption: str,
    x: int,
    y: int,
    width: int = XYPAD_SIZE,
    height: int = XYPAD_SIZE,
    fixtures: List[Tuple[int, int, int]] = None,  # [(fixture_id, pan_ch, tilt_ch), ...]
    efx_presets: List[Tuple[str, int]] = None,  # [(efx_name, function_id), ...]
    position_presets: List[Tuple[str, int]] = None,  # [(position_name, function_id), ...]
    bg_color: str = "Default",
    fixture_obj: Any = None  # Actual fixture object for calculating positions
) -> ET.Element:
    """Create a Virtual Console XY Pad widget with embedded presets."""
    xypad = ET.SubElement(parent, "XYPad")
    xypad.set("Caption", caption)
    xypad.set("ID", str(widget_id))
    xypad.set("InvertedAppearance", "0")

    create_window_state(xypad, True, x, y, width, height)
    create_appearance(xypad, "Sunken", "Default", bg_color)

    # Add fixtures (using normalized 0-1 range, not channel numbers)
    if fixtures:
        for fixture_id, pan_ch, tilt_ch in fixtures:
            fix = ET.SubElement(xypad, "Fixture")
            fix.set("ID", str(fixture_id))
            fix.set("Head", "0")

            # X-axis (Pan) - normalized 0-1 range
            x_axis = ET.SubElement(fix, "Axis")
            x_axis.set("ID", "X")
            x_axis.set("LowLimit", "0")
            x_axis.set("HighLimit", "1")
            x_axis.set("Reverse", "False")

            # Y-axis (Tilt) - normalized 0-1 range
            y_axis = ET.SubElement(fix, "Axis")
            y_axis.set("ID", "Y")
            y_axis.set("LowLimit", "0")
            y_axis.set("HighLimit", "1")
            y_axis.set("Reverse", "False")

    # Pan and Tilt positions
    pan = ET.SubElement(xypad, "Pan")
    pan.set("Position", "0")

    tilt = ET.SubElement(xypad, "Tilt")
    tilt.set("Position", "0")

    # Add EFX presets
    preset_id_counter = 0
    if efx_presets:
        for efx_name, func_id in efx_presets:
            preset = ET.SubElement(xypad, "Preset")
            preset.set("ID", str(preset_id_counter))

            ET.SubElement(preset, "Type").text = "EFX"
            ET.SubElement(preset, "Name").text = efx_name
            ET.SubElement(preset, "FuncID").text = str(func_id)

            preset_id_counter += 1

    # Add Position presets
    if position_presets and fixture_obj:
        # Calculate actual DMX values for each position preset
        for position_name, func_id in position_presets:
            preset = ET.SubElement(xypad, "Preset")
            preset.set("ID", str(preset_id_counter))

            ET.SubElement(preset, "Type").text = "Position"
            ET.SubElement(preset, "Name").text = position_name

            # Extract the position type from the full name (e.g., "Group - Center" -> "Center")
            pos_type = position_name.split(" - ")[-1] if " - " in position_name else position_name

            # Get target world coordinates from MOVEMENT_PRESETS_POS
            target_pos = MOVEMENT_PRESETS_POS.get(pos_type, {"x": 0.0, "y": 0.0, "z": 2.0})
            target_x = target_pos.get("x", 0.0)
            target_y = target_pos.get("y", 0.0)
            target_z = target_pos.get("z", 2.0)

            # Get fixture position and orientation
            fixture_x = getattr(fixture_obj, 'x', 0.0)
            fixture_y = getattr(fixture_obj, 'y', 0.0)
            fixture_z = getattr(fixture_obj, 'z', 3.0)
            mounting = getattr(fixture_obj, 'mounting', 'hanging')
            yaw = getattr(fixture_obj, 'yaw', 0.0)
            pitch = getattr(fixture_obj, 'pitch', 0.0)
            roll = getattr(fixture_obj, 'roll', 0.0)

            # Calculate pan/tilt angles
            pan_deg, tilt_deg = calculate_pan_tilt(
                fixture_x, fixture_y, fixture_z,
                target_x, target_y, target_z,
                mounting, yaw, pitch, roll
            )

            # Convert to DMX values
            pan_dmx, tilt_dmx = pan_tilt_to_dmx(pan_deg, tilt_deg)

            # Set X and Y as actual DMX values (0-255 range)
            ET.SubElement(preset, "X").text = str(pan_dmx)
            ET.SubElement(preset, "Y").text = str(tilt_dmx)

            preset_id_counter += 1
    elif position_presets:
        # Fallback if no fixture object provided
        for position_name, func_id in position_presets:
            preset = ET.SubElement(xypad, "Preset")
            preset.set("ID", str(preset_id_counter))
            ET.SubElement(preset, "Type").text = "Position"
            ET.SubElement(preset, "Name").text = position_name
            ET.SubElement(preset, "X").text = "127"
            ET.SubElement(preset, "Y").text = "127"
            preset_id_counter += 1

    return xypad


def create_vc_frame(
    parent: ET.Element,
    widget_id: int,
    caption: str,
    x: int,
    y: int,
    width: int,
    height: int,
    collapsed: bool = False,
    bg_color: str = "Default",
    show_header: bool = True,
    fg_color: str = "Default"
) -> ET.Element:
    """Create a Virtual Console Frame container widget."""
    frame = ET.SubElement(parent, "Frame")
    frame.set("Caption", caption)
    frame.set("ID", str(widget_id))

    create_window_state(frame, True, x, y, width, height)
    create_appearance(frame, "Sunken", fg_color, bg_color)

    ET.SubElement(frame, "AllowChildren").text = "True"
    ET.SubElement(frame, "AllowResize").text = "True"
    ET.SubElement(frame, "ShowHeader").text = "True" if show_header else "False"
    ET.SubElement(frame, "ShowEnableButton").text = "True"
    ET.SubElement(frame, "Collapsed").text = "True" if collapsed else "False"
    ET.SubElement(frame, "Disabled").text = "False"

    return frame


def create_vc_solo_frame(
    parent: ET.Element,
    widget_id: int,
    caption: str,
    x: int,
    y: int,
    width: int,
    height: int,
    fg_color: str = "Default"
) -> ET.Element:
    """Create a SoloFrame (only one child button can be active)."""
    frame = ET.SubElement(parent, "SoloFrame")
    frame.set("Caption", caption)
    frame.set("ID", str(widget_id))

    create_window_state(frame, True, x, y, width, height)
    create_appearance(frame, "Sunken", fg_color)

    ET.SubElement(frame, "AllowChildren").text = "True"
    ET.SubElement(frame, "AllowResize").text = "True"
    ET.SubElement(frame, "ShowHeader").text = "True"
    ET.SubElement(frame, "ShowEnableButton").text = "True"
    ET.SubElement(frame, "Mixing").text = "False"
    ET.SubElement(frame, "Collapsed").text = "False"
    ET.SubElement(frame, "Disabled").text = "False"

    return frame


def create_vc_speed_dial(
    parent: ET.Element,
    widget_id: int,
    caption: str,
    x: int,
    y: int,
    width: int = SPEED_DIAL_WIDTH,
    height: int = SPEED_DIAL_HEIGHT,
    functions: List[int] = None,
    bg_color: str = "Default",
    fg_color: str = "Default"
) -> ET.Element:
    """Create a SpeedDial widget for BPM/tempo control."""
    dial = ET.SubElement(parent, "SpeedDial")
    dial.set("Caption", caption)
    dial.set("ID", str(widget_id))

    create_window_state(dial, True, x, y, width, height)
    create_appearance(dial, "Sunken", fg_color, bg_color)

    # Time value (default 500ms = 120 BPM)
    ET.SubElement(dial, "Time").text = "500"

    # Visibility mask (show all elements)
    ET.SubElement(dial, "VisibilityMask").text = "63"

    # Reset factor
    ET.SubElement(dial, "ResetFactorOnDialChange").text = "0"

    # Add functions if provided
    if functions:
        for func_id in functions:
            func = ET.SubElement(dial, "Function")
            func.set("ID", str(func_id))

            fade_in = ET.SubElement(func, "FadeIn")
            fade_in.set("Multiplier", "1")
            fade_in.set("Mode", "Multiplier")

            fade_out = ET.SubElement(func, "FadeOut")
            fade_out.set("Multiplier", "1")
            fade_out.set("Mode", "Multiplier")

            duration = ET.SubElement(func, "Duration")
            duration.set("Multiplier", "1")
            duration.set("Mode", "Multiplier")

    # Absolute value control
    abs_val = ET.SubElement(dial, "AbsoluteValue")
    abs_val.set("Min", "100")
    abs_val.set("Max", "10000")

    # Tap tempo
    ET.SubElement(dial, "Tap")

    return dial


def get_fixture_channels_for_preset(
    fixture,
    fixture_definitions: Dict[str, Any],
    preset_names: List[str]
) -> Tuple[Dict[str, List[int]], int]:
    """Get channels matching specific presets for a fixture.

    Returns:
        Tuple of (channels_dict, total_channels)
        channels_dict maps preset names to lists of channel numbers
    """
    fixture_key = f"{fixture.manufacturer}_{fixture.model}"
    fixture_def = fixture_definitions.get(fixture_key)

    if not fixture_def:
        return {}, 0

    mode = next((m for m in fixture_def.get('modes', [])
                 if m['name'] == fixture.current_mode), None)
    if not mode:
        return {}, 0

    total_channels = len(mode.get('channels', []))
    channels_info = get_channels_by_property(fixture_def, fixture.current_mode, preset_names)

    # Convert to simple dict
    channels_dict = {}
    for preset, channel_list in channels_info.items():
        channels_dict[preset] = [c['channel'] for c in channel_list]

    return channels_dict, total_channels


def get_color_wheel_channel(fixture, fixture_definitions: Dict[str, Any]) -> Optional[int]:
    """Get the color wheel channel number for a fixture, if it has one."""
    fixture_key = f"{fixture.manufacturer}_{fixture.model}"
    fixture_def = fixture_definitions.get(fixture_key)

    if not fixture_def:
        return None

    mode = next((m for m in fixture_def.get('modes', [])
                 if m['name'] == fixture.current_mode), None)
    if not mode:
        return None

    # Find a channel with group="Colour" or group="Color"
    for channel_mapping in mode.get('channels', []):
        channel_number = channel_mapping.get('number')
        channel_name = channel_mapping.get('name')

        # Find the channel definition
        channel_def = next((ch for ch in fixture_def.get('channels', [])
                           if ch.get('name') == channel_name), None)

        if channel_def:
            group = channel_def.get('group', '')
            if group and group.lower() in ['colour', 'color']:
                return channel_number

    return None


def _create_button_frame(
    parent: ET.Element,
    widget_id: int,
    title: str,
    buttons: List[Tuple[str, int, str]],  # [(display_name, func_id, bg_color), ...]
    x: int,
    y: int,
    buttons_per_row: int = 5,
    fg_color: str = "Default"
) -> Tuple[ET.Element, int, int, int]:
    """Create a frame containing preset buttons.

    Returns:
        Tuple of (frame_element, next_widget_id, frame_width, frame_height)
    """
    if not buttons:
        return None, widget_id, 0, 0

    num_buttons = len(buttons)
    num_rows = (num_buttons + buttons_per_row - 1) // buttons_per_row
    buttons_in_widest_row = min(num_buttons, buttons_per_row)

    frame_width = buttons_in_widest_row * (BUTTON_SIZE + 5) + GROUP_PADDING * 2
    frame_height = num_rows * (BUTTON_SIZE + 5) + FRAME_HEADER_HEIGHT + GROUP_PADDING * 2

    frame = create_vc_frame(
        parent, widget_id, title,
        x, y, frame_width, frame_height,
        show_header=True, fg_color=fg_color
    )
    widget_id += 1

    btn_x = GROUP_PADDING
    btn_y = FRAME_HEADER_HEIGHT + GROUP_PADDING
    btn_count = 0

    for display_name, func_id, bg_color in buttons:
        # All buttons use black bold text for better readability
        button_fg_color = VC_BLACK_FOREGROUND
        button_font = "Arial,12,-1,5,75,0,0,0,0,0,Bold"  # Bold font

        create_vc_button(
            frame, widget_id, display_name, func_id,
            btn_x, btn_y, BUTTON_SIZE, BUTTON_SIZE, "Toggle", bg_color, button_fg_color, button_font
        )
        widget_id += 1
        btn_count += 1
        btn_x += BUTTON_SIZE + 5

        if btn_count % buttons_per_row == 0:
            btn_x = GROUP_PADDING
            btn_y += BUTTON_SIZE + 5

    return frame, widget_id, frame_width, frame_height


def generate_group_controls(
    parent: ET.Element,
    group_name: str,
    group: FixtureGroup,
    capabilities: FixtureGroupCapabilities,
    fixture_id_map: Dict[int, int],
    fixture_definitions: Dict[str, Any],
    widget_id_counter: int,
    x_offset: int,
    y_offset: int,
    preset_functions: Dict[str, int] = None,
    dark_mode: bool = False
) -> Tuple[ET.Element, int, int]:
    """Generate all controls for a fixture group based on capabilities.

    Creates sliders, XY pad, and grouped preset button frames.

    Returns:
        Tuple of (frame_element, next_widget_id, total_width_used)
    """
    # Set colors based on dark mode
    slider_bg_color = VC_DARK_GREY_BACKGROUND if dark_mode else "Default"
    frame_fg_color = VC_WHITE_FOREGROUND if dark_mode else "Default"

    # Collect channels for all fixtures in group
    dimmer_channels = []  # [(fixture_id, channel), ...]
    red_channels = []
    green_channels = []
    blue_channels = []
    white_channels = []
    color_wheel_channels = []
    focus_channels = []
    zoom_channels = []
    pan_tilt_fixtures = []  # [(fixture_id, pan_ch, tilt_ch), ...]

    for fixture in group.fixtures:
        fixture_id = fixture_id_map.get(id(fixture))
        if fixture_id is None:
            continue

        all_presets = (
            list(DIMMER_PRESETS) + list(COLOUR_PRESETS) +
            list(MOVEMENT_PRESETS) + list(SPECIAL_PRESETS)
        )
        channels_dict, _ = get_fixture_channels_for_preset(
            fixture, fixture_definitions, all_presets
        )

        # Dimmer
        for ch in channels_dict.get("IntensityMasterDimmer", []):
            dimmer_channels.append((fixture_id, ch))
        for ch in channels_dict.get("IntensityDimmer", []):
            dimmer_channels.append((fixture_id, ch))

        # RGB(W)
        for ch in channels_dict.get("IntensityRed", []):
            red_channels.append((fixture_id, ch))
        for ch in channels_dict.get("IntensityGreen", []):
            green_channels.append((fixture_id, ch))
        for ch in channels_dict.get("IntensityBlue", []):
            blue_channels.append((fixture_id, ch))
        for ch in channels_dict.get("IntensityWhite", []):
            white_channels.append((fixture_id, ch))

        # Color wheel (if no RGB)
        if not red_channels and not green_channels and not blue_channels:
            color_ch = get_color_wheel_channel(fixture, fixture_definitions)
            if color_ch is not None:
                color_wheel_channels.append((fixture_id, color_ch))

        # Special
        for ch in channels_dict.get("BeamFocusNearFar", []):
            focus_channels.append((fixture_id, ch))
        for ch in channels_dict.get("BeamFocusFarNear", []):
            focus_channels.append((fixture_id, ch))
        for ch in channels_dict.get("BeamZoomSmallBig", []):
            zoom_channels.append((fixture_id, ch))
        for ch in channels_dict.get("BeamZoomBigSmall", []):
            zoom_channels.append((fixture_id, ch))

        # Movement (pan/tilt)
        pan_ch = channels_dict.get("PositionPan", [None])[0] if channels_dict.get("PositionPan") else None
        tilt_ch = channels_dict.get("PositionTilt", [None])[0] if channels_dict.get("PositionTilt") else None
        if pan_ch is not None and tilt_ch is not None:
            pan_tilt_fixtures.append((fixture_id, pan_ch, tilt_ch))

    # Determine if we have RGB or color wheel
    has_rgb = bool(red_channels or green_channels or blue_channels)
    has_color_wheel = bool(color_wheel_channels)
    has_xypad = bool(pan_tilt_fixtures)

    # Categorize preset buttons
    color_buttons = []  # [(display_name, func_id, bg_color), ...]
    position_buttons = []
    pattern_buttons = []

    # Color map for button backgrounds
    color_bg_map = {
        "red": "4294901760",      # ARGB red
        "green": "4278255360",    # ARGB green
        "blue": "4278190335",     # ARGB blue
        "white": "4294967295",    # ARGB white
        "amber": "4294945536",    # ARGB amber
        "cyan": "4278255615",     # ARGB cyan
        "magenta": "4294902015",  # ARGB magenta
        "yellow": "4294967040",   # ARGB yellow
        "uv": "4286578816",       # ARGB purple-ish for UV
        "blackout": "4278190080", # ARGB black
    }

    if preset_functions:
        for key, func_id in preset_functions.items():
            display_name = key.split("_", 1)[1] if "_" in key else key

            if key.startswith("Color_"):
                bg_color = color_bg_map.get(display_name.lower(), "Default")
                color_buttons.append((display_name, func_id, bg_color))
            elif key.startswith("Position_"):
                position_buttons.append((display_name, func_id, "Default"))
            elif key.startswith("Pattern_"):
                pattern_buttons.append((display_name, func_id, "Default"))
            # Skip Intensity_ presets

    # Calculate layout dimensions
    num_sliders = 0
    if dimmer_channels:
        num_sliders += 1
    if has_rgb:
        num_sliders += len([c for c in [red_channels, green_channels, blue_channels, white_channels] if c])
    # Remove color wheel slider - use preset buttons instead
    if focus_channels:
        num_sliders += 1
    if zoom_channels:
        num_sliders += 1

    slider_section_width = num_sliders * (SLIDER_WIDTH + 5) if num_sliders > 0 else 0

    # Calculate XY pad height based on position presets
    # Each preset button takes ~25 pixels, base pad needs 200 pixels
    num_position_presets = len(position_buttons)
    PRESET_BUTTON_HEIGHT = 25
    xypad_height = XYPAD_SIZE + (num_position_presets * PRESET_BUTTON_HEIGHT) if has_xypad else XYPAD_SIZE

    # Pattern buttons will be stacked vertically (1 per row) next to XY pad
    pattern_buttons_per_row = 1
    pattern_frame_width = (BUTTON_SIZE + GROUP_PADDING * 2) if pattern_buttons else 0
    pattern_frame_height = len(pattern_buttons) * (BUTTON_SIZE + 5) + FRAME_HEADER_HEIGHT + GROUP_PADDING if pattern_buttons else 0

    # XY pad section includes pattern buttons to its right
    xypad_and_patterns_width = (XYPAD_SIZE + 10 + pattern_frame_width) if has_xypad else pattern_frame_width

    controls_width = slider_section_width + xypad_and_patterns_width

    # Calculate color button frame dimensions (horizontal layout, 5 per row)
    color_buttons_per_row = 5
    color_frame_width = min(len(color_buttons), color_buttons_per_row) * (BUTTON_SIZE + 5) + GROUP_PADDING * 2 if color_buttons else 0
    color_frame_height = ((len(color_buttons) + color_buttons_per_row - 1) // color_buttons_per_row) * (BUTTON_SIZE + 5) + FRAME_HEADER_HEIGHT + GROUP_PADDING if color_buttons else 0

    # Total frame dimensions
    frame_width = max(150, controls_width + GROUP_PADDING * 2, color_frame_width + GROUP_PADDING * 2)

    # Calculate height: controls row + color button frame below
    # Use calculated xypad_height instead of fixed XYPAD_SIZE
    controls_height = max(SLIDER_HEIGHT, xypad_height, pattern_frame_height) if (num_sliders > 0 or has_xypad or pattern_buttons) else 0

    button_frames_total_height = color_frame_height
    if button_frames_total_height > 0:
        button_frames_total_height += 10  # Spacing between controls and button frames

    frame_height = FRAME_HEADER_HEIGHT + GROUP_PADDING + controls_height + button_frames_total_height + GROUP_PADDING

    # Create main frame for this group
    frame = create_vc_frame(
        parent, widget_id_counter, group_name,
        x_offset, y_offset, frame_width, frame_height,
        fg_color=frame_fg_color
    )
    widget_id_counter += 1

    # Current position within frame
    current_x = GROUP_PADDING
    current_y = FRAME_HEADER_HEIGHT + GROUP_PADDING

    # Create sliders
    if dimmer_channels:
        create_vc_slider(
            frame, widget_id_counter, "Dimmer",
            current_x, current_y, SLIDER_WIDTH, SLIDER_HEIGHT,
            "Level", dimmer_channels, None, slider_bg_color
        )
        widget_id_counter += 1
        current_x += SLIDER_WIDTH + 5

    if has_rgb:
        if red_channels:
            create_vc_slider(
                frame, widget_id_counter, "Red",
                current_x, current_y, SLIDER_WIDTH, SLIDER_HEIGHT,
                "Level", red_channels, None, slider_bg_color
            )
            widget_id_counter += 1
            current_x += SLIDER_WIDTH + 5

        if green_channels:
            create_vc_slider(
                frame, widget_id_counter, "Green",
                current_x, current_y, SLIDER_WIDTH, SLIDER_HEIGHT,
                "Level", green_channels, None, slider_bg_color
            )
            widget_id_counter += 1
            current_x += SLIDER_WIDTH + 5

        if blue_channels:
            create_vc_slider(
                frame, widget_id_counter, "Blue",
                current_x, current_y, SLIDER_WIDTH, SLIDER_HEIGHT,
                "Level", blue_channels, None, slider_bg_color
            )
            widget_id_counter += 1
            current_x += SLIDER_WIDTH + 5

        if white_channels:
            create_vc_slider(
                frame, widget_id_counter, "White",
                current_x, current_y, SLIDER_WIDTH, SLIDER_HEIGHT,
                "Level", white_channels, None, slider_bg_color
            )
            widget_id_counter += 1
            current_x += SLIDER_WIDTH + 5
    # Remove color wheel slider - use color preset buttons instead

    if capabilities.has_special:
        if focus_channels:
            create_vc_slider(
                frame, widget_id_counter, "Focus",
                current_x, current_y, SLIDER_WIDTH, SLIDER_HEIGHT,
                "Level", focus_channels, None, slider_bg_color
            )
            widget_id_counter += 1
            current_x += SLIDER_WIDTH + 5

        if zoom_channels:
            create_vc_slider(
                frame, widget_id_counter, "Zoom",
                current_x, current_y, SLIDER_WIDTH, SLIDER_HEIGHT,
                "Level", zoom_channels, None, slider_bg_color
            )
            widget_id_counter += 1
            current_x += SLIDER_WIDTH + 5

    # Create XY Pad for movement (with position presets only)
    if pan_tilt_fixtures:
        # Collect Position presets for the XY Pad (no patterns)
        position_presets = []

        if preset_functions:
            for key, func_id in preset_functions.items():
                if key.startswith("Position_"):
                    # Extract position name and add as position preset
                    position_name = key.split("_", 1)[1]
                    position_presets.append((f"{group_name} - {position_name}", func_id))

        # Get first fixture for position calculations
        first_fixture = group.fixtures[0] if group.fixtures else None

        create_vc_xypad(
            frame, widget_id_counter, "XY Pad",
            current_x, current_y, XYPAD_SIZE, xypad_height,
            pan_tilt_fixtures,
            efx_presets=None,  # No patterns in XY pad
            position_presets=position_presets,
            bg_color=slider_bg_color,
            fixture_obj=first_fixture
        )
        widget_id_counter += 1
        current_x += XYPAD_SIZE + 5

        # Pattern buttons frame - stacked vertically next to XY pad
        if pattern_buttons:
            _, widget_id_counter, _, _ = _create_button_frame(
                frame, widget_id_counter, "Patterns",
                pattern_buttons, current_x, current_y, pattern_buttons_per_row, frame_fg_color
            )

    # Create color button frame below sliders/xypad
    button_frame_y = FRAME_HEADER_HEIGHT + GROUP_PADDING + controls_height + 10

    # Colors frame
    if color_buttons:
        _, widget_id_counter, _, h = _create_button_frame(
            frame, widget_id_counter, "Colors",
            color_buttons, GROUP_PADDING, button_frame_y, color_buttons_per_row, frame_fg_color
        )

    return frame, widget_id_counter, frame_width


def build_virtual_console(
    root: ET.Element,
    engine: ET.Element,
    config: Configuration,
    fixture_id_map: Dict[int, int],
    fixture_definitions: Dict[str, Any],
    capabilities_map: Dict[str, FixtureGroupCapabilities],
    options: Dict[str, bool],
    show_function_ids: Dict[str, int] = None,
    preset_function_map: Dict[str, Dict[str, int]] = None,
    widget_id_start: int = 0
) -> int:
    """Build the complete Virtual Console section.

    Args:
        root: Workspace root element
        engine: Engine element
        config: Configuration object
        fixture_id_map: Fixture ID mapping
        fixture_definitions: Fixture definitions
        capabilities_map: Dict mapping group names to capabilities
        options: Export options dict
        show_function_ids: Dict mapping show names to function IDs
        preset_function_map: Dict of preset function IDs by group
        widget_id_start: Starting widget ID

    Returns:
        Next available widget ID
    """
    widget_id = widget_id_start

    # Create VirtualConsole element
    vc = ET.SubElement(root, "VirtualConsole")

    # Main frame
    main_frame = ET.SubElement(vc, "Frame")
    main_frame.set("Caption", "")

    # Set appearance (dark mode if requested)
    bg_color = VC_BLACK_BACKGROUND if options.get('dark_mode') else "Default"
    fg_color = VC_WHITE_FOREGROUND if options.get('dark_mode') else "Default"
    create_appearance(main_frame, "None", fg_color, bg_color)

    # Constants for Virtual Console usable area (QLC+ has UI elements around edges)
    SCREEN_WIDTH = 1805
    SCREEN_HEIGHT = 995
    MARGIN = 10

    current_y = MARGIN

    # Shows section (SoloFrame at top with margins)
    if options.get('show_buttons') and show_function_ids:
        num_shows = len(show_function_ids)
        # Calculate buttons per row to fit in available width
        available_width = SCREEN_WIDTH - (2 * MARGIN)
        buttons_per_row = max(1, (available_width - GROUP_PADDING * 2) // (BUTTON_SIZE + BUTTON_SPACING))

        num_rows = (num_shows + buttons_per_row - 1) // buttons_per_row
        solo_frame_height = (BUTTON_SIZE + BUTTON_SPACING) * num_rows + FRAME_HEADER_HEIGHT + GROUP_PADDING * 2
        solo_frame_width = available_width

        solo_frame = create_vc_solo_frame(
            main_frame, widget_id, "Shows",
            MARGIN, current_y, solo_frame_width, solo_frame_height,
            fg_color
        )
        widget_id += 1

        # Add buttons for each show
        btn_x = GROUP_PADDING
        btn_y = FRAME_HEADER_HEIGHT + GROUP_PADDING
        btn_count = 0

        for show_name, func_id in show_function_ids.items():
            create_vc_button(
                solo_frame, widget_id, show_name, func_id,
                btn_x, btn_y, BUTTON_SIZE, BUTTON_SIZE, "Toggle", "Default",
                VC_BLACK_FOREGROUND, "Arial,12,-1,5,75,0,0,0,0,0,Bold"
            )
            widget_id += 1
            btn_count += 1
            btn_x += BUTTON_SIZE + BUTTON_SPACING

            if btn_count % buttons_per_row == 0:
                btn_x = GROUP_PADDING
                btn_y += BUTTON_SIZE + BUTTON_SPACING

        current_y += solo_frame_height + SECTION_SPACING

    # Group controls section - grid layout
    if options.get('group_controls'):
        # Collect all groups with their dimensions first
        group_frames = []

        for group_name, group in config.groups.items():
            if not group.fixtures:
                continue

            capabilities = capabilities_map.get(group_name, FixtureGroupCapabilities())

            # Skip groups with no controllable capabilities
            if not any([capabilities.has_dimmer, capabilities.has_colour,
                       capabilities.has_movement, capabilities.has_special]):
                continue

            group_presets = preset_function_map.get(group_name, {}) if preset_function_map else {}

            # Generate at temporary position to get dimensions
            frame, new_widget_id, frame_width = generate_group_controls(
                main_frame, group_name, group, capabilities,
                fixture_id_map, fixture_definitions, widget_id,
                0, 0, group_presets,  # Temporary position
                options.get('dark_mode', False)
            )

            # Get frame height from the WindowState
            frame_height = 0
            for child in frame:
                if child.tag == "WindowState":
                    frame_height = int(child.get("Height", 0))
                    break

            group_frames.append((frame, frame_width, frame_height, new_widget_id))
            widget_id = new_widget_id

        # Arrange groups in grid
        group_x = MARGIN
        group_y = current_y
        row_height = 0
        available_width = SCREEN_WIDTH - (2 * MARGIN)

        for frame, frame_width, frame_height, _ in group_frames:
            # Check if this group fits in current row
            if group_x + frame_width > SCREEN_WIDTH - MARGIN and group_x > MARGIN:
                # Move to next row
                group_x = MARGIN
                group_y += row_height + SECTION_SPACING
                row_height = 0

            # Update frame position
            for child in frame:
                if child.tag == "WindowState":
                    child.set("X", str(group_x))
                    child.set("Y", str(group_y))
                    break

            row_height = max(row_height, frame_height)
            group_x += frame_width + SECTION_SPACING

        current_y = group_y + row_height + SECTION_SPACING

    # Speed Dial (tap BPM) - bottom right
    if options.get('speed_dial'):
        # Collect all show function IDs for the speed dial
        all_show_ids = list(show_function_ids.values()) if show_function_ids else []

        speed_dial_x = SCREEN_WIDTH - SPEED_DIAL_WIDTH - MARGIN
        speed_dial_y = SCREEN_HEIGHT - SPEED_DIAL_HEIGHT - MARGIN

        # Use dark grey background and white text in dark mode
        speed_dial_bg = VC_DARK_GREY_BACKGROUND if options.get('dark_mode') else "Default"
        speed_dial_fg = VC_WHITE_FOREGROUND if options.get('dark_mode') else "Default"

        create_vc_speed_dial(
            main_frame, widget_id, "Tap BPM",
            speed_dial_x, speed_dial_y, SPEED_DIAL_WIDTH, SPEED_DIAL_HEIGHT,
            all_show_ids if all_show_ids else None,
            speed_dial_bg, speed_dial_fg
        )
        widget_id += 1

    # Properties
    properties = ET.SubElement(vc, "Properties")
    size = ET.SubElement(properties, "Size")
    size.set("Width", "1920")
    size.set("Height", "1080")

    grand_master = ET.SubElement(properties, "GrandMaster")
    grand_master.set("ChannelMode", "Intensity")
    grand_master.set("ValueMode", "Reduce")
    grand_master.set("SliderMode", "Normal")

    return widget_id
