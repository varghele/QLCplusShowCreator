# Fixture Orientation System

The orientation system defines how lighting fixtures are positioned and angled in 3D space. It uses mounting presets combined with Euler angle fine-tuning.

## Coordinate System

### World (Stage)

- **+X**: Stage right (from audience perspective)
- **+Y**: Upstage (toward back wall)
- **+Z**: Up (toward ceiling)
- **Origin**: Center of stage floor

### Fixture Local

Each fixture type defines its local axes:

| Type | X-axis | Y-axis | Z-axis (beam) |
|------|--------|--------|----------------|
| **Moving Head** | Front plate direction | Perpendicular | Beam at home position |
| **Strip/Bar** | Along length (pixel 1 to N) | Perpendicular | Light emission direction |
| **Wash** | Along longer dimension | Along shorter dimension | Beam direction |
| **PAR** | Arbitrary (rotationally symmetric) | Arbitrary | Beam direction |

## Data Model

On `Fixture`:
- `mounting` - Preset name (see below)
- `yaw` - Rotation around world Z (degrees, -180 to 180)
- `pitch` - Rotation around local Y after yaw (degrees, -90 to 90)
- `roll` - Rotation around local X after pitch (degrees, -180 to 180)
- `orientation_uses_group_default` - Use group's default orientation
- `z_uses_group_default` - Use group's default Z height

On `FixtureGroup`:
- `default_mounting`, `default_yaw`, `default_pitch`, `default_roll`
- `default_z_height`

## Mounting Presets

| Preset | Description | Base Pitch | Base Yaw |
|--------|-------------|------------|----------|
| **Hanging** | On truss, beam down | -90 deg | 0 deg |
| **Standing** | On floor, beam up | +90 deg | 0 deg |
| **Wall-Left** | Stage-right wall | 0 deg | -90 deg |
| **Wall-Right** | Stage-left wall | 0 deg | +90 deg |
| **Wall-Back** | Back wall, beam toward audience | 0 deg | 0 deg |
| **Wall-Front** | Front, beam toward back | 0 deg | 180 deg |

Presets set the initial orientation. Users can then fine-tune with yaw/pitch/roll adjustments on top.

## 3D Orientation Dialog

Accessed via right-click on selected fixture(s) in the Stage tab:

- **3D Preview**: ModernGL viewport showing the fixture with floor grid, back wall reference, and beam direction indicator
- **Gimbal rings**: Draggable colored rings (blue = yaw, green = pitch, red = roll)
- **Preset buttons**: One-click mounting presets
- **Spin boxes**: Fine angle adjustment
- **Z-height input**: Fixture height in meters
- **"Apply to group default"**: Sets the group's default orientation

Supports single and multi-fixture editing.

## Stage Tab Indicators

The 2D stage plot shows orientation visually:
- **Blue dot**: Hanging (beam down)
- **Orange dot**: Standing (beam up)
- **Green bar on edge**: Wall mount
- **Hollow ring**: Custom orientation (non-preset pitch/roll values)
- **Optional coordinate axes**: Toggle via "Show orientation axes" checkbox

## Rotation Utilities

`utils/orientation.py` provides:

| Function | Purpose |
|----------|---------|
| `get_rotation_matrix(mounting, yaw, pitch, roll)` | Build 3x3 rotation matrix (ZYX convention) |
| `calculate_pan_tilt(fixture, target_position)` | Pan/tilt angles to aim at a world position |
| `pan_tilt_to_dmx(pan, pan_range, tilt, tilt_range)` | Convert angles to DMX values |
| `get_beam_direction(fixture)` | Beam direction vector in world space |
| `get_fill_direction(fixture)` | Strip fill direction in world space |

These utilities are used by the ArtNet DMX manager for movement calculations and by the Visualizer for rendering.
