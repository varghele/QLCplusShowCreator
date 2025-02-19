import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing
import math


def focus_on_spot(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                  num_bars=1, speed="1", color=None, fixture_num=1, fixture_start_id=0, intensity=200, spot=None):
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
        color: Color value (not used for focus effect)
        fixture_num: Number of fixtures of this type
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Dictionary containing target spot coordinates (x, y)
    """
    if not spot:
        return []

    channels_dict = get_channels_by_property(fixture_def, mode_name, ["PositionPan", "PositionTilt"])
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
    step.set("FadeIn", str(total_duration))
    step.set("Hold", "0")
    step.set("FadeOut", "0")
    step.set("Values", str(total_channels * fixture_num))

    # Build values string for all fixtures
    values = []
    for i in range(fixture_num):
        channel_values = []
        fixture = fixture_def.get('fixtures', [])[i] if i < len(fixture_def.get('fixtures', [])) else None

        if fixture:
            # Get fixture position and direction
            fx = fixture.get('x', 0)
            fy = fixture.get('y', 0)
            fz = fixture.get('z', 0)
            rotation = fixture.get('rotation', 0)
            direction = fixture.get('direction', 'up')

            # Calculate angles to spot
            dx = spot['x'] - fx
            dy = spot['y'] - fy
            dz = -fz  # Spot's z is 0

            # Calculate pan angle (horizontal rotation)
            pan_angle = math.degrees(math.atan2(dy, dx))
            # Adjust pan angle based on fixture rotation
            pan_angle = (pan_angle - rotation) % 360

            # Calculate tilt angle (vertical angle)
            distance_xy = math.sqrt(dx * dx + dy * dy)
            tilt_angle = math.degrees(math.atan2(dz, distance_xy))
            # Invert tilt angle if fixture is hanging (direction == 'down')
            if direction == 'down':
                tilt_angle = -tilt_angle

            # Convert angles to DMX values (assuming 540° pan and 270° tilt range)
            pan_dmx = int((pan_angle + 270) * 255 / 540)  # Center at 270°
            tilt_dmx = int((tilt_angle + 135) * 255 / 270)  # Center at 135°

            # Ensure values are within DMX range
            pan_dmx = max(0, min(255, pan_dmx))
            tilt_dmx = max(0, min(255, tilt_dmx))

            # Add pan/tilt values to channels
            if 'PositionPan' in channels_dict:
                for channel in channels_dict['PositionPan']:
                    channel_values.extend([str(channel['channel']), str(pan_dmx)])

            if 'PositionTilt' in channels_dict:
                for channel in channels_dict['PositionTilt']:
                    channel_values.extend([str(channel['channel']), str(tilt_dmx)])

        values.append(f"{fixture_start_id + i}:{','.join(channel_values)}")

    step.text = ":".join(values)
    return [step]
