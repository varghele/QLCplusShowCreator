# QLC+ Show Creator - Development Phase Plan

**Last Updated:** January 2026

---

## Overview

This document tracks the development phases for QLC+ Show Creator and the integrated Visualizer. Check boxes indicate completion status.

---

## Completed Phases (Show Creator)

### Phase 1: Core Infrastructure (COMPLETE)

- [x] Project structure and PyQt6 setup
- [x] Configuration data models (`config/models.py`)
- [x] YAML save/load for configurations
- [x] Basic MainWindow with tabs

### Phase 2: Universe & Fixture Setup (COMPLETE)

- [x] Universe configuration (E1.31, ArtNet, DMX USB)
- [x] Fixture definition parsing from QLC+ `.qxf` files
- [x] Fixture inventory management
- [x] Fixture groups with color coding
- [x] Mode selection per fixture

### Phase 3: Stage Planning (COMPLETE)

- [x] Visual stage canvas (`StageView.py`)
- [x] Fixture placement with drag-and-drop
- [x] Grid snapping
- [x] Stage dimensions configuration
- [x] Coordinate system (0,0 at center)

### Phase 4: MainWindow Refactoring (COMPLETE - Dec 2025)

- [x] Split monolithic `gui.py` (1,738 → 270 lines, 84% reduction)
- [x] Modular tab architecture (`gui/tabs/`)
- [x] BaseTab class with lifecycle methods
- [x] Cross-tab communication via parent
- [x] Auto-save functionality

### Phase 5: Sublane System - Data & Detection (COMPLETE - Dec 2025)

- [x] Sublane block data models (Dimmer, Colour, Movement, Special)
- [x] Multiple blocks per sublane type (List architecture)
- [x] FixtureGroupCapabilities class
- [x] Capability auto-detection from fixture definitions
- [x] QLC+ preset categorization (`sublane_presets.py`)

### Phase 6: Sublane System - UI (COMPLETE - Dec 2025)

- [x] Sublane rendering in timeline
- [x] Dynamic lane height based on capabilities
- [x] Drag-to-create sublane blocks
- [x] Resize and move blocks
- [x] Overlap prevention with visual feedback (RED preview)
- [x] Selection and cursor feedback
- [x] Effect envelope auto-expansion

### Phase 7: Sublane Edit Dialogs (COMPLETE - Dec 2025)

- [x] DimmerBlockDialog (intensity, strobe, effect type/speed)
- [x] ColourBlockDialog (RGB, presets, color wheel)
- [x] MovementBlockDialog (2D pan/tilt, shapes, speed)
- [x] SpecialBlockDialog (gobo, prism, focus, zoom)
- [x] Copy/paste functionality (`effect_clipboard.py`)

### Phase 8: QLC+ Export - Dimmer (COMPLETE - Dec 2025)

- [x] Export dimmer blocks to QLC+ sequences
- [x] Dimmer effects (static, strobe, twinkle)
- [x] Speed-based step generation
- [x] RGB control for fixtures without dimmer channel

### Phase 9: QLC+ Export - Movement (COMPLETE - Dec 2025)

- [x] Movement sequences with pan/tilt animation
- [x] Shape generation (circle, lissajous, diamond, etc.)
- [x] Adaptive step density (24 steps/sec max)
- [x] Integration with overlapping dimmer/colour blocks
- [x] Color wheel fallback for non-RGB fixtures
- [x] Dynamic strobe in movement sequences
- [x] Special block export (gobo, prism, focus, zoom)
- [x] Fixed QLC+ crash issue (Duration attribute removal)

### Phase 10: Bug Fixes & Stabilization (COMPLETE - Dec 2025)

Priority bug fixes before new features:

- [x] **Universe configuration bugs** - Fixed UID-based format, Line mapping, cleared PluginParameters. QLC+ network settings must be configured manually in QLC+ UI (stored in separate plugin config files).
- [x] Effect system polish
- [x] Export edge cases
- [x] UI/UX improvements based on usage

### Phase 11: In-App Show Structure Creation (COMPLETE - Dec 2025)

In-app show structure creation and management:

- [x] Show structure editor UI in Structure tab
- [x] Song part management (add/remove/reorder via right-click menu)
- [x] Custom table cell widgets (TimeSignatureWidget, ColorButton)
- [x] Timing configuration per part (BPM double spinbox, bars spinbox)
- [x] BPM and time signature settings with input validation
- [x] Transition type selection (instant/gradual combobox)
- [x] Color coding for show parts with hex color picker
- [x] CSV import/export functionality maintained
- [x] Shows directory management system
- [x] Audio file management (auto-copy to audiofiles/ subfolder)
- [x] Auto-load shows on tab activation
- [x] Auto-save to CSV on structure changes
- [x] Delete show functionality with audio file cleanup
- [x] Directory selection dialog with default location warning
- [x] Audio lane integration with waveform display
- [x] Timeline synchronization between Structure and Shows tabs
- [x] Removed audio extension prompt (structure managed in Structure tab)

### Phase 12: ArtNet DMX Output (COMPLETE - Dec 2025)

Enable the Show Creator to send DMX directly for preview:

- [x] ArtNet packet generation (`utils/artnet/sender.py`)
- [x] Real-time DMX output during playback
- [x] Universe routing configuration
- [x] Rate limiting (44Hz max)
- [x] Toggle via GUI checkbox in ShowsTab toolbar
- [x] **BPM-aware movement timing** (integrated with SongStructure)
- [x] **All movement shapes implemented:**
  - [x] Circle, Figure-8, Lissajous (existing)
  - [x] Diamond, Square, Triangle, Random, Bounce (new)
- [x] **Granular block ending** (per sublane type)
- [x] **ShowsTab integration** with playback controls
- [x] Fixture channel mapping from .qxf definitions
- [x] Real-time effect calculations (strobe, twinkle)
- [x] LTP (Latest Takes Priority) block merging
- [x] 44Hz DMX update timer
- [x] Broadcast and unicast support

**Implementation files:**
- `utils/artnet/sender.py` (168 lines) - Packet generation
- `utils/artnet/dmx_manager.py` (620 lines) - DMX state + BPM integration
- `utils/artnet/shows_artnet_controller.py` (227 lines) - ShowsTab integration
- `gui/tabs/shows_tab.py` - GUI integration with checkbox toggle

**Documentation:**
- `.claude/ARTNET_IMPLEMENTATION.md` - Original implementation
- `.claude/INTEGRATION_COMPLETE.md` - Full integration summary
- `utils/artnet/README.md` - API documentation

### Phase 13: TCP Server for Visualizer (COMPLETE - Dec 2025)

TCP server in Show Creator to send configuration to Visualizer:

- [x] TCP server implementation (`utils/tcp/server.py`)
- [x] Protocol definition (JSON with newline delimiter):
  - [x] Stage dimensions message
  - [x] Fixture list message (positions, types, addresses, modes)
  - [x] Groups message (name, color, fixtures)
  - [x] Update notification on changes
  - [x] Heartbeat messages for keep-alive
- [x] Connection status UI indicator (LED in ShowsTab toolbar)
- [x] Multi-client support with thread-safe handling
- [x] Auto-send configuration on client connect
- [x] Auto-send updates on config changes
- [x] Qt signals for GUI integration
- [x] Serialize `Configuration` to JSON format

**Implementation files:**
- `utils/tcp/protocol.py` (171 lines) - Protocol definition
- `utils/tcp/server.py` (301 lines) - Multi-threaded TCP server
- `gui/tabs/shows_tab.py` - GUI integration (+130 lines)
- `test_tcp_client.py` (153 lines) - Test client

**Documentation:**
- `.claude/TCP_IMPLEMENTATION.md` - Complete implementation summary
- `utils/tcp/README.md` - API documentation and usage guide

---

## Current Phase

### Phase 14: Fixture Orientation System (COMPLETE - Dec 2025)

Rework the Stage tab to provide a proper 3D orientation system for fixtures, replacing the legacy direction values with a more flexible Euler angle-based approach.

**Design Document:** `.claude/fixture_orientation_system_spec.md`

#### Sub-Phase 14.1: Data Model Changes (COMPLETE - Dec 2025)
- [x] Replace `direction` and `rotation` fields with `mounting`, `yaw`, `pitch`, `roll` in `Fixture` class
- [x] Add `orientation_uses_group_default`, `z_uses_group_default` flags to `Fixture`
- [x] Add `default_mounting`, `default_yaw`, `default_pitch`, `default_roll`, `default_z_height` to `FixtureGroup`
- [x] Add `get_effective_orientation()` and `get_effective_z()` methods to `Fixture`
- [x] Update serialization (`save()`, `load()`) for new fields
- [x] Update all code referencing `fixture.direction` or `fixture.rotation`:
  - [x] `gui/StageView.py` - Use `yaw` for 2D rotation
  - [x] `gui/tabs/fixtures_tab.py` - Removed Direction column, updated fixture creation
  - [x] `effects/moving_heads.py` - Use `mounting` and `yaw` in all 5 effects
  - [x] `visualizer/renderer/fixtures.py` - Use `yaw` for fixture rotation
  - [x] `utils/tcp/protocol.py` - Send `yaw` instead of `rotation`

#### Sub-Phase 14.2: 2D Stage Plot Enhancements (COMPLETE - Dec 2025)
- [x] Add mounting indicator to `FixtureItem` (colored dot/ring based on mounting type)
  - Blue dot: Hanging (beam down)
  - Orange dot: Standing (beam up)
  - Green bar on edge: Wall mounts (positioned on wall side)
- [x] Add hollow ring for custom (non-preset) orientations (non-zero pitch/roll)
- [x] Implement optional coordinate axes rendering (toggle via checkbox)
  - X axis (red), Y axis (green), Z axis (blue with ⊙/⊗ indicator)
- [x] Add "Fixture Orientation" group to stage_tab.py left panel
- [x] Add "Show orientation axes" checkbox
- [x] Add "Show all axes" checkbox

#### Sub-Phase 14.3: Multi-Select Support (COMPLETE - Dec 2025)
- [x] Implement Ctrl+click multi-select in `StageView`
- [x] Implement rectangle drag selection for multiple fixtures (rubber band selection)
- [x] Add right-click context menu with "Set Orientation..." option
  - Also added "Select All Fixtures" and "Deselect All" options
- [x] Handle Shift+scroll for Z-height adjustment on multi-selection
- [x] Added `set_orientation_requested` signal for future orientation dialog
- [x] Added `get_selected_fixtures()` helper method

#### Sub-Phase 14.4: 3D Orientation Popup Dialog (COMPLETE - Dec 2025)
- [x] Create `gui/dialogs/orientation_dialog.py` dialog class
- [x] Implement 3D preview widget using ModernGL (`OrientationPreviewWidget`)
  - Fixture body rendering with lighting
  - Floor grid for reference
  - Beam direction indicator (yellow line)
- [x] Implement gimbal ring rendering with color coding
  - Blue ring: Yaw (rotation around Y)
  - Green ring: Pitch (tilt)
  - Red ring: Roll
- [x] Mouse orbit/zoom camera controls for preview
- [x] Implement preset buttons (Hanging, Standing, Wall-L/R/Back/Front)
- [x] Add Yaw/Pitch/Roll spin boxes for fine adjustment
- [x] Add Z-height input field
- [x] Add "Apply to group default" checkbox (enabled only when all fixtures in same group)
- [x] Handle single vs. multiple fixture selection modes
- [x] Connected dialog to StageView via `set_orientation_requested` signal
- [x] Apply orientation values to fixtures and config on dialog accept

#### Sub-Phase 14.5: Effect System Updates (COMPLETE - Dec 2025)
- [x] Created `utils/orientation.py` with rotation matrix utilities:
  - `get_rotation_matrix()` - Build 3x3 rotation matrix from mounting + Euler angles
  - `calculate_pan_tilt()` - Calculate pan/tilt to aim at world position
  - `pan_tilt_to_dmx()` - Convert pan/tilt degrees to DMX values
  - `get_beam_direction()` - Get beam direction vector in world space
  - `get_fill_direction()` - Get strip fill direction in world space
  - `get_direction_for_tilt_calculation()` - Legacy UP/DOWN for existing code
- [x] Updated `effects/moving_heads.py` to use orientation utilities
  - All 5 effect functions now use `get_direction_for_tilt_calculation()`
  - Centralized direction logic instead of inline mapping
- [x] `utils/artnet/dmx_manager.py` - No changes needed (uses relative pan/tilt, not position-based)

#### Sub-Phase 14.6: Visualizer Integration (COMPLETE - Dec 2025)
- [x] Update TCP protocol (`utils/tcp/protocol.py`) to send orientation data
  - Changed `yaw` field to `orientation` object with `mounting`, `yaw`, `pitch`, `roll`
- [x] Update Visualizer fixture renderers to use new orientation fields
  - Added `MOUNTING_BASE_ROTATIONS` constant with presets
  - Updated `FixtureRenderer.__init__` to extract orientation dict
  - Updated `get_model_matrix()` to apply full rotation (yaw-pitch-roll order)
  - Updated `FixtureManager.update_fixtures()` to detect orientation changes
  - Updated `MovingHeadRenderer.get_beam_direction()` to use full orientation
- [x] Verify beam direction matches configured orientation

#### Sub-Phase 14.7: Cleanup (COMPLETE - Dec 2025)
- [x] Remove "Direction" column from Fixtures tab (done in 14.1)
- [x] Remove direction-related code from fixtures_tab.py (done in 14.1)
- [x] Test saving and reloading config files with new orientation fields
  - Fixtures saved via `asdict(f)` includes all new orientation fields
  - Fixtures loaded via `Fixture(**f_data)` accepts new fields with defaults
  - Deprecated `direction` and `rotation` fields explicitly removed on load

#### Sub-Phase 14.8: Orientation Dialog Polish (COMPLETE - Dec 2025)
- [x] Visualizer-style fixture rendering in orientation dialog
  - LED Bar: Dark body with LED segment boxes (emissive glow)
  - Sunstrip: Dark body with cylindrical lamp bulbs (warm white glow)
  - PAR: Cylindrical body with lens
  - Wash: Box body with lens panel
  - Moving Head: Base cylinder, yoke arms, head box, lens
- [x] Added `GeometryBuilder` class for procedural geometry (box, cylinder)
- [x] Gimbal ring handles that rotate with current orientation
- [x] Added back wall reference geometry
- [x] Snap-to-grid enabled by default in Stage tab
- [x] Fixed dialog close/reopen issue with QTimer.singleShot deferral
- [x] Fixed hanging/standing orientation swap in mounting presets
- [x] Removed legacy rotation on scroll (orientation via dialog only)

#### Sub-Phase 14.9: Fixture Type Improvements (COMPLETE - Dec 2025)
- [x] Added SUNSTRIP fixture type detection in `determine_fixture_type()`
  - Checks XML `<Type>` tag for "sunstrip" or "LED Bar (Pixels)"
  - Detects multi-segment fixtures (layout width > 1) without RGB
- [x] Added `get_fixture_layout()` function to read segment count from QXF files
- [x] Orientation dialog passes segment count to fixture geometry
- [x] Added SUNSTRIP symbol rendering in 2D stage plot (bar with bulb circles)
- [x] Fixed new fixture DMX address assignment
  - Added `_find_next_available_address()` method
  - Scans existing fixtures for used addresses
  - Places new fixture at first available slot

**Files created:**
- `gui/dialogs/orientation_dialog.py` - 3D orientation popup with visualizer-style rendering
- `utils/orientation.py` - Rotation matrix utilities

**Files modified:**
- `config/models.py` - Add new orientation fields
- `gui/stage_items.py` - Add mounting indicators, axes rendering, SUNSTRIP symbol
- `gui/StageView.py` - Multi-select, context menu, snap-to-grid default
- `gui/tabs/stage_tab.py` - Left panel additions, dialog trigger, deferred opening
- `gui/tabs/fixtures_tab.py` - Remove Direction column, add DMX address finder
- `utils/tcp/protocol.py` - Send orientation data
- `utils/fixture_utils.py` - Add SUNSTRIP detection, get_fixture_layout()

---

## Upcoming Phases (Show Creator)

### Phase 15: Effects/Riffs System Enhancement (PLANNED)

Improve the effects system with predefined sequences:

- [ ] Define "Riff" concept (sequence of sublane effects)
- [ ] Riff library/presets
- [ ] Quick apply riffs to timeline
- [ ] Riff templates per fixture type
- [ ] User-defined riffs

### Phase 16: Audio Analysis Integration (FUTURE)

AI-assisted show generation:

- [ ] Audio file analysis (beat detection, spectral analysis)
- [ ] Song structure auto-detection
- [ ] Effect suggestion based on audio
- [ ] Automatic show generation algorithm

---

## Visualizer Phases

### Phase V1: Project Foundation (COMPLETE - Dec 2025)

Set up the Visualizer project structure:

- [x] Create `visualizer/` directory structure
- [x] Visualizer entry point (`visualizer/main.py`)
- [x] Import shared modules (`config/models.py`, `utils/fixture_utils.py`)
- [x] PyQt6 main window skeleton
- [x] Add ModernGL, PyGLM to requirements

**Files created:**
```
visualizer/
├── main.py              # Main window with toolbar, statusbar, viewport placeholder
├── __init__.py          # Package init
└── requirements.txt     # ModernGL, PyGLM, Pillow
```

### Phase V2: TCP Client Integration (COMPLETE - Dec 2025)

Receive configuration from Show Creator:

- [x] TCP client implementation (`visualizer/tcp/client.py`)
- [x] Parse stage dimensions message
- [x] Parse fixture list message
- [x] Parse groups message
- [x] Handle connection/disconnection gracefully
- [x] Connection status UI (green/red indicator in statusbar)
- [x] Store received config in local data structures
- [x] Launch Visualizer button in Stage tab
- [x] Auto-start TCP server when launching Visualizer

**Files created:**
```
visualizer/tcp/
├── __init__.py
└── client.py            # VisualizerTCPClient with Qt signals
```

**Additional changes:**
- `config/models.py`: Added `stage_width`, `stage_height` to Configuration
- `gui/tabs/stage_tab.py`: Added Visualizer group with launch button and TCP status
- `utils/tcp/protocol.py`: Fixed import (Group → FixtureGroup)

### Phase V3: ArtNet Receiver (COMPLETE - Dec 2025)

Receive live DMX values:

- [x] ArtNet UDP listener (`visualizer/artnet/listener.py`)
- [x] Parse ArtNet OpDmx packets
- [x] Support configurable universes (None = all)
- [x] Thread-safe DMX value storage
- [x] Connection status detection (receiving/not receiving with 2s timeout)
- [x] Handle both Show Creator and QLC+ as sources
- [x] Qt signals for thread-safe UI updates
- [x] Packet statistics tracking

**ArtNet OpDmx packet format:**
- Bytes 0-7: "Art-Net\0"
- Bytes 8-9: OpCode 0x5000 (little-endian)
- Byte 14-15: Universe (little-endian)
- Byte 16-17: Length (big-endian)
- Bytes 18+: DMX data (up to 512 bytes)

**Files created:**
```
visualizer/artnet/
├── __init__.py
└── listener.py          # ArtNetListener with Qt signals
```

### Phase V4: 3D Rendering Foundation (COMPLETE - Dec 2025)

Basic OpenGL setup:

- [x] ModernGL context in PyQt6 (`visualizer/renderer/engine.py`)
- [x] Orbiting camera with mouse controls (`visualizer/renderer/camera.py`)
- [x] Stage floor with grid lines (`visualizer/renderer/stage.py`)
- [x] Dark background rendering
- [x] FPS counter
- [x] Window resize handling
- [x] Coordinate system gizmo in top-right corner (`visualizer/renderer/gizmo.py`)
- [x] Colored axes matching Stage tab (X=red, Y=blue, Z=green)
- [x] Live stage dimension updates via TCP
- [x] Live grid size updates via TCP
- [x] Colored center axes in Stage tab view

**Camera controls:**
- Left mouse drag: Orbit around stage center
- Right mouse drag: Pan (also middle mouse)
- Scroll wheel: Zoom
- Home key or R: Reset view

**Files created:**
```
visualizer/renderer/
├── __init__.py          # Package exports
├── engine.py            # RenderEngine (QOpenGLWidget with ModernGL)
├── camera.py            # OrbitCamera (spherical coordinates, view/projection)
├── stage.py             # StageRenderer (floor quad + grid lines with GLSL)
└── gizmo.py             # CoordinateGizmo (XYZ axes indicator in corner)
```

**Technical details:**
- OpenGL 3.3 Core Profile with MSAA 4x
- 60 FPS render target with QTimer
- Stage grid with configurable spacing (synced via TCP)
- Colored center axes: X=red (width), Y=blue (depth), Z=green (height)
- PyGLM for matrix math (glm.lookAt, glm.perspective)
- GLSL 330 shaders for floor and grid rendering
- Qt FBO binding for correct ModernGL rendering in QOpenGLWidget
- makeCurrent()/doneCurrent() for thread-safe OpenGL updates

**Bug fixes applied:**
- Fixed Qt FBO binding issue (grid not visible initially)
- Fixed VBO memory leak when resizing stage
- Fixed grid disappearing with odd stage dimensions (7m, 11m, etc.)
- Fixed coordinate gizmo Y/Z axis swap to match stage convention

**Additional changes:**
- `config/models.py`: Added `grid_size` field to Configuration
- `utils/tcp/protocol.py`: Stage message now includes `grid_size`
- `gui/tabs/stage_tab.py`: Added colored axes (X=red, Y=blue) to 2D view
- `gui/StageView.py`: Center lines now use colored axes

### Phase V5: Fixture Rendering (COMPLETE - Dec 2025)

Render fixture models with DMX control:

- [x] Fixture base class (`visualizer/renderer/fixtures.py`)
- [x] LED Bar: RGBW segments with individual pixel control
- [x] Moving Head: Base + yoke + rotating head with pan/tilt
- [x] PAR: Simple spotlight fixture
- [x] Sunstrip: Warm white segments (8-segment layout)
- [x] Apply DMX color values to fixtures (RGB and color wheel)
- [x] Pan/tilt rotation for moving heads (from DMX)
- [x] **Color wheel support** - Parse QXF color wheel capabilities, map DMX values to colors
- [x] **Beam visualization** - Volumetric cone beams for moving heads with additive blending
- [x] **Fixture type auto-detection** - Parse QXF Type element (Moving Head, LED Bar, etc.)

**Additional Show Creator improvements (Dec 2025):**
- [x] **TCP update throttling** - Pause visualizer updates when not on Stage tab
- [x] **Auto-save effects** - Save to config when effect blocks are edited
- [x] **Toolbar status indicators** - ArtNet and TCP connection status visible from all tabs
- [x] **Color wheel DMX fix** - Use `color_wheel_position` directly when `color_mode == 'Wheel'`
- [x] **Preset to wheel mapping** - Auto-select closest wheel color when preset button clicked

**Files created/modified:**
```
visualizer/renderer/
├── fixtures.py          # BaseFixture, PARRenderer, LEDBarRenderer, MovingHeadRenderer, SunstripRenderer
└── shaders (inline)     # Fixture and beam GLSL shaders

utils/tcp/protocol.py    # Color wheel parsing from QXF
utils/artnet/dmx_manager.py  # Color wheel DMX handling
gui/Ui_MainWindow.py     # Toolbar status indicators
gui/gui.py               # Status timer updates
gui/tabs/stage_tab.py    # TCP update throttling
timeline_ui/colour_block_dialog.py  # Preset to wheel mapping
```

**Channel mapping:** Uses `utils/tcp/protocol.py` to parse QXF files and extract channel functions, color wheel capabilities, and physical dimensions.

### Phase V6: Volumetric Beam Rendering (COMPLETE - Jan 2026)

Ray-traced beam visualization:

- [x] Beam geometry: Cone from fixture lens
- [x] Basic beam shaders (inline in fixtures.py)
- [x] Beam color from color wheel DMX values
- [x] Beam intensity from dimmer channel
- [x] Moving head beam follows pan/tilt
- [x] Additive blending for overlapping beams
- [x] **Floor projection (spotlight effect)** - Soft gradient ellipse where beam hits floor
  - Ray-floor intersection calculation
  - Ellipse shape based on beam angle of incidence
  - Distance-based intensity falloff (30% reduction at 5m)
  - Proper orientation aligned with beam direction
  - Depth test disabled for decal rendering (renders on top of floor)
- [x] **Orientation system fix** - Visualizer now uses absolute yaw/pitch/roll values
  - Removed double-counting of mounting base rotation
  - `get_model_matrix()` and `get_beam_direction()` now consistent with orientation dialog
- [ ] Advanced volumetric fog shader - FUTURE

**Performance:** 60 FPS achieved with multiple fixtures

**Floor Projection Implementation:**
- Added `create_floor_projection_disk()` geometry builder (32-segment unit disk in XZ plane)
- New GLSL shader with gaussian soft-edge falloff (`FLOOR_PROJECTION_FRAGMENT_SHADER`)
- `_calculate_floor_intersection()` for ray-plane math (Y=0 intersection)
- `_render_floor_projection()` with additive blending and depth test disabled
- Only renders for moving heads when beam points downward and reaches floor

**Orientation Fix:**
- Removed `MOUNTING_BASE_ROTATIONS` addition in `get_model_matrix()` - values now used directly
- Fixed `get_beam_direction()` to use same Y-up coordinate system as model matrix
- Orientation dialog sends absolute values (e.g., hanging = pitch 90°), visualizer uses directly

### Phase V7: Prism & Gobo Effects (COMPLETE - Jan 2026)

Visual rendering of prism and gobo effects for moving heads:

- [x] **3-facet prism effect**
  - Renders 3 beam cones at 120° apart around beam axis
  - Each cone tilted 10° outward from center
  - Individual beam intensity at 40% (combined ~120%)
  - `_render_single_beam()` method for per-beam rendering
  - Rotation around Z axis (beam direction) for correct orientation
- [x] **Floor projection prism split**
  - 3 separate floor spots when prism active
  - `_calculate_prism_floor_intersection()` for offset positions
  - Each spot at 40% intensity
- [x] **Gobo pattern rendering**
  - 7 procedural GLSL patterns: Open, Dots, Star, Lines, Triangle, Cross, Breakup
  - Patterns visible in both volumetric beam AND floor projection
  - `GOBO_BEAM_FRAGMENT_SHADER` with angular UV projection
  - `GOBO_FLOOR_PROJECTION_FRAGMENT_SHADER` with radial patterns
  - Brightness range 50-100% to prevent beam cutoff
- [x] **QXF gobo wheel parsing**
  - `GOBO_PATTERN_KEYWORDS` mapping in `protocol.py`
  - `_infer_gobo_pattern()` extracts pattern type from capability names
  - Gobo wheel data sent via TCP to visualizer
- [x] **Gobo rotation animation**
  - `gobo_rotation` DMX channel controls rotation speed
  - `update_gobo_rotation()` method for continuous animation
  - Rotation uniform passed to both beam and floor shaders
- [x] **Combined prism + gobo**
  - Both effects work simultaneously
  - 3 patterned beams with 3 patterned floor projections

**Documentation:** `.claude/PRISM_GOBO_IMPLEMENTATION.md`

**Files modified:**
- `utils/tcp/protocol.py` - Gobo wheel parsing and pattern inference
- `visualizer/renderer/fixtures.py` - Prism/gobo shaders and rendering methods

### Phase V8: UI Polish (PLANNED)

Final UI touches:

- [ ] Connect/Disconnect button (TCP)
- [ ] ArtNet status indicator
- [ ] Universe activity indicators
- [ ] Smooth camera interpolation
- [ ] Remember window position (QSettings)
- [ ] Command-line arguments (--config, --port)
- [ ] Error handling and user messages

---

## Phase Dependencies

```
Show Creator                          Visualizer
─────────────                         ──────────
Phase 10 (Bug Fixes)
    ↓
Phase 11 (Show Structure)
    ↓
Phase 12 (ArtNet Output) ──────────────────────────┐
    ↓                                              │
Phase 13 (TCP Server) ────────┐                    │
    ↓                         │                    │
Phase 14 (Orientation) ◄──────┼────────────────────┤
    ↓                         │                    │
Phase 15 (Riffs)              │                    │
    ↓                         ▼                    ▼
Phase 16 (Audio)        Phase V1 (Foundation)
                              ↓
                        Phase V2 (TCP Client) ◄────┤
                              ↓                    │
                        Phase V3 (ArtNet) ◄────────┘
                              ↓
                        Phase V4 (3D Rendering)
                              ↓
                        Phase V5 (Fixtures)
                              ↓
                        Phase V6 (Beams)
                              ↓
                        Phase V7 (UI Polish)
```

**Phase 14 (Orientation) dependencies:**
- Requires Phase 13 (TCP Server) for sending orientation data to Visualizer
- Requires Visualizer Phase V5 (Fixtures) for 3D preview in orientation popup
- Updates both Show Creator and Visualizer simultaneously

**Critical path for Visualizer:**
1. Phase 12 (ArtNet Output) - Show Creator must send DMX
2. Phase 13 (TCP Server) - Show Creator must send config
3. Phase V2 + V3 - Visualizer receives data
4. Phase V4-V7 - Visualizer renders

---

## Technical Debt

Items to address when time permits:

- [ ] Add comprehensive unit tests
- [ ] Add integration tests
- [ ] Performance optimization for large shows
- [ ] Undo/redo system
- [ ] Better error handling and user messages
- [ ] Type hints throughout codebase
- [ ] Docstrings for public methods
- [ ] Logging instead of print statements

---

## File Locations by Phase

### Show Creator

| Phase | Key Files |
|-------|-----------|
| Universe/Fixtures | `gui/tabs/configuration_tab.py`, `gui/tabs/fixtures_tab.py` |
| Stage | `gui/tabs/stage_tab.py`, `gui/StageView.py`, `gui/stage_items.py` |
| Sublanes | `config/models.py`, `timeline_ui/light_block_widget.py` |
| Export | `utils/to_xml/shows_to_xml.py` |
| Show Structure | `timeline/song_structure.py`, `shows/*.csv` |
| ArtNet Output | `utils/artnet/sender.py`, `utils/artnet/dmx_manager.py`, `utils/artnet/shows_artnet_controller.py` |
| TCP Server | `utils/tcp/server.py`, `utils/tcp/protocol.py` |
| Orientation | `gui/dialogs/orientation_dialog.py`, `gui/widgets/gimbal_widget.py`, `utils/orientation.py` |

### Visualizer

| Phase | Key Files |
|-------|-----------|
| Foundation | `visualizer/main.py` |
| TCP Client | `visualizer/tcp/client.py` |
| ArtNet | `visualizer/artnet/listener.py` |
| Rendering | `visualizer/renderer/engine.py`, `visualizer/renderer/stage.py`, `visualizer/renderer/camera.py` |
| Gizmo | `visualizer/renderer/gizmo.py` |
| Beams | `visualizer/renderer/beams.py` (planned) |

---

## Version Milestones

### v0.1 - Foundation (ACHIEVED)
- Basic project structure
- Configuration save/load

### v0.2 - Setup Complete (ACHIEVED)
- Universe, fixture, stage setup working
- Groups functional

### v0.3 - Timeline MVP (ACHIEVED)
- Sublane system complete
- Basic export working

### v0.4 - Export Polish (ACHIEVED)
- All export features working
- Bug fixes complete

### v0.5 - Show Creation (ACHIEVED - Dec 2025)
- In-app show structure creation
- Shows directory management
- Audio file integration

### v0.6 - ArtNet Preview (ACHIEVED - Dec 2025)
- [x] ArtNet output for preview (Phase 12)
- [x] TCP server for visualizer (Phase 13)

### v0.7 - Visualizer Alpha (ACHIEVED - Dec 2025)
- [x] TCP + ArtNet communication working (Phase V2, V3)
- [x] Basic 3D rendering (Phase V4)

### v0.8 - Visualizer Beta (ACHIEVED - Dec 2025)
- [x] Volumetric beams for moving heads
- [x] All fixture types rendered (PAR, LED Bar, Moving Head, Sunstrip)
- [x] Color wheel support with correct DMX mapping
- [x] Toolbar status indicators for TCP/ArtNet
- [x] Auto-save effects and preset-to-wheel mapping

### v0.9 - Floor Projection (ACHIEVED - Jan 2026)
- [x] Floor projection for moving head beams
- [x] Soft gradient ellipse spotlight effect
- [x] Distance-based intensity falloff

### v1.0 - Feature Complete (FUTURE)
- All planned features
- Stable and tested
- Riffs system
- Advanced volumetric fog shader
