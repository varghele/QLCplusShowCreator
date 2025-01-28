import xml.etree.ElementTree as ET


def create_slider(slider_id, fixture_start, fixture_count, channels_per_fixture, x=0, y=0, width=60, height=200):
    """
    Creates a slider control for a group of fixtures
    Parameters:
        slider_id: ID number for the slider
        fixture_start: Starting fixture number
        fixture_count: Number of fixtures to control
        channels_per_fixture: Number of channels per fixture
        x: X position of slider
        y: Y position of slider
        width: Width of slider
        height: Height of slider
    Returns:
        Element: XML Slider element
    """
    slider = ET.Element("Slider")
    slider.set("Caption", f"Slider {slider_id}")
    slider.set("ID", str(slider_id))
    slider.set("WidgetStyle", "Slider")
    slider.set("InvertedAppearance", "false")
    slider.set("CatchValues", "true")

    # Window state
    window = ET.SubElement(slider, "WindowState")
    window.set("Visible", "True")
    window.set("X", str(x))
    window.set("Y", str(y))
    window.set("Width", str(width))
    window.set("Height", str(height))

    # Appearance
    appearance = ET.SubElement(slider, "Appearance")
    ET.SubElement(appearance, "FrameStyle").text = "Sunken"
    ET.SubElement(appearance, "ForegroundColor").text = "Default"
    ET.SubElement(appearance, "BackgroundColor").text = "Default"
    ET.SubElement(appearance, "BackgroundImage").text = "None"
    ET.SubElement(appearance, "Font").text = "Default"

    # Slider mode
    slider_mode = ET.SubElement(slider, "SliderMode")
    slider_mode.set("ValueDisplayStyle", "Exact")
    slider_mode.set("ClickAndGoType", "None")
    slider_mode.set("Monitor", "false")
    slider_mode.text = "Level"

    # Level settings
    level = ET.SubElement(slider, "Level")
    level.set("LowLimit", "0")
    level.set("HighLimit", "255")
    level.set("Value", "0")

    # Add channels for each fixture
    for fixture_num in range(fixture_start, fixture_start + fixture_count):
        for channel_num in range(channels_per_fixture):
            channel = ET.SubElement(level, "Channel")
            channel.set("Fixture", str(fixture_num))
            channel.text = str(channel_num)

    # Playback
    playback = ET.SubElement(slider, "Playback")
    ET.SubElement(playback, "Function").text = "4294967295"

    return slider


def create_slider_frame(fixture_groups, spacing=70):
    """
    Creates a frame containing multiple sliders for fixture groups
    Parameters:
        fixture_groups: List of tuples (fixture_start, fixture_count, channels_per_fixture)
        spacing: Horizontal spacing between sliders
    Returns:
        Element: XML Frame element containing sliders
    """
    frame = ET.Element("Frame")

    for i, group in enumerate(fixture_groups):
        fixture_start, fixture_count, channels_per_fixture = group
        slider = create_slider(
            slider_id=i,
            fixture_start=fixture_start,
            fixture_count=fixture_count,
            channels_per_fixture=channels_per_fixture,
            x=i * spacing
        )
        frame.append(slider)

    return frame
