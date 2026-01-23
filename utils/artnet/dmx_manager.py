# utils/artnet/dmx_manager.py
# DMX state manager for real-time DMX output

import time
import math
from typing import Dict, List, Optional, Tuple, Any
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
        # Include "Intensity" as a group name that some fixtures use for dimmer
        properties = [
            "IntensityMasterDimmer", "IntensityDimmer", "Intensity",
            "IntensityRed", "IntensityGreen", "IntensityBlue", "IntensityWhite",
            "IntensityAmber", "IntensityCyan", "IntensityMagenta", "IntensityYellow",
            "IntensityUV", "IntensityLime",
            "PositionPan", "PositionTilt", "PositionPanFine", "PositionTiltFine",
            "ColorWheel", "ColorMacro", "Colour",
            "GoboWheel", "Gobo", "Gobo1", "Gobo2",
            "PrismRotation", "Prism",
            "BeamFocusNearFar", "BeamZoomSmallBig", "BeamIrisCloseOpen",
            "ShutterStrobeOpen", "ShutterStrobeFast", "ShutterStrobeRandom", "Shutter"
        ]

        channels_dict = get_channels_by_property(self.fixture_def, self.mode_name, properties)

        # Store channel mappings (property -> list of channel offsets)
        # Include "Intensity" group for fixtures that use that naming
        self.dimmer_channels = self._get_channel_offsets(channels_dict, ["IntensityMasterDimmer", "IntensityDimmer", "Intensity"])
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
        self.color_wheel_channels = self._get_channel_offsets(channels_dict, ["ColorWheel", "ColorMacro", "Colour"])
        self.gobo_channels = self._get_channel_offsets(channels_dict, ["GoboWheel", "Gobo", "Gobo1"])
        self.prism_channels = self._get_channel_offsets(channels_dict, ["Prism"])
        self.focus_channels = self._get_channel_offsets(channels_dict, ["BeamFocusNearFar"])
        self.zoom_channels = self._get_channel_offsets(channels_dict, ["BeamZoomSmallBig"])
        self.strobe_channels = self._get_channel_offsets(channels_dict, ["ShutterStrobeOpen", "ShutterStrobeFast", "ShutterStrobeRandom", "Shutter", "ShutterOpen"])

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

        # Also initialize universes for all fixtures (in case fixture uses unconfigured universe)
        for fixture in config.fixtures:
            if fixture.universe not in self.dmx_state:
                self.dmx_state[fixture.universe] = bytearray(512)

        # Build fixture channel maps
        self.fixture_maps: Dict[str, FixtureChannelMap] = {}
        self._build_fixture_maps()

        # Track active blocks (LTP - Latest Takes Priority)
        # Dictionary: lane_key -> {sublane_type -> (fixtures, block, start_time)}
        # fixtures is a list of Fixture objects resolved from the lane's targets
        self.active_blocks: Dict[str, Dict[str, Tuple[List[Fixture], object, float]]] = {}

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
            # Get fixture definition - keys are "manufacturer_model" strings
            fixture_key = f"{fixture.manufacturer}_{fixture.model}"
            fixture_def = self.fixture_definitions.get(fixture_key)

            if fixture_def:
                self.fixture_maps[fixture.name] = FixtureChannelMap(fixture, fixture_def, self.config)
                fm = self.fixture_maps[fixture.name]
                # Enhanced logging for moving heads
                if getattr(fixture, 'type', '') == 'MH':
                    print(f"DMXManager: Mapped MH '{fixture.name}': dimmer={fm.dimmer_channels} "
                          f"shutter={fm.strobe_channels} color_wheel={fm.color_wheel_channels}")
                else:
                    print(f"DMXManager: Mapped fixture '{fixture.name}' with {len(fm.dimmer_channels)} dimmer channels")
            else:
                print(f"Warning: No fixture definition found for {fixture.name} ({fixture_key})")

    def rebuild_fixture_maps(self):
        """Rebuild fixture maps when fixtures are added, removed, or modified."""
        self.fixture_maps.clear()
        self._build_fixture_maps()

        # Ensure all fixture universes are initialized in dmx_state
        for fixture in self.config.fixtures:
            if fixture.universe not in self.dmx_state:
                self.dmx_state[fixture.universe] = bytearray(512)
                print(f"DMXManager: Initialized universe {fixture.universe} for fixture {fixture.name}")

        print(f"DMXManager: Rebuilt fixture maps, now tracking {len(self.fixture_maps)} fixtures")

    def clear_all_dmx(self):
        """Clear all DMX values to 0."""
        for universe_id in self.dmx_state.keys():
            self.dmx_state[universe_id] = bytearray(512)

    def clear_active_blocks(self):
        """Clear all active block tracking state.

        This should be called when switching shows to ensure the old show's
        block state doesn't persist into the new show.
        """
        self.active_blocks.clear()
        print("DMXManager: Cleared active blocks")

    def set_fixtures_visible(self):
        """Set all fixtures to a visible idle state (dimmer at 255, white color, shutter open, centered)."""
        for fixture_name, fixture_map in self.fixture_maps.items():
            universe = fixture_map.universe

            # Set dimmer to full
            for ch_offset in fixture_map.dimmer_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 255)

            # Set RGB to white
            for ch_offset in fixture_map.red_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 255)
            for ch_offset in fixture_map.green_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 255)
            for ch_offset in fixture_map.blue_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 255)
            for ch_offset in fixture_map.white_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 255)

            # Open shutter (many moving heads need this to emit light)
            for ch_offset in fixture_map.strobe_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 255)  # Usually 255 = open

            # Set color wheel to first position (usually white/open)
            for ch_offset in fixture_map.color_wheel_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 0)  # Usually 0 = white/open

            # Reset pan/tilt to center position (127 = middle of 0-255 range)
            for ch_offset in fixture_map.pan_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 127)
            for ch_offset in fixture_map.tilt_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 127)
            # Also reset fine channels to center
            for ch_offset in fixture_map.pan_fine_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 127)
            for ch_offset in fixture_map.tilt_fine_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 127)

    def _set_safe_idle_state(self):
        """Set all fixtures to a safe idle state (shutter open, color wheel at white).

        Unlike set_fixtures_visible(), this keeps dimmers at 0 so fixtures appear off,
        but prevents strobe modes and other unwanted behavior by setting control channels
        to safe defaults.
        """
        for fixture_name, fixture_map in self.fixture_maps.items():
            universe = fixture_map.universe

            # Keep dimmers at 0 (already cleared by clear_all_dmx)
            # But ensure shutter is open to prevent strobe modes
            for ch_offset in fixture_map.strobe_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 255)  # 255 = shutter open

            # Set color wheel to first position (white/open) to prevent weird colors
            for ch_offset in fixture_map.color_wheel_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 0)  # 0 = white/open

            # Set pan/tilt to center so moving heads don't snap around
            for ch_offset in fixture_map.pan_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 127)
            for ch_offset in fixture_map.tilt_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 127)
            for ch_offset in fixture_map.pan_fine_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 127)
            for ch_offset in fixture_map.tilt_fine_channels:
                _, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, 127)

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

    def block_started(self, lane_key: str, fixtures: List[Fixture], block: object, block_type: str, current_time: float):
        """
        Called when a block starts playback.

        Args:
            lane_key: Unique identifier for the lane (usually lane name)
            fixtures: List of resolved Fixture objects to apply the effect to
            block: Block instance (DimmerBlock, ColourBlock, etc.)
            block_type: Type of block ('dimmer', 'colour', 'movement', 'special')
            current_time: Current playback time in seconds
        """
        # Initialize lane if needed
        if lane_key not in self.active_blocks:
            self.active_blocks[lane_key] = {}

        # Store fixtures, block, and start time (LTP)
        self.active_blocks[lane_key][block_type] = (fixtures, block, current_time)

    def block_ended(self, lane_key: str, block_type: str):
        """
        Called when a block ends playback.

        Args:
            lane_key: Unique identifier for the lane (usually lane name)
            block_type: Type of block ('dimmer', 'colour', 'movement', 'special')
        """
        if lane_key in self.active_blocks:
            if block_type in self.active_blocks[lane_key]:
                del self.active_blocks[lane_key][block_type]

    def update_dmx(self, current_time: float):
        """
        Update DMX state based on active blocks at current time.

        Args:
            current_time: Current playback time in seconds
        """
        # Clear all DMX values first - only fixtures with active blocks should be lit
        self.clear_all_dmx()

        # Set safe default values for ALL fixtures to prevent strobe/weird modes
        # This ensures shutters are open, dimmers at 0, etc. for non-targeted fixtures
        self._set_safe_idle_state()

        # Process each lane's active blocks
        # Make a copy of items to avoid issues during iteration
        active_items = list(self.active_blocks.items())
        for lane_key, active in active_items:
            # Get active blocks for this lane
            dimmer_data = active.get('dimmer')
            colour_data = active.get('colour')
            movement_data = active.get('movement')
            special_data = active.get('special')

            # Extract fixtures and blocks from the stored data
            # Each data entry is (fixtures, block, start_time)
            dimmer_fixtures = dimmer_data[0] if dimmer_data else []
            dimmer_block = dimmer_data[1] if dimmer_data else None
            colour_fixtures = colour_data[0] if colour_data else []
            colour_block = colour_data[1] if colour_data else None
            movement_fixtures = movement_data[0] if movement_data else []
            movement_block = movement_data[1] if movement_data else None
            special_fixtures = special_data[0] if special_data else []
            special_block = special_data[1] if special_data else None

            # Apply dimmer block to its resolved fixtures
            if dimmer_block and dimmer_fixtures:
                # Sort fixtures by x-position for spatial effects like ping_pong_smooth
                sorted_fixtures = sorted(dimmer_fixtures, key=lambda f: f.x)
                total_fixtures = len(sorted_fixtures)

                # Debug: Print once around 12.5s
                if 12.4 < current_time < 12.6 and not hasattr(self, '_debug_dmx_12_5'):
                    self._debug_dmx_12_5 = True
                    fixture_names = [f.name for f in sorted_fixtures]
                    print(f"\n=== DMX DEBUG at {current_time:.3f}s ===")
                    print(f"  Lane: {lane_key}")
                    print(f"  Dimmer block: {dimmer_block.effect_type}, {dimmer_block.start_time:.2f}-{dimmer_block.end_time:.2f}")
                    print(f"  Fixtures: {fixture_names}, total={total_fixtures}")
                    for f in sorted_fixtures:
                        in_maps = f.name in self.fixture_maps
                        print(f"    {f.name}: in fixture_maps={in_maps}")
                    print("=== END DMX DEBUG ===\n")

                for fixture_index, fixture in enumerate(sorted_fixtures):
                    if fixture.name not in self.fixture_maps:
                        continue

                    fixture_map = self.fixture_maps[fixture.name]
                    self._apply_dimmer_block(fixture_map, dimmer_block, current_time,
                                            fixture_index, total_fixtures)

            # Apply colour block to its resolved fixtures
            if colour_block and colour_fixtures:
                for fixture in colour_fixtures:
                    if fixture.name not in self.fixture_maps:
                        continue
                    fixture_map = self.fixture_maps[fixture.name]
                    self._apply_colour_block(fixture_map, colour_block, current_time)

            # Apply movement block to its resolved fixtures
            if movement_block and movement_fixtures:
                for fixture in movement_fixtures:
                    if fixture.name not in self.fixture_maps:
                        continue
                    fixture_map = self.fixture_maps[fixture.name]
                    self._apply_movement_block(fixture_map, movement_block, current_time)

            # Apply special block to its resolved fixtures
            if special_block and special_fixtures:
                for fixture in special_fixtures:
                    if fixture.name not in self.fixture_maps:
                        continue
                    fixture_map = self.fixture_maps[fixture.name]
                    self._apply_special_block(fixture_map, special_block, current_time)

    def _apply_dimmer_block(self, fixture_map: FixtureChannelMap, block: DimmerBlock, current_time: float,
                            fixture_index: int = 0, total_fixtures: int = 1):
        """Apply dimmer block to fixture channels.

        Args:
            fixture_map: Channel mapping for this fixture
            block: DimmerBlock with effect settings
            current_time: Current playback time in seconds
            fixture_index: This fixture's index within the group (for group effects)
            total_fixtures: Total fixtures in the group (for group effects)
        """
        # Clear any previous twinkle segment intensities
        # (will be set again if effect_type is twinkle)
        if hasattr(fixture_map, '_twinkle_segment_intensities'):
            delattr(fixture_map, '_twinkle_segment_intensities')

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

            # Set all dimmer channels to same intensity for strobe
            for ch_offset in fixture_map.dimmer_channels:
                universe, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, int(intensity))

        elif block.effect_type == "twinkle":
            # Twinkle: each segment/channel gets independent random intensity
            # With SMOOTH transitions between intensity values
            import random
            import hashlib

            speed_multiplier = self._parse_speed(block.effect_speed)
            time_in_block = current_time - block.start_time

            # Time per "twinkle step" - how often a new random target is chosen
            twinkle_step_duration = 0.2 / speed_multiplier  # 200ms base, adjusted by speed

            # Calculate current and next step for interpolation
            step_float = time_in_block / twinkle_step_duration
            current_step = int(step_float)
            next_step = current_step + 1
            # How far through the transition (0.0 to 1.0)
            transition_progress = step_float - current_step

            # Check if this is a pixelbar type (has RGBW segments but limited dimmers)
            fixture_type = getattr(fixture_map.fixture, 'type', '')
            is_pixelbar = fixture_type in ('PIXELBAR', 'BAR')

            # For pixelbars: control RGBW segments, keep master dimmer at set intensity
            # For other fixtures: control dimmer channels
            if is_pixelbar and (fixture_map.red_channels or fixture_map.white_channels):
                # Set master dimmer to full intensity
                for ch_offset in fixture_map.dimmer_channels:
                    universe, channel = fixture_map.get_absolute_address(ch_offset)
                    self.set_dmx_value(universe, channel, int(block.intensity))

                # Twinkle each SEGMENT independently (not individual RGBW channels)
                # Each segment's R,G,B,W should scale together to maintain color
                # Determine number of segments from the color channels
                num_segments = max(
                    len(fixture_map.red_channels),
                    len(fixture_map.green_channels),
                    len(fixture_map.blue_channels),
                    len(fixture_map.white_channels),
                    1
                )

                # Calculate intensity multiplier for each segment
                segment_intensities = []
                for seg_idx in range(num_segments):
                    # Get current target intensity for this segment
                    seed_str = f"{fixture_map.fixture.name}_seg{seg_idx}_{current_step}"
                    seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
                    random.seed(seed_hash)
                    current_variation = random.random() * 0.7 + 0.3

                    # Get next target intensity for this segment
                    seed_str = f"{fixture_map.fixture.name}_seg{seg_idx}_{next_step}"
                    seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
                    random.seed(seed_hash)
                    next_variation = random.random() * 0.7 + 0.3

                    # Smooth interpolation
                    t = transition_progress
                    smooth_t = t * t * (3 - 2 * t)
                    variation = current_variation + (next_variation - current_variation) * smooth_t
                    segment_intensities.append(variation)

                # Store segment intensities in fixture_map for use by colour_block
                # This allows the colour block to scale its values by the twinkle factor
                fixture_map._twinkle_segment_intensities = segment_intensities
            else:
                # Regular fixtures: twinkle the dimmer channels
                for idx, ch_offset in enumerate(fixture_map.dimmer_channels):
                    # Get current target intensity (seeded by step)
                    seed_str = f"{fixture_map.fixture.name}_{idx}_{current_step}"
                    seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
                    random.seed(seed_hash)
                    current_variation = random.random() * 0.7 + 0.3

                    # Get next target intensity
                    seed_str = f"{fixture_map.fixture.name}_{idx}_{next_step}"
                    seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
                    random.seed(seed_hash)
                    next_variation = random.random() * 0.7 + 0.3

                    # Smooth interpolation between current and next
                    t = transition_progress
                    smooth_t = t * t * (3 - 2 * t)  # Smoothstep function
                    variation = current_variation + (next_variation - current_variation) * smooth_t

                    channel_intensity = int(block.intensity * variation)

                    universe, channel = fixture_map.get_absolute_address(ch_offset)
                    self.set_dmx_value(universe, channel, channel_intensity)

        elif block.effect_type == "ping_pong_smooth":
            # Ping pong smooth: one fixture lights up at a time, bouncing back and forth
            # INSTANT attack (on the beat), smooth fade out until next fixture
            speed_multiplier = self._parse_speed(block.effect_speed)
            time_in_block = current_time - block.start_time

            # Get BPM for timing
            if self.song_structure:
                bpm = self.song_structure.get_bpm_at_time(current_time)
            else:
                bpm = 120.0

            # Calculate timing: each fixture gets one beat at speed 1
            seconds_per_beat = 60.0 / bpm
            time_per_fixture = seconds_per_beat / speed_multiplier

            # Calculate intensity multiplier (0.0 to 1.0) for this fixture
            if total_fixtures <= 1:
                # Single fixture - just stay on
                intensity_multiplier = 1.0
            else:
                # Total time for one full ping-pong cycle (0→N-1→0)
                # For N fixtures: N-1 steps forward, N-1 steps back = 2*(N-1) beats
                steps_in_cycle = (total_fixtures - 1) * 2
                cycle_time = time_per_fixture * steps_in_cycle

                # Get current time within the cycle
                time_in_cycle = time_in_block % cycle_time

                # Which "step" are we on? (each step = one fixture's turn)
                current_step = time_in_cycle / time_per_fixture
                step_index = int(current_step)
                time_within_step = (current_step - step_index) * time_per_fixture

                # Convert step index to fixture index (ping-pong pattern)
                # Steps 0,1,2,...,N-2 go forward (fixtures 0,1,2,...,N-1)
                # Steps N-1,N,...,2N-3 go backward (fixtures N-2,N-3,...,1)
                if step_index < (total_fixtures - 1):
                    # Going forward
                    active_fixture = step_index
                else:
                    # Going backward
                    active_fixture = steps_in_cycle - step_index

                # Calculate intensity multiplier for this fixture
                if fixture_index == active_fixture:
                    # This is the active fixture - instant full brightness
                    # with smooth decay over the beat
                    # Decay: start at 100%, end at ~20% by end of beat
                    decay_progress = time_within_step / time_per_fixture
                    # Use exponential decay for smooth falloff
                    intensity_multiplier = 0.2 + 0.8 * math.exp(-decay_progress * 3)
                elif fixture_index == (active_fixture - 1) or fixture_index == (active_fixture + 1):
                    # Adjacent fixture - might have residual glow from previous beat
                    # Only show tail if we just left this fixture
                    prev_fixture = active_fixture - 1 if step_index < (total_fixtures - 1) else active_fixture + 1
                    if fixture_index == prev_fixture and time_within_step < time_per_fixture * 0.3:
                        # Short tail from previous fixture (first 30% of beat only)
                        tail_progress = time_within_step / (time_per_fixture * 0.3)
                        intensity_multiplier = 0.3 * (1.0 - tail_progress)
                    else:
                        intensity_multiplier = 0.0
                else:
                    # Not active, not adjacent - off
                    intensity_multiplier = 0.0

            # Check if this is a pixelbar type (has RGBW segments but may lack master dimmer)
            fixture_type = getattr(fixture_map.fixture, 'type', '')
            is_pixelbar = fixture_type in ('PIXELBAR', 'BAR')

            if is_pixelbar and (fixture_map.red_channels or fixture_map.white_channels):
                # For pixelbars: set master dimmer to full, control brightness via color scaling
                for ch_offset in fixture_map.dimmer_channels:
                    universe, channel = fixture_map.get_absolute_address(ch_offset)
                    self.set_dmx_value(universe, channel, int(block.intensity))

                # Store uniform intensity for all segments - colour_block will use this to scale colors
                num_segments = max(
                    len(fixture_map.red_channels),
                    len(fixture_map.green_channels),
                    len(fixture_map.blue_channels),
                    len(fixture_map.white_channels),
                    1
                )
                # All segments get the same intensity multiplier for ping_pong
                fixture_map._twinkle_segment_intensities = [intensity_multiplier] * num_segments
            else:
                # For regular fixtures (moving heads, sunstrips): control via dimmer channels
                intensity = int(block.intensity * intensity_multiplier)
                for ch_offset in fixture_map.dimmer_channels:
                    universe, channel = fixture_map.get_absolute_address(ch_offset)
                    self.set_dmx_value(universe, channel, intensity)

        elif block.effect_type in ("waterfall_down", "waterfall_up"):
            # Waterfall effect: light cascades down (or up) through segments
            # Each segment-to-segment transition takes one beat
            # Tail spans the entire fixture with smooth falloff
            # Each fixture has a slowly drifting random offset
            import hashlib

            speed_multiplier = self._parse_speed(block.effect_speed)
            time_in_block = current_time - block.start_time

            # Get BPM for timing
            if self.song_structure:
                bpm = self.song_structure.get_bpm_at_time(current_time)
            else:
                bpm = 120.0

            seconds_per_beat = 60.0 / bpm
            # Each segment transition takes one beat, adjusted by speed
            time_per_step = seconds_per_beat / speed_multiplier

            # Check fixture type for segment-based control
            fixture_type = getattr(fixture_map.fixture, 'type', '')
            is_segmented = fixture_type in ('PIXELBAR', 'BAR', 'SUNSTRIP')

            # Determine if this is an RGBW pixelbar or a dimmer-only sunstrip
            has_color_segments = fixture_map.red_channels or fixture_map.white_channels
            has_dimmer_segments = len(fixture_map.dimmer_channels) > 1

            if is_segmented and (has_color_segments or has_dimmer_segments):
                # Determine number of segments based on fixture type
                if has_color_segments:
                    # Pixelbar: segments are RGBW channels
                    num_segments = max(
                        len(fixture_map.red_channels),
                        len(fixture_map.green_channels),
                        len(fixture_map.blue_channels),
                        len(fixture_map.white_channels),
                        1
                    )
                    is_dimmer_only = False
                else:
                    # Sunstrip: segments are individual dimmer channels
                    num_segments = len(fixture_map.dimmer_channels)
                    is_dimmer_only = True

                # Calculate random offset for this fixture (slowly drifting)
                # Base offset from fixture name hash
                name_hash = int(hashlib.md5(fixture_map.fixture.name.encode()).hexdigest()[:8], 16)
                base_offset = (name_hash % 1000) / 1000.0  # 0.0 to 1.0

                # Slowly drifting component (changes over ~30 seconds)
                drift_period = 30.0
                drift_phase = (current_time / drift_period) * 2 * math.pi
                # Use fixture-specific phase for the drift
                drift_seed = (name_hash % 997) / 997.0 * 2 * math.pi
                drift_amount = 0.3 * math.sin(drift_phase + drift_seed)  # +/- 0.3 cycle drift

                total_offset = base_offset + drift_amount

                # Full cycle time = num_segments beats
                cycle_time = time_per_step * num_segments

                # Current position in cycle (0 to num_segments), with offset
                cycle_progress = (time_in_block / cycle_time + total_offset) % 1.0
                head_position = cycle_progress * num_segments  # 0 to num_segments

                # For waterfall_down: head moves from last segment (N-1) to first (0)
                # For waterfall_up: head moves from first segment (0) to last (N-1)
                if block.effect_type == "waterfall_down":
                    head_position = (num_segments - 1) - head_position
                # For waterfall_up, head_position is already 0 to N-1

                # Calculate intensity for each segment using circular/wrapped distance
                # This creates a continuous seamless loop where the tail wraps around
                segment_intensities = []
                for seg_idx in range(num_segments):
                    # Calculate distance from head to this segment
                    # For waterfall_down: tail extends upward (higher indices), head moves down
                    # For waterfall_up: tail extends downward (lower indices), head moves up
                    if block.effect_type == "waterfall_down":
                        raw_distance = seg_idx - head_position
                    else:  # waterfall_up
                        raw_distance = head_position - seg_idx

                    # Use modulo to wrap the distance for continuous effect
                    # This means segments "ahead" of the head are actually at the far end of the tail
                    circular_distance = raw_distance % num_segments

                    # Normalize and apply exponential decay
                    normalized_dist = circular_distance / num_segments
                    intensity_factor = math.exp(-1.5 * normalized_dist)

                    segment_intensities.append(intensity_factor)

                if is_dimmer_only:
                    # Sunstrip: apply intensities directly to dimmer channels
                    for seg_idx, ch_offset in enumerate(fixture_map.dimmer_channels):
                        if seg_idx < len(segment_intensities):
                            seg_intensity = int(block.intensity * segment_intensities[seg_idx])
                            universe, channel = fixture_map.get_absolute_address(ch_offset)
                            self.set_dmx_value(universe, channel, seg_intensity)
                else:
                    # Pixelbar: set master dimmer to full, store intensities for colour_block
                    for ch_offset in fixture_map.dimmer_channels:
                        universe, channel = fixture_map.get_absolute_address(ch_offset)
                        self.set_dmx_value(universe, channel, int(block.intensity))
                    # Store segment intensities for colour_block to use
                    fixture_map._twinkle_segment_intensities = segment_intensities
            else:
                # For non-segmented fixtures, just set static intensity
                for ch_offset in fixture_map.dimmer_channels:
                    universe, channel = fixture_map.get_absolute_address(ch_offset)
                    self.set_dmx_value(universe, channel, int(block.intensity))

        elif block.effect_type == "hit":
            # Hit effect: instant attack to full intensity, decay over the beat
            # One hit per beat at speed "1", scales with speed multiplier
            # Decay takes the full beat duration
            speed_multiplier = self._parse_speed(block.effect_speed)
            time_in_block = current_time - block.start_time

            # Get BPM for timing
            if self.song_structure:
                bpm = self.song_structure.get_bpm_at_time(current_time)
            else:
                bpm = 120.0

            seconds_per_beat = 60.0 / bpm

            # Time between hits (one beat at speed 1)
            time_per_hit = seconds_per_beat / speed_multiplier

            # Decay takes the full beat duration
            decay_time = time_per_hit

            # Calculate position within current hit cycle
            time_in_cycle = time_in_block % time_per_hit

            # Calculate intensity based on decay (full beat duration)
            decay_progress = time_in_cycle / decay_time
            # Exponential decay: e^(-3) ≈ 0.05, so multiply by 3 for ~95% decay
            intensity_multiplier = math.exp(-decay_progress * 3)

            # Check if this is a pixelbar type
            fixture_type = getattr(fixture_map.fixture, 'type', '')
            is_pixelbar = fixture_type in ('PIXELBAR', 'BAR')

            if is_pixelbar and (fixture_map.red_channels or fixture_map.white_channels):
                # For pixelbars: set master dimmer to full, control via color scaling
                for ch_offset in fixture_map.dimmer_channels:
                    universe, channel = fixture_map.get_absolute_address(ch_offset)
                    self.set_dmx_value(universe, channel, int(block.intensity))

                # Store uniform intensity for all segments
                num_segments = max(
                    len(fixture_map.red_channels),
                    len(fixture_map.green_channels),
                    len(fixture_map.blue_channels),
                    len(fixture_map.white_channels),
                    1
                )
                fixture_map._twinkle_segment_intensities = [intensity_multiplier] * num_segments
            else:
                # For regular fixtures: control via dimmer channels
                final_intensity = int(block.intensity * intensity_multiplier)
                for ch_offset in fixture_map.dimmer_channels:
                    universe, channel = fixture_map.get_absolute_address(ch_offset)
                    self.set_dmx_value(universe, channel, final_intensity)

        else:
            # Default: static intensity for all channels
            for ch_offset in fixture_map.dimmer_channels:
                universe, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, int(intensity))

        # For fixtures with shutter channels (like moving heads), ensure shutter is open
        # Set to 255 which is typically "Open" on most fixtures
        for ch_offset in fixture_map.strobe_channels:
            universe, channel = fixture_map.get_absolute_address(ch_offset)
            self.set_dmx_value(universe, channel, 255)

    def _apply_colour_block(self, fixture_map: FixtureChannelMap, block: ColourBlock, current_time: float):
        """Apply colour block to fixture channels."""
        # Check if twinkle effect has stored segment intensities for this fixture
        # If so, scale color values per segment for pixelbar twinkle effect
        twinkle_intensities = getattr(fixture_map, '_twinkle_segment_intensities', None)

        # Get base RGB values
        red_value = block.red
        green_value = block.green
        blue_value = block.blue

        # If fixture has no white channel, mix white into RGB
        if not fixture_map.white_channels and block.white > 0:
            red_value = min(255, red_value + block.white)
            green_value = min(255, green_value + block.white)
            blue_value = min(255, blue_value + block.white)

        # Set RGB/RGBW channels
        color_mapping = [
            (fixture_map.red_channels, red_value),
            (fixture_map.green_channels, green_value),
            (fixture_map.blue_channels, blue_value),
            (fixture_map.white_channels, block.white),
            (fixture_map.amber_channels, block.amber),
            (fixture_map.cyan_channels, block.cyan),
            (fixture_map.magenta_channels, block.magenta),
            (fixture_map.yellow_channels, block.yellow),
            (fixture_map.uv_channels, block.uv),
            (fixture_map.lime_channels, block.lime),
        ]

        for channels, value in color_mapping:
            for idx, ch_offset in enumerate(channels):
                # If twinkle intensities exist, scale the color value per segment
                if twinkle_intensities and idx < len(twinkle_intensities):
                    scaled_value = int(value * twinkle_intensities[idx])
                else:
                    scaled_value = int(value)
                universe, channel = fixture_map.get_absolute_address(ch_offset)
                self.set_dmx_value(universe, channel, scaled_value)

        # Set color wheel if fixture has one
        if fixture_map.color_wheel_channels:
            # Check if color mode is Wheel - use stored position directly
            color_mode = getattr(block, 'color_mode', 'RGB')
            if color_mode == 'Wheel':
                # Use the color_wheel_position directly (already a DMX value)
                wheel_value = getattr(block, 'color_wheel_position', 0)
            elif (not fixture_map.red_channels and
                  not fixture_map.green_channels and
                  not fixture_map.blue_channels):
                # No RGB channels, try to map RGB to color wheel
                wheel_value = self._rgb_to_color_wheel(block.red, block.green, block.blue)
            else:
                # Has RGB channels, skip color wheel
                wheel_value = None

            if wheel_value is not None:
                for ch_offset in fixture_map.color_wheel_channels:
                    universe, channel = fixture_map.get_absolute_address(ch_offset)
                    self.set_dmx_value(universe, channel, int(wheel_value))

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
        DMX values are set to mid-range of typical color wheel positions
        to work with most fixtures (Varytec Hero Spot 60, etc.)
        """
        # Standard color wheel positions (using mid-range DMX values)
        # Most color wheels have ~25 DMX values per color
        wheel_colors = [
            (255, 255, 255, 12),   # White (typically 0-24)
            (255, 0, 0, 37),       # Red (typically 25-50)
            (255, 255, 0, 63),     # Yellow (typically 51-75)
            (173, 216, 230, 88),   # Light Blue (typically 76-100)
            (0, 255, 0, 113),      # Green (typically 101-125)
            (255, 170, 0, 138),    # Amber/Orange (typically 126-150)
            (238, 130, 238, 163),  # Violet (typically 151-175)
            (0, 0, 255, 188),      # Blue (typically 176-200)
        ]

        min_distance = float('inf')
        closest_value = 12  # Default to white

        for wr, wg, wb, dmx_value in wheel_colors:
            distance = ((r - wr) ** 2 + (g - wg) ** 2 + (b - wb) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_value = dmx_value

        return closest_value
