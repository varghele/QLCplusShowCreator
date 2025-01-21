import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing


def color_noise(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                num_bars=1, speed="1", color="#FF0000", noise_intensity=0.1, fixture_num=1, fixture_start_id=0):
    """
    Creates a color effect with Gaussian noise around a base color for LED bars
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
        noise_intensity: Standard deviation for Gaussian noise (0-1)
        fixture_num: Number of fixtures of this type
        fixture_start_id: starting ID for the fixture to properly assign values
    Returns:
        list: List of XML Step elements
    """
    # Get RGBW channels
    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                             ["IntensityRed", "IntensityGreen", "IntensityBlue", "IntensityWhite"])
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

    steps = []
    current_step = start_step

    for step_duration in step_timings:
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(int(step_duration)))
        step.set("Hold", "0")
        step.set("FadeOut", "0")

        # Build values string for all fixtures
        values = []
        for i in range(fixture_num):
            channel_values = []

            # Add noise to RGB values
            noisy_r = min(255, max(0, int(r + np.random.normal(0, noise_intensity * 255))))
            noisy_g = min(255, max(0, int(g + np.random.normal(0, noise_intensity * 255))))
            noisy_b = min(255, max(0, int(b + np.random.normal(0, noise_intensity * 255))))

            # Add channels in order: R, G, B, W
            if 'IntensityRed' in channels_dict:
                for channel in channels_dict['IntensityRed']:
                    channel_values.extend([str(channel['channel']), str(noisy_r)])

            if 'IntensityGreen' in channels_dict:
                for channel in channels_dict['IntensityGreen']:
                    channel_values.extend([str(channel['channel']), str(noisy_g)])

            if 'IntensityBlue' in channels_dict:
                for channel in channels_dict['IntensityBlue']:
                    channel_values.extend([str(channel['channel']), str(noisy_b)])

            if 'IntensityWhite' in channels_dict:
                for channel in channels_dict['IntensityWhite']:
                    # Calculate white value as average of RGB
                    white_value = min(255, max(0, int((noisy_r + noisy_g + noisy_b) / 3)))
                    channel_values.extend([str(channel['channel']), str(white_value)])

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        #step.set("Values", ":".join(values))
        step.set("Values", str(total_channels * fixture_num))
        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

    return steps
