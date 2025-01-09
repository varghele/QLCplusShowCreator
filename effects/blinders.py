from utils.step_utils import create_step


def strobe(start_step, channels, bpm=120, speed="1", color=None):
    """
    Creates a strobe effect for blinders
    Parameters:
        start_step: Starting step number
        channels: List of channel numbers
        bpm: Beats per minute
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for basic strobe)
    Returns:
        list: List of XML Step elements
    """
    steps = []

    # Convert speed fraction to float
    if isinstance(speed, str) and '/' in speed:
        num, denom = map(int, speed.split('/'))
        speed_multiplier = num / denom
    else:
        speed_multiplier = float(speed)

    # Calculate timing based on BPM
    ms_per_beat = 60000 / bpm  # Convert BPM to milliseconds per beat
    ms_per_step = ms_per_beat / speed_multiplier

    # Base timing (in milliseconds)
    fade_in = int(ms_per_step * 0.1)  # 10% of step time
    hold = int(ms_per_step * 0.4)  # 40% of step time
    fade_out = int(ms_per_step * 0.5)  # 50% of step time

    # Create ON step
    step_on = ET.Element("Step")
    step_on.set("Number", str(start_step))
    step_on.set("FadeIn", str(fade_in))
    step_on.set("Hold", str(hold))
    step_on.set("FadeOut", str(fade_out))

    # Create values string for all channels at full
    values = []
    for channel in channels:
        values.extend([str(channel), "255"])
    step_on.set("Values", ",".join(values))

    # Create OFF step
    step_off = ET.Element("Step")
    step_off.set("Number", str(start_step + 1))
    step_off.set("FadeIn", str(fade_in))
    step_off.set("Hold", str(hold))
    step_off.set("FadeOut", str(fade_out))

    # Create values string for all channels at zero
    values = []
    for channel in channels:
        values.extend([str(channel), "0"])
    step_off.set("Values", ",".join(values))

    steps.extend([step_on, step_off])
    return steps
