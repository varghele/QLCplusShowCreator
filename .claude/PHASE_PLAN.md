# QLC+ Show Creator - Development Phase Plan

**Last Updated:** December 2024

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

### Phase 4: MainWindow Refactoring (COMPLETE - Dec 2024)

- [x] Split monolithic `gui.py` (1,738 → 270 lines, 84% reduction)
- [x] Modular tab architecture (`gui/tabs/`)
- [x] BaseTab class with lifecycle methods
- [x] Cross-tab communication via parent
- [x] Auto-save functionality

### Phase 5: Sublane System - Data & Detection (COMPLETE - Dec 2024)

- [x] Sublane block data models (Dimmer, Colour, Movement, Special)
- [x] Multiple blocks per sublane type (List architecture)
- [x] FixtureGroupCapabilities class
- [x] Capability auto-detection from fixture definitions
- [x] QLC+ preset categorization (`sublane_presets.py`)

### Phase 6: Sublane System - UI (COMPLETE - Dec 2024)

- [x] Sublane rendering in timeline
- [x] Dynamic lane height based on capabilities
- [x] Drag-to-create sublane blocks
- [x] Resize and move blocks
- [x] Overlap prevention with visual feedback (RED preview)
- [x] Selection and cursor feedback
- [x] Effect envelope auto-expansion

### Phase 7: Sublane Edit Dialogs (COMPLETE - Dec 2024)

- [x] DimmerBlockDialog (intensity, strobe, effect type/speed)
- [x] ColourBlockDialog (RGB, presets, color wheel)
- [x] MovementBlockDialog (2D pan/tilt, shapes, speed)
- [x] SpecialBlockDialog (gobo, prism, focus, zoom)
- [x] Copy/paste functionality (`effect_clipboard.py`)

### Phase 8: QLC+ Export - Dimmer (COMPLETE - Dec 2024)

- [x] Export dimmer blocks to QLC+ sequences
- [x] Dimmer effects (static, strobe, twinkle)
- [x] Speed-based step generation
- [x] RGB control for fixtures without dimmer channel

### Phase 9: QLC+ Export - Movement (COMPLETE - Dec 2024)

- [x] Movement sequences with pan/tilt animation
- [x] Shape generation (circle, lissajous, diamond, etc.)
- [x] Adaptive step density (24 steps/sec max)
- [x] Integration with overlapping dimmer/colour blocks
- [x] Color wheel fallback for non-RGB fixtures
- [x] Dynamic strobe in movement sequences
- [x] Special block export (gobo, prism, focus, zoom)
- [x] Fixed QLC+ crash issue (Duration attribute removal)

---

## Current Phase

### Phase 10: Bug Fixes & Stabilization (IN PROGRESS)

Priority bug fixes before new features:

- [ ] **Universe configuration bugs** - Investigate and fix issues with universe setup
- [ ] Effect system polish
- [ ] Export edge cases
- [ ] UI/UX improvements based on usage

---

## Upcoming Phases (Show Creator)

### Phase 11: In-App Show Structure Creation (PLANNED)

Currently, show structures must be created as CSV files manually. This phase adds in-app creation:

- [ ] Show structure editor UI
- [ ] Song part management (add/remove/reorder)
- [ ] Timing configuration per part
- [ ] BPM and time signature settings
- [ ] Import from CSV (keep existing functionality)
- [ ] Save show structure to configuration

### Phase 12: ArtNet DMX Output (PLANNED - Required for Visualizer)

Enable the Show Creator to send DMX directly for preview:

- [ ] ArtNet packet generation (`utils/artnet/sender.py`)
- [ ] Real-time DMX output during playback
- [ ] Universe routing configuration
- [ ] Network interface selection
- [ ] Rate limiting (44Hz max)
- [ ] Toggle between preview mode and QLC+ export mode

**Note:** This is required before the Visualizer can show live previews.

### Phase 13: TCP Server for Visualizer (PLANNED - Required for Visualizer)

TCP server in Show Creator to send configuration to Visualizer:

- [ ] TCP server implementation (`utils/tcp/server.py`)
- [ ] Protocol definition:
  - Stage dimensions message
  - Fixture list message (positions, types, addresses, modes)
  - Groups message (name, color, fixtures)
  - Update notification on changes
- [ ] Connection status UI indicator
- [ ] Auto-reconnect handling
- [ ] Serialize `Configuration` to network-friendly format

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

### Phase V1: Project Foundation (PLANNED - PRIORITY)

Set up the Visualizer project structure:

- [ ] Create `visualizer/` directory structure
- [ ] Visualizer entry point (`visualizer/main.py`)
- [ ] Import shared modules (`config/models.py`, `utils/fixture_utils.py`)
- [ ] PyQt6 main window skeleton
- [ ] Add ModernGL, PyGLM to requirements

**Files to create:**
```
visualizer/
├── main.py
├── __init__.py
└── requirements.txt (visualizer-specific deps)
```

### Phase V2: TCP Client Integration (PLANNED - PRIORITY)

Receive configuration from Show Creator:

- [ ] TCP client implementation (`visualizer/tcp/client.py`)
- [ ] Parse stage dimensions message
- [ ] Parse fixture list message
- [ ] Parse groups message
- [ ] Handle connection/disconnection gracefully
- [ ] Connection status UI (green/red indicator)
- [ ] Store received config in local data structures

**Files to create:**
```
visualizer/tcp/
├── __init__.py
├── client.py
└── protocol.py
```

### Phase V3: ArtNet Receiver (PLANNED)

Receive live DMX values:

- [ ] ArtNet UDP listener (`visualizer/artnet/listener.py`)
- [ ] Parse ArtNet OpDmx packets
- [ ] Support Universe 0 and 1 (configurable)
- [ ] Thread-safe DMX value storage
- [ ] Connection status detection (receiving/not receiving)
- [ ] Handle both Show Creator and QLC+ as sources

**ArtNet OpDmx packet format:**
- Bytes 0-7: "Art-Net\0"
- Bytes 8-9: OpCode 0x5000 (little-endian)
- Byte 14-15: Universe (little-endian)
- Byte 16-17: Length (big-endian)
- Bytes 18+: DMX data (up to 512 bytes)

**Files to create:**
```
visualizer/artnet/
├── __init__.py
├── listener.py
└── protocol.py
```

### Phase V4: 3D Rendering Foundation (PLANNED)

Basic OpenGL setup:

- [ ] ModernGL context in PyQt6 (`visualizer/renderer/engine.py`)
- [ ] Orbiting camera with mouse controls (`visualizer/renderer/camera.py`)
- [ ] Stage floor with grid lines (`visualizer/renderer/stage.py`)
- [ ] Dark background rendering
- [ ] FPS counter
- [ ] Window resize handling

**Camera controls:**
- Left mouse drag: Orbit around stage center
- Right mouse drag: Pan
- Scroll wheel: Zoom
- Home key: Reset view

**Files to create:**
```
visualizer/renderer/
├── __init__.py
├── engine.py
├── camera.py
└── stage.py
```

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
| ArtNet Output | `utils/artnet/sender.py` (to create) |
| TCP Server | `utils/tcp/server.py` (to create) |

### Visualizer

| Phase | Key Files |
|-------|-----------|
| Foundation | `visualizer/main.py` |
| TCP Client | `visualizer/tcp/client.py` |
| ArtNet | `visualizer/artnet/listener.py` |
| Rendering | `visualizer/renderer/engine.py` |
| Beams | `visualizer/renderer/beams.py` |

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

### v0.4 - Export Polish (CURRENT TARGET)
- All export features working
- Bug fixes complete

### v0.5 - Show Creation (NEXT)
- In-app show structure creation
- ArtNet output for preview

### v0.6 - Visualizer Alpha
- TCP + ArtNet communication working
- Basic 3D rendering

### v0.7 - Visualizer Beta
- Volumetric beams
- All fixture types rendered

### v1.0 - Feature Complete (FUTURE)
- All planned features
- Stable and tested
- Riffs system
