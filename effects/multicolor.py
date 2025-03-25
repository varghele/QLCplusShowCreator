import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing
import math


def rainbow_rgb(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
            num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None):
    """
    Creates a rainbow effect that cycles through RGB colors with smooth transitions
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
        color: Color value (not used for rainbow effect)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
    """
    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                           ["IntensityMasterDimmer","IntensityDimmer", "IntensityRed", "IntensityGreen", "IntensityBlue"])
    if not channels_dict:
        return []

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Define rainbow color sequence and scale by intensity
    rainbow_colors = [
        (int(255 * intensity / 255), 0, 0),    # Red
        (int(255 * intensity / 255), int(127 * intensity / 255), 0),  # Orange
        (int(255 * intensity / 255), int(255 * intensity / 255), 0),  # Yellow
        (0, int(255 * intensity / 255), 0),    # Green
        (0, 0, int(255 * intensity / 255)),    # Blue
        (int(75 * intensity / 255), 0, int(130 * intensity / 255)),   # Indigo
        (int(148 * intensity / 255), 0, int(211 * intensity / 255))   # Violet
    ]

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    steps = []
    current_step = start_step

    for step_idx, step_duration in enumerate(step_timings):
        # Calculate current and next color indices
        color_idx = step_idx % len(rainbow_colors)
        next_color_idx = (color_idx + 1) % len(rainbow_colors)

        # Get current color
        r, g, b = rainbow_colors[color_idx]
        next_r, next_g, next_b = rainbow_colors[next_color_idx]

        # Create step with full duration fade
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))  # Use full duration for fade
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Build values string for next color (target of fade)
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

            if 'IntensityRed' in channels_dict:
                for channel in channels_dict['IntensityRed']:
                    channel_values.extend([str(channel['channel']), str(next_r)])

            if 'IntensityGreen' in channels_dict:
                for channel in channels_dict['IntensityGreen']:
                    channel_values.extend([str(channel['channel']), str(next_g)])

            if 'IntensityBlue' in channels_dict:
                for channel in channels_dict['IntensityBlue']:
                    channel_values.extend([str(channel['channel']), str(next_b)])

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

    return steps


def rainbow_rgbw(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                num_bars=1, speed="1", color="None", fixture_conf=None, fixture_start_id=0, intensity=200, spot=None):
    """
    Creates a rainbow effect that cycles through RGBW colors with smooth transitions
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
        color: Color value (not used for rainbow effect)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
    """
    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                           ["IntensityMasterDimmer", "IntensityDimmer", "IntensityRed", "IntensityGreen", "IntensityBlue", "IntensityWhite"])
    if not channels_dict:
        return []

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Define rainbow color sequence with RGBW values (R, G, B, W) and scale by intensity
    rainbow_colors = [
        (int(255 * intensity / 255), 0, 0, 0),      # Red
        (int(255 * intensity / 255), int(127 * intensity / 255), 0, 0),    # Orange
        (int(255 * intensity / 255), int(255 * intensity / 255), 0, 0),    # Yellow
        (0, int(255 * intensity / 255), 0, 0),      # Green
        (0, int(255 * intensity / 255), int(255 * intensity / 255), 0),    # Cyan
        (0, 0, int(255 * intensity / 255), 0),      # Blue
        (int(75 * intensity / 255), 0, int(130 * intensity / 255), 0),     # Indigo
        (int(148 * intensity / 255), 0, int(211 * intensity / 255), 0),    # Violet
        (int(255 * intensity / 255), int(255 * intensity / 255), int(255 * intensity / 255), int(255 * intensity / 255))  # White
    ]

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    steps = []
    current_step = start_step

    for step_idx, step_duration in enumerate(step_timings):
        # Calculate current and next color indices
        color_idx = step_idx % len(rainbow_colors)
        next_color_idx = (color_idx + 1) % len(rainbow_colors)

        # Get current and next colors
        r, g, b, w = rainbow_colors[next_color_idx]

        # Create step with full duration fade
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))  # Use full duration for fade
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Build values string for next color (target of fade)
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
        steps.append(step)
        current_step += 1

    return steps


def plasma(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
           num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None):
    """
    Creates a plasma effect with smooth color transitions for LED bars
    with frequency and phase shift coupled to speed and BPM
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
        color: Color value (not used for plasma effect)
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

    # Convert speed to multiplier
    speed_multiplier = float(eval(speed))

    # Calculate base frequency from BPM
    avg_bpm = (start_bpm + end_bpm) / 2
    base_frequency = avg_bpm / 60.0  # Convert BPM to Hz

    # Adjust frequency based on speed multiplier
    frequency = base_frequency * speed_multiplier * 0.99  # Scale factor to make effect more visible

    # Calculate phase shift based on BPM and fixture count
    phase_shift = (2 * math.pi) / (fixture_num * max(1, base_frequency / 4))

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    steps = []
    current_step = start_step

    for step_idx, step_duration in enumerate(step_timings):
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))
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

            # Calculate plasma values using sine waves with BPM-based timing
            time = step_idx / frequency
            space = i * phase_shift

            # Create smooth color transitions using sine waves with different phases
            # Scale the color values by intensity
            r = int((127.5 + 127.5 * math.sin(time + space)) * intensity / 255)
            g = int((127.5 + 127.5 * math.sin(time + space + 2 * math.pi / 3)) * intensity / 255)
            b = int((127.5 + 127.5 * math.sin(time + space + 4 * math.pi / 3)) * intensity / 255)

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
                    w = int((r + g + b) / 3)  # Calculate white as average of RGB
                    channel_values.extend([str(channel['channel']), str(w)])

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

    return steps
