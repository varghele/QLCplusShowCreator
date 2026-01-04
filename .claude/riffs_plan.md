# Riff System Implementation Plan

## Overview

This document outlines the implementation plan for adding a **Riff System** to the QLC+ Show Creator. A Riff is a reusable, beat-based pattern of lighting effects that can be dropped onto the timeline and automatically adapts to the local BPM.

**Related Design Document**: `.claude/riff_design_v2.md`

---

## Design Decisions

The following decisions were made during planning:

| Question | Decision |
|----------|----------|
| **Insertion with overlap** | Replace existing blocks in the overlap region |
| **BPM transitions** | Stretch riff to match tempo - calculate each beat individually using `get_bpm_at_time()` |
| **Modification tracking** | Track at individual block level (`modified: bool` per sublane block) |
| **Empty sublanes** | Don't create blocks for empty sublanes; undefined = no effect on that parameter |
| **Replace feedback** | Visual indicator during drag + Ctrl+Z undo support |
| **Riff preview** | Names and metadata only (simple list, no visual pattern preview) |
| **Browser location** | Dockable panel similar to Effects Library |
| **Phase offset** | Set directly in movement subblock (no auto-distribution needed) |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Riff System                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ Riff Model   │    │ RiffLibrary  │    │ RiffBrowserWidget│  │
│  │ (models.py)  │───▶│ (riff_lib.py)│───▶│ (riff_browser.py)│  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│         │                   │                     │             │
│         │                   │                     │ drag        │
│         ▼                   ▼                     ▼             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Timeline Integration                   │  │
│  │  - LightLaneWidget: drop handling, overlap detection      │  │
│  │  - LightBlockWidget: riff-source tracking, visual badge   │  │
│  │  - UndoManager: undo/redo for riff operations             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Core Data Model

### Files to Modify
- `config/models.py` - Add riff dataclasses and extend LightBlock

### New Dataclasses

#### Beat-Based Riff Block Classes

```python
@dataclass
class RiffDimmerBlock:
    """Dimmer block within a riff - timing is in beats, not seconds."""
    start_beat: float      # e.g., 0.0 = start of riff
    end_beat: float        # e.g., 4.0 = ends at beat 4

    # Parameters (same as DimmerBlock)
    intensity: float = 255.0
    strobe_speed: float = 0.0
    iris: float = 255.0
    effect_type: str = "static"
    effect_speed: str = "1"


@dataclass
class RiffColourBlock:
    """Colour block within a riff - timing is in beats."""
    start_beat: float
    end_beat: float

    # Parameters (same as ColourBlock)
    color_mode: str = "RGB"
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
    """Movement block within a riff - timing is in beats."""
    start_beat: float
    end_beat: float

    # Parameters (same as MovementBlock)
    pan: float = 127.5
    tilt: float = 127.5
    pan_fine: float = 0.0
    tilt_fine: float = 0.0
    speed: float = 255.0
    interpolate_from_previous: bool = True
    effect_type: str = "static"
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
    """Special block within a riff - timing is in beats."""
    start_beat: float
    end_beat: float

    # Parameters (same as SpecialBlock)
    gobo_index: int = 0
    gobo_rotation: float = 0.0
    focus: float = 127.5
    zoom: float = 127.5
    prism_enabled: bool = False
    prism_rotation: float = 0.0
```

#### Riff Container Class

```python
@dataclass
class Riff:
    """A reusable pattern of sublane blocks measured in beats."""
    name: str
    category: str = "general"
    description: str = ""

    length_beats: float = 4.0
    signature: str = "4/4"

    # Fixture compatibility - empty list means universal
    fixture_types: List[str] = field(default_factory=list)

    # Content - empty lists mean "no effect on this sublane"
    dimmer_blocks: List[RiffDimmerBlock] = field(default_factory=list)
    colour_blocks: List[RiffColourBlock] = field(default_factory=list)
    movement_blocks: List[RiffMovementBlock] = field(default_factory=list)
    special_blocks: List[RiffSpecialBlock] = field(default_factory=list)

    # Metadata
    tags: List[str] = field(default_factory=list)
    author: str = ""
    version: str = "1.0"

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> 'Riff':
        """Deserialize from dictionary."""
        ...

    def is_compatible_with(self, fixture_group) -> tuple[bool, str]:
        """Check if riff can be used with fixture group.
        Returns (is_compatible, reason_if_not).
        """
        ...

    def to_light_block(self, start_time: float, song_structure) -> 'LightBlock':
        """Convert riff to absolute-timed LightBlock.
        Uses song_structure.get_bpm_at_time() for each beat.
        """
        ...
```

### LightBlock Extensions

Add the following fields to the existing `LightBlock` dataclass:

```python
@dataclass
class LightBlock:
    # ... existing fields ...

    # Riff tracking (new fields)
    riff_source: Optional[str] = None      # e.g., "builds/strobe_build_4bar"
    riff_version: Optional[str] = None     # e.g., "1.0"
```

### Sublane Block Modifications

Add `modified` flag to each sublane block type:

```python
@dataclass
class DimmerBlock:
    # ... existing fields ...
    modified: bool = False  # True if user edited this block after riff insertion

@dataclass
class ColourBlock:
    # ... existing fields ...
    modified: bool = False

@dataclass
class MovementBlock:
    # ... existing fields ...
    modified: bool = False

@dataclass
class SpecialBlock:
    # ... existing fields ...
    modified: bool = False
```

---

## Phase 2: BPM-Aware Beat-to-Time Conversion

### Key Algorithm: `Riff.to_light_block()`

This is the core algorithm that converts beat-based timing to absolute seconds while respecting BPM changes.

```python
def to_light_block(self, start_time: float, song_structure) -> LightBlock:
    """
    Convert riff to absolute-timed LightBlock.

    Each beat is individually converted using get_bpm_at_time() to handle
    BPM transitions correctly. The riff "stretches" to match the grid.
    """

    def beat_to_time(beat_offset: float) -> float:
        """Convert a beat offset from riff start to absolute time.

        Algorithm:
        1. Start at riff insertion time
        2. For each beat (or fraction), get BPM at current position
        3. Calculate time for that beat segment
        4. Accumulate total time

        For efficiency, we sample at quarter-beat intervals.
        """
        if beat_offset <= 0:
            return start_time

        current_time = start_time
        remaining_beats = beat_offset
        sample_size = 0.25  # Quarter-beat samples for accuracy

        while remaining_beats > 0:
            # Get BPM at current position
            bpm = song_structure.get_bpm_at_time(current_time)
            seconds_per_beat = 60.0 / bpm

            # Calculate time for this sample
            beats_this_sample = min(remaining_beats, sample_size)
            time_this_sample = beats_this_sample * seconds_per_beat

            current_time += time_this_sample
            remaining_beats -= beats_this_sample

        return current_time

    # Convert dimmer blocks
    dimmer_blocks = []
    for rb in self.dimmer_blocks:
        dimmer_blocks.append(DimmerBlock(
            start_time=beat_to_time(rb.start_beat),
            end_time=beat_to_time(rb.end_beat),
            intensity=rb.intensity,
            strobe_speed=rb.strobe_speed,
            iris=rb.iris,
            effect_type=rb.effect_type,
            effect_speed=rb.effect_speed,
            modified=False  # Fresh from riff
        ))

    # Similar conversion for colour_blocks, movement_blocks, special_blocks
    # ...

    return LightBlock(
        start_time=start_time,
        end_time=beat_to_time(self.length_beats),
        effect_name=f"riff:{self.name}",
        modified=False,
        dimmer_blocks=dimmer_blocks,
        colour_blocks=colour_blocks,
        movement_blocks=movement_blocks,
        special_blocks=special_blocks,
        riff_source=f"{self.category}/{self.name}",
        riff_version=self.version
    )
```

### Optimization Note

For riffs that don't span BPM transitions (the common case), the algorithm can be optimized to use a single BPM value. Check if `get_bpm_at_time(start_time) == get_bpm_at_time(end_time)` and use simple multiplication if true.

---

## Phase 3: Riff Library

### New File: `riffs/riff_library.py`

```python
class RiffLibrary:
    """Manages the collection of available riffs."""

    def __init__(self, riffs_directory: str = "riffs"):
        self.riffs_dir = riffs_directory
        self.riffs: Dict[str, Riff] = {}           # "category/name" -> Riff
        self.by_category: Dict[str, List[Riff]] = {}
        self._load_all_riffs()

    def _load_all_riffs(self):
        """Scan riffs directory and load all JSON files."""
        ...

    def load_riff(self, filepath: str) -> Optional[Riff]:
        """Load single riff from JSON file."""
        ...

    def save_riff(self, riff: Riff, category: str = None) -> str:
        """Save riff to JSON file. Returns filepath."""
        ...

    def get_compatible_riffs(self, fixture_group) -> List[Riff]:
        """Get all riffs compatible with fixture group's capabilities."""
        ...

    def get_categories(self) -> List[str]:
        """Get list of category names."""
        ...

    def get_riffs_in_category(self, category: str) -> List[Riff]:
        """Get all riffs in a category."""
        ...

    def search(self, query: str, fixture_group=None) -> List[Riff]:
        """Search riffs by name, description, or tags."""
        ...

    def refresh(self):
        """Reload all riffs from disk."""
        ...
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
│   └── strobe_accent_half.json
├── loops/
│   ├── pulse_4bar.json
│   ├── rainbow_cycle_8bar.json
│   └── twinkle_loop_4bar.json
├── drops/
│   ├── blackout_instant.json
│   ├── full_blast_4bar.json
│   └── strobe_drop_2bar.json
├── movement/
│   ├── figure8_sweep_4bar.json
│   ├── circle_slow_8bar.json
│   ├── pan_sweep_2bar.json
│   └── tilt_nod_1bar.json
└── custom/
    └── (user-created riffs)
```

### JSON File Format

```json
{
  "name": "strobe_build_4bar",
  "category": "builds",
  "description": "4-bar strobe intensity build with increasing speed",
  "length_beats": 16,
  "signature": "4/4",
  "fixture_types": [],
  "tags": ["build", "strobe", "intense", "drop-prep"],
  "author": "preset",
  "version": "1.0",

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

---

## Phase 4: Riff Browser Widget

### New File: `timeline_ui/riff_browser_widget.py`

```python
class RiffBrowserWidget(QDockWidget):
    """Dockable panel for browsing and selecting riffs."""

    # Signals
    riff_drag_started = pyqtSignal(Riff)

    def __init__(self, riff_library: RiffLibrary, parent=None):
        ...

    def _setup_ui(self):
        """Create the browser UI."""
        # Search bar at top
        # Category tree view (collapsible)
        # Riff items with metadata
        ...

    def set_fixture_filter(self, fixture_group):
        """Filter to show only compatible riffs."""
        ...

    def _on_item_drag_start(self, item):
        """Start drag operation with riff data."""
        ...
```

### UI Layout

```
┌─────────────────────────────────────────┐
│ Riff Library                    [+ New] │
├─────────────────────────────────────────┤
│ 🔍 Search...              [Filter ▼]    │
├─────────────────────────────────────────┤
│ ▼ builds                                │
│   ├─ strobe_build_4bar                  │
│   │   4 bars │ ○ Universal              │
│   ├─ intensity_crescendo_8bar           │
│   │   8 bars │ ○ Universal              │
│   └─ slow_fade_16bar                    │
│       16 bars │ ○ Universal             │
│                                         │
│ ▶ fills                                 │
│ ▶ loops                                 │
│ ▶ drops                                 │
│                                         │
│ ▼ movement                              │
│   ├─ figure8_sweep_4bar                 │
│   │   4 bars │ MH Moving Head           │
│   ├─ circle_slow_8bar                   │
│   │   8 bars │ MH Moving Head           │
│   └─ pan_sweep_2bar                     │
│       2 bars │ MH Moving Head           │
│                                         │
│ ▶ custom                                │
└─────────────────────────────────────────┘

Legend:
  ○  = Universal (works on any fixture)
  MH = Moving Head only
  SC = Scanner only
```

### Drag-and-Drop Implementation

The riff browser uses Qt's drag-and-drop system:

```python
def _start_drag(self, riff: Riff):
    """Initiate drag operation."""
    drag = QDrag(self)
    mime_data = QMimeData()

    # Serialize riff reference
    mime_data.setData("application/x-qlc-riff",
                      json.dumps({"path": f"{riff.category}/{riff.name}"}).encode())

    drag.setMimeData(mime_data)

    # Create drag pixmap (simple rectangle with name)
    pixmap = self._create_drag_pixmap(riff)
    drag.setPixmap(pixmap)

    drag.exec_(Qt.CopyAction)
```

---

## Phase 5: Timeline Integration

### Modify: `timeline_ui/light_lane_widget.py`

#### Accept Drop Events

```python
class LightLaneWidget(QWidget):
    def __init__(self, ...):
        ...
        self.setAcceptDrops(True)
        self._drop_preview = None  # For ghost preview
        self._overlap_blocks = []  # Blocks that will be replaced

    def dragEnterEvent(self, event):
        """Check if we can accept this drop."""
        if event.mimeData().hasFormat("application/x-qlc-riff"):
            riff_path = self._get_riff_from_mime(event.mimeData())
            riff = self.riff_library.get_riff(riff_path)

            if riff:
                is_compatible, reason = riff.is_compatible_with(self.fixture_group)
                if is_compatible:
                    event.acceptProposedAction()
                    return

        event.ignore()

    def dragMoveEvent(self, event):
        """Update drop preview position."""
        if event.mimeData().hasFormat("application/x-qlc-riff"):
            # Calculate drop position (snapped to beat)
            drop_time = self._pixel_to_time(event.pos().x())
            snapped_time = self.timeline.find_nearest_beat_time(drop_time)

            # Get riff and calculate end time
            riff = self._get_riff_from_mime(event.mimeData())
            end_time = self._calculate_riff_end_time(riff, snapped_time)

            # Find overlapping blocks for visual feedback
            self._overlap_blocks = self._find_overlapping_blocks(snapped_time, end_time)

            # Update preview
            self._drop_preview = {
                'start_time': snapped_time,
                'end_time': end_time,
                'riff': riff,
                'has_overlap': len(self._overlap_blocks) > 0
            }

            self.update()  # Trigger repaint

    def dropEvent(self, event):
        """Handle riff drop - create LightBlock and replace overlaps."""
        riff = self._get_riff_from_mime(event.mimeData())
        start_time = self._drop_preview['start_time']

        # Create undo command
        command = InsertRiffCommand(
            lane=self,
            riff=riff,
            start_time=start_time,
            overlap_blocks=self._overlap_blocks.copy()
        )
        self.undo_stack.push(command)

        # Clear preview
        self._drop_preview = None
        self._overlap_blocks = []
        self.update()

    def paintEvent(self, event):
        """Draw lane including drop preview."""
        super().paintEvent(event)

        if self._drop_preview:
            self._draw_drop_preview(painter)
            self._draw_overlap_indicators(painter)
```

#### Visual Feedback During Drag

```python
def _draw_drop_preview(self, painter):
    """Draw semi-transparent preview of riff placement."""
    preview = self._drop_preview

    # Calculate pixel positions
    start_x = self._time_to_pixel(preview['start_time'])
    end_x = self._time_to_pixel(preview['end_time'])

    # Draw ghost rectangle
    color = QColor(100, 200, 100, 100)  # Semi-transparent green
    if preview['has_overlap']:
        color = QColor(200, 150, 100, 100)  # Semi-transparent orange (warning)

    painter.fillRect(start_x, 0, end_x - start_x, self.height(), color)

    # Draw riff name
    painter.setPen(Qt.white)
    painter.drawText(start_x + 5, 20, preview['riff'].name)

def _draw_overlap_indicators(self, painter):
    """Highlight blocks that will be replaced."""
    for block in self._overlap_blocks:
        start_x = self._time_to_pixel(block.start_time)
        end_x = self._time_to_pixel(block.end_time)

        # Draw red border around blocks to be replaced
        painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
        painter.drawRect(start_x, 0, end_x - start_x, self.height())
```

### Overlap Detection and Replacement

```python
def _find_overlapping_blocks(self, start_time: float, end_time: float) -> List[LightBlock]:
    """Find all light blocks that overlap with the given time range."""
    overlapping = []
    for block in self.light_lane.light_blocks:
        # Check for any overlap
        if block.start_time < end_time and block.end_time > start_time:
            overlapping.append(block)
    return overlapping

def _remove_overlapping_sublane_blocks(self, light_block: LightBlock,
                                        start_time: float, end_time: float):
    """Remove or trim sublane blocks that overlap with riff insertion range.

    For each sublane block:
    - If completely inside range: remove it
    - If partially overlapping: trim to not overlap
    """
    for block_list in [light_block.dimmer_blocks, light_block.colour_blocks,
                       light_block.movement_blocks, light_block.special_blocks]:
        to_remove = []
        to_add = []

        for block in block_list:
            if block.end_time <= start_time or block.start_time >= end_time:
                # No overlap, keep as-is
                continue
            elif block.start_time >= start_time and block.end_time <= end_time:
                # Completely inside, remove
                to_remove.append(block)
            elif block.start_time < start_time and block.end_time > end_time:
                # Riff is inside block, split into two
                # Create right portion
                right_block = copy.copy(block)
                right_block.start_time = end_time
                to_add.append(right_block)
                # Trim left portion
                block.end_time = start_time
            elif block.start_time < start_time:
                # Overlaps on left, trim right edge
                block.end_time = start_time
            else:
                # Overlaps on right, trim left edge
                block.start_time = end_time

        for block in to_remove:
            block_list.remove(block)
        block_list.extend(to_add)
```

---

## Phase 6: Undo/Redo Support

### New File: `timeline_ui/undo_commands.py`

```python
class InsertRiffCommand(QUndoCommand):
    """Undoable command for inserting a riff."""

    def __init__(self, lane, riff, start_time, overlap_blocks):
        super().__init__(f"Insert Riff: {riff.name}")
        self.lane = lane
        self.riff = riff
        self.start_time = start_time

        # Store state for undo
        self.removed_blocks = []  # Complete blocks removed
        self.trimmed_blocks = []  # (block, original_start, original_end)
        self.created_block = None

        # Capture overlap state before modification
        for block in overlap_blocks:
            self.removed_blocks.append(copy.deepcopy(block))

    def redo(self):
        """Insert riff, replacing overlaps."""
        # Remove/trim overlapping blocks
        # ... (as described in overlap handling)

        # Convert riff to LightBlock
        self.created_block = self.riff.to_light_block(
            self.start_time,
            self.lane.song_structure
        )

        # Add to lane
        self.lane.add_light_block(self.created_block)

    def undo(self):
        """Remove inserted riff, restore overlaps."""
        # Remove the created block
        self.lane.remove_light_block(self.created_block)

        # Restore removed blocks
        for block in self.removed_blocks:
            self.lane.add_light_block(copy.deepcopy(block))

        # Restore trimmed blocks to original bounds
        for block, orig_start, orig_end in self.trimmed_blocks:
            block.start_time = orig_start
            block.end_time = orig_end
```

### Integration with Main Window

```python
class MainWindow(QMainWindow):
    def __init__(self):
        ...
        self.undo_stack = QUndoStack(self)

        # Create undo/redo actions
        self.undo_action = self.undo_stack.createUndoAction(self, "Undo")
        self.undo_action.setShortcut(QKeySequence.Undo)  # Ctrl+Z

        self.redo_action = self.undo_stack.createRedoAction(self, "Redo")
        self.redo_action.setShortcut(QKeySequence.Redo)  # Ctrl+Y or Ctrl+Shift+Z
```

---

## Phase 7: Context Menu - Save as Riff

### Modify: `timeline_ui/light_block_widget.py`

```python
def _show_context_menu(self, pos):
    """Show right-click context menu."""
    menu = QMenu(self)

    # Existing options
    menu.addAction("Edit Effect Envelope...", self._edit_envelope)
    menu.addSeparator()

    # Riff options
    menu.addAction("Save as Riff...", self._save_as_riff)

    if self.light_block.riff_source:
        menu.addAction("Detach from Riff", self._detach_from_riff)
        menu.addAction("Update from Riff", self._update_from_riff)

    menu.addSeparator()
    menu.addAction("Copy Effect", self._copy_effect)
    menu.addSeparator()
    menu.addAction("Delete Entire Effect", self._delete_effect)

    menu.exec_(self.mapToGlobal(pos))
```

### Save as Riff Dialog

```python
class SaveAsRiffDialog(QDialog):
    """Dialog for saving a LightBlock as a reusable riff."""

    def __init__(self, light_block, current_bpm, parent=None):
        ...
        self.light_block = light_block
        self.current_bpm = current_bpm

    def _setup_ui(self):
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow("Name:", self.name_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["builds", "fills", "loops", "drops",
                                       "movement", "custom"])
        self.category_combo.setCurrentText("custom")
        layout.addRow("Category:", self.category_combo)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        layout.addRow("Description:", self.description_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("comma, separated, tags")
        layout.addRow("Tags:", self.tags_edit)

        self.fixture_types_group = QGroupBox("Fixture Compatibility")
        # Checkboxes for fixture types or "Universal"
        layout.addRow(self.fixture_types_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def create_riff(self) -> Riff:
        """Convert LightBlock to Riff using current BPM."""
        return capture_as_riff(
            self.light_block,
            self.current_bpm,
            name=self.name_edit.text(),
            category=self.category_combo.currentText(),
            description=self.description_edit.toPlainText(),
            tags=[t.strip() for t in self.tags_edit.text().split(",")],
            fixture_types=self._get_selected_fixture_types()
        )
```

### Capture as Riff Function

```python
def capture_as_riff(light_block: LightBlock, bpm: float,
                    name: str, category: str = "custom",
                    description: str = "", tags: List[str] = None,
                    fixture_types: List[str] = None) -> Riff:
    """Convert an existing LightBlock to a reusable Riff."""

    seconds_per_beat = 60.0 / bpm
    reference_time = light_block.start_time

    def time_to_beat(time: float) -> float:
        """Convert absolute time to beat offset from block start."""
        return (time - reference_time) / seconds_per_beat

    # Convert dimmer blocks
    riff_dimmer_blocks = [
        RiffDimmerBlock(
            start_beat=time_to_beat(db.start_time),
            end_beat=time_to_beat(db.end_time),
            intensity=db.intensity,
            strobe_speed=db.strobe_speed,
            iris=db.iris,
            effect_type=db.effect_type,
            effect_speed=db.effect_speed
        )
        for db in light_block.dimmer_blocks
    ]

    # Similar for colour, movement, special blocks
    # ...

    length_beats = time_to_beat(light_block.end_time)

    return Riff(
        name=name,
        category=category,
        description=description,
        length_beats=length_beats,
        fixture_types=fixture_types or [],
        tags=tags or [],
        dimmer_blocks=riff_dimmer_blocks,
        colour_blocks=riff_colour_blocks,
        movement_blocks=riff_movement_blocks,
        special_blocks=riff_special_blocks
    )
```

---

## Phase 8: Riff Update Tracking

### Modification Detection

When a sublane block is edited, mark it as modified:

```python
# In sublane block dialogs (dimmer_block_dialog.py, etc.)
def accept(self):
    """Apply changes and mark as modified."""
    # ... apply parameter changes ...

    self.block.modified = True  # Mark this specific block as modified

    super().accept()

# In light_block_widget.py - intensity handle drag
def _on_intensity_drag_complete(self):
    self.dragging_intensity_handle.modified = True
```

### Update from Riff

```python
def _update_from_riff(self):
    """Update unmodified sublane blocks from source riff."""
    if not self.light_block.riff_source:
        return

    riff = self.riff_library.get_riff(self.light_block.riff_source)
    if not riff or riff.version == self.light_block.riff_version:
        return  # No update available

    # Convert riff to temporary block for comparison
    temp_block = riff.to_light_block(
        self.light_block.start_time,
        self.song_structure
    )

    # Update only unmodified blocks
    for sublane_type in ['dimmer_blocks', 'colour_blocks',
                         'movement_blocks', 'special_blocks']:
        current_blocks = getattr(self.light_block, sublane_type)
        new_blocks = getattr(temp_block, sublane_type)

        # Replace unmodified blocks
        for i, block in enumerate(current_blocks):
            if not block.modified and i < len(new_blocks):
                current_blocks[i] = new_blocks[i]

    # Update version
    self.light_block.riff_version = riff.version
```

### Visual Indicator for Riff-Linked Blocks

```python
def _draw_riff_badge(self, painter):
    """Draw small badge indicating block is linked to a riff."""
    if self.light_block.riff_source:
        # Draw small "R" badge in corner
        badge_rect = QRect(self.width() - 20, 2, 18, 16)

        # Different color if modified
        has_modifications = any(
            b.modified for b in
            self.light_block.dimmer_blocks +
            self.light_block.colour_blocks +
            self.light_block.movement_blocks +
            self.light_block.special_blocks
        )

        if has_modifications:
            painter.fillRect(badge_rect, QColor(200, 150, 50))  # Orange
        else:
            painter.fillRect(badge_rect, QColor(100, 150, 200))  # Blue

        painter.setPen(Qt.white)
        painter.drawText(badge_rect, Qt.AlignCenter, "R")
```

---

## Phase 9: Starter Riff Collection

Create 15 preset riffs across categories:

### builds/ (3 riffs)
1. **strobe_build_4bar.json** - Strobe with increasing speed over 4 bars
2. **intensity_crescendo_8bar.json** - Slow fade up over 8 bars
3. **pulse_build_4bar.json** - Pulsing with increasing intensity

### fills/ (3 riffs)
1. **flash_hit_1bar.json** - Quick flash accent on beat 1
2. **color_sweep_2bar.json** - Color transition over 2 bars
3. **strobe_accent_half.json** - Half-bar strobe fill

### loops/ (3 riffs)
1. **pulse_4bar.json** - Simple 4-bar pulse loop
2. **rainbow_cycle_8bar.json** - RGB color cycling
3. **twinkle_4bar.json** - Twinkle effect loop

### drops/ (2 riffs)
1. **blackout_instant.json** - Immediate blackout (1 beat)
2. **full_blast_4bar.json** - Maximum intensity strobe drop

### movement/ (4 riffs)
1. **figure8_sweep_4bar.json** - Figure-8 pattern (Moving Head)
2. **circle_slow_8bar.json** - Slow circle movement (Moving Head)
3. **pan_sweep_2bar.json** - Left-right pan sweep (Moving Head)
4. **tilt_nod_1bar.json** - Quick tilt nod (Moving Head)

---

## Testing Checklist

### Unit Tests
- [ ] `Riff.to_dict()` and `Riff.from_dict()` roundtrip
- [ ] `Riff.to_light_block()` with constant BPM
- [ ] `Riff.to_light_block()` with BPM transition
- [ ] `Riff.is_compatible_with()` for various fixture types
- [ ] `RiffLibrary.load_all_riffs()` finds all JSON files
- [ ] `RiffLibrary.get_compatible_riffs()` filters correctly

### Integration Tests
- [ ] Drag riff from browser to lane
- [ ] Drop preview shows correct position and duration
- [ ] Overlap detection highlights correct blocks
- [ ] Insertion replaces overlapping blocks correctly
- [ ] Ctrl+Z undoes riff insertion
- [ ] Ctrl+Y redoes riff insertion
- [ ] "Save as Riff" creates valid JSON file
- [ ] "Update from Riff" updates unmodified blocks only

### Edge Cases
- [ ] Riff dropped at song start (time 0)
- [ ] Riff dropped at song end
- [ ] Riff spanning BPM transition boundary
- [ ] Riff dropped on lane with no existing blocks
- [ ] Riff dropped completely inside existing block (splits it)
- [ ] Very short riff (1 beat)
- [ ] Very long riff (64 beats)
- [ ] Universal riff on moving head lane
- [ ] Moving head riff on dimmer-only lane (should reject)

### UI Tests
- [ ] Riff browser shows correct categories
- [ ] Search filters riffs correctly
- [ ] Fixture filter hides incompatible riffs
- [ ] Drag cursor shows riff name
- [ ] Drop preview updates as mouse moves
- [ ] Context menu shows correct options based on riff_source
- [ ] Riff badge displays correctly (blue/orange for modified)

---

## File Summary

### New Files
| File | Purpose |
|------|---------|
| `riffs/riff_library.py` | RiffLibrary class for loading/saving riffs |
| `timeline_ui/riff_browser_widget.py` | Dockable riff browser panel |
| `timeline_ui/undo_commands.py` | QUndoCommand subclasses for undo/redo |
| `timeline_ui/save_riff_dialog.py` | Dialog for "Save as Riff" |
| `riffs/builds/*.json` | Preset build riffs |
| `riffs/fills/*.json` | Preset fill riffs |
| `riffs/loops/*.json` | Preset loop riffs |
| `riffs/drops/*.json` | Preset drop riffs |
| `riffs/movement/*.json` | Preset movement riffs |
| `riffs/custom/` | Empty directory for user riffs |

### Modified Files
| File | Changes |
|------|---------|
| `config/models.py` | Add Riff dataclasses, extend LightBlock, add `modified` to sublane blocks |
| `timeline_ui/light_lane_widget.py` | Add drop handling, overlap detection, preview drawing |
| `timeline_ui/light_block_widget.py` | Add riff context menu options, riff badge drawing |
| `timeline_ui/dimmer_block_dialog.py` | Set `modified=True` on save |
| `timeline_ui/colour_block_dialog.py` | Set `modified=True` on save |
| `timeline_ui/movement_block_dialog.py` | Set `modified=True` on save |
| `timeline_ui/special_block_dialog.py` | Set `modified=True` on save |
| `main_window.py` | Add RiffBrowserWidget dock, QUndoStack |

---

## Implementation Order

1. **Phase 1**: Core data model (models.py) - Foundation for everything else
2. **Phase 2**: Beat-to-time conversion - Required for riff insertion
3. **Phase 3**: RiffLibrary - Required for loading preset riffs
4. **Phase 9**: Starter riffs - Create JSON files to test with
5. **Phase 4**: Riff browser widget - UI for browsing riffs
6. **Phase 5**: Timeline integration - Drag-drop and insertion
7. **Phase 6**: Undo/redo support - Critical for usability
8. **Phase 7**: Context menu - Save as Riff functionality
9. **Phase 8**: Update tracking - Polish feature

---

## Notes

- The BPM-stretching algorithm uses quarter-beat sampling for accuracy vs performance balance
- Empty sublane lists in riffs mean "no effect" - don't create blocks, don't clear existing values
- The `modified` flag is per-block, allowing fine-grained "Update from Riff" behavior
- Undo/redo is critical since riff insertion is destructive (replaces blocks)
- Preset riffs should cover common use cases but be simple enough to understand
