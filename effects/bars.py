import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing


def static_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                 num_bars=1, speed="1", color="#FF0000", fixture_num=1, fixture_start_id=0):
    """
    Creates a static color effect for LED bars
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

    # Create single step with full duration
    total_duration = sum(step_timings)

    step = ET.Element("Step")
    step.set("Number", str(current_step))
    step.set("FadeIn", "0")
    step.set("Hold", str(int(total_duration)))
    step.set("FadeOut", "0")

    # Build values string for all fixtures
    values = []
    for i in range(fixture_num):
        channel_values = []

        # Add channels in order: R, G, B, W
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
                # Calculate white value as average of RGB
                white_value = min(255, max(0, int((r + g + b) / 3)))
                channel_values.extend([str(channel['channel']), str(white_value)])

        values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

    step.set("Values", str(total_channels * fixture_num))
    step.text = ":".join(values)
    steps.append(step)

    return steps

def color_pulse(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                num_bars=1, speed="1", color="#FF0000", fixture_num=1, fixture_start_id=0):
    """
    Creates a pulsing color effect that fades in and out for LED bars
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
        fixture_num: Number of fixtures of this type
        fixture_start_id: starting ID for the fixture to properly assign values
    Returns:
        list: List of XML Step elements
    """
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

    # Split each timing into fade in and fade out
    for step_duration in step_timings:
        # Fade in step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(int(step_duration / 2)))  # Half duration for fade in
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Build values string for full intensity
        values = []
        for i in range(fixture_num):
            channel_values = []
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
                    white_value = min(255, max(0, int((r + g + b) / 3)))
                    channel_values.extend([str(channel['channel']), str(white_value)])
            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

        # Fade out step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(int(step_duration / 2)))  # Half duration for fade out
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Build values string for zero intensity
        values = []
        for i in range(fixture_num):
            channel_values = []
            for channel_type in ['IntensityRed', 'IntensityGreen', 'IntensityBlue', 'IntensityWhite']:
                if channel_type in channels_dict:
                    for channel in channels_dict[channel_type]:
                        channel_values.extend([str(channel['channel']), "0"])
            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

    return steps



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


def color_strobe(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                 num_bars=1, speed="1", color="#FF0000", fixture_num=1, fixture_start_id=0):
    """
    Creates a strobe effect with consistent color for LED bars
    """
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
    # Calculate white as average of RGB
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

    steps = []
    current_step = start_step

    for step_duration in step_timings:
        # Base timing calculations
        fade_in = min(50, int(step_duration * 0.1))
        hold = min(50, int(step_duration * 0.4))
        fade_out = 0
        remaining_time = step_duration - fade_in - hold

        # ON step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(fade_in))
        step.set("Hold", str(hold))
        step.set("FadeOut", str(fade_out))
        step.set("Values", str(total_channels * fixture_num))

        # Build values string for ON state with consistent color
        values = []
        for i in range(fixture_num):
            channel_values = []

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

        # OFF step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(int(remaining_time)))
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Build values string for OFF state
        values = []
        for i in range(fixture_num):
            channel_values = []

            for channel_type in ['IntensityRed', 'IntensityGreen', 'IntensityBlue', 'IntensityWhite']:
                if channel_type in channels_dict:
                    for channel in channels_dict[channel_type]:
                        channel_values.extend([str(channel['channel']), "0"])

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

    return steps

def ping_pong(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
              num_bars=1, speed="1", color="#FF0000", fixture_num=1, fixture_start_id=0):
    """
    Creates a ping-pong effect that strobes one bar from left to right and back
    """
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

    steps = []
    current_step = start_step
    current_fixture = 0
    direction = 1  # 1 for forward, -1 for backward

    for step_duration in step_timings:
        # Base timing calculations
        fade_in = min(50, int(step_duration * 0.1))
        hold = min(50, int(step_duration * 0.4))
        fade_out = 0
        remaining_time = step_duration - fade_in - hold

        # ON step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(fade_in))
        step.set("Hold", str(hold))
        step.set("FadeOut", str(fade_out))
        step.set("Values", str(total_channels * fixture_num))

        # Build values string with only current fixture active
        values = []
        for i in range(fixture_num):
            channel_values = []

            if i == current_fixture:
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
            else:
                for channel_type in ['IntensityRed', 'IntensityGreen', 'IntensityBlue', 'IntensityWhite']:
                    if channel_type in channels_dict:
                        for channel in channels_dict[channel_type]:
                            channel_values.extend([str(channel['channel']), "0"])

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

        # OFF step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(int(remaining_time)))
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Build values string for OFF state
        values = []
        for i in range(fixture_num):
            channel_values = []
            for channel_type in ['IntensityRed', 'IntensityGreen', 'IntensityBlue', 'IntensityWhite']:
                if channel_type in channels_dict:
                    for channel in channels_dict[channel_type]:
                        channel_values.extend([str(channel['channel']), "0"])
            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

        # Update current fixture and direction
        current_fixture += direction
        if current_fixture >= fixture_num - 1:
            current_fixture = fixture_num - 1
            direction = -1
        elif current_fixture <= 0:
            current_fixture = 0
            direction = 1

    return steps


