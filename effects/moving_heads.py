import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing
import math


def focus_on_spot(start_step, fixture_def, mode_name, start_bpm, end_bpm, signature="4/4", transition="gradual",
                  num_bars=1, speed="1", color=None, fixture_conf=None, fixture_start_id=0, intensity=200, spot=None):
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
        fixture_conf: List of fixture configurations with fixture coordinates
        fixture_start_id: starting ID for the fixture to properly assign values
        intensity: Maximum intensity value for channels (0-255)
        spot: Class containing target spot coordinates (x, y)
    """
    if not spot:
        return []

    # Convert num_bars to integer
    num_bars = int(num_bars)

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

    # Get the fixture count from fixture_conf if available
    fixture_num = len(fixture_conf) if fixture_conf else 1
    step.set("Values", str(total_channels * fixture_num))

    # Build values string for all fixtures
    values = []
    for i in range(fixture_num):
        channel_values = []

        # Get fixture from fixture_conf
        fixture = fixture_conf[i] if i < len(fixture_conf) else None

        if fixture:
            # Configuration for fixture movement ranges
            pan_range = 540  # Total pan range in degrees (typical moving head)
            tilt_range = 190  # Total tilt range in degrees (as specified in your code)

            # Derive half-ranges for calculations
            half_pan_range = pan_range / 2
            half_tilt_range = tilt_range / 2

            # Get fixture position and direction from fixture object attributes
            fx = fixture.x
            fy = fixture.y
            fz = fixture.z
            rotation = fixture.rotation
            direction = fixture.direction.upper()

            # Calculate vector from fixture to spot
            dx = spot.x - fx
            dy = spot.y - fy
            dz = 0 - fz  # Stage level is typically at z=0

            # Calculate the horizontal angle in the XY plane (pan)
            pan_angle_rad = math.atan2(dy, dx)
            pan_angle_deg = math.degrees(pan_angle_rad)

            # Convert mathematical angle to stage orientation where 0° is forward (facing positive y)
            pan_angle_deg = (pan_angle_deg - 90) % 360

            # Adjust for fixture rotation (orientation on stage)
            pan_angle_deg = (pan_angle_deg - rotation) % 360

            # Adjust pan direction based on fixture mounting
            if direction == 'DOWN':
                # Invert pan direction for DOWN fixtures
                pan_angle_deg = (360 - pan_angle_deg) % 360

            # Calculate distance in XY plane
            distance_xy = math.sqrt(dx * dx + dy * dy)

            # Calculate tilt angle (vertical angle)
            tilt_angle_rad = math.atan2(dz, distance_xy)
            tilt_angle_deg = math.degrees(tilt_angle_rad)

            # Adjust tilt angle based on fixture mounting direction
            if direction == 'UP':
                tilt_dmx_angle = 90 - tilt_angle_deg
            else:  # DOWN fixtures
                tilt_dmx_angle = 90 + tilt_angle_deg

            # Pan angle optimization - center the range around middle DMX value
            # Normalize the angle to be between -half_pan_range and +half_pan_range (centered around 0°)
            if pan_angle_deg > half_pan_range:
                pan_angle_deg -= 360

            # Map the range from -half_pan_range to +half_pan_range to DMX 0-255
            # Where DMX 127/128 corresponds to 0°
            pan_dmx = int((pan_angle_deg + half_pan_range) * 255 / pan_range)

            # Tilt DMX calculation
            # Map the fixture-specific angle (0-tilt_range) to DMX (0-255)
            tilt_dmx_angle = max(0, min(tilt_range, tilt_dmx_angle))
            tilt_dmx = int(tilt_dmx_angle * 255 / tilt_range)

            # Ensure values are within DMX range
            pan_dmx = max(0, min(255, pan_dmx))
            tilt_dmx = max(0, min(255, tilt_dmx))

            # Add diagnostic info
            print(f"Fixture at ({fx},{fy},{fz}), spot at ({spot.x},{spot.y},0)")
            print(f"Direction: {direction}, Rotation: {rotation}°")
            print(f"Pan angle: {pan_angle_deg}°, Raw tilt angle: {tilt_angle_deg}°")
            print(f"Adjusted tilt angle for fixture: {tilt_dmx_angle}°")
            print(f"DMX values: Pan={pan_dmx}, Tilt={tilt_dmx}")

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


