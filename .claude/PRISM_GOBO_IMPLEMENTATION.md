# Prism & Gobo Visualizer Implementation Plan

**Date:** January 2026
**Branch:** visualizer
**Status:** COMPLETE

---

## Completion Summary

Implementation completed January 2026. Both prism and gobo effects now render correctly in the 3D visualizer.

### What Was Implemented

**Prism Effect (3-facet):**
- Renders 3 beam cones at 120° apart around beam axis
- Each cone tilted 10° outward from center
- Each beam at 40% intensity (combined ~120%)
- Floor projection shows 3 separate spots with correct positions
- Rotation axis fix: beams rotate around Z (beam direction) not X

**Gobo Effect:**
- 7 procedural GLSL patterns: Open, Dots, Star, Lines, Triangle, Cross, Breakup
- QXF parsing extracts gobo wheel capabilities and maps to pattern IDs
- Gobo visible in BOTH volumetric beam AND floor projection
- Gobo rotation animation via DMX channel
- Beam visibility fix: patterns use 50-100% brightness range (not 0-100%)

**Combined Effects:**
- Prism + gobo work together: 3 patterned beams, 3 patterned floor spots

### Bug Fixes Applied

1. **Prism beam direction** - Fixed rotation axis from X to Z so all 3 beams point same direction
2. **Gobo beam visibility** - Changed brightness mapping from `pattern * alpha` to `mix(0.5, 1.0, pattern) * alpha` to prevent beam cutoff

### Files Modified

| File | Changes |
|------|---------|
| `utils/tcp/protocol.py` | Added `GOBO_PATTERN_KEYWORDS`, `_infer_gobo_pattern()`, gobo wheel extraction |
| `visualizer/renderer/fixtures.py` | Added gobo/prism shaders, `_render_single_beam()`, `_render_single_floor_projection()`, `get_gobo_pattern()`, prism floor intersection calc |

---

## Overview

Add prism and gobo effect visualization to the 3D visualizer's `MovingHeadRenderer`. These effects are already sent via ArtNet DMX but are not rendered visually.

**User Requirements:**
- 3-facet prism only
- Extract gobo pattern info from QXF files, generate procedurally
- Gobo patterns visible in BOTH volumetric beam AND floor projection

---

## Current State

### What Exists
- `SpecialBlock` model has `gobo_index`, `gobo_rotation`, `prism_enabled`, `prism_rotation`
- DMX manager sends gobo/prism values via ArtNet (`dmx_manager.py:574-590`)
- TCP protocol maps `gobo` and `prism` channels (`protocol.py:392-395`)
- `MovingHeadRenderer.update_dmx()` stores values in `self.dmx_values` dict
- Beam rendering exists: `_render_beam()` and `_render_floor_projection()`
- QXF files contain gobo capability names (e.g., "Circle", "Star", "Dots") in `<Capability>` text

### What's Missing
- `_render_beam()` ignores `self.dmx_values.get('prism', 0)`
- `_render_floor_projection()` ignores `self.dmx_values.get('gobo', 0)`
- No visual representation of prism beam splitting or gobo patterns
- TCP protocol doesn't extract gobo pattern metadata from QXF

---

## Implementation Plan

### Phase 1: Prism Effect

**Goal:** Split beam into 3 beams when prism is active

#### 1.1 Add Prism Detection
```python
# In _render_beam()
prism_value = self.dmx_values.get('prism', 0)
prism_active = prism_value > 20  # Threshold for "on"
```

#### 1.2 Multi-Beam Rendering
When prism is active:
- Render 3 beam cones instead of 1
- Each cone offset by rotation angles: 0°, 120°, 240° around beam axis
- Each cone tilted slightly outward (~8-12° from center)
- Reduce individual beam intensity to 40% (so combined = ~120%)

#### 1.3 Floor Projection Split
Modify `_render_floor_projection()`:
- When prism active, render 3 floor spots
- Calculate 3 separate floor intersection points
- Each spot at 40% intensity

#### Files to Modify
- `visualizer/renderer/fixtures.py` - `MovingHeadRenderer._render_beam()` (~40 lines)
- `visualizer/renderer/fixtures.py` - `MovingHeadRenderer._render_floor_projection()` (~30 lines)

---

### Phase 2: Gobo Effect - QXF Extraction

**Goal:** Extract gobo pattern info from QXF files, render in beam AND floor

#### 2.1 Parse Gobo Capabilities from QXF

Modify `utils/tcp/protocol.py` to extract gobo metadata:

```python
# New structure sent via TCP
"gobo_wheel": [
    {"min": 0, "max": 9, "pattern": "open", "name": "Open"},
    {"min": 10, "max": 26, "pattern": "dots", "name": "Gobo 1"},
    {"min": 27, "max": 43, "pattern": "star", "name": "Gobo 2"},
    ...
]
```

**Pattern keyword mapping** (parse from capability text):
| Keywords | Pattern ID | Description |
|----------|------------|-------------|
| "open", "no gobo" | 0 | No pattern |
| "dot", "circle", "spot" | 1 | Ring of circles |
| "star" | 2 | 6-pointed star |
| "line", "bar", "stripe" | 3 | Parallel bars |
| "triangle" | 4 | Triangle shape |
| "cross", "plus" | 5 | Plus/cross shape |
| (default/unknown) | 6 | Generic breakup pattern |

#### 2.2 Procedural GLSL Patterns

Create shader functions for each pattern type:
```glsl
float gobo_pattern(vec2 uv, int pattern_id, float rotation) {
    // Rotate UV coordinates
    vec2 ruv = rotate(uv - 0.5, rotation) + 0.5;

    switch(pattern_id) {
        case 0: return 1.0;  // Open
        case 1: return gobo_dots(ruv);
        case 2: return gobo_star(ruv);
        case 3: return gobo_lines(ruv);
        case 4: return gobo_triangle(ruv);
        case 5: return gobo_cross(ruv);
        default: return gobo_breakup(ruv);
    }
}
```

#### 2.3 Apply Gobo to BOTH Beam and Floor

**Beam shader** - Modify `BEAM_FRAGMENT_SHADER`:
- Add gobo pattern as alpha mask along beam length
- Pattern fades/scales with distance from fixture

**Floor projection shader** - Modify `FLOOR_PROJECTION_FRAGMENT_SHADER`:
- Apply gobo pattern mask to gaussian falloff
- Gobo rotation applied here

#### 2.4 Gobo Rotation Animation
- Track time in renderer for continuous rotation
- `gobo_rotation` DMX value controls rotation speed
- Pass rotation angle as shader uniform

#### Files to Modify
- `utils/tcp/protocol.py` - Add `_parse_gobo_wheel()` function (~40 lines)
- `visualizer/renderer/fixtures.py` - New `GOBO_BEAM_FRAGMENT_SHADER` (~60 lines)
- `visualizer/renderer/fixtures.py` - Modify floor projection shader (~40 lines)
- `visualizer/renderer/fixtures.py` - Add gobo state tracking + rotation (~30 lines)

---

### Phase 3: Combined Effects

When both prism AND gobo are active:
- Render 3 floor projections (prism split)
- Each projection uses the gobo pattern
- Same gobo rotation applied to all 3

---

## Implementation Order

1. **Prism beam split** - Most visual impact, simpler implementation
2. **Prism floor projection split** - Natural extension of step 1
3. **Gobo shader patterns** - New shader code
4. **Gobo DMX mapping** - Connect DMX to patterns
5. **Gobo rotation** - Animation support
6. **Combined prism + gobo** - Integration testing

---

## Code Structure

### New/Modified Methods in `MovingHeadRenderer`

```
MovingHeadRenderer
├── _render_beam()                    # MODIFY: Add prism multi-beam
├── _render_floor_projection()        # MODIFY: Add prism split + gobo
├── _render_single_beam()             # NEW: Extract single beam logic
├── _render_single_floor_projection() # NEW: Extract single projection logic
├── _map_gobo_dmx_to_pattern()        # NEW: DMX to pattern index
└── _calculate_floor_intersection()   # EXISTING: Reuse for prism offsets
```

### New Shader Constants

```python
GOBO_FLOOR_PROJECTION_FRAGMENT_SHADER = """
#version 330
// ... gobo pattern functions ...
"""
```

---

## Estimated Effort

| Task | Lines of Code | Complexity |
|------|---------------|------------|
| Prism beam rendering (3-facet) | ~50 | Medium |
| Prism floor split | ~40 | Medium |
| QXF gobo parsing | ~50 | Medium |
| Gobo shader patterns (7 types) | ~120 | Medium |
| Gobo in beam shader | ~40 | Medium |
| Gobo rotation animation | ~30 | Low |
| Testing/tweaking | - | - |
| **Total** | **~330 lines** | **Medium** |

---

## Testing Plan

1. **Prism testing with Show Creator:**
   - Create SpecialBlock with prism_enabled=True
   - Verify 3 beams render at 120° apart
   - Verify 3 floor spots with correct positions

2. **Gobo testing:**
   - Use fixture with gobo wheel (e.g., Varytec Hero Spot 60)
   - Set different gobo DMX values
   - Verify pattern changes in beam AND floor
   - Test rotation animation at various speeds

3. **Combined testing:**
   - Enable both prism and gobo
   - Verify 3 patterned beams
   - Verify 3 patterned floor spots

4. **QXF parsing test:**
   - Verify gobo_wheel data sent via TCP
   - Check pattern keyword extraction works

---

## Files Summary

| File | Action | Changes |
|------|--------|---------|
| `utils/tcp/protocol.py` | Modify | Add gobo wheel parsing |
| `visualizer/renderer/fixtures.py` | Modify | Prism + gobo rendering + shaders |
| `.claude/PHASE_PLAN.md` | Update | Mark feature complete |
