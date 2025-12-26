# utils/artnet/output_controller.py
# ArtNet output controller - integrates playback engine with DMX output

from PyQt6.QtCore import QObject, QTimer, pyqtSlot
from typing import Optional
from config.models import Configuration, LightBlock, DimmerBlock, ColourBlock, MovementBlock, SpecialBlock
from timeline.light_lane import LightLane
from timeline.playback_engine import PlaybackEngine
from .dmx_manager import DMXManager
from .sender import ArtNetSender


class ArtNetOutputController(QObject):
    """
    Controls real-time ArtNet DMX output during playback.

    Connects to playback engine signals and manages DMX state updates.
    Sends DMX via ArtNet at 44Hz during playback.
    """

    def __init__(self, config: Configuration, fixture_definitions: dict,
                 playback_engine: Optional[PlaybackEngine] = None,
                 target_ip: str = "255.255.255.255"):
        """
        Initialize ArtNet output controller.

        Args:
            config: Configuration with fixtures and universes
            fixture_definitions: Dictionary of parsed fixture definitions
            playback_engine: Optional playback engine to connect to
            target_ip: Target IP for ArtNet packets (default: broadcast)
        """
        super().__init__()

        self.config = config
        self.fixture_definitions = fixture_definitions

        # Create DMX manager
        self.dmx_manager = DMXManager(config, fixture_definitions)

        # Create ArtNet sender
        self.artnet_sender = ArtNetSender(target_ip=target_ip)

        # Playback engine reference
        self.playback_engine = playback_engine

        # Output enabled flag
        self.output_enabled = False

        # Timer for periodic DMX updates (44Hz)
        self.update_timer = QTimer()
        self.update_timer.setInterval(23)  # ~44Hz (22.7ms)
        self.update_timer.timeout.connect(self._update_and_send_dmx)

        # Current playback time (updated from playback engine)
        self.current_time = 0.0

        # Connect to playback engine if provided
        if playback_engine:
            self.connect_to_playback_engine(playback_engine)

        print("ArtNet Output Controller initialized")

    def connect_to_playback_engine(self, playback_engine: PlaybackEngine):
        """
        Connect to playback engine signals.

        Args:
            playback_engine: PlaybackEngine instance
        """
        self.playback_engine = playback_engine

        # Connect signals
        playback_engine.playback_started.connect(self._on_playback_started)
        playback_engine.playback_stopped.connect(self._on_playback_stopped)
        playback_engine.playback_halted.connect(self._on_playback_halted)
        playback_engine.position_changed.connect(self._on_position_changed)
        playback_engine.block_triggered.connect(self._on_block_triggered)
        playback_engine.block_ended.connect(self._on_block_ended)

        print("Connected to playback engine")

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

    @pyqtSlot()
    def _on_playback_started(self):
        """Handle playback started signal."""
        if self.output_enabled:
            self.update_timer.start()
            print("ArtNet output started")

    @pyqtSlot()
    def _on_playback_stopped(self):
        """Handle playback stopped signal."""
        self.update_timer.stop()
        self.dmx_manager.clear_all_dmx()
        self._send_all_universes()
        print("ArtNet output stopped")

    @pyqtSlot()
    def _on_playback_halted(self):
        """Handle playback halted (paused) signal."""
        self.update_timer.stop()
        print("ArtNet output paused")

    @pyqtSlot(float)
    def _on_position_changed(self, position: float):
        """Handle playback position changed signal."""
        self.current_time = position

    @pyqtSlot(object, object)
    def _on_block_triggered(self, lane: LightLane, block: LightBlock):
        """
        Handle block triggered signal.

        Called when a light block starts playing.

        Args:
            lane: LightLane containing the block
            block: LightBlock that was triggered
        """
        fixture_group = lane.fixture_group

        # Register all sublane blocks with DMX manager
        for dimmer_block in block.dimmer_blocks:
            # Check if this block is currently active
            if dimmer_block.start_time <= self.current_time < dimmer_block.end_time:
                self.dmx_manager.block_started(fixture_group, dimmer_block, 'dimmer', self.current_time)

        for colour_block in block.colour_blocks:
            if colour_block.start_time <= self.current_time < colour_block.end_time:
                self.dmx_manager.block_started(fixture_group, colour_block, 'colour', self.current_time)

        for movement_block in block.movement_blocks:
            if movement_block.start_time <= self.current_time < movement_block.end_time:
                self.dmx_manager.block_started(fixture_group, movement_block, 'movement', self.current_time)

        for special_block in block.special_blocks:
            if special_block.start_time <= self.current_time < special_block.end_time:
                self.dmx_manager.block_started(fixture_group, special_block, 'special', self.current_time)

    @pyqtSlot(object, object)
    def _on_block_ended(self, lane: LightLane, block: LightBlock):
        """
        Handle block ended signal.

        Called when a light block finishes playing.

        Args:
            lane: LightLane containing the block
            block: LightBlock that ended
        """
        fixture_group = lane.fixture_group

        # Unregister all sublane blocks from DMX manager
        # Note: This clears all block types for simplicity
        # In practice, we should track which specific sublane blocks ended
        self.dmx_manager.block_ended(fixture_group, 'dimmer')
        self.dmx_manager.block_ended(fixture_group, 'colour')
        self.dmx_manager.block_ended(fixture_group, 'movement')
        self.dmx_manager.block_ended(fixture_group, 'special')

    @pyqtSlot()
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
        print("ArtNet Output Controller cleaned up")
