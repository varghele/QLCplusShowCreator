# Fixture Orientation System - Design Specification

## Overview

This document describes the design for a fixture orientation system for a QLC+ light show creator application. The system allows users to define the 3D orientation of lighting fixtures (moving heads, strips, washes, PARs, blinders) in a user-friendly way, while maintaining the mathematical precision needed for accurate effect calculations and 3D visualization.

## Tech Stack

- Python 3.12
- PyQt6 (UI framework)
- ModernGL (3D rendering)
- pandas, numpy (data handling)
- PyYAML (configuration)

## Core Concepts

### Local Coordinate System

Each fixture type has a defined local coordinate system that describes its orientation in 3D space. The user's task is to specify how this local coordinate system maps to the world/stage coordinate system.

#### World Coordinate System (Stage)
- **+X**: Stage left (from audience perspective)
- **+Y**: Upstage (toward back wall)
- **+Z**: Up (toward ceiling)
- **Origin**: Center of stage floor

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

### Orientation Storage

Orientations are stored internally as quaternions or rotation matrices for mathematical operations. The UI presents this as either:
1. Presets (common mounting scenarios)
2. Euler angles via 3D gimbal manipulation

---

## Group-Level Defaults with Individual Overrides

### Concept

Fixture groups have default values for:
- **Orientation** (quaternion/rotation matrix)
- **Z-height** (meters above stage floor)

When a fixture is added to a group, it inherits these defaults. Individual fixtures can override the group defaults when needed.

### Data Model

```python
class FixtureGroup:
    name: str
    default_orientation: Quaternion  # or rotation matrix
    default_z_height: float  # meters
    fixtures: List[Fixture]

class Fixture:
    id: str
    fixture_type: FixtureType
    position_x: float  # stage coordinates
    position_y: float  # stage coordinates
    
    # Override flags
    orientation_override: Optional[Quaternion]  # None = use group default
    z_height_override: Optional[float]  # None = use group default
    
    @property
    def orientation(self) -> Quaternion:
        return self.orientation_override or self.group.default_orientation
    
    @property
    def z_height(self) -> float:
        return self.z_height_override if self.z_height_override is not None else self.group.default_z_height
```

### UI Indication

In the 2D plot, fixtures with overridden values could show a subtle indicator (e.g., small dot or different border style) to distinguish them from fixtures using group defaults.

---

## Mounting Presets

Common mounting scenarios are provided as one-click presets:

| Preset | Base Direction | Beam Direction | Description |
|--------|---------------|----------------|-------------|
| **Hanging** | Up (+Z) | Down (-Z) | Fixture hanging from truss/ceiling |
| **Standing** | Down (-Z) | Up (+Z) | Fixture standing on floor |
| **Wall-Left** | Stage right (-X) | Stage left (+X) | Base against stage-right wall |
| **Wall-Right** | Stage left (+X) | Stage right (-X) | Base against stage-left wall |
| **Wall-Back** | Downstage (-Y) | Upstage (+Y) | Base against back wall, beam toward audience |
| **Wall-Front** | Upstage (+Y) | Downstage (-Y) | Base toward audience, beam toward stage |

Each preset sets the initial orientation. Users can then adjust the yaw (rotation around the fixture's Z-axis) to set which direction the front plate faces.

---

## User Interface

### 2D Stage Plot

The 2D plot is a top-down view of the stage where users position fixtures.

#### Fixture Icons

**Shape indicates mounting type:**
- **Circle**: Hanging (base up) or wall-mounted
- **Square**: Standing (base down)

**Visual elements:**
- **Blue bar**: Wall mount indicator, positioned on the side where the base is attached
- **Dashed border**: Custom/non-preset orientation
- **Coordinate axes**: Show local X (red), Y (green), Z (blue) axes using engineering drawing conventions

**Coordinate axes representation:**
- **Solid arrow**: Axis lies in the viewing plane (horizontal in world space)
- **⊙ (dot in circle)**: Axis points out of the page (up, +Z world)
- **⊗ (X in circle)**: Axis points into the page (down, -Z world)
- **Dashed arrow**: Axis at an angle to the viewing plane

**Z-height label**: Shown as text near the fixture (e.g., "Z: 3.5m")

#### Axes Visibility

- **Default**: Coordinate axes are only visible when a fixture is selected or hovered
- **Toggle option**: A checkbox in the left panel labeled "Show all axes" displays coordinate axes for all fixtures when enabled

#### Interactions

| Action | Behavior |
|--------|----------|
| Left-click fixture | Select single fixture (deselects others) |
| Left-click + drag fixture | Move fixture position on stage |
| Ctrl+click fixture | Add/remove fixture from selection |
| Rectangle drag on empty space | Select multiple fixtures in rectangle |
| Right-click on selection | Open context menu with "Set Orientation..." |
| Shift+mousewheel | Adjust Z-height of all selected fixtures |

#### Removed Interactions

- **Ctrl+mousewheel rotation**: Removed. Yaw adjustment is now handled through the 3D orientation popup.

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
|  Z-Height: [____3.5____] m                       |
|                                                  |
|  [Cancel]                          [Apply]       |
+--------------------------------------------------+
```

#### 3D Preview Features

1. **Fixture model**: Shows the actual 3D model of the fixture (reuses existing visualizer rendering)

2. **Gimbal rotation rings**: Three colored rings around the fixture
   - **Red ring**: Rotate around X-axis
   - **Green ring**: Rotate around Y-axis  
   - **Blue ring**: Rotate around Z-axis
   - Dragging a ring rotates the fixture around that axis

3. **Reference geometry**:
   - **Floor**: Gray grid plane showing the stage floor
   - **Back wall**: Subtle vertical plane indicating upstage direction

4. **Mini coordinate system**: Small XYZ axes indicator in the corner showing world orientation (helps user understand which way is up/front/left)

#### Behavior

- **Single fixture selected**: Popup shows that fixture's current orientation. On Apply, updates only that fixture.
- **Multiple fixtures selected**: Popup shows group default orientation (or first selected fixture's orientation). On Apply, updates all selected fixtures.
- **Preset buttons**: Clicking a preset immediately updates the 3D preview. User can then fine-tune with gimbal before applying.
- **Z-Height field**: Numeric input for setting height. Updates all selected fixtures on Apply.

---

## Changes to Existing UI

### Fixtures Tab

The "Fixtures" tab where users add and remove fixtures should have the following changes:

**Remove:**
- "Orientation" column (no longer set here)

**Keep:**
- All other fixture properties (name, type, DMX address, etc.)

**Note:** Fixture orientation is now exclusively set in the Stage tab via the 2D plot and 3D orientation popup.

---

## Effect Calculations

### Per-Fixture Transformation

Effects generate target positions or patterns in world space. For each fixture, the system must transform these to fixture-local space to calculate correct DMX values.

```python
def calculate_pan_tilt(fixture: Fixture, target_world_position: Vector3) -> Tuple[float, float]:
    """
    Calculate pan and tilt values for a moving head to point at a world position.
    
    Args:
        fixture: The fixture with its position and orientation
        target_world_position: The target point in world coordinates
    
    Returns:
        Tuple of (pan_degrees, tilt_degrees)
    """
    # Get vector from fixture to target in world space
    fixture_world_pos = Vector3(fixture.position_x, fixture.position_y, fixture.z_height)
    direction_world = (target_world_position - fixture_world_pos).normalized()
    
    # Transform direction to fixture's local space
    # fixture.orientation is the rotation from local to world
    # We need the inverse to go from world to local
    inverse_orientation = fixture.orientation.inverse()
    direction_local = inverse_orientation.rotate(direction_world)
    
    # Calculate pan and tilt from local direction
    # In local space: Z is forward (beam), X is front plate reference, Y is perpendicular
    pan = atan2(direction_local.y, direction_local.x)  # Angle in XY plane
    tilt = acos(direction_local.z)  # Angle from Z axis
    
    return (degrees(pan), degrees(tilt))
```

### Strip Fixture Fill Direction

For strip fixtures, the orientation determines fill direction:

```python
def get_fill_direction(strip_fixture: Fixture) -> Vector3:
    """
    Get the fill direction for a strip fixture in world space.
    Fill goes along the local X-axis (pixel 1 to pixel N).
    """
    local_x = Vector3(1, 0, 0)
    return strip_fixture.orientation.rotate(local_x)
```

---

## Implementation Checklist

### Data Model Changes
- [ ] Add `default_orientation` and `default_z_height` to `FixtureGroup`
- [ ] Add `orientation_override` and `z_height_override` to `Fixture`
- [ ] Remove old orientation fields ("up", "down", "towards", "away", rotation angle)
- [ ] Add properties for resolved orientation and z_height

### 2D Plot Changes
- [ ] Update fixture icon rendering to show shapes based on mounting type
- [ ] Implement coordinate axes rendering (with ⊙/⊗ symbols)
- [ ] Add hover/selection state for axes visibility
- [ ] Add "Show all axes" toggle checkbox in left panel
- [ ] Implement multi-select (Ctrl+click, rectangle selection)
- [ ] Implement Shift+mousewheel for Z-height adjustment on selection
- [ ] Remove Ctrl+mousewheel rotation behavior
- [ ] Add right-click context menu with "Set Orientation..."
- [ ] Add Z-height label rendering

### 3D Orientation Popup
- [ ] Create popup dialog with PyQt6
- [ ] Implement 3D preview using ModernGL (reuse visualizer code)
- [ ] Implement gimbal ring rendering and interaction
- [ ] Add reference floor and back wall geometry
- [ ] Add mini coordinate system indicator
- [ ] Implement preset buttons
- [ ] Add Z-height numeric input
- [ ] Handle single vs. multiple fixture selection

### Fixtures Tab Changes
- [ ] Remove "Orientation" column from fixtures table

### Effect System Changes
- [ ] Update pan/tilt calculations to use new orientation system
- [ ] Update strip fill effects to use orientation for direction
- [ ] Test all position-dependent effects with various orientations

### Migration
- [ ] Write migration code to convert old orientation values to new quaternion system
- [ ] Handle edge cases (custom rotations, etc.)

---

## Visual Reference

See accompanying SVG files:
- `fixture_2d_plot_with_axes.svg`: Complete reference for 2D plot icon representations

---

## Future Considerations

1. **Undo/Redo**: Orientation changes should be undoable
2. **Copy/Paste orientation**: Allow copying orientation from one fixture to paste onto others
3. **Orientation templates**: Save custom orientations as named templates
4. **Visual feedback during adjustment**: Show beam direction preview in 2D plot while adjusting in 3D popup
5. **Keyboard shortcuts**: Quick preset application (e.g., H for Hanging, S for Standing)
6. **Guardrails**: If user feedback indicates issues with incompatible orientations in groups, implement warnings or constraints
