# Tests

This folder contains test files for the QLCplusShowCreator project.

## Test Categories

### `/visual/`
Visual/interactive tests that open GUI windows for manual verification.

**Files:**
- `test_sublane_blocks.py` - Test sublane block rendering with multiple blocks per type
- `test_sublane_ui.py` - Test sublane layout and height calculations
- `test_capability_detection.py` - Test fixture capability detection

**Running visual tests:**
```bash
python tests/visual/test_sublane_blocks.py
python tests/visual/test_sublane_ui.py
python tests/visual/test_capability_detection.py
```

## Test Types

### Visual Tests
These tests open interactive windows to manually verify:
- Visual appearance
- User interaction
- Layout and rendering
- Multiple blocks per sublane
- Overlap prevention with RED feedback

### What to Look For

**test_sublane_blocks.py:**
- Block 1: All sublanes synchronized
- Block 2: **TWO dimmer blocks** (demonstrates multiple blocks)
- Block 3: Partial sublanes (only dimmer/colour)
- Block 4: **THREE colour blocks** (red → green → blue)
- Try drag-to-create in empty areas
- Try overlapping movement blocks (should show RED)

**test_sublane_ui.py:**
- Correct number of sublanes per fixture type
- Proper height calculations
- Sublane separators (dashed lines)
- Lane resizing based on sublane count

**test_capability_detection.py:**
- Fixture capabilities correctly detected
- Moving heads show all 4 sublanes
- RGBW pars show 2 sublanes (dimmer + colour)
- Simple fixtures show 1 sublane (dimmer only)

## Future Tests

### Unit Tests (Planned)
- Data model validation
- Serialization/deserialization
- Overlap detection logic
- Envelope bounds calculation

### Integration Tests (Planned)
- Timeline with multiple lanes
- Effect copying/pasting
- Undo/redo operations
- DMX generation (when implemented)

### Performance Tests (Planned)
- Many blocks rendering
- Large timelines
- Real-time playback

## Adding New Tests

1. Create test file in appropriate folder
2. Follow naming convention: `test_<feature>.py`
3. Add description to this README
4. Ensure tests can run independently
