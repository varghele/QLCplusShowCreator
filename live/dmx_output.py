"""
Live DMX Controller — dedicated ArtNet output for live mode.

Runs its own DMXManager + ArtNetSender, completely independent
from the main app's ShowsArtNetController. Supports configurable
target IP and universe mapping for venue-specific setups.
"""

import time
import threading
from typing import Optional, Dict, Callable

from utils.artnet.dmx_manager import DMXManager
from utils.artnet.sender import ArtNetSender
from config.models import Configuration
from live.engine import LiveShowEngine


class LiveDMXController:
    """Manages DMX output for live mode on a dedicated 30Hz thread."""

    def __init__(self, config: Configuration, fixture_definitions: dict,
                 target_ip: str = "192.168.1.151",
                 local_dmx_callback: Optional[Callable[[int, bytes], None]] = None):
        """
        Args:
            config: Fixture configuration from the main app
            fixture_definitions: QLC+ fixture definition dicts
            target_ip: ArtNet target IP address
            local_dmx_callback: Optional ``(universe, dmx_bytes)`` hook
                invoked once per universe per frame, after the ArtNet
                packet is sent. Used by the embedded visualizer in the
                Live tab to mirror what's going on the wire without a
                TCP/ArtNet round-trip. Standalone visualizer keeps
                receiving DMX over the wire as before — this is additive.
        """
        self.config = config

        # Own instances — separate from main app
        self.dmx_manager = DMXManager(config, fixture_definitions)
        self.artnet_sender = ArtNetSender(target_ip=target_ip)

        # Second sender for visualizer (always broadcast)
        self._visualizer_sender = ArtNetSender(target_ip="255.255.255.255")
        self._mirror_to_visualizer = True

        # Local in-process visualizer hook (see __init__ docstring).
        self._local_dmx_callback = local_dmx_callback

        # Universe mapping: {config_universe_id: artnet_universe_number}
        # Default: identity mapping (config universe 1 → artnet 0, etc.)
        self._universe_mapping: Dict[int, int] = {}
        for uid in config.universes.keys():
            uid_int = int(uid)
            self._universe_mapping[uid_int] = uid_int - 1  # 1-based → 0-based

        # Engine reference
        self._engine: Optional[LiveShowEngine] = None

        # Thread control
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._update_interval = 1.0 / 30.0  # 30Hz

    def set_engine(self, engine: LiveShowEngine):
        """Connect the live show engine."""
        self._engine = engine
        engine.set_dmx_manager(self.dmx_manager)

    def set_target_ip(self, ip: str):
        """Change ArtNet target IP at runtime."""
        self.artnet_sender.target_ip = ip

    def set_mirror_to_visualizer(self, enabled: bool):
        """Enable/disable mirroring DMX to broadcast for the visualizer."""
        self._mirror_to_visualizer = enabled

    def set_local_dmx_callback(
        self, callback: Optional[Callable[[int, bytes], None]]
    ) -> None:
        """Update or clear the embedded-visualizer DMX hook after init."""
        self._local_dmx_callback = callback

    def set_universe_mapping(self, mapping: Dict[int, int]):
        """Set universe mapping.

        Args:
            mapping: {config_universe_id: artnet_universe_number}
                     e.g. {1: 0, 2: 1} for Enttec ODE port 0 + port 1
        """
        self._universe_mapping = dict(mapping)

    def start(self):
        """Start the DMX output thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()

        # Start the engine's riff cycle
        if self._engine:
            self._engine.start()

        self._thread = threading.Thread(
            target=self._update_loop,
            name="LiveDMXController",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Stop the DMX output thread and clear fixtures."""
        # Stop engine first
        if self._engine:
            self._engine.stop()

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        # Send blackout
        self._send_blackout()

    def _update_loop(self):
        """Main DMX update loop — runs at 30Hz."""
        while not self._stop_event.is_set():
            loop_start = time.monotonic()

            try:
                # Advance engine
                if self._engine:
                    self._engine.tick(loop_start)

                # Compute DMX state
                self.dmx_manager.update_dmx(loop_start)

                # Send all universes
                self._send_all_universes()

            except Exception as e:
                print(f"Live DMX update error: {e}")

            # Maintain consistent frame rate
            elapsed = time.monotonic() - loop_start
            sleep_time = self._update_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _send_all_universes(self):
        """Send DMX data for all configured universes."""
        for config_uid, artnet_uid in self._universe_mapping.items():
            try:
                dmx_data = self.dmx_manager.get_dmx_data(config_uid)
                self.artnet_sender.send_dmx(artnet_uid, dmx_data)

                # Mirror to broadcast for visualizer
                if self._mirror_to_visualizer:
                    self._visualizer_sender.send_dmx(artnet_uid, dmx_data)

                # Forward the same frame to the in-process visualizer if
                # one is wired up. Wrap in try/except so a misbehaving
                # callback can't kill the DMX thread mid-show. Pass the
                # 1-based config universe id to match what the embedded
                # visualizer keys off (build_fixtures_payload uses
                # fixture.universe directly, also 1-based).
                if self._local_dmx_callback is not None:
                    try:
                        self._local_dmx_callback(config_uid, bytes(dmx_data))
                    except Exception as cb_err:
                        print(f"Live local_dmx_callback raised: {cb_err}")
            except Exception as e:
                print(f"Error sending universe {config_uid}→{artnet_uid}: {e}")

    def _send_blackout(self):
        """Send all zeros to all universes (blackout)."""
        blackout = bytearray(512)
        for artnet_uid in self._universe_mapping.values():
            try:
                self.artnet_sender.send_dmx(artnet_uid, blackout, force=True)
                if self._mirror_to_visualizer:
                    self._visualizer_sender.send_dmx(artnet_uid, blackout, force=True)
            except Exception:
                pass
