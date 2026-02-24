import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing
import math
from utils.effects_utils import find_closest_color_dmx, find_gobo_dmx_value, find_gobo_rotation_value, add_reset_step
from utils.orientation import calculate_pan_tilt, pan_tilt_to_dmx
import random


def focus_on_spot(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                  num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None,
                  auto_reset=True):
    """
    Creates a focus effect that points moving heads towards a specific spot
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
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Class containing target spot coordinates (x, y)
        auto_reset: Automatically add a reset step at the end
    """
    if not spot:
        return []

    # Convert num_bars to integer
    num_bars = int(num_bars)

    channels_dict = get_channels_by_property(fixture_def, mode_name, ["PositionPan", "PositionTilt",
                                                                      "IntensityMasterDimmer", "ColorMacro"])
    if not channels_dict:
        return []

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
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Create single step with full duration
    total_duration = sum(step_timings)
    step = ET.Element("Step")
    step.set("Number", str(start_step))
    step.set("FadeIn", "0")
    step.set("Hold", str(total_duration - 1)) # -1 because of the rest step
    step.set("FadeOut", "0")

    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1
    step.set("Values", str(total_channels * fixture_num))

    # Find closest color DMX value if a color is provided
    color_dmx_value = find_closest_color_dmx(channels_dict, color, fixture_def) if color else None

    # Build values string for all fixtures
    values = []
    for i in range(fixture_num):
        channel_values = []

        # Get fixture from fixture_conf
        fixture = fixture_conf[i] if i < len(fixture_conf) else None

        if fixture:
            # Configuration for fixture movement ranges
            pan_range = 540  # Total pan range in degrees (typical moving head)
            tilt_range = 270  # Total tilt range in degrees (typical moving head)

            # Calculate pan/tilt using proper 3D orientation math
            # This uses the same rotation matrices as the visualizer
            pan_degrees, tilt_degrees = calculate_pan_tilt(
                fixture.x, fixture.y, fixture.z,
                spot.x, spot.y, 0,
                fixture.mounting, fixture.yaw, fixture.pitch, fixture.roll,
                pan_range=pan_range, tilt_range=tilt_range
            )
            pan_dmx, tilt_dmx = pan_tilt_to_dmx(
                pan_degrees, tilt_degrees, pan_range, tilt_range
            )

            print(f"Fixture at ({fixture.x},{fixture.y},{fixture.z}), spot at ({spot.x},{spot.y},0)")
            print(f"Pan: {pan_degrees:.1f}°, Tilt: {tilt_degrees:.1f}°")
            print(f"DMX values: Pan={pan_dmx}, Tilt={tilt_dmx}")

            # Add pan/tilt values to channels
            if 'PositionPan' in channels_dict:
                for channel in channels_dict['PositionPan']:
                    channel_values.extend([str(channel['channel']), str(pan_dmx)])

            if 'PositionTilt' in channels_dict:
                for channel in channels_dict['PositionTilt']:
                    channel_values.extend([str(channel['channel']), str(tilt_dmx)])

            # Add intensity values to master dimmer channel
            if 'IntensityMasterDimmer' in channels_dict:
                for channel in channels_dict['IntensityMasterDimmer']:
                    # Use the intensity parameter passed to the function
                    intensity_val = min(255, max(0, intensity))  # Ensure within DMX range
                    channel_values.extend([str(channel['channel']), str(intensity_val)])

            # Add color values if available
            if color_dmx_value is not None and 'ColorMacro' in channels_dict:
                for channel in channels_dict['ColorMacro']:
                    channel_values.extend([str(channel['channel']), str(color_dmx_value)])

        values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

    step.text = ":".join(values)
    # Add a reset step because of LTP behaviour of MHs
    steps = [step]
    if auto_reset:
        reset_step = add_reset_step(
            fixture_def,
            mode_name,
            fixture_conf,
            fixture_start_id,
            start_step + 1  # Next step number
        )
        if reset_step is not None:
            steps.append(reset_step)
    return steps


def whirl(start_step, fixture_def, mode_name, start_bpm, end_bpm=None, signature="4/4",
                        transition="gradual",
                        num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200,
                        gobo_index=1, rotation_speed="slow", rotation_direction="cw", tilt_angle=-10, spot=None,
                        auto_reset=True):
    """
    Creates a whirl effect that makes moving heads display a rotating gobo pointed toward the audience
    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition
        mode_name: Name of the mode to use
        start_bpm: Starting BPM
        end_bpm: Ending BPM (defaults to start_bpm if None)
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Hex color code (e.g. "#FF0000" for red)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        gobo_index: Index of gobo to use (typically 1-8)
        rotation_speed: "slow", "medium", or "fast"
        rotation_direction: "cw" for clockwise or "ccw" for counterclockwise
        tilt_angle: Slight downward angle for the beam in degrees
        spot: Spot object (unused in this effect)
        auto_reset: Automatically add a reset step at the end
    """
    # Set end_bpm to start_bpm if not provided
    if end_bpm is None:
        end_bpm = start_bpm

    # Convert num_bars to integer
    num_bars = int(num_bars)

    # Get channels for pan/tilt, color, intensity, gobo selection and gobo rotation
    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                             ["PositionPan", "PositionTilt", "IntensityMasterDimmer",
                                              "ColorMacro", "GoboMacro", "GoboWheel"])
    if not channels_dict:
        return []

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
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Create single step with full duration
    total_duration = sum(step_timings)
    step = ET.Element("Step")
    step.set("Number", str(start_step))
    step.set("FadeIn", "0")
    step.set("Hold", str(total_duration - 1)) # -1 because of the reset step
    step.set("FadeOut", "0")

    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1
    step.set("Values", str(total_channels * fixture_num))

    # Find closest color DMX value if a color is provided
    color_dmx_value = find_closest_color_dmx(channels_dict, color, fixture_def) if color else None

    # Find the right DMX value for the selected gobo
    gobo_dmx_value = find_gobo_dmx_value(channels_dict, gobo_index, fixture_def)

    # Find gobo rotation channel and suitable value based on direction and speed
    rotation_dmx_value = find_gobo_rotation_value(fixture_def, rotation_direction, rotation_speed)

    # Build values string for all fixtures
    values = []
    for i in range(fixture_num):
        channel_values = []

        # Get fixture from fixture_conf
        fixture = fixture_conf[i] if i < len(fixture_conf) else None

        if fixture:
            # Pan centered, tilt at specified angle (center-based DMX: 127 = 0°)
            pan_dmx, tilt_dmx = pan_tilt_to_dmx(0, tilt_angle)

            # Add pan/tilt values to channels
            if 'PositionPan' in channels_dict:
                for channel in channels_dict['PositionPan']:
                    channel_values.extend([str(channel['channel']), str(pan_dmx)])

            if 'PositionTilt' in channels_dict:
                for channel in channels_dict['PositionTilt']:
                    channel_values.extend([str(channel['channel']), str(tilt_dmx)])

            # Add intensity values to master dimmer channel
            if 'IntensityMasterDimmer' in channels_dict:
                for channel in channels_dict['IntensityMasterDimmer']:
                    intensity_val = min(255, max(0, intensity))  # Ensure within DMX range
                    channel_values.extend([str(channel['channel']), str(intensity_val)])

            # Add color values if available
            if color_dmx_value is not None and 'ColorMacro' in channels_dict:
                for channel in channels_dict['ColorMacro']:
                    channel_values.extend([str(channel['channel']), str(color_dmx_value)])

            # Add gobo selection if available
            if gobo_dmx_value is not None:
                # Find the right channel for gobos
                for channel_type in ['GoboMacro', 'GoboWheel']:
                    if channel_type in channels_dict:
                        for channel in channels_dict[channel_type]:
                            channel_values.extend([str(channel['channel']), str(gobo_dmx_value)])
                            break

            # Add gobo rotation if available
            if rotation_dmx_value:
                channel_num, dmx_value = rotation_dmx_value
                channel_values.extend([str(channel_num), str(dmx_value)])

        values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

    step.text = ":".join(values)
    # Add a reset step because of LTP behaviour of MHs
    steps=[step]
    if auto_reset:
        reset_step = add_reset_step(
            fixture_def,
            mode_name,
            fixture_conf,
            fixture_start_id,
            start_step + 1  # Next step number
        )
        if reset_step is not None:
            steps.append(reset_step)
    return steps


def twinkle(start_step, fixture_def, mode_name, start_bpm, end_bpm=None, signature="4/4", transition="gradual",
            num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200,
            max_intensity=255, min_intensity=30, twinkle_density=0.7, auto_reset=True, spot=None):
    """
    Creates a twinkling stars effect with moving heads

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition
        mode_name: Name of the mode to use
        start_bpm: Starting BPM
        end_bpm: Ending BPM (defaults to start_bpm if None)
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Hex color code (e.g. "#FFFFFF" for white stars)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: Starting ID for the fixture to properly assign values
        intensity: Base intensity value for channels (0-255)
        max_intensity: Maximum intensity for brightest stars
        min_intensity: Minimum intensity for dimmest stars
        twinkle_density: Probability of a fixture "twinkling" (0.0-1.0)
        auto_reset: Automatically add a reset step at the end
        spot: Spot object (unused in this effect)
    """
    # Set end_bpm to start_bpm if not provided
    if end_bpm is None:
        end_bpm = start_bpm

    # Convert num_bars to integer
    num_bars = int(num_bars)

    # Get required channels
    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                             ["PositionPan", "PositionTilt", "IntensityMasterDimmer",
                                              "ColorMacro", "Shutter"])
    if not channels_dict:
        return []

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    # Find closest color DMX value if a color is provided (white is ideal for stars)
    color_dmx_value = find_closest_color_dmx(channels_dict, color or "#FFFFFF", fixture_def)

    # Define the tilt range for the stars to appear in the "sky"
    # Upward angles work best for a starfield effect
    min_tilt = 30  # Minimum angle upward
    max_tilt = 80  # Maximum angle upward (nearly vertical)

    # Generate multiple steps for the twinkling effect
    # Each step will have a different random pattern of lit fixtures
    steps = []
    twinkle_steps = min(8, max(4, int(total_steps / 2)))  # Number of twinkle variations
    step_duration = total_duration = int(sum(step_timings) / twinkle_steps)

    # For each twinkle step
    for step_idx in range(twinkle_steps):
        # Create a new step
        step = ET.Element("Step")
        step.set("Number", str(start_step + step_idx))
        step.set("FadeIn", "0")  # Fast fade in for twinkling effect
        step.set("Hold", str(step_duration))
        step.set("FadeOut", "0")

        # Count total channels
        total_channels = 0
        for preset, channels in channels_dict.items():
            if isinstance(channels, list):
                total_channels += len(channels)

        step.set("Values", str(total_channels * fixture_num))

        # Build values string for all fixtures with random positions
        values = []
        for i in range(fixture_num):
            channel_values = []

            # Get fixture from fixture_conf
            fixture = fixture_conf[i] if i < len(fixture_conf) else None

            if fixture:
                # Randomly decide if this fixture twinkles in this step
                twinkle_active = random.random() < twinkle_density

                # Only create star positions for active fixtures
                if twinkle_active:
                    # Generate random pan/tilt angles for a star-like position
                    pan_angle = random.uniform(-270, 270)  # Full pan range in degrees
                    tilt_angle = random.uniform(min_tilt, max_tilt)  # Upward angle for stars

                    # Convert to center-based DMX (127 = 0°)
                    pan_dmx, tilt_dmx = pan_tilt_to_dmx(pan_angle, tilt_angle)

                    # Random intensity for twinkling effect
                    fixture_intensity = random.randint(min_intensity, max_intensity) if twinkle_active else 0
                else:
                    # Keep the fixture off for this step
                    pan_dmx = 0
                    tilt_dmx = 0
                    fixture_intensity = 0

                # Add pan/tilt values to channels
                if 'PositionPan' in channels_dict:
                    for channel in channels_dict['PositionPan']:
                        channel_values.extend([str(channel['channel']), str(pan_dmx)])

                if 'PositionTilt' in channels_dict:
                    for channel in channels_dict['PositionTilt']:
                        channel_values.extend([str(channel['channel']), str(tilt_dmx)])

                # Add intensity values to master dimmer channel
                if 'IntensityMasterDimmer' in channels_dict:
                    for channel in channels_dict['IntensityMasterDimmer']:
                        channel_values.extend([str(channel['channel']), str(fixture_intensity)])

                # Add color values if available
                if color_dmx_value is not None and 'ColorMacro' in channels_dict:
                    for channel in channels_dict['ColorMacro']:
                        channel_values.extend([str(channel['channel']), str(color_dmx_value)])

                # Add shutter values if available (open)
                if 'Shutter' in channels_dict:
                    for channel in channels_dict['Shutter']:
                        channel_values.extend([str(channel['channel']), "255"])  # Open shutter

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)

    # Add a reset step if auto_reset is enabled
    if auto_reset:
        reset_step = add_reset_step(
            fixture_def,
            mode_name,
            fixture_conf,
            fixture_start_id,
            start_step + twinkle_steps
        )
        if reset_step is not None:
            steps.append(reset_step)

    return steps


def wave_sweep(start_step, fixture_def, mode_name, start_bpm, end_bpm=None, signature="4/4", transition="gradual",
               num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200,
               wave_direction="horizontal", wave_height=60, cycles=2, auto_reset=True, spot=None):
    """
    Creates a wave-like motion effect across multiple moving head fixtures

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition
        mode_name: Name of the mode to use
        start_bpm: Starting BPM
        end_bpm: Ending BPM (defaults to start_bpm if None)
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Hex color code (e.g. "#0000FF" for blue)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: Starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        wave_direction: Direction of wave sweep ("horizontal" or "vertical")
        wave_height: Height/amplitude of the wave in degrees
        cycles: Number of complete wave cycles to perform
        auto_reset: Automatically add a reset step at the end
        spot: Spot object (unused in this effect)
    """
    # Set end_bpm to start_bpm if not provided
    if end_bpm is None:
        end_bpm = start_bpm

    # Convert num_bars to integer
    num_bars = int(num_bars)

    # Get required channels
    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                             ["PositionPan", "PositionTilt", "IntensityMasterDimmer",
                                              "ColorMacro", "Shutter"])
    if not channels_dict:
        return []

    # Get step timings
    step_timings, total_steps = calculate_step_timing(
        signature=signature,
        start_bpm=start_bpm,
        end_bpm=end_bpm,
        num_bars=num_bars,
        speed=speed,
        transition=transition
    )

    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    # Find closest color DMX value if a color is provided
    color_dmx_value = find_closest_color_dmx(channels_dict, color, fixture_def) if color else None

    # Sort fixtures based on position for wave effect
    # For horizontal waves, sort by X coordinate
    # For vertical waves, sort by Y coordinate
    if fixture_conf:
        if wave_direction == "horizontal":
            sorted_fixtures = sorted(fixture_conf, key=lambda f: f.x)
        else:  # vertical
            sorted_fixtures = sorted(fixture_conf, key=lambda f: f.y)
    else:
        sorted_fixtures = fixture_conf

    # Number of steps to create for the wave animation
    wave_steps = min(24, max(12, int(total_steps)))  # Number of frames in the wave animation
    step_duration = total_duration = int(sum(step_timings) / wave_steps)

    # Create steps for the wave animation
    steps = []
    for step_idx in range(wave_steps):
        # Create a new step
        step = ET.Element("Step")
        step.set("Number", str(start_step + step_idx))
        step.set("FadeIn", str(step_duration // 2))  # Smooth transitions
        step.set("Hold", str(step_duration // 2))
        step.set("FadeOut", "0")

        # Count total channels
        total_channels = 0
        for preset, channels in channels_dict.items():
            if isinstance(channels, list):
                total_channels += len(channels)

        step.set("Values", str(total_channels * fixture_num))

        # Build values string for all fixtures
        values = []
        for i, fixture in enumerate(sorted_fixtures):
            channel_values = []

            if fixture:
                # Calculate the fixture's position in the wave sequence
                if wave_direction == "horizontal":
                    position_ratio = i / max(1, len(sorted_fixtures) - 1)  # 0.0 to 1.0
                else:  # vertical
                    position_ratio = i / max(1, len(sorted_fixtures) - 1)  # 0.0 to 1.0

                # Calculate wave phase for this fixture at this step
                # The phase combines the fixture's position and the current step
                phase = 2 * math.pi * (position_ratio + (step_idx / wave_steps) * cycles)

                # Calculate pan/tilt angles in degrees (0° = center)
                if wave_direction == "horizontal":
                    # Horizontal waves: pan centered, tilt sweeps
                    pan_degrees = 0
                    tilt_offset = wave_height * math.sin(phase)
                    tilt_degrees = 40 + tilt_offset  # Base 40° + wave offset
                else:
                    # Vertical waves: pan sweeps, tilt fixed
                    pan_degrees = wave_height * math.sin(phase)
                    tilt_degrees = 40  # Fixed 40° tilt

                # Convert to center-based DMX (127 = 0°)
                pan_dmx, tilt_dmx = pan_tilt_to_dmx(pan_degrees, tilt_degrees)

                # Add pan/tilt values to channels
                if 'PositionPan' in channels_dict:
                    for channel in channels_dict['PositionPan']:
                        channel_values.extend([str(channel['channel']), str(pan_dmx)])

                if 'PositionTilt' in channels_dict:
                    for channel in channels_dict['PositionTilt']:
                        channel_values.extend([str(channel['channel']), str(tilt_dmx)])

                # Add intensity values to master dimmer channel
                if 'IntensityMasterDimmer' in channels_dict:
                    for channel in channels_dict['IntensityMasterDimmer']:
                        # Use the intensity parameter passed to the function
                        intensity_val = min(255, max(0, intensity))
                        channel_values.extend([str(channel['channel']), str(intensity_val)])

                # Add color values if available
                if color_dmx_value is not None and 'ColorMacro' in channels_dict:
                    for channel in channels_dict['ColorMacro']:
                        channel_values.extend([str(channel['channel']), str(color_dmx_value)])

                # Add shutter values if available (open)
                if 'Shutter' in channels_dict:
                    for channel in channels_dict['Shutter']:
                        channel_values.extend([str(channel['channel']), "255"])  # Open shutter

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)

    # Add a reset step if auto_reset is enabled
    if auto_reset:
        reset_step = add_reset_step(
            fixture_def,
            mode_name,
            fixture_conf,
            fixture_start_id,
            start_step + wave_steps
        )
        if reset_step is not None:
            steps.append(reset_step)

    return steps


def wave_sweep_fig8(start_step, fixture_def, mode_name, start_bpm, end_bpm=None, signature="4/4",
                    transition="gradual", num_bars=1, speed="1", color=None, fixture_conf=None,
                    fixture_start_id=0, intensity=200, spot=None, gobo_index=1, tilt_angle=-10, base_pan_angle=0,
                    wave_size=20, wave_offset=0.25, auto_reset=True):
    """
    Creates a wave sweep effect with moving heads performing figure-8 patterns in the air

    Parameters:
        start_step: Starting step number
        fixture_def: Dictionary containing fixture definition
        mode_name: Name of the mode to use
        start_bpm: Starting BPM
        end_bpm: Ending BPM (defaults to start_bpm if None)
        signature: Time signature as string (e.g. "4/4")
        transition: Type of transition ("instant" or "gradual")
        num_bars: Number of bars to fill
        speed: Speed multiplier ("1/4", "1/2", "1", "2", "4" etc)
        color: Hex color code (e.g. "#FF0000" for red)
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Spot object (unused in this effect)
        gobo_index: Index of gobo to use (typically 1-8)
        tilt_angle: Base downward angle for the beam in degrees
        base_pan_angle: Center pan angle (0 = front, -20 = slight left, 20 = slight right)
        wave_size: Size of the figure-8 pattern (higher = bigger movement)
        wave_offset: Offset between fixtures (0-1, higher = more asynchronous)
        auto_reset: Automatically add a reset step at the end
    """
    # Set end_bpm to start_bpm if not provided
    if end_bpm is None:
        end_bpm = start_bpm

    # Convert num_bars to integer
    num_bars = int(num_bars)

    # Get channels for pan/tilt, color, intensity, gobo selection
    channels_dict = get_channels_by_property(fixture_def, mode_name,
                                             ["PositionPan", "PositionTilt", "IntensityMasterDimmer",
                                              "ColorMacro", "GoboMacro", "GoboWheel"])
    if not channels_dict:
        return []

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
    total_channels = 0
    for preset, channels in channels_dict.items():
        if isinstance(channels, list):
            total_channels += len(channels)

    # Find closest color DMX value if a color is provided
    color_dmx_value = find_closest_color_dmx(channels_dict, color, fixture_def) if color else None

    # Find the right DMX value for the selected gobo
    gobo_dmx_value = find_gobo_dmx_value(channels_dict, gobo_index, fixture_def)

    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1

    # Create steps for the wave sweep animation
    steps = []
    current_step = start_step

    # Create one step per step timing to match other effects
    for step_idx, step_duration in enumerate(step_timings):
        # Calculate animation progress for this step (0.0 to 1.0)
        progress = step_idx / max(1, len(step_timings) - 1)

        # Create new step
        step = ET.Element("Step")
        step.set("Number", str(current_step))
        step.set("FadeIn", str(step_duration))  # Use full step duration
        step.set("Hold", "0")
        step.set("FadeOut", "0")
        step.set("Values", str(total_channels * fixture_num))

        # Build values string for all fixtures
        values = []
        for i in range(fixture_num):
            channel_values = []

            # Get fixture from fixture_conf
            fixture = fixture_conf[i] if i < len(fixture_conf) else None

            if fixture:
                # Create unique phase offset for each fixture to make them asynchronous
                fixture_offset = (i * wave_offset) % 1.0

                # Calculate the figure-8 pattern
                # Basic figure-8 uses sin(t) for horizontal and sin(2t) for vertical
                phase = 2 * math.pi * (progress + fixture_offset)

                # Calculate pan and tilt offsets using Lissajous figure (figure-8)
                pan_offset = math.sin(phase) * wave_size
                tilt_offset = math.sin(2 * phase) * (wave_size * 0.5)  # Half amplitude for tilt

                # Calculate angles in degrees (0° = center) and convert to DMX
                pan_degrees = base_pan_angle + pan_offset
                tilt_degrees = tilt_angle + tilt_offset
                pan_dmx, tilt_dmx = pan_tilt_to_dmx(pan_degrees, tilt_degrees)

                # Add pan/tilt values to channels
                if 'PositionPan' in channels_dict:
                    for channel in channels_dict['PositionPan']:
                        channel_values.extend([str(channel['channel']), str(pan_dmx)])

                if 'PositionTilt' in channels_dict:
                    for channel in channels_dict['PositionTilt']:
                        channel_values.extend([str(channel['channel']), str(tilt_dmx)])

                # Add intensity values to master dimmer channel
                if 'IntensityMasterDimmer' in channels_dict:
                    for channel in channels_dict['IntensityMasterDimmer']:
                        intensity_val = min(255, max(0, intensity))  # Ensure within DMX range
                        channel_values.extend([str(channel['channel']), str(intensity_val)])

                # Add color values if available
                if color_dmx_value is not None and 'ColorMacro' in channels_dict:
                    for channel in channels_dict['ColorMacro']:
                        channel_values.extend([str(channel['channel']), str(color_dmx_value)])

                # Add gobo selection if available
                if gobo_dmx_value is not None:
                    # Find the right channel for gobos
                    for channel_type in ['GoboMacro', 'GoboWheel']:
                        if channel_type in channels_dict:
                            for channel in channels_dict[channel_type]:
                                channel_values.extend([str(channel['channel']), str(gobo_dmx_value)])
                                break

            values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

        step.text = ":".join(values)
        steps.append(step)
        current_step += 1

    # Add a reset step if auto_reset is enabled
    if auto_reset:
        reset_step = add_reset_step(
            fixture_def,
            mode_name,
            fixture_conf,
            fixture_start_id,
            current_step  # Next step number after all animation steps
        )
        if reset_step is not None:
            steps.append(reset_step)

    return steps





