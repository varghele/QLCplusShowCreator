import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing
import math


def fadein_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                num_bars=1, speed="1", color="#FF0000", fixture_num=1, fixture_start_id=0):
    """
    Creates a fade-in color effect for LED bars with a single step
    """
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

    # Convert hex to RGB
    color = color.lstrip('#')
    r, g, b = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

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

        # Set dimmer intensity to full
        if 'IntensityMasterDimmer' in channels_dict:
            for channel in channels_dict['IntensityMasterDimmer']:
                channel_values.extend([str(channel['channel']), "255"])
        if 'IntensityDimmer' in channels_dict:
            for channel in channels_dict['IntensityDimmer']:
                channel_values.extend([str(channel['channel']), "255"])

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
            # Calculate white value as average of RGB
            white_value = min(255, max(0, int((r + g + b) / 3)))
            for channel in channels_dict['IntensityWhite']:
                channel_values.extend([str(channel['channel']), str(white_value)])

        values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

    step.text = ":".join(values)
    return [step]