from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
import math
from utils.to_xml.shows_to_xml import calculate_step_timing
from effects.fixture_helpers import (
    get_fixture_dimmer_channels,
    sort_fixtures_by_position,
    build_dimmer_values_for_fixtures,
    count_total_dimmer_channels
)


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
    Creates a strobe effect for fixtures with intensity channels.

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

    steps = []
    current_step = start_step

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

        # OFF step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(int(remaining_time)))
        step.set("Hold", "0")
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

    return steps


def twinkle(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
            num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None,
            fixture_definitions=None, fixture_id_map=None):
    """
    Creates a twinkling effect with curved BPM transition.

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

    steps = []
    current_step = start_step

    for step_idx, step_duration in enumerate(step_timings):
        # Create step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(int(step_duration)))
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        if use_per_fixture:
            # Alternate intensity based on step index
            intensity_per_fixture = []
            for i in range(fixture_num):
                value = int(intensity) if (i + step_idx) % 2 == 0 else int(intensity * 0.6)
                intensity_per_fixture.append(value)
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
                    channel = channel_info['channel']
                    value = str(int(intensity)) if (idx + step_idx) % 2 == 0 else str(int(intensity * 0.6))
                    channel_values.extend([str(channel), value])
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
    Creates a smooth ping-pong effect that moves light from left to right and back,
    based on fixture x-position for proper spatial traversal.

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

    # Sort fixtures by x-position for proper left-to-right traversal
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

    steps = []
    current_step = start_step
    current_position = 0  # Position in sorted fixture list
    direction = 1  # 1 for forward (left to right), -1 for backward

    for step_duration in step_timings:
        # Create step with full duration fade
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        # Calculate next position
        next_position = current_position + direction
        if next_position >= fixture_num:
            next_position = fixture_num - 2 if fixture_num > 1 else 0
            direction = -1
        elif next_position < 0:
            next_position = 1 if fixture_num > 1 else 0
            direction = 1

        # Build intensity per fixture - lit fixture at next_position, others off
        if use_per_fixture:
            intensity_per_fixture = []
            for sorted_idx, (orig_idx, fixture) in enumerate(sorted_indexed_fixtures):
                if sorted_idx == next_position:
                    intensity_per_fixture.append(int(intensity))
                else:
                    intensity_per_fixture.append(0)

            # Build values in original fixture order for proper fixture_id mapping
            values = []
            for orig_idx, fixture in enumerate(fixture_conf):
                fixture_id = fixture_id_map[(fixture.universe, fixture.address)]
                # Find this fixture's intensity in the sorted order
                for sorted_idx, (oidx, f) in enumerate(sorted_indexed_fixtures):
                    if oidx == orig_idx:
                        fix_intensity = intensity_per_fixture[sorted_idx]
                        break
                else:
                    fix_intensity = 0

                channels = get_fixture_dimmer_channels(fixture, fixture_definitions)
                channel_values = []
                for ch_info in channels:
                    channel_values.extend([str(ch_info['channel']), str(fix_intensity)])
                values.append(f"{fixture_id}:{','.join(channel_values)}")

            step.text = ":".join(values)
        else:
            # Legacy mode - use index order (not position-based)
            channels_dict = get_channels_by_property(fixture_def, mode_name, ["IntensityDimmer"])
            if not channels_dict:
                channels_dict = {'IntensityDimmer': [{'channel': 0}]}

            values = []
            for i in range(fixture_num):
                channel_values = []
                if i == next_position:
                    for channel in channels_dict['IntensityDimmer']:
                        channel_values.extend([str(channel['channel']), str(int(intensity))])
                else:
                    for channel in channels_dict['IntensityDimmer']:
                        channel_values.extend([str(channel['channel']), "0"])
                values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

            step.text = ":".join(values)

        steps.append(step)
        current_step += 1
        current_position = next_position

    return steps


def random_strobe(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4",
                  transition="gradual", num_bars=1, speed="1", color=None, fixture_conf=None,
                  fixture_start_id=0, intensity=200, spot=None,
                  fixture_definitions=None, fixture_id_map=None):
    """
    Creates a random strobe effect where fixtures light up one at a time in shuffled order.
    Once all fixtures have been lit, the order is reshuffled (like shuffling a deck of cards).

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
    """
    import random

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

    steps = []
    current_step = start_step

    # Create shuffled fixture indices - reshuffle when we've used all fixtures
    shuffled_indices = list(range(fixture_num))
    random.seed(42)  # Use fixed seed for reproducible export
    random.shuffle(shuffled_indices)
    shuffle_position = 0

    for step_duration in step_timings:
        # Get next fixture from shuffled order
        active_fixture_idx = shuffled_indices[shuffle_position]

        # Move to next position, reshuffle if we've cycled through all
        shuffle_position += 1
        if shuffle_position >= fixture_num:
            shuffle_position = 0
            random.shuffle(shuffled_indices)

        # Create step with full duration fade
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        # Build intensity per fixture - lit fixture at active_fixture_idx, others off
        if use_per_fixture:
            values = []
            for orig_idx, fixture in enumerate(fixture_conf):
                fixture_id = fixture_id_map[(fixture.universe, fixture.address)]
                fix_intensity = int(intensity) if orig_idx == active_fixture_idx else 0

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
                channel_values = []
                fix_intensity = int(intensity) if i == active_fixture_idx else 0
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

        # Create step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))
        step.set("Hold", "0")
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

        # Create step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))
        step.set("Hold", "0")
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
    Creates a waterfall effect with light "packets" flowing across dimmer fixtures.

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
        wave_size: Number of fixtures lit at once in the wave packet
        fixture_definitions: Dict of fixture definitions (new)
        fixture_id_map: Dict mapping id(fixture) to QLC+ fixture ID (new)

    Returns:
        list: List of XML Step elements
    """
    if not fixture_conf:
        return []

    fixture_num = len(fixture_conf)
    use_per_fixture = fixture_definitions is not None and fixture_id_map is not None

    # Determine sort axis and direction based on flow direction
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

    steps = []
    current_step = start_step

    for step_idx, step_duration in enumerate(step_timings):
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels))

        # Calculate wave position for this step
        wave_position = step_idx % (fixture_num + wave_size)

        if use_per_fixture:
            # Build per-fixture intensity based on wave position
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

                # Calculate distance from wave
                distance_from_wave = fixture_position - wave_position

                if 0 <= distance_from_wave < wave_size:
                    center_position = wave_size / 2
                    distance_from_center = abs(distance_from_wave - center_position)
                    intensity_factor = 1.0 - (distance_from_center / center_position) if center_position > 0 else 1.0
                    fixture_intensity = int(intensity * intensity_factor)
                else:
                    fixture_intensity = 0

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

            # Sort fixtures for position-based effect (legacy uses fixture_conf directly)
            if fixture_conf:
                if direction in ("down", "up"):
                    sorted_fixtures = sorted(fixture_conf, key=lambda f: f.y, reverse=(direction == "up"))
                else:
                    sorted_fixtures = sorted(fixture_conf, key=lambda f: f.x, reverse=(direction == "right"))
            else:
                sorted_fixtures = fixture_conf

            values = []
            for i, fixture in enumerate(sorted_fixtures):
                channel_values = []
                fixture_position = i
                distance_from_wave = fixture_position - wave_position

                if 0 <= distance_from_wave < wave_size:
                    center_position = wave_size / 2
                    distance_from_center = abs(distance_from_wave - center_position)
                    intensity_factor = 1.0 - (distance_from_center / center_position) if center_position > 0 else 1.0
                    fixture_intensity = int(intensity * intensity_factor)
                else:
                    fixture_intensity = 0

                for channel in channels_dict['IntensityDimmer']:
                    channel_values.extend([str(channel['channel']), str(fixture_intensity)])
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
