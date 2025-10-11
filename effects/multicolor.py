import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing
import math
import random


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


def starfall(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
             num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200,
             star_color="#FFFFFF", trail_length=5, star_density=0.5, star_speed_variation=0.3):
    """
    Creates a falling stars effect for LED bar fixtures where each fixture has asynchronous meteor-like patterns

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
        color: Background color (will be very dim)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        star_color: Color of falling stars (default white)
        trail_length: Length of star trails (1-10)
        star_density: Probability of a new star appearing (0.1-1.0)
        star_speed_variation: Variation in star speeds (0.1-0.5)
    """
    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    # Get RGB channels for the LED bars
    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                             ["IntensityMasterDimmer", "IntensityRed", "IntensityGreen",
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

    # Calculate base animation speed from BPM
    avg_bpm = (start_bpm + end_bpm) / 2
    base_speed = avg_bpm / 60.0 * speed_multiplier  # Frames per second

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    # Limit the number of animation frames to a reasonable value
    animation_frames = min(24, max(12, int(total_steps)))
    step_duration = sum(step_timings) / animation_frames

    # Define RGB values for star color
    if star_color.startswith('#'):
        star_color = star_color[1:]
    try:
        star_r = int(star_color[0:2], 16)
        star_g = int(star_color[2:4], 16)
        star_b = int(star_color[4:6], 16)
    except (ValueError, IndexError):
        # Default to white if invalid color
        star_r, star_g, star_b = 255, 255, 255

    # Define RGB values for background (very dim)
    bg_r, bg_g, bg_b = 0, 0, 0
    if color:
        if color.startswith('#'):
            color = color[1:]
        try:
            bg_r = int(int(color[0:2], 16) * 0.05)  # Very dim background
            bg_g = int(int(color[2:4], 16) * 0.05)
            bg_b = int(int(color[4:6], 16) * 0.05)
        except (ValueError, IndexError):
            pass

    # Normalize trail_length
    trail_length = max(1, min(10, trail_length))

    # Generate random starting phases for each fixture to ensure they're out of sync
    fixture_phases = [random.uniform(0, 2 * math.pi) for _ in range(fixture_num)]

    # Generate random speed variations for each fixture
    fixture_speeds = [
        1.0 + random.uniform(-star_speed_variation, star_speed_variation)
        for _ in range(fixture_num)
    ]

    # Create animation frames
    steps = []
    for frame in range(animation_frames):
        step = ET.Element("Step")
        step.set("Number", str(start_step + frame))
        step.set("FadeIn", str(step_duration * 0.5))  # Half step time for fade
        step.set("Hold", str(step_duration * 0.5))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Build values string for all fixtures
        values = []

        # Animation time (normalized from 0 to 1 over the course of all frames)
        normalized_time = frame / animation_frames

        for i in range(fixture_num):
            channel_values = []

            # Get unique phase and speed for this fixture
            fixture_phase = fixture_phases[i]
            fixture_speed = fixture_speeds[i]

            # Calculate progressing time for this fixture
            fixture_time = (normalized_time * base_speed * fixture_speed + fixture_phase) % 1.0

            # Set dimmer intensity if available
            if 'IntensityMasterDimmer' in channels_dict:
                for channel in channels_dict['IntensityMasterDimmer']:
                    channel_values.extend([str(channel['channel']), str(intensity)])

            # Determine if we have pixel-by-pixel control or just fixture-wide color
            rgb_channel_count = 0
            if 'IntensityRed' in channels_dict:
                rgb_channel_count = len(channels_dict['IntensityRed'])

            # For pixel-by-pixel fixtures (like LED bars)
            if rgb_channel_count > 1:
                # Get number of pixels in the fixture
                num_pixels = rgb_channel_count

                # Initialize all pixels to background color
                pixel_colors = [(bg_r, bg_g, bg_b) for _ in range(num_pixels)]

                # Create falling stars based on time
                for pixel_offset in range(num_pixels):
                    # Each pixel has its own phase offset
                    pixel_phase = (pixel_offset * 0.1 + fixture_time) % 1.0

                    # Check if this is where a star should appear
                    # We use phase, fixture number, and frame to create variability
                    star_seed = (i * 1000 + pixel_offset * 100 + frame) % 1000
                    random.seed(star_seed)
                    star_active = random.random() < star_density / num_pixels

                    if star_active:
                        # Create a star at this pixel
                        starting_pixel = pixel_offset

                        # Calculate position based on time
                        position_offset = int(fixture_time * num_pixels * 2) % (num_pixels * 2)

                        # Trail pixels
                        for trail in range(trail_length):
                            # Calculate pixel position with trail
                            pixel_pos = starting_pixel + position_offset - trail

                            # Wrap around if needed
                            while pixel_pos >= num_pixels:
                                pixel_pos -= num_pixels

                            if 0 <= pixel_pos < num_pixels:
                                # Calculate trail intensity (fading toward the end)
                                trail_intensity = 1.0 - (trail / trail_length)

                                # Set pixel color with trail intensity
                                pixel_colors[pixel_pos] = (
                                    int(star_r * trail_intensity),
                                    int(star_g * trail_intensity),
                                    int(star_b * trail_intensity)
                                )

                # Set RGB values for each pixel
                for pixel in range(num_pixels):
                    r, g, b = pixel_colors[pixel]

                    # Scale by intensity parameter
                    r = int(r * intensity / 255)
                    g = int(g * intensity / 255)
                    b = int(b * intensity / 255)

                    # Add RGB values for this pixel
                    if 'IntensityRed' in channels_dict and pixel < len(channels_dict['IntensityRed']):
                        channel_values.extend([str(channels_dict['IntensityRed'][pixel]['channel']), str(r)])

                    if 'IntensityGreen' in channels_dict and pixel < len(channels_dict['IntensityGreen']):
                        channel_values.extend([str(channels_dict['IntensityGreen'][pixel]['channel']), str(g)])

                    if 'IntensityBlue' in channels_dict and pixel < len(channels_dict['IntensityBlue']):
                        channel_values.extend([str(channels_dict['IntensityBlue'][pixel]['channel']), str(b)])

                    if 'IntensityWhite' in channels_dict and pixel < len(channels_dict['IntensityWhite']):
                        w = int((r + g + b) / 3)  # White as average of RGB
                        channel_values.extend([str(channels_dict['IntensityWhite'][pixel]['channel']), str(w)])

            else:
                # For fixtures without pixel-by-pixel control, create whole-fixture animation
                # Calculate a sin wave based on time to simulate a star passing through
                wave_position = math.sin(2 * math.pi * fixture_time + fixture_phase)
                star_visibility = max(0, min(1, 1.0 - abs(wave_position)))

                # Determine colors based on star visibility
                r = int(bg_r + (star_r - bg_r) * star_visibility)
                g = int(bg_g + (star_g - bg_g) * star_visibility)
                b = int(bg_b + (star_b - bg_b) * star_visibility)

                # Scale by intensity parameter
                r = int(r * intensity / 255)
                g = int(g * intensity / 255)
                b = int(b * intensity / 255)

                # Set RGB values for the fixture
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
                        w = int((r + g + b) / 3)  # White as average of RGB
                        channel_values.extend([str(channel['channel']), str(w)])

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)

    return steps

