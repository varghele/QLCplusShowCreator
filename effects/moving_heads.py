import numpy as np
from utils.effects_utils import get_channels_by_property
import xml.etree.ElementTree as ET
from utils.to_xml.shows_to_xml import calculate_step_timing
import math


def find_closest_color_dmx(channels_dict, hex_color, fixture_def=None):
    """
    Find the closest color match in the fixture's ColorMacro channel

    Parameters:
        channels_dict: Dictionary of channels by property
        hex_color: Target color as hex string (e.g. "#FF0000")
        fixture_def: Full fixture definition to search if colors not in channels_dict
    Returns:
        int: DMX value for the closest matching color
    """
    if not hex_color:
        return None

    # Remove '#' if present and normalize
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    hex_color = hex_color.upper()

    # Convert the target hex color to RGB
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except (ValueError, IndexError):
        return None

    # Find all color capabilities across all relevant channels
    color_capabilities = []

    # First check ColorMacro channels from channels_dict
    if 'ColorMacro' in channels_dict:
        for channel in channels_dict['ColorMacro']:
            for capability in channel.get('capabilities', []):
                if 'color' in capability and capability['color']:
                    color_capabilities.append(capability)

    # If no colors found in ColorMacro, search through all channels in fixture_def
    if not color_capabilities and fixture_def:
        for channel in fixture_def.get('channels', []):
            # Look for any channel in the Color group or with color capabilities
            if channel.get('group') == 'Colour' or channel.get('name') == 'Color':
                for capability in channel.get('capabilities', []):
                    if 'color' in capability:
                        color_capabilities.append(capability)

    # If still no colors found, try searching all channels for any color information
    if not color_capabilities and fixture_def:
        for channel in fixture_def.get('channels', []):
            for capability in channel.get('capabilities', []):
                if 'color' in capability:
                    color_capabilities.append(capability)

    # Find the closest color match
    best_match = None
    min_distance = float('inf')

    for capability in color_capabilities:
        color_val = capability.get('color', '')

        # Skip SVG files and non-hex values
        if color_val.endswith('.svg') or not color_val.startswith('#'):
            continue

        # Remove '#' if present
        if color_val.startswith('#'):
            color_val = color_val[1:]

        # Convert fixture color to RGB
        try:
            c_r = int(color_val[0:2], 16)
            c_g = int(color_val[2:4], 16)
            c_b = int(color_val[4:6], 16)
        except (ValueError, IndexError):
            continue

        # Calculate color distance (Euclidean distance in RGB space)
        distance = ((r - c_r) ** 2 + (g - c_g) ** 2 + (b - c_b) ** 2) ** 0.5

        if distance < min_distance:
            min_distance = distance
            # Get the middle of the DMX range for this color
            dmx_value = (int(capability['min']) + int(capability['max'])) // 2
            best_match = dmx_value
            print(f"Found color match: {capability.get('name')} (distance: {distance:.2f}) - DMX: {dmx_value}")

    return best_match


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
    step.set("FadeIn", str(total_duration))
    step.set("Hold", "0")
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
            tilt_range = 190  # Total tilt range in degrees (as specified in your code)

            # Derive half-ranges for calculations
            half_pan_range = pan_range / 2

            # Get fixture position and direction from fixture object attributes
            fx = fixture.x
            fy = fixture.y
            fz = fixture.z
            rotation = fixture.rotation + 90 # Fix, since code seemingly has rotated the fixtures by 90 deg
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

            # Print raw calculated angles for debugging
            print(f"Raw calculated tilt angle: {tilt_angle_deg}°")

            # CORRECTED TILT CALCULATION
            # For moving heads:
            # 0 DMX = beam points horizontal
            # 50% DMX (127/128) = beam points up (for UP fixtures) or down (for DOWN fixtures)
            # 100% DMX (255) = beam at maximum tilt position
            if direction == 'UP':
                # For UP fixtures:
                # Map the tilt angle where 0° = horizontal, positive = up
                # to DMX where 0 = horizontal, 127/128 = 90° up
                if tilt_angle_deg >= 0:
                    # Positive angles (pointing up)
                    tilt_dmx = int(tilt_angle_deg * 127 / 90)  # Map 0-90° to 0-127
                else:
                    # Negative angles (pointing down)
                    tilt_dmx = 0  # Keep at horizontal for negative angles
            else:  # DOWN fixtures
                # For DOWN fixtures:
                # Map the tilt angle where 0° = horizontal, positive = up
                # to DMX where 0 = horizontal, 127/128 = 90° down
                if tilt_angle_deg <= 0:
                    # Negative angles (pointing down from horizontal)
                    tilt_dmx = int(abs(tilt_angle_deg) * 127 / 90)  # Map 0-90° to 0-127
                else:
                    # Positive angles (pointing up)
                    tilt_dmx = 0  # Keep at horizontal for positive angles

            # Pan angle optimization - center the range around middle DMX value
            if pan_angle_deg > half_pan_range:
                pan_angle_deg -= 360

            # Map the range from -half_pan_range to +half_pan_range to DMX 0-255
            pan_dmx = int((pan_angle_deg + half_pan_range) * 255 / pan_range)

            # Ensure values are within DMX range
            pan_dmx = max(0, min(255, pan_dmx))
            tilt_dmx = max(0, min(255, tilt_dmx))

            # Add diagnostic info
            print(f"Fixture at ({fx},{fy},{fz}), spot at ({spot.x},{spot.y},0)")
            print(f"Direction: {direction}, Rotation: {rotation}°")
            print(f"Pan angle: {pan_angle_deg}°, Raw tilt angle: {tilt_angle_deg}°")
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
    return [step]


