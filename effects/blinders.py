from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing


def strobe(start_step, fixture_def, mode_name, start_bpm=120, end_bpm=120, speed="1", color=None, total_beats=4,
           fixture_num=1):
    """
    Creates a strobe effect for fixtures with intensity channels
    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition
        mode_name: Name of the mode to use
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for basic strobe)
        total_beats: Total number of beats to fill
        fixture_num: Number of fixtures of this type
    Returns:
        list: List of XML Step elements
    """
    channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
    if not channels_dict:
        return []

    steps = []

    # Convert speed fraction to float
    if isinstance(speed, str) and '/' in speed:
        num, denom = map(int, speed.split('/'))
        speed_multiplier = num / denom
    else:
        speed_multiplier = float(speed)

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    current_step = start_step
    num_steps = total_beats  # Two steps per beat (ON/OFF)

    for step_idx in range(num_steps):
        # Calculate curved progress and current BPM
        progress = (step_idx / num_steps) ** 0.52  # Adding slight curve to the transition
        current_bpm = start_bpm + (end_bpm - start_bpm) * progress

        # Calculate step timing based on current BPM
        ms_per_beat = 60000 / current_bpm
        ms_per_step = ms_per_beat / speed_multiplier

        # Base timing (in milliseconds)
        fade_in = min(50, int(ms_per_step * 0.1))
        hold = min(50, int(ms_per_step * 0.4))
        fade_out = 0
        remaining_time = ms_per_step - fade_in - hold

        if step_idx % 2 == 0:  # ON step
            step = ET.Element("Step")
            step.set("Number", str(current_step))
            step.set("FadeIn", str(fade_in))
            step.set("Hold", str(hold))
            step.set("FadeOut", str(fade_out))
            step.set("Values", str(total_channels * fixture_num))

            # Build values string for ON state
            values = []
            for i in range(fixture_num):
                channel_values = []
                for channel_info in channels_dict['IntensityDimmer']:
                    channel = channel_info['channel']
                    channel_values.extend([str(channel), "255"])
                values.append(f"{i}:{','.join(channel_values)}")

            step.text = ":".join(values)
            steps.append(step)

        else:  # OFF step
            step = ET.Element("Step")
            step.set("Number", str(current_step))
            step.set("FadeIn", str(int(remaining_time)))
            step.set("Hold", "0")
            step.set("FadeOut", "0")
            step.set("Values", str(total_channels * fixture_num))
            steps.append(step)

        current_step += 1

    return steps


def twinkle(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
            num_bars=1, speed="1", color=None, fixture_num=1):
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
        fixture_num: Number of fixtures of this type
    Returns:
        list: List of XML Step elements
    """
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
                value = "255" if (idx + step_idx) % 2 == 0 else "150"
                channel_values.extend([str(channel), value])
            values.append(f"{i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

    return steps





