# Riff System Design for QLC+ Show Creator

## Understanding the Current Structure

Based on the codebase analysis, here's what currently exists:

### Data Hierarchy
```
Show
  └── TimelineData
        └── LightLane (per fixture group)
              └── LightBlock (envelope/effect container)
                    ├── dimmer_blocks: List[DimmerBlock]
                    ├── colour_blocks: List[ColourBlock]
                    ├── movement_blocks: List[MovementBlock]
                    └── special_blocks: List[SpecialBlock]
```

### Key Observations

1. **LightBlock is already an envelope** - it contains lists of sublane blocks and its bounds auto-adjust based on contained blocks via `update_envelope_bounds()`
2. **Sublane blocks are independent** - each has its own `start_time` and `end_time` (absolute times in seconds)
3. **Timing is beat-based** - `SongStructure` provides BPM at any position and `find_nearest_beat_time()` for snapping
4. **Effects are Python functions** - stored in `effects/` folder (e.g., `dimmers.py`), called with fixture/timing params to generate QLC+ XML steps
5. **Capabilities are per-group** - `FixtureGroupCapabilities` determines which sublanes are shown (has_dimmer, has_colour, has_movement, has_special)
6. **Copy/paste exists** - `effect_clipboard.py` already handles copying LightBlocks with time adjustment

### Integration Points for Riffs

The system is well-suited for riffs:
- `timeline_widget.py` has `find_nearest_beat_time()` for snap-to-grid
- `song_structure.py` has `get_bpm_at_time()` for BPM lookup
- `LightBlock.from_dict()` already handles deserialization
- `light_lane.py` has `add_light_block_with_sublanes()` ready to use
- `effect_clipboard.py` pattern shows time offset adjustment

---

## The Riff Concept

A **Riff** is a pre-defined, reusable pattern of sublane blocks measured in **beats** (not seconds). Think of it like a drum pattern:

```
                    Beat: 1     2     3     4     5     6     7     8
Dimmer:             [████████████████████]     [████]           [████]
Colour:             [████████]     [████████████████████████████████]
Movement:           [████████████████████████████████████████████████]
Special:                           [████████████████]
```

When dropped onto the timeline:
- The riff's beat timings get converted to absolute times based on the BPM at that position
- All four lanes are "stamped" onto the timeline
- Not all lanes need content (empty lanes leave the fixture unchanged for that parameter)
- **Fixture-type constraints are checked** (a moving-head riff won't work on PAR lanes)

---

## Proposed Data Model

### Fixture Type Compatibility

Riffs can be either **universal** or **fixture-type specific**:

```python
# Empty fixture_types = universal (works on any fixture)
# Non-empty = requires one of the listed types

fixture_types: List[str] = []  # e.g., ["Moving Head", "Scanner"]
```

### RiffBlock Classes (relative timing in beats)

```python
@dataclass
class RiffDimmerBlock:
    """Dimmer block within a riff - timing is in beats, not seconds."""
    start_beat: float      # e.g., 0.0 = start, 0.5 = half beat in
    end_beat: float        # e.g., 4.0 = ends at beat 4
    
    # Same parameters as DimmerBlock
    intensity: float = 255.0
    strobe_speed: float = 0.0
    iris: float = 255.0
    effect_type: str = "static"  # "static", "twinkle", "strobe", "ping_pong_smooth", "waterfall"
    effect_speed: str = "1"      # "1/4", "1/2", "1", "2", "4"

@dataclass
class RiffColourBlock:
    start_beat: float
    end_beat: float
    color_mode: str = "RGB"  # "RGB", "CMY", "HSV", "Wheel"
    red: float = 255.0
    green: float = 255.0
    blue: float = 255.0
    white: float = 0.0
    amber: float = 0.0
    cyan: float = 0.0
    magenta: float = 0.0
    yellow: float = 0.0
    uv: float = 0.0
    lime: float = 0.0
    hue: float = 0.0
    saturation: float = 0.0
    value: float = 0.0
    color_wheel_position: int = 0
    
@dataclass  
class RiffMovementBlock:
    start_beat: float
    end_beat: float
    pan: float = 127.5
    tilt: float = 127.5
    pan_fine: float = 0.0
    tilt_fine: float = 0.0
    speed: float = 255.0
    interpolate_from_previous: bool = True
    effect_type: str = "static"  # "static", "circle", "diamond", "lissajous", "figure_8", "square", "triangle", "random", "bounce"
    effect_speed: str = "1"
    pan_min: float = 0.0
    pan_max: float = 255.0
    tilt_min: float = 0.0
    tilt_max: float = 255.0
    pan_amplitude: float = 50.0
    tilt_amplitude: float = 50.0
    lissajous_ratio: str = "1:2"
    phase_offset_enabled: bool = False
    phase_offset_degrees: float = 0.0

@dataclass
class RiffSpecialBlock:
    start_beat: float
    end_beat: float
    gobo_index: int = 0
    gobo_rotation: float = 0.0
    focus: float = 127.5
    zoom: float = 127.5
    prism_enabled: bool = False
    prism_rotation: float = 0.0
```

### Riff (the pattern container)

```python
@dataclass
class Riff:
    """A reusable pattern of sublane blocks."""
    name: str                          # e.g., "figure8_sweep_4bar"
    category: str = "general"          # "builds", "fills", "loops", "drops", "movement"
    description: str = ""              
    
    length_beats: float = 4.0          # Total length in beats
    signature: str = "4/4"             # Time signature designed for
    
    # Fixture compatibility - empty list means universal
    fixture_types: List[str] = field(default_factory=list)
    # Examples:
    #   [] = works on any fixture
    #   ["Moving Head"] = only moving heads
    #   ["Moving Head", "Scanner"] = moving heads or scanners
    
    # The actual pattern content
    dimmer_blocks: List[RiffDimmerBlock] = field(default_factory=list)
    colour_blocks: List[RiffColourBlock] = field(default_factory=list)
    movement_blocks: List[RiffMovementBlock] = field(default_factory=list)
    special_blocks: List[RiffSpecialBlock] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    author: str = ""
    version: str = "1.0"
```

---

## Riff Library Structure

### File Format (JSON for consistency)

```json
{
  "name": "figure8_sweep_4bar",
  "category": "movement",
  "description": "4-bar figure-8 sweep with intensity pulse",
  "length_beats": 16,
  "signature": "4/4",
  "fixture_types": ["Moving Head"],
  "tags": ["sweep", "movement", "smooth"],
  "author": "varghele",
  "version": "1.0",
  
  "dimmer_blocks": [
    {
      "start_beat": 0,
      "end_beat": 16,
      "intensity": 200,
      "effect_type": "static",
      "effect_speed": "1"
    }
  ],
  
  "colour_blocks": [
    {
      "start_beat": 0,
      "end_beat": 8,
      "color_mode": "RGB",
      "red": 0,
      "green": 100,
      "blue": 255
    },
    {
      "start_beat": 8,
      "end_beat": 16,
      "color_mode": "RGB",
      "red": 255,
      "green": 0,
      "blue": 100
    }
  ],
  
  "movement_blocks": [
    {
      "start_beat": 0,
      "end_beat": 16,
      "pan": 127.5,
      "tilt": 127.5,
      "effect_type": "figure_8",
      "effect_speed": "1",
      "pan_amplitude": 80,
      "tilt_amplitude": 60,
      "phase_offset_enabled": true,
      "phase_offset_degrees": 45
    }
  ],
  
  "special_blocks": []
}
```

### Universal Riff Example (works on any fixture)

```json
{
  "name": "strobe_build_4bar",
  "category": "builds",
  "description": "4-bar strobe intensity build",
  "length_beats": 16,
  "signature": "4/4",
  "fixture_types": [],
  "tags": ["build", "strobe", "intense"],
  
  "dimmer_blocks": [
    {
      "start_beat": 0,
      "end_beat": 4,
      "intensity": 100,
      "effect_type": "strobe",
      "effect_speed": "1/2"
    },
    {
      "start_beat": 4,
      "end_beat": 8,
      "intensity": 150,
      "effect_type": "strobe",
      "effect_speed": "1"
    },
    {
      "start_beat": 8,
      "end_beat": 12,
      "intensity": 200,
      "effect_type": "strobe",
      "effect_speed": "2"
    },
    {
      "start_beat": 12,
      "end_beat": 16,
      "intensity": 255,
      "effect_type": "strobe",
      "effect_speed": "4"
    }
  ],
  
  "colour_blocks": [],
  "movement_blocks": [],
  "special_blocks": []
}
```

### Directory Structure

```
riffs/
├── builds/
│   ├── strobe_build_4bar.json
│   ├── intensity_crescendo_8bar.json
│   └── slow_fade_16bar.json
├── fills/
│   ├── flash_hit_1bar.json
│   ├── color_sweep_2bar.json
│   └── strobe_fill_4bar.json
├── loops/
│   ├── chase_4bar.json
│   ├── rainbow_cycle_8bar.json
│   └── twinkle_loop_4bar.json
├── drops/
│   ├── blackout_instant.json
│   ├── strobe_drop_4bar.json
│   └── full_blast_8bar.json
├── movement/
│   ├── figure8_sweep_4bar.json
│   ├── circle_slow_8bar.json
│   ├── diamond_chase_4bar.json
│   └── lissajous_complex_8bar.json
└── custom/
    └── (user-created riffs)
```

---

## Core Implementation

### RiffLibrary Class

```python
class RiffLibrary:
    """Manages the collection of available riffs."""
    
    def __init__(self, riffs_directory: str = "riffs"):
        self.riffs_dir = riffs_directory
        self.riffs: Dict[str, Riff] = {}  # name -> Riff
        self.by_category: Dict[str, List[Riff]] = {}
        self.load_all_riffs()
    
    def load_all_riffs(self):
        """Load all riff JSON files from the riffs directory."""
        for category_dir in os.listdir(self.riffs_dir):
            category_path = os.path.join(self.riffs_dir, category_dir)
            if os.path.isdir(category_path):
                for filename in os.listdir(category_path):
                    if filename.endswith('.json'):
                        filepath = os.path.join(category_path, filename)
                        riff = self.load_riff(filepath)
                        if riff:
                            self.riffs[riff.name] = riff
                            self.by_category.setdefault(riff.category, []).append(riff)
    
    def load_riff(self, filepath: str) -> Optional[Riff]:
        """Load a single riff from JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return Riff.from_dict(data)
        except Exception as e:
            print(f"Error loading riff {filepath}: {e}")
            return None
    
    def get_compatible_riffs(self, fixture_group: FixtureGroup) -> List[Riff]:
        """Get all riffs compatible with a fixture group."""
        compatible = []
        for riff in self.riffs.values():
            is_compat, _ = riff.is_compatible_with(fixture_group)
            if is_compat:
                compatible.append(riff)
        return compatible
    
    def save_riff(self, riff: Riff, filepath: str = None):
        """Save a riff to JSON file."""
        if filepath is None:
            filepath = os.path.join(self.riffs_dir, riff.category, f"{riff.name}.json")
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(riff.to_dict(), f, indent=2)
```

### Riff Compatibility Check

```python
def is_compatible_with(self, fixture_group: FixtureGroup) -> tuple[bool, str]:
    """Check if riff can be used with a fixture group.
    
    Returns:
        (is_compatible, reason_if_not)
    """
    # Check fixture type compatibility
    if self.fixture_types:
        group_types = {f.type for f in fixture_group.fixtures}
        if not any(ft in group_types for ft in self.fixture_types):
            return False, f"Requires fixture type: {', '.join(self.fixture_types)}"
    
    # Check capability compatibility
    caps = fixture_group.capabilities
    
    if self.movement_blocks and not caps.has_movement:
        return False, "Requires movement capability (pan/tilt)"
    if self.special_blocks and not caps.has_special:
        return False, "Requires special capability (gobo/prism)"
        
    return True, ""
```

### Beat-to-Time Conversion

```python
def to_light_block(self, start_time: float, bpm: float) -> LightBlock:
    """Convert riff to an absolute-timed LightBlock at given position."""
    seconds_per_beat = 60.0 / bpm
    
    # Convert each sublane block type
    dimmer_blocks = [
        DimmerBlock(
            start_time=start_time + (rb.start_beat * seconds_per_beat),
            end_time=start_time + (rb.end_beat * seconds_per_beat),
            intensity=rb.intensity,
            strobe_speed=rb.strobe_speed,
            iris=rb.iris,
            effect_type=rb.effect_type,
            effect_speed=rb.effect_speed
        )
        for rb in self.dimmer_blocks
    ]
    
    # ... similar for colour_blocks, movement_blocks, special_blocks
    
    end_time = start_time + (self.length_beats * seconds_per_beat)
    
    return LightBlock(
        start_time=start_time,
        end_time=end_time,
        effect_name=f"riff:{self.name}",
        modified=False,
        dimmer_blocks=dimmer_blocks,
        colour_blocks=colour_blocks,
        movement_blocks=movement_blocks,
        special_blocks=special_blocks
    )
```

### Capture Selection as Riff

```python
def capture_as_riff(light_block: LightBlock, bpm: float, 
                    name: str, category: str = "custom",
                    fixture_types: List[str] = None) -> Riff:
    """Convert an existing LightBlock to a reusable Riff."""
    seconds_per_beat = 60.0 / bpm
    reference_time = light_block.start_time
    
    # Convert absolute times to beat offsets
    dimmer_blocks = [
        RiffDimmerBlock(
            start_beat=(db.start_time - reference_time) / seconds_per_beat,
            end_beat=(db.end_time - reference_time) / seconds_per_beat,
            intensity=db.intensity,
            strobe_speed=db.strobe_speed,
            iris=db.iris,
            effect_type=db.effect_type,
            effect_speed=db.effect_speed
        )
        for db in light_block.dimmer_blocks
    ]
    
    # ... similar for other block types
    
    return Riff(
        name=name,
        category=category,
        length_beats=(light_block.end_time - reference_time) / seconds_per_beat,
        fixture_types=fixture_types or [],
        dimmer_blocks=dimmer_blocks,
        colour_blocks=colour_blocks,
        movement_blocks=movement_blocks,
        special_blocks=special_blocks
    )
```

---

## UI Integration

### Riff Browser Panel

```
┌─────────────────────────────────────────┐
│ Riff Library                    [+ New] │
├─────────────────────────────────────────┤
│ 🔍 Search...          [Filter: All ▼]   │
├─────────────────────────────────────────┤
│ ▼ Builds                                │
│   ├─ strobe_build_4bar (4 bars)     ○   │
│   ├─ intensity_crescendo_8bar (8)   ○   │
│   └─ slow_fade_16bar (16 bars)      ○   │
│ ▶ Fills                                 │
│ ▶ Loops                                 │
│ ▶ Drops                                 │
│ ▼ Movement                          ⚡  │
│   ├─ figure8_sweep_4bar (4 bars)    MH  │
│   ├─ circle_slow_8bar (8 bars)      MH  │
│   └─ diamond_chase_4bar (4 bars)    MH  │
│ ▶ Custom                                │
└─────────────────────────────────────────┘

Legend:
  ○  = Universal (works on any fixture)
  MH = Moving Head only
  ⚡ = Category contains fixture-specific riffs
```

### Drag & Drop Workflow

1. User drags riff from library onto a lane's timeline
2. System checks: `riff.is_compatible_with(lane.fixture_group)`
   - If incompatible: show error tooltip, reject drop
   - If compatible: continue
3. Ghost preview shows where it will land (snapped to beat grid)
4. On drop:
   - Get BPM at drop position: `song_structure.get_bpm_at_time(target_time)`
   - Convert riff to LightBlock: `riff.to_light_block(target_time, bpm)`
   - Add to lane: `lane.light_blocks.append(light_block)`
   - Create widget: `create_light_block_widget(light_block)`

### Right-Click Context Menu on LightBlock

```
┌────────────────────────────┐
│ Edit Effect Envelope...    │
├────────────────────────────┤
│ Save as Riff...            │  ← New option
│ Detach from Riff           │  ← Only if riff-derived
│ Update from Riff           │  ← Only if riff-derived
├────────────────────────────┤
│ Copy Effect                │
├────────────────────────────┤
│ Delete Entire Effect       │
└────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core Data Model (models.py additions)
- [ ] Add `RiffDimmerBlock`, `RiffColourBlock`, `RiffMovementBlock`, `RiffSpecialBlock` dataclasses
- [ ] Add `Riff` dataclass with `to_dict()`, `from_dict()`, `to_light_block()`, `is_compatible_with()`
- [ ] Add JSON serialization matching existing patterns

### Phase 2: Riff Library
- [ ] Create `RiffLibrary` class in new `riffs/riff_library.py`
- [ ] Implement `load_all_riffs()`, `save_riff()`, `get_compatible_riffs()`
- [ ] Create `riffs/` directory structure
- [ ] Add 5-10 starter riffs

### Phase 3: UI - Browser Panel
- [ ] Create `RiffBrowserWidget` (collapsible panel or tab)
- [ ] Tree view by category with compatibility indicators
- [ ] Search/filter functionality
- [ ] Drag source implementation

### Phase 4: UI - Timeline Integration
- [ ] Add drop target handling to `LightLaneWidget`
- [ ] Implement ghost preview during drag
- [ ] Compatibility checking with visual feedback
- [ ] "Save as Riff" dialog and context menu

### Phase 5: Preset Riffs
- [ ] Create 20-30 useful preset riffs across categories
- [ ] Include both universal and fixture-specific riffs
- [ ] Test with various fixture types

### Phase 6: Advanced Features
- [ ] Riff editor (visual beat-based editor)
- [ ] Riff variants (color variations)
- [ ] Import/export riff packs
- [ ] Riff preview (visualize without dropping)

---

## Questions Resolved

1. **Beat-based timing?** ✅ Yes - riffs adapt to BPM at drop position

2. **File format?** ✅ JSON for consistency with existing config

3. **Fixture-group specific?** ✅ Via `fixture_types` field:
   - Empty list = universal
   - `["Moving Head"]` = moving heads only
   - `["Moving Head", "Scanner"]` = either type

4. **Riff relationships?** ✅ Tracked via `effect_name = "riff:riff_name"`, enables "Update from Riff"

5. **Partial riffs?** ✅ Empty sublane lists are valid - only populated lanes create blocks
