# utils/artnet/dmx_manager.py
# DMX state manager for real-time DMX output

import time
import math
from typing import Dict, List, Optional, Tuple
from config.models import Configuration, Fixture, LightBlock, DimmerBlock, ColourBlock, MovementBlock, SpecialBlock
from utils.effects_utils import get_channels_by_property


class FixtureChannelMap:
    """
    Maps a fixture's capabilities to its DMX channel addresses.

    Handles conversion from fixture universe/address to absolute DMX channels.
    """

    def __init__(self, fixture: Fixture, fixture_def: dict, config: Configuration):
        """
        Initialize fixture channel mapping.

        Args:
            fixture: Fixture instance
            fixture_def: Fixture definition from .qxf parsing
            config: Configuration containing universe settings
        """
        self.fixture = fixture
        self.fixture_def = fixture_def
        self.config = config

        # Get base DMX address (universe and channel)
        self.universe = fixture.universe
        self.base_address = fixture.address - 1  # DMX is 1-indexed, array is 0-indexed

        # Get channel mappings from fixture definition
        self.mode_name = fixture.current_mode
        self._build_channel_map()

    def _build_channel_map(self):
        """Build channel mapping from fixture definition."""
        # Query channels by property using effects_utils
        properties = [
            "IntensityMasterDimmer", "IntensityDimmer",
            "IntensityRed", "IntensityGreen", "IntensityBlue", "IntensityWhite",
            "IntensityAmber", "IntensityCyan", "IntensityMagenta", "IntensityYellow",
            "IntensityUV", "IntensityLime",
            "PositionPan", "PositionTilt", "PositionPanFine", "PositionTiltFine",
            "ColorWheel", "ColorMacro",
            "GoboWheel", "Gobo", "Gobo1", "Gobo2",
            "PrismRotation", "Prism",
            "BeamFocusNearFar", "BeamZoomSmallBig", "BeamIrisCloseOpen",
            "ShutterStrobeOpen", "ShutterStrobeFast", "ShutterStrobeRandom"
        ]

        channels_dict = get_channels_by_property(self.fixture_def, self.mode_name, properties)

        # Store channel mappings (property -> list of channel offsets)
        self.dimmer_channels = self._get_channel_offsets(channels_dict, ["IntensityMasterDimmer", "IntensityDimmer"])
        self.red_channels = self._get_channel_offsets(channels_dict, ["IntensityRed"])
        self.green_channels = self._get_channel_offsets(channels_dict, ["IntensityGreen"])
        self.blue_channels = self._get_channel_offsets(channels_dict, ["IntensityBlue"])
        self.white_channels = self._get_channel_offsets(channels_dict, ["IntensityWhite"])
        self.amber_channels = self._get_channel_offsets(channels_dict, ["IntensityAmber"])
        self.cyan_channels = self._get_channel_offsets(channels_dict, ["IntensityCyan"])
        self.magenta_channels = self._get_channel_offsets(channels_dict, ["IntensityMagenta"])
        self.yellow_channels = self._get_channel_offsets(channels_dict, ["IntensityYellow"])
        self.uv_channels = self._get_channel_offsets(channels_dict, ["IntensityUV"])
        self.lime_channels = self._get_channel_offsets(channels_dict, ["IntensityLime"])
        self.pan_channels = self._get_channel_offsets(channels_dict, ["PositionPan"])
        self.tilt_channels = self._get_channel_offsets(channels_dict, ["PositionTilt"])
        self.pan_fine_channels = self._get_channel_offsets(channels_dict, ["PositionPanFine"])
        self.tilt_fine_channels = self._get_channel_offsets(channels_dict, ["PositionTiltFine"])
        self.color_wheel_channels = self._get_channel_offsets(channels_dict, ["ColorWheel", "ColorMacro"])
        self.gobo_channels = self._get_channel_offsets(channels_dict, ["GoboWheel", "Gobo", "Gobo1"])
        self.prism_channels = self._get_channel_offsets(channels_dict, ["Prism"])
        self.focus_channels = self._get_channel_offsets(channels_dict, ["BeamFocusNearFar"])
        self.zoom_channels = self._get_channel_offsets(channels_dict, ["BeamZoomSmallBig"])
        self.strobe_channels = self._get_channel_offsets(channels_dict, ["ShutterStrobeOpen", "ShutterStrobeFast", "ShutterStrobeRandom"])

    def _get_channel_offsets(self, channels_dict: dict, properties: List[str]) -> List[int]:
        """
        Get channel offsets for given properties.

        Args:
            channels_dict: Dictionary from get_channels_by_property
            properties: List of property names to look for

        Returns:
            List of channel offsets (0-indexed)
        """
        offsets = []
        for prop in properties:
            if prop in channels_dict:
                for ch_info in channels_dict[prop]:
                    offsets.append(ch_info['channel'])
        return offsets

    def get_absolute_address(self, channel_offset: int) -> Tuple[int, int]:
        """
        Convert fixture-relative channel to absolute universe/channel.

        Args:
            channel_offset: Channel offset (0-indexed)

        Returns:
            (universe, channel) tuple
        """
        absolute_channel = self.base_address + channel_offset
        return (self.universe, absolute_channel)


class DMXManager:
    """
    Manages DMX state for all universes.

    Tracks active blocks and converts them to DMX values in real-time.
    Handles overlapping blocks with LTP (Latest Takes Priority).
    """

    def __init__(self, config: Configuration, fixture_definitions: dict, song_structure=None):
        """
        Initialize DMX manager.

        Args:
            config: Configuration with fixtures and universes
            fixture_definitions: Dictionary of parsed fixture definitions
            song_structure: Optional SongStructure for BPM-aware timing
        """
        self.config = config
        self.fixture_definitions = fixture_definitions
        self.song_structure = song_structure

        # DMX state - universe_id -> 512-byte array
        self.dmx_state: Dict[int, bytearray] = {}

        # Initialize universes from configuration
        for universe_id in config.universes.keys():
            self.dmx_state[universe_id] = bytearray(512)

        # Build fixture channel maps
        self.fixture_maps: Dict[str, FixtureChannelMap] = {}
        self._build_fixture_maps()

        # Track active blocks (LTP - Latest Takes Priority)
        # Dictionary: fixture_group -> {sublane_type -> (block, start_time)}
        self.active_blocks: Dict[str, Dict[str, Tuple[object, float]]] = {}

        print(f"DMX Manager initialized with {len(self.dmx_state)} universes")

    def set_song_structure(self, song_structure):
        """
        Set or update the song structure for BPM-aware calculations.

        Args:
            song_structure: SongStructure instance
        """
        self.song_structure = song_structure

    def _build_fixture_maps(self):
        """Build channel maps for all fixtures."""
        for fixture in self.config.fixtures:
            # Get fixture definition
            fixture_key = f"{fixture.manufacturer}_{fixture.model}"
            fixture_def = self.fixture_definitions.get(fixture_key)

            if fixture_def:
                self.fixture_maps[fixture.name] = FixtureChannelMap(fixture, fixture_def, self.config)
            else:
                print(f"Warning: No fixture definition found for {fixture.name} ({fixture_key})")

    def clear_all_dmx(self):
        """Clear all DMX values to 0."""
        for universe_id in self.dmx_state.keys():
            self.dmx_state[universe_id] = bytearray(512)

    def set_dmx_value(self, universe: int, channel: int, value: int):
        """
        Set a single DMX channel value.

        Args:
            universe: Universe ID
            channel: Channel number (0-511)
            value: DMX value (0-255)
        """
        if universe not in self.dmx_state:
            print(f"Warning: Universe {universe} not initialized")
            return

        if 0 <= channel < 512:
            self.dmx_state[universe][channel] = max(0, min(255, value))

    def get_dmx_data(self, universe: int) -> bytes:
        """
        Get DMX data for a universe.

        Args:
            universe: Universe ID

        Returns:
            512 bytes of DMX data
        """
        if universe not in self.dmx_state:
            return bytes(512)

        return bytes(self.dmx_state[universe])

    def block_started(self, fixture_group: str, block: object, block_type: str, current_time: float):
        """
        Called when a block starts playback.

        Args:
            fixture_group: Name of the fixture group
            block: Block instance (DimmerBlock, ColourBlock, etc.)
            block_type: Type of block ('dimmer', 'colour', 'movement', 'special')
            current_time: Current playback time in seconds
        """
        # Initialize group if needed
        if fixture_group not in self.active_blocks:
            self.active_blocks[fixture_group] = {}

        # Store block with start time (LTP)
        self.active_blocks[fixture_group][block_type] = (block, current_time)

    def block_ended(self, fixture_group: str, block_type: str):
        """
        Called when a block ends playback.

        Args:
            fixture_group: Name of the fixture group
            block_type: Type of block ('dimmer', 'colour', 'movement', 'special')
        """
        if fixture_group in self.active_blocks:
            if block_type in self.active_blocks[fixture_group]:
                del self.active_blocks[fixture_group][block_type]

    def update_dmx(self, current_time: float):
        """
        Update DMX state based on active blocks at current time.

        Args:
            current_time: Current playback time in seconds
        """
        # Clear DMX state
        self.clear_all_dmx()

        # Process each fixture group
        for group_name, group in self.config.groups.items():
            if group_name not in self.active_blocks:
                continue

            active = self.active_blocks[group_name]

            # Get active blocks for this group
            dimmer_block = None
            colour_block = None
            movement_block = None
            special_block = None

            if 'dimmer' in active:
                dimmer_block, _ = active['dimmer']
            if 'colour' in active:
                colour_block, _ = active['colour']
            if 'movement' in active:
                movement_block, _ = active['movement']
            if 'special' in active:
                special_block, _ = active['special']

            # Apply blocks to each fixture in the group
            for fixture in group.fixtures:
                if fixture.name not in self.fixture_maps:
                    continue

                fixture_map = self.fixture_maps[fixture.name]

                # Apply dimmer block
                if dimmer_block:
                    self._apply_dimmer_block(fixture_map, dimmer_block, current_time)

                # Apply colour block
                if colour_block:
                    self._apply_colour_block(fixture_map, colour_block, current_time)

                # Apply movement block
                if movement_block:
                    self._apply_movement_block(fixture_map, movement_block, current_time)

                # Apply special block
                if special_block:
                    self._apply_special_block(fixture_map, special_block, current_time)

    def _apply_dimmer_block(self, fixture_map: FixtureChannelMap, block: DimmerBlock, current_time: float):
        """Apply dimmer block to fixture channels."""
        # Calculate current intensity based on effect type
        intensity = block.intensity

        if block.effect_type == "strobe":
            # Strobe effect: alternate between intensity and 0
            # Calculate strobe frequency from effect_speed
            speed_multiplier = self._parse_speed(block.effect_speed)
            # Strobe at (2 * speed_multiplier) Hz
            strobe_hz = 2.0 * speed_multiplier
            # Calculate phase
            time_in_block = current_time - block.start_time
            phase = (time_in_block * strobe_hz) % 1.0
            # 50% duty cycle
            intensity = block.intensity if phase < 0.5 else 0

        elif block.effect_type == "twinkle":
            # Twinkle: random variation
            # Use time-based seed for smooth variation
            import random
            random.seed(int(current_time * 10))
            variation = random.random() * 0.3
            intensity = block.intensity * (0.7 + variation)

        # Set dimmer channels
        for ch_offset in fixture_map.dimmer_channels:
            universe, channel = fixture_map.get_absolute_address(ch_offset)
            self.set_dmx_value(universe, channel, int(intensity))

    def _apply_colour_block(self, fixture_map: FixtureChannelMap, block: ColourBlock, current_time: float):
        """Apply colour block to fixture channels."""
        # Set RGB/RGBW channels
        color_mapping = [
            (fixture_map.red_channels, block.red),
            (fixture_map.green_channels, block.green),
            (fixture_map.blue_channels, block.blue),
            (fixture_map.white_channels, block.white),
            (fixture_map.amber_channels, block.amber),
            (fixture_map.cyan_channels, block.cyan),
            (fixture_map.magenta_channels, block.magenta),
            (fixture_map.yellow_channels, block.yellow),
            (fixture_map.uv_channels, block.uv),
            (fixture_map.lime_channels, block.lime),
        ]

        for channels, value in color_mapping:
            for ch_offset in channels:
                universe, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, int(value))

        # Set color wheel if RGB not available
        if (not fixture_map.red_channels and
            not fixture_map.green_channels and
            not fixture_map.blue_channels and
            fixture_map.color_wheel_channels):
            # Map RGB to color wheel position
            wheel_value = self._rgb_to_color_wheel(block.red, block.green, block.blue)
            for ch_offset in fixture_map.color_wheel_channels:
                universe, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, wheel_value)

    def _apply_movement_block(self, fixture_map: FixtureChannelMap, block: MovementBlock, current_time: float):
        """Apply movement block to fixture channels with real-time shape calculation."""
        # Calculate current position based on effect type
        time_in_block = current_time - block.start_time
        block_duration = block.end_time - block.start_time

        # Get parameters
        effect_type = block.effect_type
        center_pan = block.pan
        center_tilt = block.tilt
        pan_amplitude = block.pan_amplitude
        tilt_amplitude = block.tilt_amplitude
        pan_min = block.pan_min
        pan_max = block.pan_max
        tilt_min = block.tilt_min
        tilt_max = block.tilt_max

        # Calculate speed multiplier
        speed_multiplier = self._parse_speed(block.effect_speed)

        # Get actual BPM from song structure if available
        if self.song_structure:
            bpm = self.song_structure.get_bpm_at_time(current_time)
        else:
            bpm = 120.0  # Fallback to default

        seconds_per_beat = 60.0 / bpm
        seconds_per_bar = seconds_per_beat * 4  # Assume 4/4 time
        total_cycles = (block_duration / seconds_per_bar) * speed_multiplier

        # Calculate t (angle in radians) and progress
        if block_duration > 0:
            progress = time_in_block / block_duration
        else:
            progress = 0
        t = 2 * math.pi * total_cycles * progress

        # Calculate pan/tilt based on effect type
        if effect_type == "static":
            pan = center_pan
            tilt = center_tilt

        elif effect_type == "circle":
            pan = center_pan + pan_amplitude * math.cos(t)
            tilt = center_tilt + tilt_amplitude * math.sin(t)

        elif effect_type == "diamond":
            # Diamond: 4 corners traversed linearly
            phase = progress * 4 * total_cycles
            corner = int(phase) % 4
            local_t = phase - int(phase)
            corners = [
                (center_pan, center_tilt - tilt_amplitude),          # Top
                (center_pan + pan_amplitude, center_tilt),           # Right
                (center_pan, center_tilt + tilt_amplitude),          # Bottom
                (center_pan - pan_amplitude, center_tilt),           # Left
            ]
            start = corners[corner]
            end = corners[(corner + 1) % 4]
            pan = start[0] + local_t * (end[0] - start[0])
            tilt = start[1] + local_t * (end[1] - start[1])

        elif effect_type == "square":
            # Square: 4 corners traversed linearly
            phase = progress * 4 * total_cycles
            corner = int(phase) % 4
            local_t = phase - int(phase)
            corners = [
                (center_pan - pan_amplitude, center_tilt - tilt_amplitude),  # Top-left
                (center_pan + pan_amplitude, center_tilt - tilt_amplitude),  # Top-right
                (center_pan + pan_amplitude, center_tilt + tilt_amplitude),  # Bottom-right
                (center_pan - pan_amplitude, center_tilt + tilt_amplitude),  # Bottom-left
            ]
            start = corners[corner]
            end = corners[(corner + 1) % 4]
            pan = start[0] + local_t * (end[0] - start[0])
            tilt = start[1] + local_t * (end[1] - start[1])

        elif effect_type == "triangle":
            # Triangle: 3 corners traversed linearly
            phase = progress * 3 * total_cycles
            corner = int(phase) % 3
            local_t = phase - int(phase)
            corners = [
                (center_pan, center_tilt - tilt_amplitude),                           # Top
                (center_pan + pan_amplitude * 0.866, center_tilt + tilt_amplitude * 0.5),  # Bottom-right
                (center_pan - pan_amplitude * 0.866, center_tilt + tilt_amplitude * 0.5),  # Bottom-left
            ]
            start = corners[corner]
            end = corners[(corner + 1) % 3]
            pan = start[0] + local_t * (end[0] - start[0])
            tilt = start[1] + local_t * (end[1] - start[1])

        elif effect_type == "figure_8":
            pan = center_pan + pan_amplitude * math.sin(t)
            tilt = center_tilt + tilt_amplitude * math.sin(2 * t)

        elif effect_type == "lissajous":
            # Parse ratio
            ratio_parts = block.lissajous_ratio.split(':')
            try:
                freq_pan = int(ratio_parts[0])
                freq_tilt = int(ratio_parts[1])
            except (ValueError, IndexError):
                freq_pan, freq_tilt = 1, 2
            pan = center_pan + pan_amplitude * math.sin(freq_pan * t)
            tilt = center_tilt + tilt_amplitude * math.sin(freq_tilt * t)

        elif effect_type == "random":
            # Pseudo-random smooth motion using multiple sine waves
            pan = center_pan + pan_amplitude * (
                0.5 * math.sin(3 * t) + 0.3 * math.sin(7 * t) + 0.2 * math.sin(11 * t)
            )
            tilt = center_tilt + tilt_amplitude * (
                0.5 * math.sin(5 * t) + 0.3 * math.sin(11 * t) + 0.2 * math.sin(13 * t)
            )

        elif effect_type == "bounce":
            # Bouncing pattern using triangle waves
            bounce_t = progress * 4 * total_cycles
            pan_t = abs((bounce_t % 2) - 1)
            tilt_t = abs(((bounce_t + 0.5) % 2) - 1)
            pan = center_pan - pan_amplitude + 2 * pan_amplitude * pan_t
            tilt = center_tilt - tilt_amplitude + 2 * tilt_amplitude * tilt_t

        else:
            # Default to static for unknown effect types
            pan = center_pan
            tilt = center_tilt

        # Apply clipping to boundaries
        pan = max(pan_min, min(pan_max, pan))
        tilt = max(tilt_min, min(tilt_max, tilt))

        # Set pan/tilt channels
        for ch_offset in fixture_map.pan_channels:
            universe, channel = fixture_map.get_absolute_address(ch_offset)
            self.set_dmx_value(universe, channel, int(pan))

        for ch_offset in fixture_map.tilt_channels:
            universe, channel = fixture_map.get_absolute_address(ch_offset)
            self.set_dmx_value(universe, channel, int(tilt))

    def _apply_special_block(self, fixture_map: FixtureChannelMap, block: SpecialBlock, current_time: float):
        """Apply special block to fixture channels."""
        # Set gobo
        if fixture_map.gobo_channels:
            # Map gobo_index to DMX value (simple linear mapping)
            gobo_value = min(255, block.gobo_index * 25)
            for ch_offset in fixture_map.gobo_channels:
                universe, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, gobo_value)

        # Set prism
        if fixture_map.prism_channels:
            prism_value = 128 if block.prism_enabled else 0
            for ch_offset in fixture_map.prism_channels:
                universe, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, prism_value)

        # Set focus
        if fixture_map.focus_channels:
            for ch_offset in fixture_map.focus_channels:
                universe, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, int(block.focus))

        # Set zoom
        if fixture_map.zoom_channels:
            for ch_offset in fixture_map.zoom_channels:
                universe, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, int(block.zoom))

    def _parse_speed(self, speed: str) -> float:
        """
        Parse speed string to multiplier.

        Args:
            speed: Speed string like "1", "2", "1/2", "1/4"

        Returns:
            Speed multiplier as float
        """
        if '/' in speed:
            parts = speed.split('/')
            try:
                return float(parts[0]) / float(parts[1])
            except (ValueError, ZeroDivisionError):
                return 1.0
        else:
            try:
                return float(speed)
            except ValueError:
                return 1.0

    def _rgb_to_color_wheel(self, r: float, g: float, b: float) -> int:
        """
        Map RGB to color wheel position.

        Simple mapping to closest standard color.
        """
        wheel_colors = [
            (255, 255, 255, 5),    # White
            (255, 0, 0, 16),       # Red
            (255, 127, 0, 27),     # Orange
            (255, 255, 0, 43),     # Yellow
            (0, 255, 0, 64),       # Green
            (0, 255, 255, 85),     # Cyan
            (0, 0, 255, 106),      # Blue
            (255, 0, 255, 127),    # Magenta
            (255, 0, 127, 148),    # Pink
        ]

        min_distance = float('inf')
        closest_value = 0

        for wr, wg, wb, dmx_value in wheel_colors:
            distance = ((r - wr) ** 2 + (g - wg) ** 2 + (b - wb) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_value = dmx_value

        return closest_value
