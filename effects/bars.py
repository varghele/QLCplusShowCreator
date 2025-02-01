import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing
import math


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

def fadein_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                num_bars=1, speed="1", color="#FF0000", fixture_num=1, fixture_start_id=0):
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

    step.text = ":".join(values)
    return [step]


def pulse_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
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


def noise_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
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


def plasma_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                 num_bars=1, speed="1", color=None, fixture_num=1, fixture_start_id=0):
    """
    Creates a plasma effect with smooth color transitions for LED bars
    with frequency and phase shift coupled to speed and BPM
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

            # Calculate plasma values using sine waves with BPM-based timing
            time = step_idx / frequency
            space = i * phase_shift

            # Create smooth color transitions using sine waves with different phases
            r = int(127.5 + 127.5 * math.sin(time + space))
            g = int(127.5 + 127.5 * math.sin(time + space + 2 * math.pi / 3))
            b = int(127.5 + 127.5 * math.sin(time + space + 4 * math.pi / 3))

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
                    white_value = min(255, max(0, int((r + g + b) / 3)))
                    channel_values.extend([str(channel['channel']), str(white_value)])

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

    return steps


def wave_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
               num_bars=1, speed="1", color="#FF0000", wave_length=2.0, fixture_num=1, fixture_start_id=0):
    """
    Creates a wave effect that travels across fixtures with a single color
    Parameters:
        wave_length: Length of the wave relative to fixture count (2.0 means wave spans 2 fixtures)
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
    base_r, base_g, base_b = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    # Calculate wave parameters based on BPM
    avg_bpm = (start_bpm + end_bpm) / 2
    speed_multiplier = float(eval(speed))
    wave_frequency = avg_bpm / 60.0 * speed_multiplier

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
            # Calculate wave position for this fixture
            wave_pos = (step_idx / wave_frequency) - (i / wave_length)
            intensity = 0.5 + 0.5 * math.sin(2 * math.pi * wave_pos)

            # Apply intensity to base color
            r = int(base_r * intensity)
            g = int(base_g * intensity)
            b = int(base_b * intensity)

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

    return steps


def breathing_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                    num_bars=1, speed="1", color="#FF0000", inhale_ratio=0.4, fixture_num=1, fixture_start_id=0):
    """
    Creates a breathing effect that mimics natural breathing pattern
    Parameters:
        inhale_ratio: Ratio of inhale time to total breath cycle (0.4 = 40% inhale, 60% exhale)
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
    base_r, base_g, base_b = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    # Calculate breathing parameters based on BPM
    avg_bpm = (start_bpm + end_bpm) / 2
    speed_multiplier = float(eval(speed))
    breath_frequency = avg_bpm / 60.0 * speed_multiplier

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

        # Calculate breathing phase
        phase = (step_idx / breath_frequency) % 1.0

        # Create asymmetric breathing curve
        if phase < inhale_ratio:
            # Inhale (faster, using sine curve)
            intensity = math.sin((phase / inhale_ratio) * math.pi / 2)
        else:
            # Exhale (slower, using cosine curve)
            exhale_phase = (phase - inhale_ratio) / (1 - inhale_ratio)
            intensity = math.cos(exhale_phase * math.pi / 2)

        # Apply intensity to base color
        r = int(base_r * intensity)
        g = int(base_g * intensity)
        b = int(base_b * intensity)

        # Build values string for all fixtures
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

    return steps


def flicker_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                  num_bars=1, speed="1", color="#FF0000", flicker_intensity=0.3, min_brightness=0.2,
                  fixture_num=1, fixture_start_id=0):
    """
    Creates a flickering effect with random intensity variations
    Parameters:
        flicker_intensity: Amount of random variation (0-1)
        min_brightness: Minimum brightness level (0-1)
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
    base_r, base_g, base_b = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    # Calculate flicker parameters based on BPM
    avg_bpm = (start_bpm + end_bpm) / 2
    speed_multiplier = float(eval(speed))
    flicker_frequency = avg_bpm / 60.0 * speed_multiplier

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

    # Create random noise generator with seed for reproducibility
    rng = np.random.default_rng(42)

    for step_idx, step_duration in enumerate(step_timings):
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Generate random flicker intensity
        flicker = min_brightness + (1 - min_brightness) * (
                1 + flicker_intensity * (2 * rng.random() - 1)
        )

        # Apply flicker to base color
        r = int(base_r * flicker)
        g = int(base_g * flicker)
        b = int(base_b * flicker)

        # Build values string for all fixtures
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

    return steps


def heartbeat_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                   num_bars=1, speed="1", color="#FF0000", beat_intensity=0.8, fixture_num=1, fixture_start_id=0):
    """
    Creates a heartbeat effect with a characteristic double-beat pattern
    Parameters:
        beat_intensity: Maximum intensity of the heartbeat (0-1)
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
    base_r, base_g, base_b = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    # Calculate heartbeat parameters based on BPM
    avg_bpm = (start_bpm + end_bpm) / 2
    speed_multiplier = float(eval(speed))
    heart_frequency = avg_bpm / 60.0 * speed_multiplier

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
        # First beat (stronger)
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(int(step_duration * 0.1)))  # Quick rise
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Calculate heartbeat phase
        phase = (step_idx / heart_frequency) % 1.0

        # Create double-beat pattern
        if phase < 0.15:
            intensity = beat_intensity
        elif phase < 0.25:
            intensity = beat_intensity * 0.3
        elif phase < 0.35:
            intensity = beat_intensity * 0.7
        else:
            intensity = beat_intensity * 0.2

        # Apply intensity to base color
        r = int(base_r * intensity)
        g = int(base_g * intensity)
        b = int(base_b * intensity)

        # Build values string for peak
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

        # Fall step (fade to zero)
        fall_step = ET.Element("Step")
        fall_step.set("Number", str(current_step))
        fall_step.set("FadeIn", str(int(step_duration * 0.9)))  # Slow fall
        fall_step.set("Hold", "0")
        fall_step.set("FadeOut", "0")
        fall_step.set("Values", str(total_channels * fixture_num))

        # Build values string for zero intensity
        values = []
        for i in range(fixture_num):
            channel_values = []
            for channel_type in ['IntensityRed', 'IntensityGreen', 'IntensityBlue', 'IntensityWhite']:
                if channel_type in channels_dict:
                    for channel in channels_dict[channel_type]:
                        channel_values.extend([str(channel['channel']), "0"])
            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        fall_step.text = ":".join(values)
        steps.append(fall_step)
        current_step += 1

    return steps


def strobe_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
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


def random_strobe_color(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                        num_bars=1, speed="1", color="#FF0000", fixture_num=1, fixture_start_id=0):
    """
    Creates a strobe effect where only one random fixture strobes per step
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

    # Create random number generator with seed for reproducibility
    rng = np.random.default_rng(42)

    for step_duration in step_timings:
        # Base timing calculations
        fade_in = min(50, int(step_duration * 0.1))
        hold = min(50, int(step_duration * 0.4))
        fade_out = 0
        remaining_time = step_duration - fade_in - hold

        # Select random fixture for this step
        active_fixture = rng.integers(0, fixture_num)

        # ON step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(fade_in))
        step.set("Hold", str(hold))
        step.set("FadeOut", str(fade_out))
        step.set("Values", str(total_channels * fixture_num))

        # Build values string with only random fixture active
        values = []
        for i in range(fixture_num):
            channel_values = []

            if i == active_fixture:
                # Active fixture gets the color
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
                # Other fixtures stay off
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

        # Build values string for OFF state (all fixtures off)
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


def ping_pong_smooth(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                     num_bars=1, speed="1", color="#FF0000", fixture_num=1, fixture_start_id=0):
    """
    Creates a smooth ping-pong effect that moves one bar from left to right and back
    with smooth transitions using fade-in
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
        # Create step with full duration fade
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))  # Use full duration for fade
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Calculate next fixture position
        next_fixture = current_fixture + direction
        if next_fixture >= fixture_num:
            next_fixture = fixture_num - 2  # Start moving back
            direction = -1
        elif next_fixture < 0:
            next_fixture = 1  # Start moving forward
            direction = 1

        # Build values string for next position (target of fade)
        values = []
        for i in range(fixture_num):
            channel_values = []

            if i == next_fixture:
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

        # Update current fixture position
        current_fixture = next_fixture

    return steps


def rainbow_rgb(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
            num_bars=1, speed="1", color=None, fixture_num=1, fixture_start_id=0):
    """
    Creates a rainbow effect that cycles through RGB colors with smooth transitions
    """
    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                             ["IntensityRed", "IntensityGreen", "IntensityBlue"])
    if not channels_dict:
        return []

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Define rainbow color sequence
    rainbow_colors = [
        (255, 0, 0),  # Red
        (255, 127, 0),  # Orange
        (255, 255, 0),  # Yellow
        (0, 255, 0),  # Green
        (0, 0, 255),  # Blue
        (75, 0, 130),  # Indigo
        (148, 0, 211)  # Violet
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
                 num_bars=1, speed="1", color="None", fixture_num=1, fixture_start_id=0):
    """
    Creates a rainbow effect that cycles through RGBW colors with smooth transitions
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

    # Define rainbow color sequence with RGBW values (R, G, B, W)
    rainbow_colors = [
        (255, 0, 0, 0),  # Red
        (255, 127, 0, 0),  # Orange
        (255, 255, 0, 0),  # Yellow
        (0, 255, 0, 0),  # Green
        (0, 255, 255, 0),  # Cyan
        (0, 0, 255, 0),  # Blue
        (75, 0, 130, 0),  # Indigo
        (148, 0, 211, 0),  # Violet
        (255, 255, 255, 255)  # White
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


