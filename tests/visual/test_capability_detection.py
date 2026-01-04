# test_capability_detection.py
# Test script for sublane capability detection

import sys
import os
from config.models import Fixture, FixtureMode, FixtureGroup
from utils.fixture_utils import detect_fixture_group_capabilities

def test_capability_detection():
    """Test capability detection with custom fixtures."""

    print("=" * 60)
    print("Testing Sublane Capability Detection")
    print("=" * 60)

    # Test 1: Moving Head (Varytec Hero Spot 60)
    print("\n1. Testing Moving Head: Varytec Hero Spot 60")
    print("-" * 60)
    moving_head_fixture = Fixture(
        universe=1,
        address=1,
        manufacturer="Varytec",
        model="Hero Spot 60",
        name="MH1",
        group="Moving Heads",
        direction="",
        current_mode="14-Channel",
        available_modes=[FixtureMode("14-Channel", 14)],
        type="MH"
    )

    moving_head_group = FixtureGroup(
        name="Moving Heads",
        fixtures=[moving_head_fixture]
    )

    caps = detect_fixture_group_capabilities(moving_head_group.fixtures)
    print(f"  Dimmer:   {caps.has_dimmer}")
    print(f"  Colour:   {caps.has_colour}")
    print(f"  Movement: {caps.has_movement}")
    print(f"  Special:  {caps.has_special}")

    expected = {"dimmer": True, "colour": True, "movement": True, "special": True}
    actual = {
        "dimmer": caps.has_dimmer,
        "colour": caps.has_colour,
        "movement": caps.has_movement,
        "special": caps.has_special
    }

    if actual == expected:
        print("  [PASS] All expected capabilities detected")
    else:
        print(f"  [FAIL] Expected {expected}, got {actual}")

    # Test 2: RGBW Par (Stairville Retro Flat Par)
    print("\n2. Testing RGBW Par: Stairville Retro Flat Par 18x12W RGBW")
    print("-" * 60)
    rgbw_fixture = Fixture(
        universe=1,
        address=10,
        manufacturer="Stairville",
        model="Retro Flat Par 18x12W RGBW ",
        name="Par1",
        group="RGBW Pars",
        direction="",
        current_mode="8-Channel",
        available_modes=[FixtureMode("8-Channel", 8)],
        type="WASH"
    )

    rgbw_group = FixtureGroup(
        name="RGBW Pars",
        fixtures=[rgbw_fixture]
    )

    caps = detect_fixture_group_capabilities(rgbw_group.fixtures)
    print(f"  Dimmer:   {caps.has_dimmer}")
    print(f"  Colour:   {caps.has_colour}")
    print(f"  Movement: {caps.has_movement}")
    print(f"  Special:  {caps.has_special}")

    expected = {"dimmer": True, "colour": True, "movement": False, "special": False}
    actual = {
        "dimmer": caps.has_dimmer,
        "colour": caps.has_colour,
        "movement": caps.has_movement,
        "special": caps.has_special
    }

    if actual == expected:
        print("  [PASS] All expected capabilities detected")
    else:
        print(f"  [FAIL] Expected {expected}, got {actual}")

    # Test 3: Simple Dimmer (hypothetical)
    print("\n3. Testing Simple Dimmer (if such fixture exists)")
    print("-" * 60)
    print("  (Skipped - would need actual simple dimmer fixture)")

    print("\n" + "=" * 60)
    print("Capability Detection Tests Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_capability_detection()
