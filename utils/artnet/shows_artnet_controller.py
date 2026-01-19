# utils/artnet/shows_artnet_controller.py
# Simplified ArtNet controller for ShowsTab integration

from PyQt6.QtCore import QObject, QTimer
from typing import Optional, Dict, Tuple, List, Callable
from config.models import Configuration, Fixture
from timeline.light_lane import LightLane
from .dmx_manager import DMXManager
from .sender import ArtNetSender
from utils.target_resolver import resolve_targets_unique


class ShowsArtNetController(QObject):
    """
    Simplified ArtNet controller for ShowsTab.

    Directly interfaces with ShowsTab's playback mechanism without PlaybackEngine.
    """

    def __init__(self, config: Configuration, fixture_definitions: dict,
                 song_structure=None, target_ip: str = "255.255.255.255"):
        """
        Initialize ArtNet controller for ShowsTab.

        Args:
            config: Configuration with fixtures and universes
            fixture_definitions: Dictionary of parsed fixture definitions
            song_structure: Optional SongStructure for BPM-aware timing
            target_ip: Target IP for ArtNet packets (default: broadcast)
        """
        super().__init__()

        self.config = config
        self.fixture_definitions = fixture_definitions

        # Create DMX manager with song structure
        self.dmx_manager = DMXManager(config, fixture_definitions, song_structure)

        # Create ArtNet sender
        self.artnet_sender = ArtNetSender(target_ip=target_ip)

        # Output enabled flag
        self.output_enabled = False

        # Timer for periodic DMX updates (44Hz)
        self.update_timer = QTimer()
        self.update_timer.setInterval(23)  # ~44Hz (22.7ms)
        self.update_timer.timeout.connect(self._update_and_send_dmx)

        # Current playback time (set from ShowsTab or callback)
        self.current_time = 0.0

        # Position callback for getting fresh audio position
        # When set, this is called on each DMX update to get sample-accurate time
        self._position_callback: Optional[Callable[[], float]] = None

        # Track active blocks per lane - used for detecting block endings
        # lane_name -> {sublane_type -> set of block ids}
        self.active_block_ids: Dict[str, Dict[str, set]] = {}

        # Reference to light lanes (set from ShowsTab)
        self.light_lanes = []

        print("ShowsArtNet Controller initialized")

    def set_position_callback(self, callback: Callable[[], float]):
        """
        Set callback for getting fresh audio position.

        When set, the DMX update will call this to get sample-accurate
        position from the audio engine, reducing sync drift.

        Args:
            callback: Function that returns current position in seconds
        """
        self._position_callback = callback

    def set_song_structure(self, song_structure):
        """
        Update song structure for BPM-aware calculations.

        Args:
            song_structure: SongStructure instance
        """
        self.dmx_manager.set_song_structure(song_structure)

    def set_light_lanes(self, lanes: list):
        """
        Set light lanes for processing.

        Args:
            lanes: List of LightLane instances
        """
        self.light_lanes = lanes

    def update_fixtures(self):
        """
        Rebuild fixture mappings when fixtures are added, removed, or modified.

        Call this when fixtures change (e.g., after duplicating or adding fixtures).
        """
        self.dmx_manager.rebuild_fixture_maps()
        # Also reset fixtures to visible state so new fixtures appear
        self.dmx_manager.set_fixtures_visible()
        self._send_all_universes()
        print("ShowsArtNet: Fixture mappings updated")

    def enable_output(self):
        """Enable ArtNet output."""
        self.output_enabled = True
        print("ArtNet output enabled")

    def disable_output(self):
        """Disable ArtNet output and clear DMX."""
        self.output_enabled = False
        self.update_timer.stop()
        self.dmx_manager.clear_all_dmx()
        self._send_all_universes()
        print("ArtNet output disabled")

    def start_playback(self):
        """Start ArtNet output during playback."""
        if self.output_enabled:
            self.update_timer.start()
            print("ArtNet output started")

    def stop_playback(self):
        """Stop ArtNet output and reset fixtures to visible state."""
        self.update_timer.stop()
        # Reset fixtures to visible (full dimmer, white color) instead of blackout
        self.dmx_manager.set_fixtures_visible()
        # Send multiple packets to ensure visualizer receives the reset state
        for _ in range(5):
            self._send_all_universes()
        # Clear both controller and DMX manager block tracking
        self.active_block_ids.clear()
        self.dmx_manager.clear_active_blocks()
        print("ArtNet output stopped - fixtures reset to visible")

    def pause_playback(self):
        """Pause ArtNet output."""
        self.update_timer.stop()
        print("ArtNet output paused")

    def update_position(self, position: float):
        """
        Update current playback position.

        Called from ShowsTab during playback. When position_callback is set,
        block processing is handled by _update_and_send_dmx with fresh audio
        position, so we skip it here to avoid double-processing.

        Args:
            position: Current position in seconds
        """
        self.current_time = position

        # Only process blocks here if no position callback is set
        # (otherwise _update_and_send_dmx handles it with fresh audio position)
        if self.light_lanes and not self._position_callback:
            self._process_lane_blocks()

    def _process_lane_blocks(self):
        """Process blocks for all lanes at current time."""
        # Debug: Print lane info once when time is around 12.5s (Lane 3 starts)
        if 12.4 < self.current_time < 12.6 and not hasattr(self, '_debug_printed_12_5'):
            self._debug_printed_12_5 = True
            print(f"\n=== DEBUG at {self.current_time:.3f}s ===")
            print(f"Total lanes: {len(self.light_lanes)}")
            for i, lane in enumerate(self.light_lanes):
                targets = getattr(lane, 'fixture_targets', [])
                print(f"  Lane {i}: name={lane.name}, targets={targets}, muted={lane.muted}")
                print(f"    light_blocks: {len(lane.light_blocks)}")
                for lb in lane.light_blocks:
                    print(f"      LB {lb.start_time:.2f}-{lb.end_time:.2f}: {len(lb.dimmer_blocks)} dimmer, {len(lb.colour_blocks)} colour")
            print("=== END DEBUG ===\n")

        for lane in self.light_lanes:
            if lane.muted:
                continue

            # Get fixture targets (with backward compatibility for old fixture_group field)
            targets = getattr(lane, 'fixture_targets', [])
            if not targets and hasattr(lane, 'fixture_group') and lane.fixture_group:
                targets = [lane.fixture_group]

            # Resolve targets to fixtures
            resolved_fixtures = resolve_targets_unique(targets, self.config)
            if not resolved_fixtures:
                print(f"  WARNING: No fixtures resolved for targets {targets}")
                continue

            # Use unique lane key - combine id with name to ensure uniqueness
            # (multiple lanes could have the same name)
            lane_key = f"{id(lane)}_{lane.name}" if lane.name else f"{id(lane)}_{targets[0]}" if targets else f"{id(lane)}_unknown"

            # Initialize tracking for this lane if needed
            if lane_key not in self.active_block_ids:
                self.active_block_ids[lane_key] = {
                    'dimmer': set(),
                    'colour': set(),
                    'movement': set(),
                    'special': set()
                }

            # Track which blocks are currently active
            currently_active = {
                'dimmer': set(),
                'colour': set(),
                'movement': set(),
                'special': set()
            }

            # Process all light blocks in the lane
            for light_block in lane.light_blocks:
                # Check dimmer blocks
                for dimmer_block in light_block.dimmer_blocks:
                    block_id = id(dimmer_block)
                    if dimmer_block.start_time <= self.current_time < dimmer_block.end_time:
                        currently_active['dimmer'].add(block_id)

                        # Start block if not already active
                        if block_id not in self.active_block_ids[lane_key]['dimmer']:
                            fixture_names = [f.name for f in resolved_fixtures]
                            print(f"[{self.current_time:.2f}s] Starting {dimmer_block.effect_type} on {fixture_names} ({dimmer_block.start_time:.2f}s-{dimmer_block.end_time:.2f}s)")
                            self.dmx_manager.block_started(lane_key, resolved_fixtures, dimmer_block, 'dimmer', self.current_time)
                            self.active_block_ids[lane_key]['dimmer'].add(block_id)

                # Check colour blocks
                for colour_block in light_block.colour_blocks:
                    block_id = id(colour_block)
                    if colour_block.start_time <= self.current_time < colour_block.end_time:
                        currently_active['colour'].add(block_id)

                        if block_id not in self.active_block_ids[lane_key]['colour']:
                            self.dmx_manager.block_started(lane_key, resolved_fixtures, colour_block, 'colour', self.current_time)
                            self.active_block_ids[lane_key]['colour'].add(block_id)

                # Check movement blocks
                for movement_block in light_block.movement_blocks:
                    block_id = id(movement_block)
                    if movement_block.start_time <= self.current_time < movement_block.end_time:
                        currently_active['movement'].add(block_id)

                        if block_id not in self.active_block_ids[lane_key]['movement']:
                            self.dmx_manager.block_started(lane_key, resolved_fixtures, movement_block, 'movement', self.current_time)
                            self.active_block_ids[lane_key]['movement'].add(block_id)

                # Check special blocks
                for special_block in light_block.special_blocks:
                    block_id = id(special_block)
                    if special_block.start_time <= self.current_time < special_block.end_time:
                        currently_active['special'].add(block_id)

                        if block_id not in self.active_block_ids[lane_key]['special']:
                            self.dmx_manager.block_started(lane_key, resolved_fixtures, special_block, 'special', self.current_time)
                            self.active_block_ids[lane_key]['special'].add(block_id)

            # End blocks that are no longer active (granular ending per sublane type)
            for sublane_type in ['dimmer', 'colour', 'movement', 'special']:
                ended_blocks = self.active_block_ids[lane_key][sublane_type] - currently_active[sublane_type]
                if ended_blocks:
                    # Only clear the sublane if there are NO currently active blocks
                    # If there are active blocks, they will maintain the state
                    if not currently_active[sublane_type]:
                        # No active blocks remaining, clear the sublane
                        fixture_names = [f.name for f in resolved_fixtures]
                        print(f"[{self.current_time:.2f}s] Ending {sublane_type} blocks on {fixture_names}")
                        self.dmx_manager.block_ended(lane_key, sublane_type)
                    # Always update tracking to reflect current active blocks
                    self.active_block_ids[lane_key][sublane_type] = currently_active[sublane_type]

    def _update_and_send_dmx(self):
        """
        Update DMX state and send via ArtNet.

        Called periodically by update_timer at ~44Hz.
        """
        if not self.output_enabled:
            return

        # Get fresh position from callback if available (sample-accurate sync)
        if self._position_callback:
            try:
                self.current_time = self._position_callback()
            except Exception:
                pass  # Keep using last known position

        # Process active blocks with current time
        if self.light_lanes:
            self._process_lane_blocks()

        # Update DMX state based on current time and active blocks
        self.dmx_manager.update_dmx(self.current_time)

        # Send DMX for all universes
        self._send_all_universes()

    def _send_all_universes(self):
        """Send DMX data for all configured universes."""
        for universe_id in self.config.universes.keys():
            dmx_data = self.dmx_manager.get_dmx_data(universe_id)
            self.artnet_sender.send_dmx(universe_id, dmx_data)

    def set_target_ip(self, ip: str):
        """
        Set target IP address for ArtNet packets.

        Args:
            ip: Target IP address (e.g., "192.168.1.100" or "255.255.255.255")
        """
        self.artnet_sender.target_ip = ip
        print(f"ArtNet target IP set to: {ip}")

    def cleanup(self):
        """Cleanup resources."""
        self.update_timer.stop()
        self.dmx_manager.clear_all_dmx()
        self._send_all_universes()
        self.artnet_sender.close()
        print("ShowsArtNet Controller cleaned up")
