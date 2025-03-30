from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing


def static(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
           num_bars=1, speed="1", color=None, intensity=200, fixture_conf=None, fixture_start_id=0, spot=None):
    """
    Creates a static effect for fixtures with intensity channels
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
        color: Color value (not used for static effect)
        intensity: Maximum intensity value for channels (0-255)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        spot: Spot object (unused in this effect)
    Returns:
        list: List of XML Step elements
    """
    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
    if not channels_dict:
        return []

    # Get step timings and count
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Create single step with full duration
    total_duration = sum(step_timings)

    step = ET.Element("Step")
    step.set("Number", str(start_step))
    step.set("FadeIn", "0")
    step.set("Hold", str(int(total_duration)))
    step.set("FadeOut", "0")
    step.set("Values", str(total_channels * fixture_num))

    # Build values string for all fixtures at specified intensity
    values = []
    for i in range(fixture_num):
        channel_values = []
        for channel_info in channels_dict['IntensityDimmer']:
            channel = channel_info['channel']
            channel_values.extend([str(channel), str(intensity)])
        values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

    step.text = ":".join(values)

    return [step]


def strobe(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
           num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None):
    """
    Creates a strobe effect for fixtures with intensity channels
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
        color: Color value (not used for basic strobe)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
    Returns:
        list: List of XML Step elements
    """
    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
    if not channels_dict:
        return []

    # Get step timings and count - double the duration since each ON/OFF pair needs one full step
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

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Each timing needs to be split between ON and OFF steps
    for step_duration in step_timings:
        # Base timing calculations for ON step
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

        values = []
        for i in range(fixture_num):
            channel_values = []
            for channel_info in channels_dict['IntensityDimmer']:
                channel = channel_info['channel']
                channel_values.extend([str(channel), str(intensity)])
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

        values = []
        for i in range(fixture_num):
            channel_values = []
            for channel_info in channels_dict['IntensityDimmer']:
                channel = channel_info['channel']
                channel_values.extend([str(channel), "0"])
            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

    return steps


def twinkle(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
            num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None):
    """
    Creates a twinkling effect with curved BPM transition
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
        color: Color value (not used for basic twinkle)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
    Returns:
        list: List of XML Step elements
    """
    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
    if not channels_dict:
        return []

    # Get step timings and count
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    steps = []

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    current_step = start_step
    for step_idx, step_duration in enumerate(step_timings):
        # Create step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(int(step_duration)))  # Full step time for fade
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Build values string based on step index
        values = []
        for i in range(fixture_num):
            channel_values = []
            for idx, channel_info in enumerate(channels_dict['IntensityDimmer']):
                channel = channel_info['channel']
                # Scale the intensity values by the intensity parameter
                value = str(int(intensity)) if (idx + step_idx) % 2 == 0 else str(int(intensity * 0.6))
                channel_values.extend([str(channel), value])
            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

    return steps


def ping_pong_smooth(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4",
                    transition="gradual", num_bars=1, speed="1", color=None, fixture_conf=None,
                    fixture_start_id=0, intensity=200, spot=None):
    """
    Creates a smooth ping-pong effect that moves one bar from left to right and back
    using only intensity channels with smooth transitions
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
        color: Color value (not used for basic ping-pong)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
    """
    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
    if not channels_dict:
        return []

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

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
                if 'IntensityDimmer' in channels_dict:
                    for channel in channels_dict['IntensityDimmer']:
                        channel_values.extend([str(channel['channel']), str(intensity)])
            else:
                if 'IntensityDimmer' in channels_dict:
                    for channel in channels_dict['IntensityDimmer']:
                        channel_values.extend([str(channel['channel']), "0"])

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

        # Update current fixture position
        current_fixture = next_fixture

    return steps
