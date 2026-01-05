# Riff System Implementation Plan

## Status: COMPLETED

All phases have been implemented and tested. Unit tests pass (45/45).

---

## Overview

This document outlines the implementation plan for adding a **Riff System** to the QLC+ Show Creator. A Riff is a reusable, beat-based pattern of lighting effects that can be dropped onto the timeline and automatically adapts to the local BPM.

**Related Design Document**: `.claude/riff_design_v2.md` (archived)

---

## Design Decisions

The following decisions were made during planning:

| Question | Decision |
|----------|----------|
| **Insertion with overlap** | Replace existing blocks in the overlap region |
| **BPM transitions** | Stretch riff to match tempo - calculate each beat individually using `get_bpm_at_time()` |
| **Modification tracking** | Track at LightBlock level (`modified: bool`) - visual indicator shows R (green) or R* (yellow) |
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

## Implementation Summary

### Phase 1: Core Data Model - COMPLETED

**File Modified**: `config/models.py`

Added the following dataclasses:
- `RiffDimmerBlock` - Beat-based dimmer block (lines ~540-570)
- `RiffColourBlock` - Beat-based colour block (lines ~572-610)
- `RiffMovementBlock` - Beat-based movement block (lines ~612-650)
- `RiffSpecialBlock` - Beat-based special block (lines ~652-675)
- `Riff` - Container class with `to_dict()`, `from_dict()`, `is_compatible_with()`, `to_light_block()` methods

Extended `LightBlock` with:
- `riff_source: Optional[str]` - e.g., "builds/strobe_build_4bar"
- `riff_version: Optional[str]` - e.g., "1.0"
- `modified: bool` - Tracks if block was modified after insertion

Added `modified: bool` flag to:
- `DimmerBlock`
- `ColourBlock`
- `MovementBlock`
- `SpecialBlock`

All new fields are serialized to/from YAML.

---

### Phase 2: BPM-Aware Beat-to-Time Conversion - COMPLETED

**Implemented in**: `config/models.py` - `Riff.to_light_block()` method

Key features:
- Optimization for constant BPM (common case) - single multiplication
- Quarter-beat sampling for BPM transitions
- Preserves all sublane block parameters during conversion
- Sets `riff_source` and `riff_version` on created LightBlock

```python
def beat_to_time(beat_offset: float) -> float:
    """Convert beat offset to absolute time, handling BPM changes."""
    # Check if BPM is constant (optimization)
    if abs(start_bpm - end_bpm) < 0.01:
        return start_time + (beat_offset * 60.0 / start_bpm)

    # BPM varies - sample at quarter-beat intervals
    # ... (full implementation in models.py)
```

---

### Phase 3: Riff Library - COMPLETED

**New File**: `riffs/riff_library.py`

`RiffLibrary` class with methods:
- `__init__(riffs_directory)` - Initialize and load all riffs
- `_load_all_riffs()` - Scan directories and load JSON files
- `load_riff(filepath)` - Load single riff from JSON
- `save_riff(riff, category)` - Save riff to JSON file
- `get_riff(riff_path)` - Get riff by "category/name" path
- `get_compatible_riffs(fixture_group)` - Filter by fixture type
- `get_categories()` - List all categories
- `get_riffs_in_category(category)` - List riffs in category
- `search(query, fixture_group)` - Search by name/description/tags
- `delete_riff(riff_path)` - Remove riff from library
- `refresh()` - Reload all riffs from disk
- `get_all_riffs()` - Get all riffs sorted
- `__len__`, `__contains__` - Collection interface

---

### Phase 4: Riff Browser Widget - COMPLETED

**New File**: `timeline_ui/riff_browser_widget.py`

Components:
- `RiffBrowserWidget(QDockWidget)` - Main dockable panel with collapse/expand
- `RiffItemWidget(QFrame)` - Individual riff item with drag support
- `CollapsedRiffBar(QWidget)` - Thin vertical bar when collapsed

Features:
- Search bar with real-time filtering
- Category tree view (collapsible)
- Riff items showing name, duration, fixture compatibility
- Drag-and-drop with custom MIME type `application/x-qlc-riff`
- Drag pixmap shows riff name
- **Collapse/expand functionality**: Click ▶ to collapse to thin 28px bar, ◀ to expand
- **Tab-based visibility**: Only visible in Shows tab (index 4)
- **State persistence**: Collapsed state remembered when switching tabs

---

### Phase 5: Timeline Integration - COMPLETED

**Files Modified**:
- `timeline_ui/timeline_widget.py` - Added drag-drop event handlers
- `timeline_ui/light_lane_widget.py` - Added riff drop handling

Features:
- `dragEnterEvent` - Check riff compatibility
- `dragMoveEvent` - Update drop preview position (snapped to beat)
- `dropEvent` - Create LightBlock and handle overlaps
- `draw_drag_preview()` - Semi-transparent preview rectangle
- Overlap detection and block replacement
- Signal: `riff_dropped(riff_path, drop_time)`

---

### Phase 6: Undo/Redo Support - COMPLETED

**New File**: `timeline_ui/undo_commands.py`

QUndoCommand subclasses:
- `InsertRiffCommand` - Insert riff block, remove overlapping blocks
- `DeleteBlockCommand` - Delete a light block
- `MoveBlockCommand` - Move block to new position (with sublane time updates)
- `ResizeBlockCommand` - Resize block
- `AddBlockCommand` - Add new block

**Integration** (`gui/gui.py`):
- `QUndoStack` created in main window
- Edit menu with Undo (Ctrl+Z) and Redo (Ctrl+Y) actions
- Shortcuts use `ApplicationShortcut` context for global availability
- Undo stack accessed via `_get_undo_stack()` with parent chain traversal

**Important**: When checking for undo stack, use `if undo_stack is not None:` instead of `if undo_stack:` because PyQt objects can have unexpected truthiness behavior.

---

### Phase 7: Context Menu - Save as Riff - COMPLETED

**Files Modified**:
- `timeline_ui/light_block_widget.py` - Added "Save as Riff..." context menu action

**New File**: `timeline_ui/save_riff_dialog.py`

`SaveRiffDialog` features:
- Name input with validation
- Category selection (combo box, editable)
- Description text area
- Tags input (comma-separated)
- Duration info display (seconds and beats)
- `_convert_block_to_riff()` - Time-to-beat conversion

---

### Phase 8: Riff Update Tracking - COMPLETED

**Files Modified**:
- `timeline_ui/light_block_widget.py` - Added `_draw_riff_indicator()` method

Visual indicator:
- Green "R" badge - Block from riff, unmodified
- Yellow "R*" badge - Block from riff, modified

Modification tracking locations:
- Sublane block resize/drag
- Intensity handle drag
- New sublane block creation
- Sublane dialog edits
- Sublane block deletion
- Speed change via mouse wheel

---

### Phase 9: Starter Riff Collection - COMPLETED

**Created 15 riff files**:

#### builds/ (3 riffs)
- `strobe_build_4bar.json` - Strobe with increasing speed
- `intensity_crescendo_8bar.json` - Slow fade up
- `pulse_build_4bar.json` - Pulsing with increasing intensity

#### fills/ (3 riffs)
- `flash_hit_1bar.json` - Quick flash accent
- `color_sweep_2bar.json` - Color transition
- `strobe_accent_half.json` - Half-bar strobe fill

#### loops/ (3 riffs)
- `pulse_4bar.json` - Simple pulse loop
- `rainbow_cycle_8bar.json` - RGB color cycling
- `twinkle_4bar.json` - Twinkle effect

#### drops/ (2 riffs)
- `blackout_instant.json` - Immediate blackout
- `full_blast_4bar.json` - Maximum intensity strobe

#### movement/ (4 riffs)
- `figure8_sweep_4bar.json` - Figure-8 pattern (MH)
- `circle_slow_8bar.json` - Slow circle (MH)
- `pan_sweep_2bar.json` - Left-right pan (MH)
- `tilt_nod_1bar.json` - Quick tilt nod (MH)

---

## Testing - COMPLETED

### Unit Tests: `tests/unit/test_riffs.py`

**45 tests passing** covering:

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestRiffDimmerBlock` | 5 | Creation, serialization, roundtrip |
| `TestRiffColourBlock` | 3 | Creation, to_dict, from_dict |
| `TestRiffMovementBlock` | 3 | Defaults, effect params, roundtrip |
| `TestRiffSpecialBlock` | 2 | Defaults, special effects |
| `TestRiff` | 4 | Creation, serialization, JSON roundtrip |
| `TestRiffCompatibility` | 4 | Universal/MH/PAR compatibility, empty group |
| `TestBeatToTimeConversion` | 6 | Constant BPM, offset start, different BPM, riff metadata |
| `TestRiffLibrary` | 13 | Init, save/load, categories, search, compatible, delete, refresh |
| `TestLightBlockRiffFields` | 3 | riff_source/version serialization |
| `TestRiffIntegration` | 2 | End-to-end workflow |

Run tests with:
```bash
python -m pytest tests/unit/test_riffs.py -v
```

---

## File Summary

### New Files
| File | Purpose |
|------|---------|
| `riffs/__init__.py` | Package init |
| `riffs/riff_library.py` | RiffLibrary class for loading/saving riffs |
| `timeline_ui/riff_browser_widget.py` | Dockable riff browser panel |
| `timeline_ui/undo_commands.py` | QUndoCommand subclasses for undo/redo |
| `timeline_ui/save_riff_dialog.py` | Dialog for "Save as Riff" |
| `riffs/builds/*.json` | 3 preset build riffs |
| `riffs/fills/*.json` | 3 preset fill riffs |
| `riffs/loops/*.json` | 3 preset loop riffs |
| `riffs/drops/*.json` | 2 preset drop riffs |
| `riffs/movement/*.json` | 4 preset movement riffs |
| `tests/unit/__init__.py` | Unit test package init |
| `tests/unit/test_riffs.py` | 45 unit tests for riff system |

### Modified Files
| File | Changes |
|------|---------|
| `config/models.py` | Added Riff dataclasses, extended LightBlock with riff_source/riff_version, added `modified` to sublane blocks |
| `timeline_ui/timeline_widget.py` | Added drag-drop event handlers, riff_dropped signal |
| `timeline_ui/light_lane_widget.py` | Added riff drop handling, overlap detection, `_get_undo_stack()` with parent traversal |
| `timeline_ui/light_block_widget.py` | Added "Save as Riff" context menu, `_draw_riff_indicator()` method |
| `timeline_ui/__init__.py` | Export RiffBrowserWidget |
| `gui/gui.py` | Added RiffBrowserWidget dock (Shows tab only), QUndoStack, Edit menu with Undo/Redo, tab-based riff browser visibility |

---

## Implementation Order (Completed)

1. ✅ **Phase 1**: Core data model (models.py)
2. ✅ **Phase 2**: Beat-to-time conversion
3. ✅ **Phase 3**: RiffLibrary
4. ✅ **Phase 9**: Starter riffs (moved up for testing)
5. ✅ **Phase 4**: Riff browser widget
6. ✅ **Phase 5**: Timeline integration
7. ✅ **Phase 6**: Undo/redo support
8. ✅ **Phase 7**: Context menu - Save as Riff
9. ✅ **Phase 8**: Update tracking & visual indicator
10. ✅ **Unit Tests**: 45 tests covering all components

---

## Notes

- The BPM-stretching algorithm uses quarter-beat sampling for accuracy vs performance balance
- Optimization: constant BPM detection skips sampling for the common case
- Empty sublane lists in riffs mean "no effect" - don't create blocks, don't clear existing values
- The `modified` flag is tracked at LightBlock level for simplicity
- Visual indicator: Green "R" = unmodified, Yellow "R*" = modified
- Undo/redo is critical since riff insertion is destructive (replaces blocks)
- All riff-related fields are serialized to YAML for persistence
- **PyQt truthiness**: Always use `is not None` when checking PyQt objects (e.g., QUndoStack)
- **Riff browser visibility**: Only visible in Shows tab, hidden in all other tabs
- **Collapsible UI**: Riff browser collapses to 28px thin bar with expand button
- **No View menu**: Removed View menu - riff browser auto-shows in Shows tab
