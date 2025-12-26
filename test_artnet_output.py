# test_artnet_output.py
# Simple test script for ArtNet DMX output

import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from config.models import Configuration
from utils.artnet import ArtNetOutputController
from timeline.playback_engine import PlaybackEngine


def test_artnet_output():
    """Test ArtNet DMX output with a simple scenario."""

    print("=" * 60)
    print("ArtNet DMX Output Test")
    print("=" * 60)

    # Create QApplication (required for Qt signals)
    app = QApplication(sys.argv)

    # Load configuration
    print("\n1. Loading configuration...")
    try:
        config = Configuration.load("config.yaml")
        print(f"   ✓ Loaded {len(config.fixtures)} fixtures")
        print(f"   ✓ Loaded {len(config.groups)} fixture groups")
        print(f"   ✓ Loaded {len(config.universes)} universes")
    except Exception as e:
        print(f"   ✗ Error loading config: {e}")
        return

    # Load fixture definitions
    print("\n2. Loading fixture definitions...")
    try:
        fixture_defs = Configuration._scan_fixture_definitions()
        print(f"   ✓ Loaded {len(fixture_defs)} fixture definitions")
    except Exception as e:
        print(f"   ✗ Error loading fixture definitions: {e}")
        return

    # Create playback engine
    print("\n3. Creating playback engine...")
    playback_engine = PlaybackEngine()
    print("   ✓ Playback engine created")

    # Create ArtNet controller
    print("\n4. Creating ArtNet output controller...")
    try:
        artnet_controller = ArtNetOutputController(
            config=config,
            fixture_definitions=fixture_defs,
            playback_engine=playback_engine,
            target_ip="255.255.255.255"  # Broadcast
        )
        print("   ✓ ArtNet controller created")
        print(f"   ✓ Broadcasting to 255.255.255.255:6454")
    except Exception as e:
        print(f"   ✗ Error creating ArtNet controller: {e}")
        import traceback
        traceback.print_exc()
        return

    # Enable output
    print("\n5. Enabling ArtNet output...")
    artnet_controller.enable_output()
    print("   ✓ ArtNet output enabled")

    # Test: Send a simple DMX pattern
    print("\n6. Testing DMX output...")
    print("   Sending test pattern for 5 seconds...")
    print("   (Check Visualizer or DMX monitor to see output)")

    # Start playback
    playback_engine.play()

    # Create a simple test: fade up all fixtures
    print("\n   Creating test fade pattern...")

    # Simulate a dimmer block for each group
    from config.models import DimmerBlock
    for group_name, group in config.groups.items():
        print(f"   - Setting {group_name} to 50% intensity")

        # Create a simple dimmer block
        dimmer_block = DimmerBlock(
            start_time=0.0,
            end_time=10.0,
            intensity=128,  # 50% intensity
            effect_type="static"
        )

        # Register with DMX manager
        artnet_controller.dmx_manager.block_started(
            group_name, dimmer_block, 'dimmer', 0.0
        )

    # Let it run for 5 seconds
    print("\n   Test pattern running...")
    start_time = time.time()
    while time.time() - start_time < 5.0:
        # Update current time
        current_time = time.time() - start_time
        playback_engine.current_position = current_time

        # Trigger DMX update manually
        artnet_controller._update_and_send_dmx()

        # Process Qt events
        app.processEvents()

        # Wait a bit
        time.sleep(0.02)  # ~50Hz

    print("   ✓ Test pattern complete")

    # Cleanup
    print("\n7. Cleaning up...")
    playback_engine.stop()
    artnet_controller.cleanup()
    print("   ✓ Cleanup complete")

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    print("\nIf you have a DMX monitor or Visualizer running,")
    print("you should have seen fixture intensities at 50%.")
    print("\nNext steps:")
    print("1. Integrate ArtNetOutputController into your main GUI")
    print("2. Connect it to your playback engine")
    print("3. Enable output when playing timeline")
    print("=" * 60)


if __name__ == "__main__":
    test_artnet_output()
