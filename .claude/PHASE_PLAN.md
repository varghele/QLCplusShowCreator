# QLC+ Show Creator - Development Phase Plan

**Last Updated:** December 2025

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

**Phase V4: Complete** - Ready for Phase V5 (Fixture Rendering).

---

## Upcoming Phases (Show Creator)

### Phase 14: Effects/Riffs System Enhancement (PLANNED)

Improve the effects system with predefined sequences:

- [ ] Define "Riff" concept (sequence of sublane effects)
- [ ] Riff library/presets
- [ ] Quick apply riffs to timeline
- [ ] Riff templates per fixture type
- [ ] User-defined riffs

### Phase 15: Audio Analysis Integration (FUTURE)

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

### Phase V5: Fixture Rendering (PLANNED)

Render fixture models:

- [ ] Fixture base class (`visualizer/renderer/fixtures.py`)
- [ ] LED Bar: 10 RGBW segments
- [ ] Moving Head: Base + rotating head
- [ ] Wash: Box with color glow
- [ ] Sunstrip: Warm white segments
- [ ] Apply DMX color values to fixtures
- [ ] Pan/tilt rotation for moving heads (from DMX)

**Channel mapping:** Use `utils/fixture_utils.py` to get channel functions from QXF files.

### Phase V6: Volumetric Beam Rendering (PLANNED)

Ray-traced beam visualization:

- [ ] Beam geometry: Cone from fixture to floor
- [ ] Volumetric fragment shader (`visualizer/renderer/shaders/beam.frag`)
- [ ] Beam color from RGB DMX values
- [ ] Beam intensity from dimmer channel
- [ ] Moving head beam follows pan/tilt
- [ ] Additive blending for overlapping beams
- [ ] Floor projection (spotlight effect)

**Performance target:** 60 FPS with 10+ active beams

**Files to create:**
```
visualizer/renderer/
├── beams.py
└── shaders/
    ├── beam.vert
    ├── beam.frag
    ├── fixture.vert
    └── fixture.frag
```

### Phase V7: UI Polish (PLANNED)

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
Phase 14 (Riffs)              │                    │
    ↓                         ▼                    ▼
Phase 15 (Audio)        Phase V1 (Foundation)
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
| Stage | `gui/tabs/stage_tab.py`, `gui/StageView.py` |
| Sublanes | `config/models.py`, `timeline_ui/light_block_widget.py` |
| Export | `utils/to_xml/shows_to_xml.py` |
| Show Structure | `timeline/song_structure.py`, `shows/*.csv` |
| ArtNet Output | `utils/artnet/sender.py`, `utils/artnet/dmx_manager.py`, `utils/artnet/shows_artnet_controller.py` |
| TCP Server | `utils/tcp/server.py`, `utils/tcp/protocol.py` |

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

### v0.8 - Visualizer Beta
- Volumetric beams
- All fixture types rendered

### v1.0 - Feature Complete (FUTURE)
- All planned features
- Stable and tested
- Riffs system
