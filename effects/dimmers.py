from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
import math
import hashlib
import random
from utils.to_xml.shows_to_xml import calculate_step_timing
from effects.fixture_helpers import (
    get_fixture_dimmer_channels,
    sort_fixtures_by_position,
    build_dimmer_values_for_fixtures,
    count_total_dimmer_channels
)


def _parse_speed(speed):
    """Parse speed string to float multiplier."""
    if isinstance(speed, str) and '/' in speed:
        num, denom = map(int, speed.split('/'))
        return num / denom
    return float(speed)


def _calc_bpm_timing(start_bpm, end_bpm, signature):
    """Calculate basic BPM timing parameters."""
    avg_bpm = (float(start_bpm or end_bpm) + float(end_bpm)) / 2.0
    try:
        sig_parts = signature.split('/')
        beats_per_bar = (int(sig_parts[0]) * 4) / int(sig_parts[1])
    except (ValueError, IndexError):
        beats_per_bar = 4
    ms_per_beat = 60000.0 / avg_bpm
    return avg_bpm, beats_per_bar, ms_per_beat


def _generate_sub_steps(total_duration_ms, steps_per_beat, ms_per_beat, speed_mult):
    """Generate sub-step time grid for effects that need finer resolution than 1-per-beat.

    Returns list of (step_start_ms, step_duration_ms) tuples.
    """
    beat_duration = ms_per_beat / speed_mult
    sub_step_duration = max(40, int(beat_duration / steps_per_beat))
    total_sub_steps = max(1, int(total_duration_ms / sub_step_duration))
    # Adjust duration to fit evenly
    sub_step_duration = max(40, int(total_duration_ms / total_sub_steps))
    result = []
    for i in range(total_sub_steps):
        start = i * sub_step_duration
        result.append((start, sub_step_duration))
    return result


def static(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
           num_bars=1, speed="1", color=None, intensity=200, fixture_conf=None, fixture_start_id=0, spot=None,
           fixture_definitions=None, fixture_id_map=None):
    """
    Creates a static effect for fixtures with intensity channels.

    Supports both legacy single-fixture-def mode and new per-fixture mode.

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy, used if fixture_definitions not provided)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for static effect)
        intensity: Maximum intensity value for channels (0-255)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for fixtures (legacy)
        spot: Spot object (unused in this effect)
        fixture_definitions: Dict of fixture definitions keyed by "manufacturer_model" (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)

    Returns:
        list: List of XML Step elements
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None

    # Get step timings and count
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    # Calculate total duration
    total_duration = sum(step_timings)

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    # Create single step with full duration
    step = ET.Element("Step")
    step.set("Number", str(start_step))
    step.set("FadeIn", "0")
    step.set("Hold", str(int(total_duration)))
    step.set("FadeOut", "0")
    step.set("Values", str(total_channels))

    # Build values string
    if use_per_fixture:
        intensity_per_fixture = [int(intensity)] * fixture_num
        step.text = build_dimmer_values_for_fixtures(
            fixture_conf, fixture_id_map, fixture_definitions, intensity_per_fixture
        )
    else:
        # Legacy mode
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}

        values = []
        for i in range(fixture_num):
            channel_values = []
            for channel_info in channels_dict['IntensityDimmer']:
                channel = channel_info['channel']
                channel_values.extend([str(channel), str(int(intensity))])
            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")
        step.text = ":".join(values)

    return [step]


def strobe(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
           num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None,
           fixture_definitions=None, fixture_id_map=None):
    """
    Creates a strobe effect: hard 50% duty cycle at 2*speed_mult Hz.
    Matches the real-time ArtNet engine (dmx_manager.py).

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for basic strobe)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)

    Returns:
        list: List of XML Step elements
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None
    speed_mult = _parse_speed(speed)
    avg_bpm, beats_per_bar, ms_per_beat = _calc_bpm_timing(start_bpm, end_bpm, signature)

    # Total duration
    total_duration_ms = int(ms_per_beat * beats_per_bar * int(num_bars))

    # Strobe at 2*speed_mult Hz → period = 1/(2*speed_mult) seconds
    strobe_hz = 2.0 * speed_mult
    period_ms = max(40, int(1000.0 / strobe_hz))
    half_period_ms = max(20, period_ms // 2)

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    steps = []
    current_step = start_step
    elapsed = 0

    while elapsed < total_duration_ms:
        remaining = total_duration_ms - elapsed
        # ON step
        on_duration = min(half_period_ms, remaining)
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", "0")
        step.set("Hold", str(int(on_duration)))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        if use_per_fixture:
            intensity_per_fixture = [int(intensity)] * fixture_num
            step.text = build_dimmer_values_for_fixtures(
                fixture_conf, fixture_id_map, fixture_definitions, intensity_per_fixture
            )
        else:
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}
            values = []
            for i in range(fixture_num):
                channel_values = []
                for channel_info in channels_dict['IntensityDimmer']:
                    channel = channel_info['channel']
                    channel_values.extend([str(channel), str(int(intensity))])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")
            step.text = ":".join(values)

        steps.append(step)
        current_step += 1
        elapsed += on_duration

        if elapsed >= total_duration_ms:
            break

        # OFF step
        remaining = total_duration_ms - elapsed
        off_duration = min(half_period_ms, remaining)
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", "0")
        step.set("Hold", str(int(off_duration)))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        if use_per_fixture:
            intensity_per_fixture = [0] * fixture_num
            step.text = build_dimmer_values_for_fixtures(
                fixture_conf, fixture_id_map, fixture_definitions, intensity_per_fixture
            )
        else:
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
        elapsed += off_duration

    return steps


def twinkle(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
            num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None,
            fixture_definitions=None, fixture_id_map=None):
    """
    Creates a twinkling effect with MD5-seeded random targets per fixture,
    smoothstep interpolation, 200ms twinkle steps.
    Matches the real-time ArtNet engine (dmx_manager.py).

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for basic twinkle)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)

    Returns:
        list: List of XML Step elements
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None
    speed_mult = _parse_speed(speed)
    avg_bpm, beats_per_bar, ms_per_beat = _calc_bpm_timing(start_bpm, end_bpm, signature)

    # Total duration
    total_duration_ms = int(ms_per_beat * beats_per_bar * int(num_bars))

    # Twinkle step duration: 200ms base, adjusted by speed
    twinkle_step_ms = max(40, int(200.0 / speed_mult))
    # Generate ~2 XML steps per twinkle step for smooth interpolation (half-step sampling)
    xml_step_ms = max(40, twinkle_step_ms // 2)
    total_sub_steps = max(1, int(total_duration_ms / xml_step_ms))
    xml_step_ms = max(40, int(total_duration_ms / total_sub_steps))

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    steps = []
    current_step = start_step

    for sub_idx in range(total_sub_steps):
        time_ms = sub_idx * xml_step_ms
        time_s = time_ms / 1000.0

        # Calculate twinkle interpolation parameters
        twinkle_step_s = twinkle_step_ms / 1000.0
        step_float = time_s / twinkle_step_s
        current_twinkle_step = int(step_float)
        next_twinkle_step = current_twinkle_step + 1
        transition_progress = step_float - current_twinkle_step

        # Smoothstep
        t = transition_progress
        smooth_t = t * t * (3 - 2 * t)

        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", "0")
        step.set("Hold", str(xml_step_ms))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        if use_per_fixture:
            intensity_per_fixture = []
            for i in range(fixture_num):
                # Current target
                seed_str = f"fixture_{i}_{current_twinkle_step}"
                seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
                random.seed(seed_hash)
                current_var = random.random() * 0.7 + 0.3

                # Next target
                seed_str = f"fixture_{i}_{next_twinkle_step}"
                seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
                random.seed(seed_hash)
                next_var = random.random() * 0.7 + 0.3

                variation = current_var + (next_var - current_var) * smooth_t
                intensity_per_fixture.append(int(intensity * variation))

            step.text = build_dimmer_values_for_fixtures(
                fixture_conf, fixture_id_map, fixture_definitions, intensity_per_fixture
            )
        else:
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}
            values = []
            for i in range(fixture_num):
                channel_values = []
                for idx, channel_info in enumerate(channels_dict['IntensityDimmer']):
                    ch = channel_info['channel']
                    # Use fixture index * channel count + idx for unique seed
                    fixture_idx = i * len(channels_dict['IntensityDimmer']) + idx

                    seed_str = f"fixture_{fixture_idx}_{current_twinkle_step}"
                    seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
                    random.seed(seed_hash)
                    current_var = random.random() * 0.7 + 0.3

                    seed_str = f"fixture_{fixture_idx}_{next_twinkle_step}"
                    seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
                    random.seed(seed_hash)
                    next_var = random.random() * 0.7 + 0.3

                    variation = current_var + (next_var - current_var) * smooth_t
                    value = int(intensity * variation)
                    channel_values.extend([str(ch), str(value)])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")
            step.text = ":".join(values)

        steps.append(step)
        current_step += 1

    return steps


def ping_pong_smooth(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4",
                     transition="gradual", num_bars=1, speed="1", color=None, fixture_conf=None,
                     fixture_start_id=0, intensity=200, spot=None,
                     fixture_definitions=None, fixture_id_map=None):
    """
    Creates a smooth ping-pong effect with exponential decay on active fixture
    and 30% tail window on previous fixture.
    Matches the real-time ArtNet engine (dmx_manager.py).

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for basic ping-pong)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None
    speed_mult = _parse_speed(speed)
    avg_bpm, beats_per_bar, ms_per_beat = _calc_bpm_timing(start_bpm, end_bpm, signature)

    # Sort fixtures by x-position for proper left-to-right traversal
    sorted_indexed_fixtures = sort_fixtures_by_position(fixture_conf, axis='x', reverse=False)
    # Build sorted_idx → orig_idx mapping
    orig_idx_for_sorted = [orig_idx for orig_idx, _ in sorted_indexed_fixtures]
    # Build orig_idx → sorted_idx mapping
    sorted_idx_for_orig = {}
    for sorted_idx, (orig_idx, _) in enumerate(sorted_indexed_fixtures):
        sorted_idx_for_orig[orig_idx] = sorted_idx

    # Total duration and sub-step grid
    total_duration_ms = int(ms_per_beat * beats_per_bar * int(num_bars))
    beat_ms = ms_per_beat / speed_mult
    sub_step_ms = max(40, int(beat_ms / 10))
    total_sub_steps = max(1, int(total_duration_ms / sub_step_ms))
    sub_step_ms = max(40, int(total_duration_ms / total_sub_steps))

    # Ping-pong cycle timing
    time_per_fixture_ms = beat_ms  # each fixture gets one beat
    if fixture_num <= 1:
        steps_in_cycle = 1
    else:
        steps_in_cycle = (fixture_num - 1) * 2
    cycle_time_ms = time_per_fixture_ms * steps_in_cycle

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    steps = []
    current_step = start_step

    for sub_idx in range(total_sub_steps):
        time_ms = sub_idx * sub_step_ms

        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", "0")
        step.set("Hold", str(sub_step_ms))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        # Calculate active fixture and decay for this time
        if fixture_num <= 1:
            # Single fixture - always on
            intensities = [int(intensity)]
        else:
            time_in_cycle = time_ms % cycle_time_ms
            current_beat = time_in_cycle / time_per_fixture_ms
            step_index = int(current_beat)
            time_within_step = (current_beat - step_index) * time_per_fixture_ms

            # Convert step to active fixture (ping-pong)
            if step_index < (fixture_num - 1):
                active_sorted = step_index
            else:
                active_sorted = steps_in_cycle - step_index

            # Determine previous fixture for tail
            if step_index < (fixture_num - 1):
                prev_sorted = active_sorted - 1
            else:
                prev_sorted = active_sorted + 1

            intensities = []
            for sorted_idx in range(fixture_num):
                if sorted_idx == active_sorted:
                    decay_progress = time_within_step / time_per_fixture_ms if time_per_fixture_ms > 0 else 0
                    mult = 0.2 + 0.8 * math.exp(-decay_progress * 3)
                elif sorted_idx == prev_sorted and 0 <= prev_sorted < fixture_num:
                    if time_within_step < time_per_fixture_ms * 0.3:
                        tail_progress = time_within_step / (time_per_fixture_ms * 0.3) if time_per_fixture_ms > 0 else 1
                        mult = 0.3 * (1.0 - tail_progress)
                    else:
                        mult = 0.0
                else:
                    mult = 0.0
                intensities.append(int(intensity * mult))

        if use_per_fixture:
            # Map sorted intensities back to original fixture order
            values = []
            for orig_idx, fixture in enumerate(fixture_conf):
                fixture_id = fixture_id_map[(fixture.universe, fixture.address)]
                sorted_idx = sorted_idx_for_orig[orig_idx]
                fix_intensity = intensities[sorted_idx] if fixture_num > 1 else intensities[0]

                channels = get_fixture_dimmer_channels(fixture, fixture_definitions)
                channel_values = []
                for ch_info in channels:
                    channel_values.extend([str(ch_info['channel']), str(fix_intensity)])
                values.append(f"{fixture_id}:{','.join(channel_values)}")
            step.text = ":".join(values)
        else:
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}
            values = []
            for i in range(fixture_num):
                fix_intensity = intensities[i] if fixture_num > 1 else intensities[0]
                channel_values = []
                for channel in channels_dict['IntensityDimmer']:
                    channel_values.extend([str(channel['channel']), str(fix_intensity)])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")
            step.text = ":".join(values)

        steps.append(step)
        current_step += 1

    return steps


def random_strobe(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4",
                  transition="gradual", num_bars=1, speed="1", color=None, fixture_conf=None,
                  fixture_start_id=0, intensity=200, spot=None,
                  fixture_definitions=None, fixture_id_map=None,
                  start_time=0.0):
    """
    Creates a random strobe effect with block-start-time-based seed and
    exponential decay on active fixture.
    Matches the real-time ArtNet engine (dmx_manager.py).

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for basic random strobe)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)
        start_time: Block start time in seconds (for deterministic seed)
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None
    speed_mult = _parse_speed(speed)
    avg_bpm, beats_per_bar, ms_per_beat = _calc_bpm_timing(start_bpm, end_bpm, signature)

    # Total duration and sub-step grid
    total_duration_ms = int(ms_per_beat * beats_per_bar * int(num_bars))
    beat_ms = ms_per_beat / speed_mult
    sub_step_ms = max(40, int(beat_ms / 10))
    total_sub_steps = max(1, int(total_duration_ms / sub_step_ms))
    sub_step_ms = max(40, int(total_duration_ms / total_sub_steps))

    # Cycle timing
    time_per_fixture_ms = beat_ms  # each fixture gets one beat
    cycle_time_ms = time_per_fixture_ms * fixture_num if fixture_num > 0 else 1

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    steps = []
    current_step = start_step

    for sub_idx in range(total_sub_steps):
        time_ms = sub_idx * sub_step_ms

        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", "0")
        step.set("Hold", str(sub_step_ms))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        if fixture_num <= 1:
            intensities = [int(intensity)]
        else:
            # Which cycle and step within cycle?
            cycle_number = int(time_ms / cycle_time_ms)
            time_in_cycle = time_ms % cycle_time_ms
            current_beat = time_in_cycle / time_per_fixture_ms
            step_index = int(current_beat)
            time_within_step = (current_beat - step_index) * time_per_fixture_ms

            # Generate shuffled order deterministically based on block start time + cycle
            seed = int(start_time * 1000) + cycle_number
            rng = random.Random(seed)
            shuffled_indices = list(range(fixture_num))
            rng.shuffle(shuffled_indices)

            active_fixture = shuffled_indices[step_index % fixture_num]

            intensities = []
            for i in range(fixture_num):
                if i == active_fixture:
                    decay_progress = time_within_step / time_per_fixture_ms if time_per_fixture_ms > 0 else 0
                    mult = 0.2 + 0.8 * math.exp(-decay_progress * 3)
                else:
                    mult = 0.0
                intensities.append(int(intensity * mult))

        if use_per_fixture:
            values = []
            for orig_idx, fixture in enumerate(fixture_conf):
                fixture_id = fixture_id_map[(fixture.universe, fixture.address)]
                fix_intensity = intensities[orig_idx] if orig_idx < len(intensities) else 0

                channels = get_fixture_dimmer_channels(fixture, fixture_definitions)
                channel_values = []
                for ch_info in channels:
                    channel_values.extend([str(ch_info['channel']), str(fix_intensity)])
                values.append(f"{fixture_id}:{','.join(channel_values)}")
            step.text = ":".join(values)
        else:
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}
            values = []
            for i in range(fixture_num):
                fix_intensity = intensities[i] if i < len(intensities) else 0
                channel_values = []
                for channel in channels_dict['IntensityDimmer']:
                    channel_values.extend([str(channel['channel']), str(fix_intensity)])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")
            step.text = ":".join(values)

        steps.append(step)
        current_step += 1

    return steps


def snake(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4",
          transition="gradual", num_bars=1, speed="1", color=None, fixture_conf=None,
          fixture_start_id=0, intensity=200, spot=None,
          fixture_definitions=None, fixture_id_map=None):
    """
    Creates a snake effect where a "snake" with a fading tail moves through fixtures,
    bouncing back and forth like the classic Snake game.

    - 4 beats = full cycle (bottom→top→bottom)
    - Tail spans approximately half the fixtures
    - Head at full intensity, tail fades smoothly

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used)
        fixture_conf: List of fixture configurations
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    # Sort fixtures by position for proper traversal
    sorted_indexed_fixtures = sort_fixtures_by_position(fixture_conf, axis='x', reverse=False)

    steps = []
    current_step = start_step

    # Snake parameters
    tail_length = max(1, fixture_num // 2)  # Tail spans half the fixtures

    # 4 beats = full cycle (forward + backward)
    # So 2 beats for forward pass, 2 beats for backward pass
    # steps_in_half_cycle = fixture_num steps to traverse all fixtures
    steps_in_cycle = fixture_num * 2  # Full ping-pong cycle

    for step_idx, step_duration in enumerate(step_timings):
        # Calculate snake head position (ping-pong pattern)
        cycle_position = step_idx % steps_in_cycle

        if cycle_position < fixture_num:
            # Going forward (0 to fixture_num-1)
            head_position = cycle_position
        else:
            # Going backward (fixture_num-1 to 0)
            head_position = steps_in_cycle - cycle_position - 1

        # Create step — FadeIn=0, Hold=step_duration for instant snap (matching RT engine)
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", "0")
        step.set("Hold", str(int(step_duration)))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        # Build intensity per fixture based on distance from snake head
        if use_per_fixture:
            values = []
            for orig_idx, fixture in enumerate(fixture_conf):
                fixture_id = fixture_id_map[(fixture.universe, fixture.address)]

                # Find this fixture's position in sorted order
                for sorted_idx, (oidx, f) in enumerate(sorted_indexed_fixtures):
                    if oidx == orig_idx:
                        fixture_position = sorted_idx
                        break
                else:
                    fixture_position = 0

                # Calculate distance from head (considering direction)
                if cycle_position < fixture_num:
                    # Going forward - tail extends backward
                    distance = head_position - fixture_position
                else:
                    # Going backward - tail extends forward
                    distance = fixture_position - head_position

                # Calculate intensity based on distance
                if distance < 0:
                    # Ahead of head - off
                    fix_intensity = 0
                elif distance == 0:
                    # At head - full intensity
                    fix_intensity = int(intensity)
                elif distance <= tail_length:
                    # In tail - fade based on distance
                    fade_factor = 1.0 - (distance / (tail_length + 1))
                    fix_intensity = int(intensity * fade_factor * 0.8)  # Max 80% for tail
                else:
                    # Beyond tail - off
                    fix_intensity = 0

                channels = get_fixture_dimmer_channels(fixture, fixture_definitions)
                channel_values = []
                for ch_info in channels:
                    channel_values.extend([str(ch_info['channel']), str(fix_intensity)])
                values.append(f"{fixture_id}:{','.join(channel_values)}")

            step.text = ":".join(values)
        else:
            # Legacy mode
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}

            values = []
            for i in range(fixture_num):
                # Calculate distance from head
                if cycle_position < fixture_num:
                    distance = head_position - i
                else:
                    distance = i - head_position

                if distance < 0:
                    fix_intensity = 0
                elif distance == 0:
                    fix_intensity = int(intensity)
                elif distance <= tail_length:
                    fade_factor = 1.0 - (distance / (tail_length + 1))
                    fix_intensity = int(intensity * fade_factor * 0.8)
                else:
                    fix_intensity = 0

                channel_values = []
                for channel in channels_dict['IntensityDimmer']:
                    channel_values.extend([str(channel['channel']), str(fix_intensity)])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

            step.text = ":".join(values)

        steps.append(step)
        current_step += 1

    return steps


def zigzag(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4",
           transition="gradual", num_bars=1, speed="1", color=None, fixture_conf=None,
           fixture_start_id=0, intensity=200, spot=None,
           fixture_definitions=None, fixture_id_map=None):
    """
    Creates a zigzag effect where a snake with fading tail moves across ALL fixtures
    as one continuous chain, bouncing back and forth.

    Unlike 'snake' which runs independently per fixture, 'zigzag' treats all segments
    across all fixtures as one long strip:
    - Fixture 1 segments → Fixture 2 segments → ... → Fixture N segments
    - Then bounces back

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used)
        fixture_conf: List of fixture configurations
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    # Sort fixtures by position for proper traversal
    sorted_indexed_fixtures = sort_fixtures_by_position(fixture_conf, axis='x', reverse=False)

    # For zigzag, we treat all fixtures as having segments
    # If fixtures don't have segments, each fixture counts as 1 segment
    # Total positions = sum of segments across all fixtures
    total_positions = fixture_num  # Default: 1 position per fixture

    steps = []
    current_step = start_step

    # Zigzag parameters
    tail_length = max(1, total_positions // 2)  # Tail spans half the total

    # 4 beats = full cycle (forward + backward)
    steps_in_cycle = total_positions * 2

    for step_idx, step_duration in enumerate(step_timings):
        # Calculate snake head position (ping-pong pattern across all positions)
        cycle_position = step_idx % steps_in_cycle

        if cycle_position < total_positions:
            # Going forward (0 to total_positions-1)
            head_position = cycle_position
        else:
            # Going backward (total_positions-1 to 0)
            head_position = steps_in_cycle - cycle_position - 1

        # Create step — FadeIn=0, Hold=step_duration for instant snap (matching RT engine)
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", "0")
        step.set("Hold", str(int(step_duration)))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        # Build intensity per fixture based on distance from snake head
        if use_per_fixture:
            values = []
            for orig_idx, fixture in enumerate(fixture_conf):
                fixture_id = fixture_id_map[(fixture.universe, fixture.address)]

                # Find this fixture's position in sorted order
                for sorted_idx, (oidx, f) in enumerate(sorted_indexed_fixtures):
                    if oidx == orig_idx:
                        fixture_position = sorted_idx
                        break
                else:
                    fixture_position = 0

                # Calculate distance from head (considering direction)
                if cycle_position < total_positions:
                    # Going forward - tail extends backward
                    distance = head_position - fixture_position
                else:
                    # Going backward - tail extends forward
                    distance = fixture_position - head_position

                # Calculate intensity based on distance
                if distance < 0:
                    fix_intensity = 0
                elif distance == 0:
                    fix_intensity = int(intensity)
                elif distance <= tail_length:
                    fade_factor = 1.0 - (distance / (tail_length + 1))
                    fix_intensity = int(intensity * fade_factor * 0.8)
                else:
                    fix_intensity = 0

                channels = get_fixture_dimmer_channels(fixture, fixture_definitions)
                channel_values = []
                for ch_info in channels:
                    channel_values.extend([str(ch_info['channel']), str(fix_intensity)])
                values.append(f"{fixture_id}:{','.join(channel_values)}")

            step.text = ":".join(values)
        else:
            # Legacy mode
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}

            values = []
            for i in range(fixture_num):
                if cycle_position < total_positions:
                    distance = head_position - i
                else:
                    distance = i - head_position

                if distance < 0:
                    fix_intensity = 0
                elif distance == 0:
                    fix_intensity = int(intensity)
                elif distance <= tail_length:
                    fade_factor = 1.0 - (distance / (tail_length + 1))
                    fix_intensity = int(intensity * fade_factor * 0.8)
                else:
                    fix_intensity = 0

                channel_values = []
                for channel in channels_dict['IntensityDimmer']:
                    channel_values.extend([str(channel['channel']), str(fix_intensity)])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

            step.text = ":".join(values)

        steps.append(step)
        current_step += 1

    return steps


def waterfall(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
              num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None,
              direction="down", wave_size=3,
              fixture_definitions=None, fixture_id_map=None):
    """
    Creates a waterfall effect with MD5-hashed base offset, slow sinusoidal drift,
    and exponential decay with circular wrapping.
    Matches the real-time ArtNet engine (dmx_manager.py).

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for basic dimmer effects)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
        direction: Flow direction ("down", "up", "left", "right")
        wave_size: Number of fixtures lit at once in the wave packet (legacy, unused in new algorithm)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)

    Returns:
        list: List of XML Step elements
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None
    speed_mult = _parse_speed(speed)
    avg_bpm, beats_per_bar, ms_per_beat = _calc_bpm_timing(start_bpm, end_bpm, signature)

    # Determine sort axis based on flow direction
    if direction == "down":
        axis, reverse = 'y', False
    elif direction == "up":
        axis, reverse = 'y', True
    elif direction == "left":
        axis, reverse = 'x', True
    else:  # right
        axis, reverse = 'x', False

    # Sort fixtures by position
    sorted_indexed_fixtures = sort_fixtures_by_position(fixture_conf, axis=axis, reverse=reverse)
    # Build orig_idx → sorted_idx mapping
    sorted_idx_for_orig = {}
    for sorted_idx, (orig_idx, _) in enumerate(sorted_indexed_fixtures):
        sorted_idx_for_orig[orig_idx] = sorted_idx

    # Total duration and sub-step grid
    total_duration_ms = int(ms_per_beat * beats_per_bar * int(num_bars))
    beat_ms = ms_per_beat / speed_mult
    sub_step_ms = max(40, int(beat_ms / 10))
    total_sub_steps = max(1, int(total_duration_ms / sub_step_ms))
    sub_step_ms = max(40, int(total_duration_ms / total_sub_steps))

    # Waterfall timing: each fixture transition = one beat
    time_per_step_s = (ms_per_beat / speed_mult) / 1000.0
    cycle_time_s = time_per_step_s * fixture_num if fixture_num > 0 else 1

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    # Map "down"/"left" to waterfall_down behavior, "up"/"right" to waterfall_up
    is_down = direction in ("down", "left")

    steps = []
    current_step = start_step

    for sub_idx in range(total_sub_steps):
        time_ms = sub_idx * sub_step_ms
        time_s = time_ms / 1000.0

        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", "0")
        step.set("Hold", str(sub_step_ms))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        # Calculate per-fixture intensity using MD5 offset + sinusoidal drift + exp decay
        sorted_intensities = []
        for sorted_idx in range(fixture_num):
            # MD5-hashed base offset for this fixture
            seed_str = f"waterfall_fixture_{sorted_idx}"
            name_hash = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
            base_offset = (name_hash % 1000) / 1000.0

            # Slowly drifting component
            drift_period = 30.0
            drift_phase = (time_s / drift_period) * 2 * math.pi
            drift_seed = (name_hash % 997) / 997.0 * 2 * math.pi
            drift_amount = 0.3 * math.sin(drift_phase + drift_seed)

            total_offset = base_offset + drift_amount

            # Current head position with offset
            cycle_progress = (time_s / cycle_time_s + total_offset) % 1.0
            head_position = cycle_progress * fixture_num

            if is_down:
                head_position = (fixture_num - 1) - head_position

            # Circular distance and exponential decay
            if is_down:
                raw_distance = sorted_idx - head_position
            else:
                raw_distance = head_position - sorted_idx

            circular_distance = raw_distance % fixture_num
            normalized_dist = circular_distance / fixture_num
            intensity_factor = math.exp(-1.5 * normalized_dist)

            sorted_intensities.append(int(intensity * intensity_factor))

        if use_per_fixture:
            values = []
            for orig_idx, fixture in enumerate(fixture_conf):
                fixture_id = fixture_id_map[(fixture.universe, fixture.address)]
                s_idx = sorted_idx_for_orig[orig_idx]
                fix_intensity = sorted_intensities[s_idx]

                channels = get_fixture_dimmer_channels(fixture, fixture_definitions)
                channel_values = []
                for ch_info in channels:
                    channel_values.extend([str(ch_info['channel']), str(fix_intensity)])
                values.append(f"{fixture_id}:{','.join(channel_values)}")
            step.text = ":".join(values)
        else:
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}
            values = []
            for i in range(fixture_num):
                fix_intensity = sorted_intensities[i]
                channel_values = []
                for channel in channels_dict['IntensityDimmer']:
                    channel_values.extend([str(channel['channel']), str(fix_intensity)])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")
            step.text = ":".join(values)

        steps.append(step)
        current_step += 1

    return steps


def hit(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
        num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None,
        fixture_definitions=None, fixture_id_map=None):
    """
    Creates a hit/bump effect: instant attack, decay over the beat duration.

    One hit per beat at speed "1". Decay takes the full beat duration.

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for basic hit)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)

    Returns:
        list: List of XML Step elements
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None

    # Parse speed multiplier
    if '/' in speed:
        parts = speed.split('/')
        try:
            speed_multiplier = float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            speed_multiplier = 1.0
    else:
        try:
            speed_multiplier = float(speed)
        except ValueError:
            speed_multiplier = 1.0

    # Parse time signature for beats per bar
    try:
        sig_parts = signature.split('/')
        beats_per_bar = int(sig_parts[0])
    except (ValueError, IndexError):
        beats_per_bar = 4

    # Calculate timing
    avg_bpm = (start_bpm + end_bpm) / 2.0  # Use average BPM for step calculations
    seconds_per_beat = 60.0 / avg_bpm
    seconds_per_bar = seconds_per_beat * beats_per_bar

    # Time between hits (one beat at speed 1)
    time_per_hit = seconds_per_beat / speed_multiplier

    # Decay takes the full beat duration
    decay_time = time_per_hit
    decay_ms = int(decay_time * 1000)

    # Calculate total duration
    total_duration = seconds_per_bar * num_bars

    # Calculate number of hits in the block
    num_hits = int(total_duration / time_per_hit)
    if num_hits < 1:
        num_hits = 1

    time_per_hit_ms = int(time_per_hit * 1000)

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    steps = []
    current_step = start_step

    # Generate steps for decay curve
    # We'll use ~10 steps per decay for smooth falloff
    steps_per_decay = 10
    step_duration_in_decay = decay_ms // steps_per_decay

    for hit_idx in range(num_hits):
        # Generate decay steps for this hit
        for decay_step in range(steps_per_decay):
            step = ET.Element("Step")
            step.set("Number", str(current_step))

            # Calculate intensity at this point in decay
            decay_progress = decay_step / steps_per_decay
            # Exponential decay: e^(-3) ≈ 0.05
            intensity_multiplier = math.exp(-decay_progress * 3)
            step_intensity = int(intensity * intensity_multiplier)

            # First step has no fade-in (instant attack), others fade
            if decay_step == 0:
                step.set("FadeIn", "0")
            else:
                step.set("FadeIn", str(step_duration_in_decay))

            step.set("Hold", "0")
            step.set("FadeOut", "0")
            step.set("Values", str(total_channels))

            # Build values string
            if use_per_fixture:
                intensity_per_fixture = [step_intensity] * fixture_num
                step.text = build_dimmer_values_for_fixtures(
                    fixture_conf, fixture_id_map, fixture_definitions, intensity_per_fixture
                )
            else:
                channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
                if not channels_dict:
                    channels_dict = {'IntensityDimmer': [{'channel': 0}]}
                values = []
                for i in range(fixture_num):
                    channel_values = []
                    for channel_info in channels_dict['IntensityDimmer']:
                        channel = channel_info['channel']
                        channel_values.extend([str(channel), str(step_intensity)])
                    values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")
                step.text = ":".join(values)

            steps.append(step)
            current_step += 1

    return steps


def breathing_sync(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                   num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None,
                   fixture_definitions=None, fixture_id_map=None, floor=0.3, **kwargs):
    """
    Breathing effect - all fixtures fade in/out together smoothly in a sine curve pattern.

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for dimmer effects)
        fixture_conf: List of fixture configurations
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)
        floor: Minimum intensity as fraction (0.0-1.0), default 0.3
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    total_duration = sum(step_timings)

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    # Animation frames - use more frames for smoother animation
    num_frames = min(32, max(16, int(total_steps)))
    frame_duration = total_duration / num_frames

    steps = []
    current_step = start_step

    for frame in range(num_frames):
        # Sine wave for smooth breathing (0 to 1)
        phase = (frame / num_frames) * 2 * math.pi
        brightness = floor + (1 - floor) * (math.sin(phase) + 1) / 2

        # Apply brightness to intensity
        frame_intensity = int(intensity * brightness)

        # Create step with fade for smoothness
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        fade_time = int(frame_duration / 2)
        step.set("FadeIn", str(fade_time))
        step.set("Hold", str(int(frame_duration - fade_time)))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        # Build values string
        if use_per_fixture:
            intensity_per_fixture = [frame_intensity] * fixture_num
            step.text = build_dimmer_values_for_fixtures(
                fixture_conf, fixture_id_map, fixture_definitions, intensity_per_fixture
            )
        else:
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}
            values = []
            for i in range(fixture_num):
                channel_values = []
                for channel_info in channels_dict['IntensityDimmer']:
                    channel = channel_info['channel']
                    channel_values.extend([str(channel), str(frame_intensity)])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")
            step.text = ":".join(values)

        steps.append(step)
        current_step += 1

    return steps


def wave_travel(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None,
                fixture_definitions=None, fixture_id_map=None, direction="right", wavelength=None, **kwargs):
    """
    Wave effect - intensity wave travels across fixtures like a stadium wave.

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for dimmer effects)
        fixture_conf: List of fixture configurations
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)
        direction: "left" or "right" (default: "right")
        wavelength: How many fixtures wide the wave is (default: num_fixtures/2)
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None

    # Set default wavelength if not provided
    if wavelength is None:
        wavelength = max(2, fixture_num // 2)

    # Sort fixtures by position for proper wave traversal
    sorted_indexed_fixtures = sort_fixtures_by_position(fixture_conf, axis='x', reverse=False)

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    num_frames = len(step_timings)

    steps = []
    current_step = start_step

    for frame_idx, step_duration in enumerate(step_timings):
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        if use_per_fixture:
            values = []
            for orig_idx, fixture in enumerate(fixture_conf):
                fixture_id = fixture_id_map[(fixture.universe, fixture.address)]

                # Find this fixture's position in sorted order
                for sorted_idx, (oidx, f) in enumerate(sorted_indexed_fixtures):
                    if oidx == orig_idx:
                        fixture_position = sorted_idx
                        break
                else:
                    fixture_position = orig_idx

                # Wave position calculation
                if direction == "left":
                    wave_pos = 2 * math.pi * (fixture_position / wavelength + frame_idx / num_frames)
                else:  # right
                    wave_pos = 2 * math.pi * (fixture_position / wavelength - frame_idx / num_frames)

                # Sine wave intensity (0 to 1)
                fixture_intensity_factor = (math.sin(wave_pos) + 1) / 2
                fixture_intensity = int(intensity * fixture_intensity_factor)

                channels = get_fixture_dimmer_channels(fixture, fixture_definitions)
                channel_values = []
                for ch_info in channels:
                    channel_values.extend([str(ch_info['channel']), str(fixture_intensity)])
                values.append(f"{fixture_id}:{','.join(channel_values)}")

            step.text = ":".join(values)
        else:
            # Legacy mode
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}

            values = []
            for i in range(fixture_num):
                # Wave position calculation
                if direction == "left":
                    wave_pos = 2 * math.pi * (i / wavelength + frame_idx / num_frames)
                else:  # right
                    wave_pos = 2 * math.pi * (i / wavelength - frame_idx / num_frames)

                fixture_intensity_factor = (math.sin(wave_pos) + 1) / 2
                fixture_intensity = int(intensity * fixture_intensity_factor)

                channel_values = []
                for channel_info in channels_dict['IntensityDimmer']:
                    channel = channel_info['channel']
                    channel_values.extend([str(channel), str(fixture_intensity)])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

            step.text = ":".join(values)

        steps.append(step)
        current_step += 1

    return steps


def heartbeat_pulse(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                    num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None,
                    fixture_definitions=None, fixture_id_map=None, floor=0.2, **kwargs):
    """
    Heartbeat effect - double-pulse pattern mimicking heartbeat rhythm (bump-bump... pause... bump-bump).

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition (legacy)
        mode_name: Name of the mode to use (legacy)
        start_bpm: Starting BPM
        end_bpm: Ending BPM
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Color value (not used for dimmer effects)
        fixture_conf: List of fixture configurations
        fixture_start_id: starting ID for fixtures (legacy)
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)
        floor: Minimum intensity between beats (default: 0.2)

    Timing pattern per cycle:
        - Beat 1 up: 10% of cycle
        - Beat 1 down: 10% of cycle
        - Beat 2 up: 10% of cycle
        - Beat 2 down: 20% of cycle
        - Rest: 50% of cycle
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    total_duration = sum(step_timings)

    # Count total channels
    if use_per_fixture:
        total_channels = count_total_dimmer_channels(fixture_conf, fixture_definitions)
    else:
        channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
        if not channels_dict:
            channels_dict = {'IntensityDimmer': [{'channel': 0}]}
        total_channels = len(channels_dict.get('IntensityDimmer', [])) * fixture_num

    # Create heartbeat pattern frames
    # Pattern: beat1_up, beat1_down, beat2_up, beat2_down, rest
    # Timing:    10%,       10%,       10%,       20%,     50%
    pattern_frames = 20  # Number of frames per heartbeat cycle
    num_cycles = max(1, int(len(step_timings) / pattern_frames))
    num_frames = num_cycles * pattern_frames

    frame_duration = total_duration / num_frames

    steps = []
    current_step = start_step

    for frame in range(num_frames):
        # Position within current cycle (0 to 1)
        cycle_pos = (frame % pattern_frames) / pattern_frames

        # Calculate beat level based on position in cycle
        if cycle_pos < 0.10:
            # Beat 1 up: quick fade up to 100%
            beat_level = floor + (1.0 - floor) * (cycle_pos / 0.10)
        elif cycle_pos < 0.20:
            # Beat 1 down: quick fade to 60%
            beat_level = 1.0 - (1.0 - 0.6) * ((cycle_pos - 0.10) / 0.10)
        elif cycle_pos < 0.30:
            # Beat 2 up: quick fade up to 80%
            beat_level = 0.6 + (0.8 - 0.6) * ((cycle_pos - 0.20) / 0.10)
        elif cycle_pos < 0.50:
            # Beat 2 down: fade down to floor
            beat_level = 0.8 - (0.8 - floor) * ((cycle_pos - 0.30) / 0.20)
        else:
            # Rest: stay at floor
            beat_level = floor

        # Apply beat level to intensity
        frame_intensity = int(intensity * beat_level)

        # Create step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        fade_time = int(frame_duration / 2)
        step.set("FadeIn", str(fade_time))
        step.set("Hold", str(int(frame_duration - fade_time)))
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        # Build values string
        if use_per_fixture:
            intensity_per_fixture = [frame_intensity] * fixture_num
            step.text = build_dimmer_values_for_fixtures(
                fixture_conf, fixture_id_map, fixture_definitions, intensity_per_fixture
            )
        else:
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}
            values = []
            for i in range(fixture_num):
                channel_values = []
                for channel_info in channels_dict['IntensityDimmer']:
                    channel = channel_info['channel']
                    channel_values.extend([str(channel), str(frame_intensity)])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")
            step.text = ":".join(values)

        steps.append(step)
        current_step += 1

    return steps
