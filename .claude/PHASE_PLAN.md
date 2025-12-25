# QLC+ Show Creator - Development Phase Plan

**Last Updated:** December 2024

---

## Overview

This document tracks the development phases for QLC+ Show Creator. Check boxes indicate completion status.

---

## Completed Phases

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

## Upcoming Phases

### Phase 11: In-App Show Structure Creation (PLANNED)

Currently, show structures must be created as CSV files manually. This phase adds in-app creation:

- [ ] Show structure editor UI
- [ ] Song part management (add/remove/reorder)
- [ ] Timing configuration per part
- [ ] BPM and time signature settings
- [ ] Import from CSV (keep existing functionality)
- [ ] Save show structure to configuration

**Note:** This replaces the manual CSV workflow and should come before effects creation in the user workflow.

### Phase 12: Effects/Riffs System Enhancement (PLANNED)

Improve the effects system with predefined sequences:

- [ ] Define "Riff" concept (sequence of sublane effects)
- [ ] Riff library/presets
- [ ] Quick apply riffs to timeline
- [ ] Riff templates per fixture type
- [ ] User-defined riffs

### Phase 13: ArtNet DMX Output (PLANNED)

Enable the app to send DMX directly (for preview/testing):

- [ ] ArtNet packet generation
- [ ] Real-time DMX output during playback
- [ ] Universe routing configuration
- [ ] Network interface selection
- [ ] Rate limiting to avoid overload

### Phase 14: External Visualizer Connection (PLANNED)

TCP connection for external visualizer application:

- [ ] TCP server in Show Creator
- [ ] Protocol definition for stage/fixture data
- [ ] Real-time fixture position updates
- [ ] Fixture configuration sync
- [ ] Connection status UI

**Note:** Visualizer will be a separate repository.

### Phase 15: Audio Analysis Integration (FUTURE)

AI-assisted show generation:

- [ ] Audio file analysis (beat detection, spectral analysis)
- [ ] Song structure auto-detection
- [ ] Effect suggestion based on audio
- [ ] Automatic show generation algorithm

**Note:** This is a longer-term goal requiring significant research and design.

---

## Phase Dependencies

```
Phase 10 (Bug Fixes)
    ↓
Phase 11 (Show Structure) ─────────┐
    ↓                              │
Phase 12 (Riffs)                   │
    ↓                              │
Phase 13 (ArtNet Output) ──────────┤
    ↓                              │
Phase 14 (Visualizer) ←────────────┘
    ↓
Phase 15 (Audio Analysis)
```

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

| Phase | Key Files |
|-------|-----------|
| Universe/Fixtures | `gui/tabs/configuration_tab.py`, `gui/tabs/fixtures_tab.py` |
| Stage | `gui/tabs/stage_tab.py`, `gui/StageView.py` |
| Sublanes | `config/models.py`, `timeline_ui/light_block_widget.py` |
| Export | `utils/to_xml/shows_to_xml.py` |
| Show Structure | `timeline/song_structure.py`, `shows/*.csv` |

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
- Riffs system

### v1.0 - Feature Complete (FUTURE)
- All planned features
- Stable and tested
