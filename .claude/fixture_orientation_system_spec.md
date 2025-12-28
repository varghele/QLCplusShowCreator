# Fixture Orientation System - Design Specification

## Overview

This document describes the design for a fixture orientation system for the QLC+ Show Creator application. The system allows users to define the 3D orientation of lighting fixtures (moving heads, strips, washes, PARs, blinders) in a user-friendly way, while maintaining the mathematical precision needed for accurate effect calculations and 3D visualization.

**Note:** This spec has been updated to align with the existing codebase structure.

## Tech Stack

- Python 3.12
- PyQt6 (UI framework)
- ModernGL (3D rendering - Visualizer)
- pandas, numpy (data handling)
- PyYAML (configuration)

---

## Core Concepts

### Local Coordinate System

Each fixture type has a defined local coordinate system that describes its orientation in 3D space. The user's task is to specify how this local coordinate system maps to the world/stage coordinate system.

#### World Coordinate System (Stage)
- **+X**: Stage right (from audience perspective, positive to the right)
- **+Y**: Upstage (toward back wall, positive toward back)
- **+Z**: Up (toward ceiling)
- **Origin**: Center of stage floor

**Note:** This matches the existing Stage tab coordinate system where (0,0) is center stage.

#### Fixture Local Coordinate System

**Moving Heads:**
- **X-axis (red)**: Points toward the front plate/display panel (pan=0 reference direction)
- **Y-axis (green)**: Perpendicular to X, completes right-hand system
- **Z-axis (blue)**: Points along the beam direction at home position (tilt=0, pan=0)

**Strip Fixtures (Sunstrips, LED bars):**
- **X-axis (red)**: Along the length of the strip (pixel 1 → pixel N)
- **Y-axis (green)**: Perpendicular to X, in the plane of the fixture
- **Z-axis (blue)**: Points where the light goes (perpendicular to the strip face)

**Wash Fixtures:**
- **X-axis (red)**: Along the longer dimension (if measurable)
- **Y-axis (green)**: Along the shorter dimension
- **Z-axis (blue)**: Points where the beam goes

**PAR Fixtures and other rotationally symmetric fixtures:**
- **Z-axis (blue)**: Points where the beam goes
- **X-axis (red)** and **Y-axis (green)**: Form a plane orthogonal to Z (orientation around Z is arbitrary)

---

## Data Model Changes

### Updated `Fixture` Class (config/models.py)

Replace the existing `direction` and `rotation` fields with the new orientation system:

```python
@dataclass
class Fixture:
    universe: int
    address: int
    manufacturer: str
    model: str
    name: str
    group: str
    current_mode: str
    available_modes: List[FixtureMode]
    type: str = "PAR"       # "PAR", "MH", "WASH", "BAR"
    x: float = 0.0          # X position in meters (center-based)
    y: float = 0.0          # Y position in meters (center-based)
    z: float = 0.0          # Z height in meters (individual value, or uses group default)

    # Orientation using Euler angles (degrees)
    # Convention: Yaw (Z) -> Pitch (Y) -> Roll (X)
    mounting: str = "hanging"       # "hanging", "standing", "wall_left", "wall_right", "wall_back", "wall_front"
    yaw: float = 0.0                # Rotation around world Z (degrees, -180 to 180)
    pitch: float = 0.0              # Rotation around local Y after yaw (degrees, -90 to 90)
    roll: float = 0.0               # Rotation around local X after pitch (degrees, -180 to 180)

    # Override flags (True = use own value, False = use group default)
    orientation_uses_group_default: bool = True
    z_uses_group_default: bool = True

    @property
    def effective_mounting(self) -> str:
        """Get mounting, considering group default if applicable."""
        if self.orientation_uses_group_default and self.group:
            # Will need to look up group default at runtime
            return self.mounting  # Placeholder - actual implementation uses group lookup
        return self.mounting

    @property
    def effective_z(self) -> float:
        """Get Z height, considering group default if applicable."""
        if self.z_uses_group_default and self.group:
            # Will need to look up group default at runtime
            return self.z  # Placeholder - actual implementation uses group lookup
        return self.z
```

### Updated `FixtureGroup` Class (config/models.py)

Add group-level orientation defaults:

```python
@dataclass
class FixtureGroup:
    name: str
    fixtures: List[Fixture]
    color: str = '#808080'
    capabilities: Optional['FixtureGroupCapabilities'] = None

    # Group-level defaults for orientation
    default_mounting: str = "hanging"
    default_yaw: float = 0.0
    default_pitch: float = 0.0
    default_roll: float = 0.0
    default_z_height: float = 3.0   # Default height in meters
```

### Fields to Remove

Remove these legacy fields from `Fixture`:
- `direction` - replaced by `mounting`
- `rotation` - replaced by `yaw`

---

## Mounting Presets

Common mounting scenarios are provided as one-click presets:

| Preset | Mounting Value | Base Pitch | Base Yaw | Description |
|--------|---------------|------------|----------|-------------|
| **Hanging** | `"hanging"` | -90° | 0° | Fixture hanging from truss, beam down |
| **Standing** | `"standing"` | +90° | 0° | Fixture on floor, beam up |
| **Wall-Left** | `"wall_left"` | 0° | -90° | Base against stage-right wall |
| **Wall-Right** | `"wall_right"` | 0° | +90° | Base against stage-left wall |
| **Wall-Back** | `"wall_back"` | 0° | 0° | Base against back wall, beam toward audience |
| **Wall-Front** | `"wall_front"` | 0° | 180° | Base toward audience, beam toward back |

Each preset sets the initial orientation (base pitch + yaw). Users can then fine-tune with additional yaw/pitch/roll adjustments.

---

## User Interface

### Stage Tab - 2D Stage Plot

The 2D plot is a top-down view of the stage where users position fixtures. We will **extend** the existing `StageView` and `FixtureItem` classes.

#### Fixture Icons

**Current Implementation** (gui/stage_items.py):
- PAR: Circle
- BAR: Wide rectangle
- MH: Circle with triangle indicator
- WASH: Rounded rectangle

**Proposed Changes:**
Add visual indicators for mounting type:
- **Blue dot/ring**: Beam points down (hanging)
- **Orange dot/ring**: Beam points up (standing)
- **Blue bar on edge**: Wall mount (positioned on the wall side)
- **Dashed border**: Custom orientation (not a standard preset)

**Coordinate axes (optional, toggle in left panel):**
- Show when fixture is selected or hovered
- Use engineering drawing conventions:
  - **Solid arrow**: Axis lies in the viewing plane (horizontal)
  - **⊙ (dot in circle)**: Axis points out of the page (up, +Z world)
  - **⊗ (X in circle)**: Axis points into the page (down, -Z world)

**Z-height label**: Already implemented, shows as "Z: 3.5m" text

#### Interactions

| Action | Current | Proposed |
|--------|---------|----------|
| Left-click fixture | Select (works) | Keep same |
| Left-click + drag fixture | Move position (works) | Keep same |
| Ctrl+click fixture | Not implemented | Add/remove from multi-selection |
| Rectangle drag on empty space | Not implemented | Select multiple fixtures |
| Right-click on selection | Not implemented | Context menu with "Set Orientation..." |
| Scroll wheel | Rotate yaw (works) | Keep same |
| Shift+scroll wheel | Adjust Z-height (works) | Keep same |

### Stage Tab - Left Panel Additions

Add to the existing control panel in `stage_tab.py`:

```
+------------------------------------------+
| Stage Dimensions (existing)              |
+------------------------------------------+
| Grid Settings (existing)                 |
+------------------------------------------+
| Stage Marks (existing)                   |
+------------------------------------------+
| Fixture Orientation                      |  <-- NEW GROUP
|   [x] Show orientation axes              |
|   [ ] Show all axes (not just selected)  |
+------------------------------------------+
| 3D Visualizer (existing)                 |
+------------------------------------------+
```

### 3D Orientation Popup

Opened via right-click → "Set Orientation..." on selected fixtures.

#### Layout

```
+--------------------------------------------------+
|  Set Orientation                            [X]  |
+--------------------------------------------------+
|                                                  |
|  +------------------------------------------+    |
|  |                                          |    |
|  |          3D Fixture Preview              |    |
|  |                                          |    |
|  |    [Fixture model with gimbal rings]     |    |
|  |                                          |    |
|  |    Reference floor (gray grid)           |    |
|  |    Reference back wall (subtle)          |    |
|  |                                          |    |
|  |                        +--+              |    |
|  |                        |XYZ|  (mini axes)|    |
|  |                        +--+              |    |
|  +------------------------------------------+    |
|                                                  |
|  Presets:                                        |
|  [Hanging] [Standing] [Wall-L] [Wall-R]          |
|  [Wall-Back] [Wall-Front]                        |
|                                                  |
|  Fine Adjustment:                                |
|  Yaw:   [____0.0____]°  (or drag blue ring)      |
|  Pitch: [____0.0____]°  (or drag green ring)     |
|  Roll:  [____0.0____]°  (or drag red ring)       |
|                                                  |
|  Z-Height: [____3.5____] m                       |
|                                                  |
|  [ ] Apply to group default                      |
|                                                  |
|  [Cancel]                          [Apply]       |
+--------------------------------------------------+
```

#### 3D Preview Features

1. **Fixture model**: Reuse existing Visualizer fixture rendering (MovingHeadRenderer, etc.)

2. **Gimbal rotation rings**: Three colored rings around the fixture
   - **Blue ring**: Rotate around Z-axis (yaw)
   - **Green ring**: Rotate around Y-axis (pitch)
   - **Red ring**: Rotate around X-axis (roll)
   - Dragging a ring rotates the fixture around that axis

3. **Reference geometry**:
   - **Floor**: Gray grid plane showing the stage floor
   - **Back wall**: Subtle vertical plane indicating upstage direction

4. **Mini coordinate system**: Small XYZ axes indicator in the corner

#### Behavior

- **Single fixture selected**: Popup shows that fixture's current orientation
- **Multiple fixtures selected**: Popup shows group default (or first selected fixture). On Apply, updates all selected fixtures
- **"Apply to group default" checkbox**: If checked, also updates the group's default orientation
- **Preset buttons**: Clicking a preset immediately updates the 3D preview and angle fields

---

## Changes to Existing Files

### `config/models.py`

1. Add new fields to `Fixture`: `mounting`, `yaw`, `pitch`, `roll`, `orientation_uses_group_default`, `z_uses_group_default`
2. Add new fields to `FixtureGroup`: `default_mounting`, `default_yaw`, `default_pitch`, `default_roll`, `default_z_height`
3. Add `rotation` property for backwards compatibility
4. Update `to_dict()` and `from_dict()` methods
5. Add migration logic for `direction` → `mounting` conversion

### `gui/stage_items.py`

1. Add mounting indicator rendering (colored dot/ring)
2. Add optional coordinate axes rendering
3. Add dashed border for custom orientations
4. Keep existing fixture type shapes (PAR=circle, MH=circle+triangle, etc.)

### `gui/tabs/stage_tab.py`

1. Add "Fixture Orientation" group to left panel with checkboxes
2. Add right-click context menu handler for fixtures
3. Add multi-select support (Ctrl+click, rectangle selection)
4. Add orientation popup dialog trigger

### `gui/StageView.py`

1. Add multi-selection support
2. Add rectangle selection handler
3. Pass orientation display preferences to fixture items

### `gui/tabs/fixtures_tab.py`

1. **Remove "Direction" column** (orientation now set in Stage tab)
2. Or: Keep for backwards compatibility but make read-only, showing mounting preset name

### New Files

1. `gui/dialogs/orientation_dialog.py` - The 3D orientation popup
2. `gui/widgets/gimbal_widget.py` - 3D gimbal preview widget (uses ModernGL)

---

## Effect Calculations

### Per-Fixture Transformation

Effects generate target positions or patterns in world space. For each fixture, the system must transform these to fixture-local space to calculate correct DMX values.

The existing `utils/artnet/dmx_manager.py` calculates pan/tilt values. Update to use the new orientation:

```python
import numpy as np

def get_rotation_matrix(mounting: str, yaw: float, pitch: float, roll: float) -> np.ndarray:
    """
    Build rotation matrix from mounting preset and Euler angles.
    Uses ZYX (yaw-pitch-roll) convention.
    """
    # Convert to radians
    yaw_rad = np.radians(yaw)
    pitch_rad = np.radians(pitch)
    roll_rad = np.radians(roll)

    # Base rotation from mounting preset
    base_pitch = {
        'hanging': -90,
        'standing': 90,
        'wall_left': 0,
        'wall_right': 0,
        'wall_back': 0,
        'wall_front': 0,
    }.get(mounting, 0)

    base_yaw = {
        'wall_left': -90,
        'wall_right': 90,
        'wall_front': 180,
    }.get(mounting, 0)

    # Add base rotation to user adjustments
    total_yaw = np.radians(base_yaw + yaw)
    total_pitch = np.radians(base_pitch + pitch)
    total_roll = np.radians(roll)

    # Build rotation matrices
    Rz = np.array([
        [np.cos(total_yaw), -np.sin(total_yaw), 0],
        [np.sin(total_yaw), np.cos(total_yaw), 0],
        [0, 0, 1]
    ])
    Ry = np.array([
        [np.cos(total_pitch), 0, np.sin(total_pitch)],
        [0, 1, 0],
        [-np.sin(total_pitch), 0, np.cos(total_pitch)]
    ])
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(total_roll), -np.sin(total_roll)],
        [0, np.sin(total_roll), np.cos(total_roll)]
    ])

    return Rz @ Ry @ Rx

def calculate_pan_tilt(fixture, target_world_position: np.ndarray) -> tuple:
    """
    Calculate pan and tilt values for a moving head to point at a world position.
    """
    # Get vector from fixture to target in world space
    fixture_pos = np.array([fixture.x, fixture.y, fixture.z])
    direction_world = target_world_position - fixture_pos
    direction_world = direction_world / np.linalg.norm(direction_world)

    # Get fixture's rotation matrix (world to local transform is the inverse/transpose)
    R = get_rotation_matrix(fixture.mounting, fixture.yaw, fixture.pitch, fixture.roll)
    direction_local = R.T @ direction_world

    # Calculate pan and tilt from local direction
    # In local space: Z is forward (beam), X is right, Y is up
    pan = np.degrees(np.arctan2(direction_local[0], direction_local[2]))
    tilt = np.degrees(np.arcsin(-direction_local[1]))

    return (pan, tilt)
```

### Strip Fixture Fill Direction

For strip fixtures, the orientation determines fill direction:

```python
def get_fill_direction(strip_fixture) -> np.ndarray:
    """
    Get the fill direction for a strip fixture in world space.
    Fill goes along the local X-axis (pixel 1 to pixel N).
    """
    R = get_rotation_matrix(
        strip_fixture.mounting,
        strip_fixture.yaw,
        strip_fixture.pitch,
        strip_fixture.roll
    )
    local_x = np.array([1, 0, 0])
    return R @ local_x
```

---

## Implementation Checklist

**Status: ALL PHASES COMPLETE (Dec 2025)**

### Phase 1: Data Model Changes ✓
- [x] Replace `direction` and `rotation` fields with `mounting`, `yaw`, `pitch`, `roll` in `Fixture`
- [x] Add `orientation_uses_group_default`, `z_uses_group_default` flags to `Fixture`
- [x] Add `default_mounting`, `default_yaw`, `default_pitch`, `default_roll`, `default_z_height` to `FixtureGroup`
- [x] Add `get_effective_orientation()` and `get_effective_z()` methods to `Fixture`
- [x] Update `Fixture.to_dict()` and `from_dict()` for serialization
- [x] Update `FixtureGroup` serialization
- [x] Update all code that references `fixture.direction` or `fixture.rotation`

### Phase 2: 2D Plot Changes ✓
- [x] Add mounting indicator to `FixtureItem` (colored dot/ring based on mounting)
- [x] Add hollow ring for custom orientations (non-zero pitch/roll)
- [x] Implement coordinate axes rendering (optional, toggle via checkbox)
- [x] Add "Fixture Orientation" group to stage_tab.py left panel
- [x] Add "Show orientation axes" checkbox
- [x] Add "Show all axes" checkbox
- [x] Add SUNSTRIP symbol rendering (bar with bulb circles)

### Phase 3: Multi-Select Support ✓
- [x] Implement Ctrl+click multi-select in StageView
- [x] Implement rectangle drag selection (rubber band)
- [x] Add right-click context menu with "Set Orientation..."
- [x] Handle Shift+scroll for Z-height on multi-selection

### Phase 4: 3D Orientation Popup ✓
- [x] Create `orientation_dialog.py` dialog class
- [x] Implement 3D preview widget using ModernGL
- [x] Implement gimbal ring rendering with draggable handles
- [x] Add reference floor grid and back wall geometry
- [x] Implement preset buttons (Hanging, Standing, Wall-L/R/Back/Front)
- [x] Add Yaw/Pitch/Roll spin boxes with ring drag sync
- [x] Add Z-height input
- [x] Add "Apply to group default" checkbox
- [x] Handle single vs. multiple fixture selection
- [x] Visualizer-style fixture rendering (LED segments, lamp bulbs, etc.)
- [x] Segment count from QXF layout for bars/sunstrips

### Phase 5: Effect System Updates ✓
- [x] Add `get_rotation_matrix()` utility function in `utils/orientation.py`
- [x] Add `calculate_pan_tilt()`, `pan_tilt_to_dmx()` utilities
- [x] Add `get_beam_direction()`, `get_fill_direction()` utilities
- [x] Add `get_direction_for_tilt_calculation()` for legacy compatibility
- [x] Updated `effects/moving_heads.py` to use orientation utilities

### Phase 6: Visualizer Updates ✓
- [x] Update TCP protocol to send orientation data (mounting, yaw, pitch, roll)
- [x] Update fixture renderers to use new orientation
- [x] Added `MOUNTING_BASE_ROTATIONS` constant
- [x] Verify beam direction matches orientation

### Phase 7: Fixtures Tab Cleanup ✓
- [x] Remove "Direction" column from fixtures table
- [x] Remove direction-related code from fixtures_tab.py
- [x] Add `_find_next_available_address()` for new fixture DMX assignment

### Phase 8: Additional Improvements ✓
- [x] Snap-to-grid enabled by default
- [x] Fixed dialog close/reopen issue with event deferral
- [x] Fixed hanging/standing orientation swap
- [x] Removed legacy rotation on scroll
- [x] Added SUNSTRIP fixture type detection
- [x] Added `get_fixture_layout()` for segment count lookup

---

## TCP Protocol Updates

Update `utils/tcp/protocol.py` to include orientation data:

```python
def create_fixtures_message(config):
    fixtures_data = []
    for fixture in config.fixtures:
        fixtures_data.append({
            'name': fixture.name,
            'type': fixture.type,
            'x': fixture.x,
            'y': fixture.y,
            'z': fixture.z,
            # NEW: Orientation fields
            'mounting': getattr(fixture, 'mounting', 'hanging'),
            'yaw': getattr(fixture, 'yaw', fixture.rotation),  # Fallback to rotation
            'pitch': getattr(fixture, 'pitch', 0.0),
            'roll': getattr(fixture, 'roll', 0.0),
            # ... existing fields ...
        })
    return {'type': 'fixtures', 'fixtures': fixtures_data}
```

---

## Future Considerations

1. **Undo/Redo**: Orientation changes should be undoable
2. **Copy/Paste orientation**: Allow copying orientation from one fixture to paste onto others
3. **Orientation templates**: Save custom orientations as named templates
4. **Visual feedback during adjustment**: Show beam direction preview in 2D plot while adjusting in 3D popup
5. **Keyboard shortcuts**: Quick preset application (e.g., H for Hanging, S for Standing)
6. **Guardrails**: If user feedback indicates issues with incompatible orientations in groups, implement warnings or constraints
7. **Quaternion storage**: If Euler angle gimbal lock becomes problematic in the future, consider using quaternions for internal storage while keeping Euler UI
