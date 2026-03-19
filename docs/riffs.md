# Riff System

A Riff is a reusable, beat-based pattern of lighting effects that can be dropped onto the timeline. Riffs automatically adapt to the local BPM, stretching or compressing to match the tempo.

## Concepts

- Riffs define timing in **beats**, not seconds
- When placed on the timeline, beats are converted to absolute time using the song's BPM at that position
- A riff can contain any combination of sublane blocks (dimmer, colour, movement, special)
- Empty sublanes mean "no effect" - they don't clear existing values

## Data Model

Riff blocks mirror the standard sublane blocks but use beat-based timing:

| Standard Block | Riff Block | Timing |
|----------------|------------|--------|
| `DimmerBlock` | `RiffDimmerBlock` | `start_beat`, `end_beat` |
| `ColourBlock` | `RiffColourBlock` | `start_beat`, `end_beat` |
| `MovementBlock` | `RiffMovementBlock` | `start_beat`, `end_beat` |
| `SpecialBlock` | `RiffSpecialBlock` | `start_beat`, `end_beat` |

A `Riff` contains:
- `name`, `description`, `tags` - Metadata
- `duration_beats` - Total length in beats
- `fixture_type` - Compatibility filter ("any", "MH", "PAR", etc.)
- Lists of riff blocks for each sublane type
- `to_light_block(start_time, bpm_func)` - Converts to a placed `LightBlock`

When a riff is placed, the resulting `LightBlock` tracks its origin:
- `riff_source` - e.g., "builds/strobe_build_4bar"
- `riff_version` - e.g., "1.0"
- `modified` - Tracks whether the block was edited after placement

## BPM Conversion

For constant BPM (common case), beat-to-time is a simple multiplication. When BPM varies across the riff's span, quarter-beat sampling is used for accuracy:

```python
# Constant BPM (optimized):
time = start_time + (beat_offset * 60.0 / bpm)

# Variable BPM:
# Sample at quarter-beat intervals using song_structure.get_bpm_at_time()
```

## Riff Library

`riffs/riff_library.py` manages the riff collection:
- Scans `riffs/` subdirectories for JSON files
- Categories map to subdirectories: `builds/`, `drops/`, `fills/`, `loops/`, `movement/`, `custom/`
- Search by name, description, or tags
- Filter by fixture type compatibility
- Save user-created riffs

### Included Riffs

| Category | Riffs |
|----------|-------|
| **builds** | Strobe build (4 bar), Intensity crescendo (8 bar), Pulse build (4 bar) |
| **drops** | Blackout instant, Full blast (4 bar) |
| **fills** | Flash hit (1 bar), Color sweep (2 bar), Strobe accent (half bar) |
| **loops** | Pulse (4 bar), Rainbow cycle (8 bar), Twinkle (4 bar) |
| **movement** | Figure-8 sweep (4 bar), Circle slow (8 bar), Pan sweep (2 bar), Tilt nod (1 bar) |

## Riff Browser

A dockable panel (visible only in the Shows tab) that shows available riffs:
- Search bar with real-time filtering
- Collapsible category tree
- Drag-and-drop onto timeline lanes
- Collapses to a thin 28px bar when not in use

## Timeline Integration

**Placing a riff**: Drag from browser onto a lane. The riff snaps to beat positions. Overlapping blocks in the drop zone are replaced.

**Saving a riff**: Right-click a light block on the timeline, select "Save as Riff...". A dialog lets you set name, category, description, and tags. Time-based blocks are converted to beat-based.

**Modification tracking**: A visual badge on placed riff blocks shows:
- Green **R** - Unmodified riff block
- Yellow **R*** - Block has been edited since placement

**Undo/redo**: Riff insertion (and other timeline operations) supports Ctrl+Z / Ctrl+Y via `QUndoStack`.
