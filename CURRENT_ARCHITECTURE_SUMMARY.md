# Current Architecture Summary
## For Sublane Feature Implementation Reference

This document summarizes the current codebase architecture relevant to the sublane feature implementation.

## Data Models (`config/models.py`)

### Current Effect Representation

**LightBlock** (lines 75-97):
```python
@dataclass
class LightBlock:
    start_time: float
    duration: float
    effect_name: str  # "module.function" e.g., "bars.static"
    parameters: Dict[str, any]  # {speed, color, intensity, spot}
```

- Currently a single monolithic block
- Contains all parameters in one dict
- **This will be expanded to support sublanes**

**LightLane** (lines 101-128):
```python
@dataclass
class LightLane:
    name: str
    fixture_group: str
    muted: bool
    solo: bool
    light_blocks: List[LightBlock]
```

- Contains a list of LightBlocks
- **Will need to track which sublanes to display based on fixture group capabilities**

### Fixture Model

**Fixture** (lines 20-34):
```python
@dataclass
class Fixture:
    universe: int
    address: int
    manufacturer: str
    model: str
    name: str
    group: str
    direction: str
    current_mode: str
    available_modes: List[FixtureMode]
    type: str  # "PAR", "MH" (Moving Head), "WASH", "BAR"
    x, y, z: float
    rotation: float
```

**FixtureGroup** (lines 45-48):
```python
@dataclass
class FixtureGroup:
    name: str
    fixtures: List[Fixture]
    color: str
```

- **Needs: capability flags (has_dimmer, has_colour, has_movement, has_special)**

## Fixture Definition Files

### Location
- Custom fixtures: `custom_fixtures/*.qxf`
- System fixtures: scanned from OS-specific QLC+ directories (see `_scan_fixture_definitions()` in models.py)

### Format (XML with namespace)
```xml
<FixtureDefinition xmlns="http://www.qlcplus.org/FixtureDefinition">
    <Manufacturer>...</Manufacturer>
    <Model>...</Model>
    <Type>Moving Head</Type>

    <!-- Channels with Preset attributes -->
    <Channel Name="Pan" Preset="PositionPan"/>
    <Channel Name="Dimmer" Preset="IntensityMasterDimmer"/>
    <Channel Name="Red" Preset="IntensityRed"/>
    <Channel Name="Gobo" Preset="GoboWheel"/>
    ...

    <Mode Name="...">
        <Channel Number="0">Pan</Channel>
        ...
    </Mode>
</FixtureDefinition>
```

### Key Attributes
- **Channel Preset**: The crucial attribute for capability detection
  - Examples: `PositionPan`, `IntensityRed`, `IntensityMasterDimmer`, `GoboWheel`
  - Maps directly to our sublane categorization
  - See `SUBLANE_FEATURE_PLAN.md` for full categorization

### Parsing Logic
**In `utils/fixture_utils.py`:**

1. `load_fixture_definitions_from_qlc()` (lines 5-140):
   - Loads fixture definitions for specific models
   - Extracts channels with their preset attributes
   - Returns dict with channel info and capabilities

2. `determine_fixture_type()` (lines 143-189):
   - Currently determines: MH, WASH, BAR, PAR
   - Checks for Pan/Tilt (movement), RGB/RGBW (color), Dimmer
   - **Will be extended to detect all four sublane capabilities**

## Timeline UI Architecture

### Component Hierarchy

```
ShowsTab (gui/tabs/shows_tab.py)
├── MasterTimelineContainer (timeline_ui/master_timeline_widget.py)
├── AudioLaneWidget (timeline_ui/audio_lane_widget.py)
└── LightLaneWidget (timeline_ui/light_lane_widget.py) [MULTIPLE]
    ├── Controls Widget (left side, fixed width 320px)
    │   ├── Name edit
    │   ├── Fixture group combo
    │   └── Mute/Solo/Add Block buttons
    └── TimelineWidget (right side, scrollable)
        └── LightBlockWidget (timeline_ui/light_block_widget.py) [MULTIPLE]
            └── Rendered effect blocks
```

### LightLaneWidget (`timeline_ui/light_lane_widget.py`)

**Current Dimensions:**
- Fixed width controls: 320px (line 86)
- Fixed height: min 80px, max 120px (lines 42-43)
- **Will need: Variable height based on number of sublanes**

**Key Methods:**
- `create_light_block_widget(block)` (line 242): Creates LightBlockWidget for a block
- `add_light_block()` (line 252): Adds new block at playhead position
- `set_zoom_factor()` (line 226): Updates zoom and repositions blocks

**Signals:**
- `remove_requested`
- `scroll_position_changed`
- `zoom_changed`
- `playhead_moved`

### LightBlockWidget (`timeline_ui/light_block_widget.py`)

**Purpose:** Renders individual effect blocks on the timeline

**Likely responsibilities:**
- Drawing the block rectangle
- Handling drag/resize
- Displaying effect name and parameters
- Click to edit

**Will need modification for:**
- Sublane positioning (which sublane to render in)
- Sublane-specific styling
- Envelope vs sublane block distinction

### TimelineWidget (`timeline_ui/timeline_widget.py`)

**Purpose:** The canvas where blocks are drawn

**Will need:**
- Sublane row rendering
- Grid lines per sublane
- Sublane height calculation

## Capability Detection Strategy

### Step 1: Parse Fixture Definition
For each fixture in a group:
1. Get (manufacturer, model) tuple
2. Load fixture definition file (.qxf)
3. Parse XML to extract Channel elements with Preset attributes

### Step 2: Categorize Presets
Map each Preset to a sublane:

| Sublane | Preset Examples |
|---------|----------------|
| Dimmer | `IntensityMasterDimmer`, `IntensityDimmer`, `ShutterStrobeSlowFast` |
| Colour | `IntensityRed`, `IntensityGreen`, `IntensityBlue`, `ColorWheel`, `IntensityHue` |
| Movement | `PositionPan`, `PositionTilt`, `SpeedPanTiltSlowFast` |
| Special | `GoboWheel`, `BeamFocusNearFar`, `PrismRotationSlowFast` |

### Step 3: Determine Group Capabilities
```python
class FixtureGroupCapabilities:
    has_dimmer: bool = False
    has_colour: bool = False
    has_movement: bool = False
    has_special: bool = False

# Logic:
for fixture in group.fixtures:
    fixture_def = load_fixture_definition(fixture)
    for channel in fixture_def.channels:
        preset = channel.preset
        if preset in DIMMER_PRESETS:
            capabilities.has_dimmer = True
        elif preset in COLOUR_PRESETS:
            capabilities.has_colour = True
        # ... etc
```

### Step 4: Apply to UI
- LightLaneWidget checks group capabilities
- Renders only applicable sublanes
- Adjusts height: `num_sublanes * 80px`

## Files That Will Be Modified

### Phase 1: Data Models
- ✅ `config/models.py` - Add sublane block models, update LightBlock and FixtureGroup

### Phase 2: Capability Detection
- ✅ `utils/fixture_utils.py` - Extend capability detection logic
- ✅ New: `utils/sublane_presets.py` - Categorization of QLC+ presets

### Phase 3: Timeline UI
- ✅ `timeline_ui/light_lane_widget.py` - Add sublane rendering
- ✅ `timeline_ui/light_block_widget.py` - Handle sublane positioning
- ✅ `timeline_ui/timeline_widget.py` - Sublane grid and canvas

### Phase 4: Dialogs & Interaction
- ✅ Effect creation/editing dialogs (TBD - need to find existing dialogs)
- ✅ Sublane block interaction handlers

## Key Insights for Implementation

1. **Preset attribute is key**: The `Preset` attribute in fixture channels directly maps to our sublane categorization

2. **Height calculation**:
   - Current: Fixed 80-120px
   - New: Dynamic based on capabilities
   - Suggested: 60-80px per sublane

3. **Block positioning**:
   - Currently: Single row within lane
   - New: Multi-row (one per sublane)
   - Need y-offset calculation based on sublane

4. **Effect envelope concept**:
   - Render as outer border spanning all active sublanes
   - Individual sublane blocks rendered within
   - Click detection: envelope vs sublane block

5. **Backwards compatibility**:
   - Not required per user request
   - Can completely replace old LightBlock format
   - Simplifies implementation

## Next Steps

1. Create sublane block data models (DimmerBlock, ColourBlock, etc.)
2. Create preset categorization mapping
3. Implement fixture capability detection
4. Update LightBlock to contain sublane blocks
5. Modify UI to render sublanes

## References

- Main plan: `SUBLANE_FEATURE_PLAN.md`
- QLC+ Fixture Definition format: http://www.qlcplus.org/FixtureDefinition
- Current effect system: `config/models.py` lines 75-128
- Timeline UI entry point: `gui/tabs/shows_tab.py`
- Lane rendering: `timeline_ui/light_lane_widget.py`
