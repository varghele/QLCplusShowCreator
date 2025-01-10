from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET


def strobe(start_step, fixture_def, mode_name, bpm=120, speed="1", color=None, total_beats=4, fixture_num=1):
    """
    Creates a strobe effect for fixtures with intensity channels
    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition
        mode_name: Name of the mode to use
        bpm: Beats per minute
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for basic strobe)
        total_beats: Total number of beats to fill
    Returns:
        list: List of XML Step elements
    """
    # Get all intensity channels
    channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])

    # For Sunstrip, we'll have multiple channels with IntensityDimmer preset
    intensity_channels = []
    for preset, channel in channels_dict.items():
        if isinstance(channel, list):
            intensity_channels.extend([c['channel'] for c in channel])
        else:
            intensity_channels.append(channel)

    if not intensity_channels:
        return []

    steps = []

    # Convert speed fraction to float
    if isinstance(speed, str) and '/' in speed:
        num, denom = map(int, speed.split('/'))
        speed_multiplier = num / denom
    else:
        speed_multiplier = float(speed)

    # Calculate timing based on BPM
    ms_per_beat = 60000 / bpm
    ms_per_step = ms_per_beat / speed_multiplier

    # Calculate total time and number of cycles
    total_time = ms_per_beat * total_beats
    cycles = int(total_time / (ms_per_step * 2))

    # Base timing (in milliseconds)
    fade_in = min(50, int(ms_per_step * 0.1))
    hold = min(50, int(ms_per_step * 0.4))
    fade_out = 0
    remaining_time = ms_per_step - fade_in - hold  # Define remaining_time here

    # Count total channels
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Create cycles of ON/OFF steps
    for cycle in range(cycles):
        current_step = start_step + (cycle * 2)

        # Create ON step
        step_on = ET.Element("Step")
        step_on.set("Number", str(current_step))
        step_on.set("FadeIn", str(fade_in))
        step_on.set("Hold", str(hold))
        step_on.set("FadeOut", str(fade_out))
        step_on.set("Values", str(total_channels*fixture_num))

        # Build values string for ON state
        values = []
        for i in range(fixture_num):
            channel_values = []
            for channel_info in channels_dict['IntensityDimmer']:
                channel = channel_info['channel']
                channel_values.extend([str(channel), "255"])
            values.append(f"{i}:{','.join(channel_values)}")

        # Set the text content of the element
        step_on.text = ":".join(values)

        # Create OFF step
        step_off = ET.Element("Step")
        step_off.set("Number", str(current_step + 1))
        step_off.set("FadeIn", str(int(remaining_time)))
        step_off.set("Hold", "0")
        step_off.set("FadeOut", "0")
        step_off.set("Values", str(total_channels*fixture_num))

        steps.extend([step_on, step_off])

    return steps
