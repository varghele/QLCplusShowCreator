# Implementation Plan: Spot-Based Targeting for Moving Heads

## Overview
Add the ability for moving head fixtures to automatically calculate pan/tilt values to point at a selected stage spot/mark. This involves:
1. Adding z-coordinate to spots
2. Adding spot selection to movement blocks
3. Implementing automatic pan/tilt calculation using existing orientation utilities

## Phase 1: Extend Spot Model with Z-Coordinate

### File: `config/models.py`
- Add `z: float = 0.0` field to the `Spot` dataclass (around line 68-73)

### File: `gui/tabs/stage_tab.py` (or wherever spot editing UI lives)
- Add Z-coordinate input field to the spot editing UI
- Update spot creation/editing to include z value

## Phase 2: Add Target Spot to MovementBlock Model

### File: `config/models.py`
- Add `target_spot_name: Optional[str] = None` field to `MovementBlock` dataclass
- This allows linking a movement block to a specific spot by name

## Phase 3: Add Spot Selector to Movement Block Dialog

### File: `timeline_ui/movement_block_dialog.py`
- Add a new "Target Spot" group/section in the dialog
- Add combo box to select from available spots (loaded from config)
- When a spot is selected, store its name in `target_spot_name`
- Show "None" option to disable spot targeting (use manual/effect-based positioning)

## Phase 4: Implement Pan/Tilt Calculation in DMX Manager

### File: `utils/artnet/dmx_manager.py`

In `_apply_movement_block()`:
1. Check if `block.target_spot_name` is set
2. If set, look up the spot coordinates from config
3. For each fixture:
   - Get fixture's x, y, z position from fixture definition
   - Get fixture's orientation (yaw, pitch, roll, mounting_preset)
   - Get fixture's pan_range and tilt_range from Physical section
   - Call `calculate_pan_tilt()` from `utils/orientation.py` to get pan/tilt angles
   - Call `pan_tilt_to_dmx()` to convert angles to DMX values (center = 127)
   - Apply the calculated DMX values to pan/tilt channels

### Key calculation flow:
```
Spot(x, y, z) + Fixture(x, y, z, orientation)
    → calculate_pan_tilt()
    → (pan_angle, tilt_angle)
    → pan_tilt_to_dmx(pan_angle, pan_range, tilt_angle, tilt_range)
    → (pan_dmx, tilt_dmx)
```

## Phase 5: Integration with Existing Effects

When `target_spot_name` is set:
- The spot position becomes the "base" or "center" position
- Existing effects (circle, lissajous, etc.) can still apply as offsets around this position
- If effect is "static" or "none", fixture simply points at the spot

## Files to Modify

| File | Changes |
|------|---------|
| `config/models.py` | Add `z` to Spot, add `target_spot_name` to MovementBlock |
| `gui/tabs/stage_tab.py` | Add Z input field to spot editing UI |
| `timeline_ui/movement_block_dialog.py` | Add spot selector combo box |
| `utils/artnet/dmx_manager.py` | Implement spot-based pan/tilt calculation |

## Dependencies
- `utils/orientation.py` - Already has `calculate_pan_tilt()` and `pan_tilt_to_dmx()` functions
- Fixture definitions must have pan_range/tilt_range in Physical section (PanMax/TiltMax)

## Notes
- Pan/Tilt DMX center is 127 (middle of 0-255 range)
- Phase offset should still work - each fixture calculates its own pan/tilt based on its position
- Existing effects can work as offsets around the target spot position
