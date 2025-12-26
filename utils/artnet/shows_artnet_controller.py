# utils/artnet/shows_artnet_controller.py
# Simplified ArtNet controller for ShowsTab integration

from PyQt6.QtCore import QObject, QTimer
from typing import Optional, Dict, Tuple
from config.models import Configuration
from timeline.light_lane import LightLane
from .dmx_manager import DMXManager
from .sender import ArtNetSender


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

        # Current playback time (set from ShowsTab)
        self.current_time = 0.0

        # Track active blocks per lane - used for detecting block endings
        # lane_name -> {sublane_type -> set of block ids}
        self.active_block_ids: Dict[str, Dict[str, set]] = {}

        # Reference to light lanes (set from ShowsTab)
        self.light_lanes = []

        print("ShowsArtNet Controller initialized")

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
        """Stop ArtNet output and clear DMX."""
        self.update_timer.stop()
        self.dmx_manager.clear_all_dmx()
        self._send_all_universes()
        self.active_block_ids.clear()
        print("ArtNet output stopped")

    def pause_playback(self):
        """Pause ArtNet output."""
        self.update_timer.stop()
        print("ArtNet output paused")

    def update_position(self, position: float):
        """
        Update current playback position.

        Called from ShowsTab during playback.

        Args:
            position: Current position in seconds
        """
        self.current_time = position

        # Process active blocks for all lanes
        if self.light_lanes:
            self._process_lane_blocks()

    def _process_lane_blocks(self):
        """Process blocks for all lanes at current time."""
        for lane in self.light_lanes:
            if lane.muted:
                continue

            fixture_group = lane.fixture_group
            lane_name = lane.name

            # Initialize tracking for this lane if needed
            if lane_name not in self.active_block_ids:
                self.active_block_ids[lane_name] = {
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
                        if block_id not in self.active_block_ids[lane_name]['dimmer']:
                            self.dmx_manager.block_started(fixture_group, dimmer_block, 'dimmer', self.current_time)
                            self.active_block_ids[lane_name]['dimmer'].add(block_id)

                # Check colour blocks
                for colour_block in light_block.colour_blocks:
                    block_id = id(colour_block)
                    if colour_block.start_time <= self.current_time < colour_block.end_time:
                        currently_active['colour'].add(block_id)

                        if block_id not in self.active_block_ids[lane_name]['colour']:
                            self.dmx_manager.block_started(fixture_group, colour_block, 'colour', self.current_time)
                            self.active_block_ids[lane_name]['colour'].add(block_id)

                # Check movement blocks
                for movement_block in light_block.movement_blocks:
                    block_id = id(movement_block)
                    if movement_block.start_time <= self.current_time < movement_block.end_time:
                        currently_active['movement'].add(block_id)

                        if block_id not in self.active_block_ids[lane_name]['movement']:
                            self.dmx_manager.block_started(fixture_group, movement_block, 'movement', self.current_time)
                            self.active_block_ids[lane_name]['movement'].add(block_id)

                # Check special blocks
                for special_block in light_block.special_blocks:
                    block_id = id(special_block)
                    if special_block.start_time <= self.current_time < special_block.end_time:
                        currently_active['special'].add(block_id)

                        if block_id not in self.active_block_ids[lane_name]['special']:
                            self.dmx_manager.block_started(fixture_group, special_block, 'special', self.current_time)
                            self.active_block_ids[lane_name]['special'].add(block_id)

            # End blocks that are no longer active (granular ending per sublane type)
            for sublane_type in ['dimmer', 'colour', 'movement', 'special']:
                ended_blocks = self.active_block_ids[lane_name][sublane_type] - currently_active[sublane_type]
                if ended_blocks:
                    # End this specific sublane type
                    self.dmx_manager.block_ended(fixture_group, sublane_type)
                    self.active_block_ids[lane_name][sublane_type] = currently_active[sublane_type]

    def _update_and_send_dmx(self):
        """
        Update DMX state and send via ArtNet.

        Called periodically by update_timer at ~44Hz.
        """
        if not self.output_enabled:
            return

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
