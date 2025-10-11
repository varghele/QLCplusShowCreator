import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing
import math


def fade_in(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
            num_bars=1, speed="1", color="#FF0000", fixture_conf=None, fixture_start_id=0, intensity=200, spot=None):
    """
    Creates a fade-in color effect for LED bars with a single step
    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition
        mode_name: Name of the mode to use
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Hex color code (e.g. "#FF0000" for red)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
    """
    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                           ["IntensityMasterDimmer", "IntensityDimmer", "IntensityRed", "IntensityGreen",
                                            "IntensityBlue", "IntensityWhite"])
    if not channels_dict:
        return []

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Convert hex to RGB and scale by intensity
    color = color.lstrip('#')
    r, g, b = tuple(int(int(color[i:i + 2], 16) * intensity / 255) for i in (0, 2, 4))
    # Calculate white value as average of RGB and scale by intensity
    w = int((r + g + b) / 3)

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    # Create single step with full duration fade-in
    total_duration = sum(step_timings)

    step = ET.Element("Step")
    step.set("Number", str(start_step))
    step.set("FadeIn", str(total_duration))
    step.set("Hold", "0")
    step.set("FadeOut", "0")
    step.set("Values", str(total_channels * fixture_num))

    # Build values string for all fixtures
    values = []
    for i in range(fixture_num):
        channel_values = []

        # Set dimmer intensity
        if 'IntensityMasterDimmer' in channels_dict:
            for channel in channels_dict['IntensityMasterDimmer']:
                channel_values.extend([str(channel['channel']), str(intensity)])
        if 'IntensityDimmer' in channels_dict:
            for channel in channels_dict['IntensityDimmer']:
                channel_values.extend([str(channel['channel']), str(intensity)])

        # Add color channels
        if 'IntensityRed' in channels_dict:
            for channel in channels_dict['IntensityRed']:
                channel_values.extend([str(channel['channel']), str(r)])

        if 'IntensityGreen' in channels_dict:
            for channel in channels_dict['IntensityGreen']:
                channel_values.extend([str(channel['channel']), str(g)])

        if 'IntensityBlue' in channels_dict:
            for channel in channels_dict['IntensityBlue']:
                channel_values.extend([str(channel['channel']), str(b)])

        if 'IntensityWhite' in channels_dict:
            for channel in channels_dict['IntensityWhite']:
                channel_values.extend([str(channel['channel']), str(w)])

        values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

    step.text = ":".join(values)
    return [step]

def static_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                num_bars=1, speed="1", color="#FF0000", fixture_conf=None, fixture_start_id=0, intensity=200, spot=None):
    """
    Creates a static color effect for LED bars with a single step - displays a solid color for the duration
    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition
        mode_name: Name of the mode to use
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Hex color code (e.g. "#FF0000" for red)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
    """
    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                           ["IntensityMasterDimmer", "IntensityDimmer", "IntensityRed", "IntensityGreen",
                                            "IntensityBlue", "IntensityWhite"])
    if not channels_dict:
        return []

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Convert hex to RGB and scale by intensity
    color = color.lstrip('#')
    r, g, b = tuple(int(int(color[i:i + 2], 16) * intensity / 255) for i in (0, 2, 4))
    # Calculate white value as average of RGB and scale by intensity
    w = int((r + g + b) / 3)

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    # Create single step with no fade - instant on and hold for full duration
    total_duration = sum(step_timings)

    step = ET.Element("Step")
    step.set("Number", str(start_step))
    step.set("FadeIn", "0")  # Instant on
    step.set("Hold", str(total_duration))  # Hold for full duration
    step.set("FadeOut", "0")
    step.set("Values", str(total_channels * fixture_num))

    # Build values string for all fixtures
    values = []
    for i in range(fixture_num):
        channel_values = []

        # Set dimmer intensity
        if 'IntensityMasterDimmer' in channels_dict:
            for channel in channels_dict['IntensityMasterDimmer']:
                channel_values.extend([str(channel['channel']), str(intensity)])
        if 'IntensityDimmer' in channels_dict:
            for channel in channels_dict['IntensityDimmer']:
                channel_values.extend([str(channel['channel']), str(intensity)])

        # Add color channels
        if 'IntensityRed' in channels_dict:
            for channel in channels_dict['IntensityRed']:
                channel_values.extend([str(channel['channel']), str(r)])

        if 'IntensityGreen' in channels_dict:
            for channel in channels_dict['IntensityGreen']:
                channel_values.extend([str(channel['channel']), str(g)])

        if 'IntensityBlue' in channels_dict:
            for channel in channels_dict['IntensityBlue']:
                channel_values.extend([str(channel['channel']), str(b)])

        if 'IntensityWhite' in channels_dict:
            for channel in channels_dict['IntensityWhite']:
                channel_values.extend([str(channel['channel']), str(w)])

        values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

    step.text = ":".join(values)
    return [step]

