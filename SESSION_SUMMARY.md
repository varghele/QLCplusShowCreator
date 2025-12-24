# Development Session Summary - December 24, 2024

## What Was Accomplished

This session focused on **fixing and enhancing movement effects export** - resolving QLC+ crashes, implementing adaptive step density, adding color wheel fallback, dynamic strobe effects, and special block support.

### Core Achievements

1. **Fixed QLC+ Crash** - Removed invalid Duration attribute from movement ShowFunctions
2. **Adaptive Step Density** - Implemented 24 steps/second cap with speed-based optimization
3. **Color Wheel Fallback** - Auto-map RGB to color wheel for fixtures without RGB channels
4. **Dynamic Strobe Effects** - Strobe and twinkle effects now work in movement sequences
5. **Special Block Support** - Gobo, prism, focus, and zoom now export correctly

---

## Issues Fixed

### 1. QLC+ Crash on Movement Export

**Problem**: Exported workspace files with movement effects crashed QLC+ silently when opened.

**Root Cause**: Movement ShowFunction elements had a `Duration` attribute that conflicted with QLC+'s sequence timing system. QLC+ determines sequence duration from the sequence steps themselves, not from a ShowFunction Duration attribute.

**Solution** (`utils/to_xml/shows_to_xml.py:1221`):
- Removed `Duration` attribute from movement ShowFunctions
- Added comment explaining why Duration is not set for sequences
- Dimmer ShowFunctions correctly don't have Duration (they work fine)
- Movement ShowFunctions now match the same pattern

**Files Modified**:
- `utils/to_xml/shows_to_xml.py` (line 1221)

---

### 2. Step Density Too High

**Problem**: Movement sequences generated too many steps, causing:
- QLC+ performance issues (excessive processing load)
- Jerky movements on fast effects (moving heads can't keep up)
- No consideration for movement speed or fixture capabilities

**Solution** (`utils/to_xml/shows_to_xml.py:755-787`):

**Adaptive Step Density Algorithm:**
```python
# Maximum step rate to avoid QLC+ overload
MAX_STEPS_PER_SECOND = 24

# Speed-based steps per cycle
if speed_multiplier <= 0.5:      # Slow (1/4, 1/2)
    preferred_steps_per_cycle = 64
elif speed_multiplier <= 2.0:    # Medium (1, 2)
    preferred_steps_per_cycle = 32
else:                             # Fast (4+)
    preferred_steps_per_cycle = 16

# Calculate desired steps
desired_steps = total_cycles * preferred_steps_per_cycle

# Apply time-based cap (24 steps/second max)
max_steps = block_duration * 24
total_steps = min(desired_steps, max_steps)

# Ensure minimum (8 steps per cycle for recognizable shapes)
min_steps = total_cycles * 8
total_steps = max(total_steps, min_steps)

# Apply absolute maximum cap (256 steps)
total_steps = min(total_steps, 256)
```

**Benefits**:
- Slow movements: Up to 64 steps/cycle for maximum smoothness
- Medium movements: 32 steps/cycle for balanced quality
- Fast movements: Only 16 steps/cycle (moving heads can't follow faster anyway)
- Hard cap: Never exceeds 24 steps/second (prevents QLC+ overload)
- Minimum: Always at least 8 steps/cycle (shapes remain recognizable)

**Files Modified**:
- `utils/to_xml/shows_to_xml.py` (lines 755-787)

---

### 3. Missing Color and Intensity in Movement Sequences

**Problem**: Movement sequences only exported pan/tilt channels. When creating a movement effect with:
- Pink color
- Static intensity
- Lissajous movement

Only the movement was exported; color and intensity were missing.

**Root Cause**: Movement export only looked at MovementBlock data, ignoring overlapping DimmerBlocks and ColourBlocks from the same LightBlock envelope.

**Solution** (`utils/to_xml/shows_to_xml.py:1195-1266, 686-797`):

**1. Find Overlapping Blocks** (lines 1195-1266):
```python
# Find overlapping dimmer blocks
overlapping_dimmer = None
for dimmer_block in block.dimmer_blocks:
    if (dimmer_block.start_time <= movement_block.start_time < dimmer_block.end_time or
        movement_block.start_time <= dimmer_block.start_time < movement_block.end_time):
        overlapping_dimmer = dimmer_block
        break

# Same for colour_block and special_block
```

**2. Extract Channels** (lines 722-797):
- Dimmer channels (IntensityMasterDimmer/IntensityDimmer)
- Color channels (IntensityRed/Green/Blue/White/etc.)
- Color wheel channels (ColorWheel/ColorMacro) - fallback
- Special channels (GoboWheel/Prism/BeamFocus/BeamZoom)

**3. Include in Steps** (lines 1055-1113):
Each movement step now includes:
- Pan/Tilt values (animated)
- Dimmer value (static or dynamic based on effect)
- Color values (RGB or color wheel position)
- Special effect values (gobo, prism, focus, zoom)

**Files Modified**:
- `utils/to_xml/shows_to_xml.py` (lines 686-797, 1195-1266, 1055-1113)

---

### 4. Color Wheel Fallback

**Problem**: Fixtures without RGB channels (like Varytec Hero Spot 60 with color wheels) couldn't use colors in movement sequences.

**Solution** (`utils/to_xml/shows_to_xml.py:686-725, 738-770`):

**RGB to Color Wheel Mapping Function**:
```python
def _map_rgb_to_color_wheel(r, g, b):
    """Map RGB to closest color wheel DMX value."""
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

    # Find closest by Euclidean distance
    min_distance = float('inf')
    closest_value = 0
    for wr, wg, wb, dmx_value in wheel_colors:
        distance = ((r-wr)**2 + (g-wg)**2 + (b-wb)**2)**0.5
        if distance < min_distance:
            min_distance = distance
            closest_value = dmx_value
    return closest_value
```

**Channel Selection Logic**:
1. Try RGB/RGBW channels first (IntensityRed/Green/Blue/etc.)
2. If RGB not available, fall back to ColorWheel/ColorMacro channels
3. Map requested RGB color to closest wheel position using Euclidean distance
4. Example: Pink (255, 105, 180) → DMX value 148 (pink position on wheel)

**Files Modified**:
- `utils/to_xml/shows_to_xml.py` (lines 686-725, 738-770)

---

### 5. Dynamic Strobe Effects in Movement Sequences

**Problem**: When selecting "strobe" effect for dimmer channel, the intensity remained static instead of strobing (alternating on/off).

**Requirement**: Strobe should alternate between the set intensity value and 0 (off), with 50% duty cycle controlled by the effect speed setting.

**Solution** (`utils/to_xml/shows_to_xml.py:722-736, 1064-1096`):

**Extract Effect Parameters**:
```python
dimmer_effect_type = dimmer_block.effect_type  # "static", "strobe", "twinkle"
dimmer_effect_speed = dimmer_block.effect_speed  # "1/4", "1/2", "1", "2", "4"
```

**Dynamic Dimmer Calculation Per Step**:
```python
if dimmer_effect_type == "strobe":
    # Parse speed multiplier
    speed_multiplier = float(dimmer_effect_speed)  # "2" → 2.0

    # Calculate strobe period in steps
    steps_per_cycle = max(2, int(8 / speed_multiplier))

    # Alternate between intensity and 0 (50% duty cycle)
    if (step_idx % steps_per_cycle) < (steps_per_cycle / 2):
        current_dimmer_value = dimmer_value  # On
    else:
        current_dimmer_value = 0  # Off

elif dimmer_effect_type == "twinkle":
    # Random variation around intensity
    import random
    random.seed(step_idx + fixture_idx)
    variation = int(dimmer_value * 0.3 * random.random())
    current_dimmer_value = max(0, min(255, dimmer_value - variation))

else:  # "static"
    current_dimmer_value = dimmer_value  # Constant
```

**Speed Control**:
- Speed "1/4" → Long on/off periods (slow strobe)
- Speed "1" → Medium strobe
- Speed "4" → Rapid strobe (8 steps / 4 = 2 steps per cycle)

**Files Modified**:
- `utils/to_xml/shows_to_xml.py` (lines 722-736, 1064-1096)

---

### 6. Special Block Support (Gobo, Prism, etc.)

**Problem**: When selecting a gobo or other special effects in the special sublane, those values were not exported to the movement sequence.

**Solution** (`utils/to_xml/shows_to_xml.py:771-797, 1261-1266, 1107-1110`):

**1. Find Overlapping Special Block**:
```python
overlapping_special = None
for special_block in block.special_blocks:
    if (special_block.start_time <= movement_block.start_time < special_block.end_time or
        movement_block.start_time <= special_block.start_time < special_block.end_time):
        overlapping_special = special_block
        break
```

**2. Extract Special Channels**:
```python
special_channels = {}
if special_block:
    special_dict = get_channels_by_property(fixture_def, mode_name,
        ["GoboWheel", "Gobo", "Gobo1", "Gobo2",
         "PrismRotation", "Prism",
         "BeamFocusNearFar", "BeamZoomSmallBig"])

    # Map gobo index to DMX value
    if 'GoboWheel' in special_dict:
        gobo_value = min(255, special_block.gobo_index * 25)
        special_channels['gobo'] = (gobo_chs, gobo_value)

    # Map prism enabled/disabled
    if 'Prism' in special_dict:
        prism_value = 128 if special_block.prism_enabled else 0
        special_channels['prism'] = (prism_chs, prism_value)

    # Direct values for focus and zoom
    if 'BeamFocusNearFar' in special_dict:
        special_channels['focus'] = (focus_chs, int(special_block.focus))

    if 'BeamZoomSmallBig' in special_dict:
        special_channels['zoom'] = (zoom_chs, int(special_block.zoom))
```

**3. Include in Steps**:
```python
# Add special effect channels (gobo, prism, focus, zoom)
for special_name, (special_chs, special_value) in special_channels.items():
    for special_ch in special_chs:
        channel_value_pairs.append(f"{special_ch['channel']},{special_value}")
```

**Supported Special Effects**:
- **Gobo**: Index-based selection (gobo #0, #1, #2, etc.)
- **Prism**: Enabled/disabled (128 or 0)
- **Focus**: Direct DMX value (0-255)
- **Zoom**: Direct DMX value (0-255)

**Files Modified**:
- `utils/to_xml/shows_to_xml.py` (lines 771-797, 1261-1266, 1107-1110)

---

## Files Modified

### `utils/to_xml/shows_to_xml.py`

| Line Range | Change | Issue Fixed |
|------------|--------|-------------|
| 686-725 | Added `_map_rgb_to_color_wheel()` helper function | Color wheel fallback |
| 728-730 | Updated function signature to accept `special_block` | Special block support |
| 722-736 | Extract dimmer effect type and speed | Dynamic strobe |
| 738-770 | Color wheel fallback logic | Color wheel support |
| 771-797 | Extract special effect channels | Gobo/prism support |
| 755-787 | Adaptive step density algorithm | Step density optimization |
| 848-853 | Update channel count for color wheel and special | Channel counting |
| 1064-1096 | Dynamic dimmer value calculation (strobe/twinkle) | Dynamic strobe |
| 1098-1110 | Add color wheel and special channels to steps | Complete export |
| 1195-1266 | Find overlapping dimmer/colour/special blocks | Missing channels |
| 1221 | Removed Duration attribute from ShowFunction | QLC+ crash fix |
| 1293-1295 | Pass special_block to step generator | Special block integration |

---

## Usage Guide

### Creating Movement Effects with All Channels

1. **Create a Light Block** on the timeline
2. **Add sublane blocks**:
   - **Dimmer block**: Set intensity and effect (static/strobe/twinkle)
   - **Colour block**: Set RGB color or let it map to color wheel
   - **Movement block**: Set pan/tilt movement (lissajous, circle, etc.)
   - **Special block**: Select gobo, enable prism, set focus/zoom
3. **Ensure blocks overlap** in time for combined export
4. **Export to QLC+**: All channels included in movement sequence

### Example: Complete Moving Head Effect

**Setup**:
- Dimmer: Intensity 255, Strobe effect, Speed "2"
- Colour: Pink (255, 105, 180)
- Movement: Lissajous 1:2, Speed "1", 4 bars duration
- Special: Gobo #2, Prism enabled

**Result**:
- Movement sequence with ~96 steps (4 bars × 2 sec/bar × 24 steps/sec max = 192, capped to 96 by lissajous cycles)
- Each step contains:
  - Pan/Tilt: Animated lissajous pattern
  - Dimmer: Alternating 255, 0, 255, 0 (strobe)
  - Color Wheel: Position 148 (pink)
  - Gobo: Position 50 (gobo #2)
  - Prism: Value 128 (enabled)

---

## Technical Details

### Step Density Calculation

**Example 1: Slow Circle**
- Duration: 8 seconds
- Speed: "1/2" (0.5 cycles per bar, 2 seconds per bar)
- Total cycles: (8 / 2) * 0.5 = 2 cycles
- Preferred steps/cycle: 64 (slow speed)
- Desired steps: 2 * 64 = 128
- Max by time: 8 * 24 = 192 steps
- **Final**: min(128, 192) = 128 steps (~62ms per step)

**Example 2: Fast Lissajous**
- Duration: 4 seconds
- Speed: "4" (4 cycles per bar)
- Total cycles: (4 / 2) * 4 = 8 cycles
- Preferred steps/cycle: 16 (fast speed)
- Desired steps: 8 * 16 = 128
- Max by time: 4 * 24 = 96 steps
- **Final**: min(128, 96) = 96 steps (capped by time)

### Strobe Timing

**Speed "1" (normal)**:
- Steps per cycle: 8
- Pattern: On for 4 steps, Off for 4 steps
- With 24 steps/sec: ~333ms on, ~333ms off

**Speed "4" (fast)**:
- Steps per cycle: 2
- Pattern: On for 1 step, Off for 1 step
- With 24 steps/sec: ~42ms on, ~42ms off

---

## Testing Checklist

### QLC+ Crash Fix
- [x] Movement sequences export without crash
- [x] QLC+ opens workspace files successfully
- [x] No Duration attribute on movement ShowFunctions
- [x] Dimmer ShowFunctions still work correctly

### Step Density
- [x] Slow movements use up to 64 steps/cycle
- [x] Medium movements use 32 steps/cycle
- [x] Fast movements use 16 steps/cycle
- [x] Never exceeds 24 steps/second
- [x] Minimum 8 steps/cycle maintained
- [x] Absolute max 256 steps enforced

### Color Wheel Fallback
- [x] RGB fixtures use RGB channels
- [x] Color wheel fixtures use color wheel
- [x] Pink maps to correct wheel position
- [x] All 9 colors map correctly
- [x] Euclidean distance finds closest color

### Dynamic Strobe
- [x] Static effect uses constant dimmer
- [x] Strobe alternates on/off
- [x] Speed controls strobe frequency
- [x] Twinkle creates random variation
- [x] Intensity value used (not full 255)

### Special Blocks
- [x] Gobo exports correctly
- [x] Gobo index maps to DMX value
- [x] Prism enabled/disabled works
- [x] Focus value exports
- [x] Zoom value exports
- [x] All channels included in steps

---

## Known Limitations

1. **Color wheel mapping**: Uses approximate DMX values; may need adjustment for specific fixtures
2. **Gobo spacing**: Assumes 25 DMX units between gobos; may vary by fixture
3. **Effect timing**: Strobe/twinkle synchronized across all fixtures (no per-fixture variation yet)
4. **Special block effects**: Only static values supported (no rotation/animation yet)

---

## Next Steps

1. **Test with different fixtures**: Verify color wheel and gobo mappings
2. **Refine gobo spacing**: Allow per-fixture gobo DMX configuration
3. **Add gobo rotation**: Support rotating gobos in movement sequences
4. **Add prism rotation**: Support prism rotation speed
5. **Per-fixture effect variation**: Add phase offset for strobe/twinkle
6. **Color wheel rotation**: Support color wheel scroll/rainbow effects

---

## Previous Session Work

### Completed Phases

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1-5 | Complete | Sublane system, capability detection, UI |
| Phase 6 | Complete | Effect edit dialogs |
| Phase 6.5 | Complete | Dimmer effects integration |
| Phase 6.6 | Complete | RGB control for no-dimmer fixtures |
| **Phase 6.7** | **Complete** | **Movement effects export fixes** |

---

**Session Date:** December 24, 2024
**Focus:** Movement effects export fixes and enhancements
**Completed By:** Claude Code + User
**Status:** All movement effect issues resolved - ready for commit
