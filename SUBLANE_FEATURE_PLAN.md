# Effect Sublanes Feature - Implementation Plan

## Overview

This document describes the refactoring of the effect system to support sublanes within light lanes, allowing more granular control over different aspects of lighting effects.

## Current State

- Effects are represented as single blocks in a lane
- Each effect contains all parameters (intensity, color, movement, etc.) in one block
- No visual separation of different effect aspects
- No independent control of different effect parameters

## Final Design (Requirements Finalized)

### Four Sublane System

Each light lane will support up to four sublanes:

1. **Dimmer Sublane** - Controls intensity and shutter effects
2. **Colour Sublane** - Controls all color-related parameters
3. **Movement Sublane** - Controls pan, tilt, and positioning
4. **Special Sublane** - Controls gobo, beam, and prism effects

### Dynamic Sublane Display

The visibility of sublanes is determined by the capabilities of the fixture group, detected automatically from fixture definition files:

- **Moving Head Groups**: May display all 4 sublanes (Dimmer, Colour, Movement, Special)
- **Colored Light Groups**: Display 2 sublanes (Dimmer, Colour)
- **Simple Dimmer Groups**: Display 1 sublane (Dimmer only)

### Capability Detection

Fixture group capabilities are **automatically inferred** from the channels defined in the fixture definition files. The system will:
1. Read fixture definition files for all fixtures in a group
2. Analyze the channel presets to determine which capabilities exist
3. Display only the relevant sublanes for each group

## QLC+ Preset Categorization (FINAL)

### Dimmer Sublane
- `IntensityMasterDimmer`, `IntensityMasterDimmerFine`
- `IntensityDimmer`, `IntensityDimmerFine`
- `ShutterStrobeSlowFast`, `ShutterStrobeFastSlow`
- `ShutterIrisMinToMax`, `ShutterIrisMaxToMin`, `ShutterIrisFine`

### Colour Sublane
- **RGB Components**: `IntensityRed`, `IntensityRedFine`, `IntensityGreen`, `IntensityGreenFine`, `IntensityBlue`, `IntensityBlueFine`
- **CMY Components**: `IntensityCyan`, `IntensityCyanFine`, `IntensityMagenta`, `IntensityMagentaFine`, `IntensityYellow`, `IntensityYellowFine`
- **Additional Colors**: `IntensityAmber`, `IntensityAmberFine`, `IntensityWhite`, `IntensityWhiteFine`, `IntensityUV`, `IntensityUVFine`, `IntensityIndigo`, `IntensityIndigoFine`, `IntensityLime`, `IntensityLimeFine`
- **HSV/HSL**: `IntensityHue`, `IntensityHueFine`, `IntensitySaturation`, `IntensitySaturationFine`, `IntensityLightness`, `IntensityLightnessFine`, `IntensityValue`, `IntensityValueFine`
- **Color Selection**: `ColorMacro`, `ColorWheel`, `ColorWheelFine`, `ColorRGBMixer`, `ColorCTOMixer`, `ColorCTCMixer`, `ColorCTBMixer`

### Movement Sublane
- **Position**: `PositionPan`, `PositionPanFine`, `PositionTilt`, `PositionTiltFine`, `PositionXAxis`, `PositionYAxis`
- **Speed**: `SpeedPanSlowFast`, `SpeedPanFastSlow`, `SpeedTiltSlowFast`, `SpeedTiltFastSlow`, `SpeedPanTiltSlowFast`, `SpeedPanTiltFastSlow`

### Special Sublane
- **Gobo**: `GoboWheel`, `GoboWheelFine`, `GoboIndex`, `GoboIndexFine`
- **Beam**: `BeamFocusNearFar`, `BeamFocusFarNear`, `BeamFocusFine`, `BeamZoomSmallBig`, `BeamZoomBigSmall`, `BeamZoomFine`
- **Prism**: `PrismRotationSlowFast`, `PrismRotationFastSlow`

### Uncategorized
- `Custom` - Requires manual handling
- `NoFunction` - No action

## Core Concepts

### Effect as Envelope

The overall effect block serves as an **envelope** for the sublanes:
- Provides a container for easy copying/moving of all sublane blocks together
- Acts as a visual grouping mechanism
- Automatically adjusts its borders when sublanes are extended

### Sublane Independence

**Sublane blocks are completely independent:**
- Each sublane block has its own start and end time
- Sublane blocks do NOT need to be synchronized
- Color changes can occur without intensity changes (explicitly desired)
- Sublanes cannot extend beyond the effect envelope borders
- If a sublane block is extended, the effect envelope borders must expand

### Modified Effects

When sublane blocks are modified beyond the original effect definition:
- Mark the effect name with an asterisk (e.g., "Effect A*")
- Indicates the effect has been customized

## Sublane Behavior Rules

### Gap Handling

When there are gaps between sublane blocks:
- **Dimmer**: DMX values go to 0
- **Colour**: DMX values go to 0
- **Movement**: **Gradual transition** to the next movement block (default behavior, toggleable)
  - Fixtures should start in the right position for the next block
  - Smooth interpolation between blocks
- **Special**: DMX values go to 0

### Overlapping Blocks

When sublane blocks overlap:
- **Dimmer**: Implement **cross-fade** functionality
- **Colour**: Implement **cross-fade** functionality
- **Movement**: **No conflicts allowed** - prevent overlapping blocks
- **Special**: **No conflicts allowed** - prevent overlapping blocks (same as Movement)

### Movement Interpolation

For the Movement sublane:
- Default behavior: Gradual transition between blocks
- Toggleable per-effect or per-block
- Ensures fixtures are in correct position when next block starts
- Prevents jarring jumps in position

## User Workflows

### Workflow 1: Create Full Effect

1. User opens effect creation dialog
2. User defines all parameters (dimmer, color, movement, special)
3. System automatically populates all relevant sublanes based on fixture group capabilities
4. Effect envelope is created spanning all sublane blocks

### Workflow 2: Create Sublane Block

1. User drags/selects a region in a specific sublane
2. User defines only the parameters for that sublane (e.g., just color)
3. System creates a block only in that sublane
4. Effect envelope adjusts to contain the new block

### Workflow 3: Edit Entire Effect

1. User clicks on the effect envelope
2. Dialog shows all sublane parameters
3. User modifies parameters across all sublanes
4. All sublane blocks update simultaneously

### Workflow 4: Edit Individual Sublane

1. User clicks on a specific sublane block
2. Dialog shows only parameters for that sublane
3. User modifies sublane-specific parameters
4. Only that sublane block is updated
5. If modified beyond original effect, mark with asterisk

### Workflow 5: Extend Sublane Block

1. User drags edge of sublane block to extend duration
2. If extension goes beyond effect envelope border:
   - Effect envelope border automatically extends
   - Effect marked with asterisk
3. All timing stays independent per sublane

## Technical Requirements

### Data Model Changes

**Effect Model (UPDATED - now supports multiple blocks per sublane):**
```python
class LightBlock:  # Renamed from Effect
    name: str
    start_time: float  # Envelope start
    end_time: float    # Envelope end
    modified: bool     # True if sublanes modified beyond original

    # CHANGED: Now lists to support multiple blocks per type
    dimmer_blocks: List[DimmerBlock] = field(default_factory=list)
    colour_blocks: List[ColourBlock] = field(default_factory=list)
    movement_blocks: List[MovementBlock] = field(default_factory=list)
    special_blocks: List[SpecialBlock] = field(default_factory=list)
```

**Note:** Changed from single Optional[Block] to List[Block] to enable:
- Multiple dimmer blocks for complex fade sequences
- Multiple colour blocks for color changes (red → green → blue)
- Multiple movement blocks for position sequences
- Foundation for future "Riffs" feature

**Sublane Block Models:**
```python
class DimmerBlock:
    start_time: float
    end_time: float
    intensity: float
    strobe: Optional[StrobeSettings]
    # ... other dimmer parameters

class ColourBlock:
    start_time: float
    end_time: float
    color_mode: str  # "RGB", "CMY", "HSV", "Wheel"
    # ... color parameters

class MovementBlock:
    start_time: float
    end_time: float
    interpolate_gaps: bool  # Default: True
    pan: float
    tilt: float
    # ... movement parameters

class SpecialBlock:
    start_time: float
    end_time: float
    gobo: Optional[GoboSettings]
    beam: Optional[BeamSettings]
    prism: Optional[PrismSettings]
```

### Fixture Group Capabilities

```python
class FixtureGroupCapabilities:
    has_dimmer: bool
    has_colour: bool
    has_movement: bool
    has_special: bool

    # Detected from fixture definitions
    @staticmethod
    def detect_from_fixtures(fixtures: List[Fixture]) -> FixtureGroupCapabilities:
        # Read fixture definition files
        # Parse channel presets
        # Determine capabilities
```

### UI Changes

**Lane Rendering:**
- Each lane shows up to 4 sublanes vertically
- Sublane visibility based on group capabilities
- Effect envelope rendered as outer border
- Individual sublane blocks rendered within envelope

**Interaction:**
- Click on envelope: Edit entire effect
- Click on sublane block: Edit that sublane
- Drag in empty sublane: Create new sublane block
- Drag sublane block edge: Resize (auto-expand envelope if needed)
- Prevent overlapping in Movement and Special sublanes

**Visual Indicators:**
- Asterisk (*) on modified effects
- Different colors per sublane type
- Cross-fade regions shown for overlapping Dimmer/Colour blocks
- Interpolation indicators for Movement gaps

### DMX Generation

**Gap Handling:**
```python
def get_dmx_value(sublane, time):
    if sublane == "movement" and in_gap(time):
        return interpolate_to_next_block(time)
    elif no_block_at_time(time):
        return 0
    else:
        return block_value(time)
```

**Cross-fade:**
```python
def get_dmx_value_with_crossfade(sublane, time):
    if overlapping_blocks(time):
        return crossfade_blend(block1, block2, time)
    else:
        return block_value(time)
```

## Migration Strategy

**No backwards compatibility required:**
- Existing shows do not need to be supported
- Can implement clean data model without legacy support
- Old effect format can be completely replaced

If conversion is desired:
- Simple script to convert old effects to new format
- Place all parameters in appropriate sublanes
- Synchronized timing (all sublanes same start/end)

## Implementation Phases

### Phase 1: Data Model & Categorization ✅ COMPLETE (Dec 2024)
- [x] Finalize QLC+ preset categorization into 4 sublanes
- [x] Create sublane block data models (DimmerBlock, ColourBlock, etc.)
- [x] **ENHANCED:** Refactored to support **multiple blocks per sublane type** (List[Block])
- [x] Implement FixtureGroupCapabilities detection from fixture files
- [x] Backward compatibility with auto-migration from old format

### Phase 2: Fixture Capability Detection ✅ COMPLETE (Dec 2024)
- [x] Implement fixture definition file parser
- [x] Create capability detection logic
- [x] Test with various fixture types (dimmer, RGB, moving head, theatrical)
- [x] Cached capabilities in FixtureGroup for performance

### Phase 3: Core Effect Logic ✅ MOSTLY COMPLETE (Dec 2024)
- [x] Implement effect envelope management
- [x] Implement sublane block creation/editing
- [x] Implement gap handling logic (blocks return to defaults)
- [ ] Implement cross-fade logic for Dimmer/Colour (pending playback engine)
- [x] Implement overlap prevention for Movement and Special

### Phase 4: UI Implementation - Timeline ✅ COMPLETE (Dec 2024)
- [x] Render sublanes in timeline widget
- [x] Implement effect envelope rendering (dashed border)
- [x] Implement sublane block rendering (colored by type)
- [x] Add visual indicators (asterisk for modified, colored blocks)
- [x] Implement sublane height calculation based on capabilities

### Phase 5: UI Implementation - Interaction ✅ COMPLETE (Dec 2024)
- [x] Implement click handlers (envelope vs sublane block)
- [x] Implement drag-to-create in sublane
- [x] Implement drag-to-resize sublane blocks
- [x] Implement drag-to-move sublane blocks
- [x] Implement auto-expand envelope on sublane extension
- [x] Implement overlap prevention with **visual feedback** (RED preview)
- [x] Implement selection highlighting
- [x] Implement cursor changes (resize arrows on edges)

### Phase 6: Effect Creation/Editing Dialogs
- [ ] Create/update full effect dialog (all sublanes)
- [ ] Create sublane-specific edit dialogs
- [ ] Implement auto-population of sublanes from effect parameters
- [ ] Add movement interpolation toggle
- [ ] Add modified indicator (*) update logic

### Phase 7: DMX Generation
- [ ] Update DMX generation to read from sublane blocks
- [ ] Implement gap handling in DMX output
- [ ] Implement cross-fade in DMX output
- [ ] Implement movement interpolation in DMX output
- [ ] Test DMX output with various effect combinations

### Phase 8: Testing & Refinement
- [ ] Test with dimmer-only groups
- [ ] Test with RGB groups
- [ ] Test with moving head groups
- [ ] Test with theatrical fixtures (special effects)
- [ ] Test cross-fade functionality
- [ ] Test movement interpolation
- [ ] Test effect envelope auto-expansion
- [ ] Performance testing with many sublane blocks

## Files to be Modified

### Core Models
- `config/models.py` - Add sublane block models, update Effect model

### Fixture Definitions
- `fixtures/*.qxf` (or similar) - Read existing fixture definition files
- New module for parsing fixture definitions and detecting capabilities

### GUI
- `gui/tabs/shows_tab.py` - Main timeline UI, sublane rendering
- `gui/dialogs/` - Effect creation/editing dialogs

### Logic
- DMX generation module - Update to use sublane blocks
- Effect management - Envelope management, sublane block operations

### Configuration
- Configuration save/load - Support new data models

## Success Criteria

### Functionality
- [x] Four sublanes: Dimmer, Colour, Movement, Special
- [ ] Sublane visibility based on fixture group capabilities (auto-detected)
- [ ] Effects create as envelopes containing sublane blocks
- [ ] Sublane blocks are independent (different start/end times)
- [ ] Can create effects via full dialog or drag in sublane
- [ ] Can edit entire effect or individual sublanes
- [ ] Modified effects marked with asterisk
- [ ] Gaps: DMX to 0 (except movement)
- [ ] Movement: Gradual transition in gaps (toggleable)
- [ ] Dimmer/Colour: Cross-fade on overlap
- [ ] Movement/Special: No overlap allowed
- [ ] Sublane extension auto-expands envelope

### Quality
- [ ] Fixture group capabilities correctly detected from definition files
- [ ] UI is intuitive and responsive
- [ ] DMX output is correct for all scenarios
- [ ] No performance degradation with complex shows

## Open Questions / Future Considerations

1. ~~**Special Sublane Priority**: When multiple special effects overlap, which takes priority?~~ **RESOLVED**: No conflicts allowed (same as Movement)
2. ~~**Cross-fade Curve**: Linear cross-fade or other curve options (ease-in/out)?~~ **RESOLVED**: Linear for now, can add curve options later
3. ~~**Movement Interpolation Curve**: Linear interpolation or other curves (ease-in/out, S-curve)?~~ **RESOLVED**: Linear for now, can add curve options later
4. **Undo/Redo**: How to handle multi-sublane operations in undo stack? (decide during implementation)
5. **Copy/Paste**: Should copying a sublane block also copy the envelope? (decide during implementation)
6. **Keyboard Shortcuts**: What shortcuts for sublane-specific operations? (decide during implementation)
7. **Visual Spacing**: How much vertical space per sublane? Fixed or dynamic? (decide during implementation)

## Future Features (Post-Initial Implementation)

### Grid Snap Timing Adjustment
**Feature**: Adjust effect internal timing to grid with Shift+Click+Scroll
- User holds Shift and clicks on effect
- Scroll wheel adjusts internal sublane block timing to snap to grid divisions
- Grid options: 1/8, 1/4, 1/2, etc.
- **Overall effect duration remains unchanged**
- Only internal step timing adjusts
- Example: 4-second effect with 4 steps at irregular intervals → scroll to snap to 1-second grid

**Implementation Later**: This can be easily added after core sublane functionality is working

## Notes for Development

- Think in terms of sublanes, not monolithic effects
- Effect envelope is just a container/grouping mechanism
- Each sublane operates independently
- Always update envelope borders when sublanes extend
- Movement sublane is special (interpolation, no overlaps)
- Read fixture capabilities from actual definition files, don't hardcode
