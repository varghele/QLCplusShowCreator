# QLC+ Show Creator - Project Overview

**Last Updated:** December 2025

---

## Initial Prompter for Claude

> **Copy this section when starting a new Claude session:**
>
> I'm working on **QLC+ Show Creator**, a PyQt6 application for creating light shows for QLC+ (open-source lighting control software). The project includes:
>
> **Show Creator** (main application):
> - Timeline-based editing with audio synchronization
> - Fixture/universe configuration (E1.31, ArtNet, DMX USB)
> - Stage planning with visual fixture placement
> - Sublane-based effect system (Dimmer, Colour, Movement, Special)
> - Export to QLC+ workspace files (.qxw)
> - ArtNet output for live preview
>
> **Visualizer** (3D preview):
> - Real-time 3D beam visualization
> - Receives stage/fixture config via TCP from Show Creator
> - Receives DMX data via ArtNet (from Show Creator or QLC+)
> - OpenGL rendering with volumetric beams
>
> **Key files:**
> - `.claude/OVERVIEW.md` - This file (project context)
> - `.claude/PHASE_PLAN.md` - Current development roadmap
> - `.claude/PROMPTS.md` - Specific task prompts
> - `config/models.py` - Core data models (shared)
> - `utils/fixture_utils.py` - Fixture parsing (shared)
>
> **Current branch:** `visualizer`
>
> **Tech stack:** Python 3.12, PyQt6, ModernGL, pandas, numpy, PyYAML

---

## Project Purpose

QLC+ Show Creator is a visual tool for creating light shows that export to QLC+ workspace files. The Visualizer provides real-time 3D preview of the lighting effects.

**Workflow:**
1. Configure DMX universes and fixtures (Show Creator)
2. Plan stage layouts visually (Show Creator)
3. Create show structure and effects (Show Creator)
4. Preview in real-time (Visualizer receives data via TCP + ArtNet)
5. Export to QLC+ for live performance

---

## Architecture Overview

```
QLCplusShowCreator/
├── main.py                    # Show Creator entry point
├── config/
│   └── models.py              # Core data models (SHARED)
├── gui/                       # Show Creator GUI
│   ├── gui.py                 # MainWindow orchestration
│   ├── tabs/                  # Modular tab system
│   └── StageView.py           # 2D stage visualization
├── timeline/                  # Timeline logic
├── timeline_ui/               # Timeline widgets
├── effects/                   # Effect functions
├── utils/
│   ├── fixture_utils.py       # QXF parsing (SHARED)
│   ├── sublane_presets.py     # Channel categorization (SHARED)
│   └── to_xml/                # QLC+ export
├── audio/                     # Audio playback (optional)
├── shows/                     # Show structure CSV files
├── custom_fixtures/           # User fixture definitions
│
└── visualizer/                # 3D Visualizer (separate app)
    ├── main.py                # Visualizer entry point
    ├── tcp/                   # TCP client for config sync
    ├── artnet/                # ArtNet receiver for DMX
    ├── renderer/              # OpenGL 3D rendering
    │   ├── engine.py          # Main render loop
    │   ├── camera.py          # Orbiting camera
    │   ├── stage.py           # Floor/grid rendering
    │   ├── fixtures.py        # Fixture models
    │   ├── beams.py           # Volumetric beams
    │   └── shaders/           # GLSL shaders
    └── ui/                    # Visualizer UI
```

---

## Communication Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Show Creator                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Config    │  │  Timeline   │  │   Playback Engine   │  │
│  │   Models    │  │   Effects   │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         ▼                │                     ▼             │
│  ┌─────────────┐         │         ┌─────────────────────┐  │
│  │ TCP Server  │         │         │   ArtNet Sender     │  │
│  │ (Config)    │         │         │   (DMX Output)      │  │
│  └──────┬──────┘         │         └──────────┬──────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────┘
          │                │                     │
          │ TCP            │                     │ ArtNet (UDP 6454)
          │ Stage layout   │                     │ DMX values
          │ Fixtures       │                     │
          │ Groups         │                     │
          ▼                │                     ▼
┌─────────────────────────────────────────────────────────────┐
│                       Visualizer                             │
│  ┌─────────────┐                   ┌─────────────────────┐  │
│  │ TCP Client  │                   │  ArtNet Listener    │  │
│  │ (Config)    │                   │  (DMX Input)        │  │
│  └──────┬──────┘                   └──────────┬──────────┘  │
│         │                                     │             │
│         ▼                                     ▼             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              3D Rendering Engine                     │   │
│  │   Stage Floor │ Fixtures │ Volumetric Beams         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

                              OR

┌─────────────────┐
│      QLC+       │──── ArtNet (UDP 6454) ────▶ Visualizer
│  (DMX Control)  │     (when Show Creator
└─────────────────┘      is not playing)
```

### TCP Protocol (Config Sync)

Show Creator → Visualizer:
- Stage dimensions (width, depth, height)
- Fixture list (positions, types, DMX addresses, modes)
- Groups (name, color, fixture members)
- Updates on configuration changes

### ArtNet Protocol (DMX Data)

- **Source**: Show Creator (during playback) OR QLC+ (for testing)
- **Port**: UDP 6454
- **Universes**: Configurable (typically 0, 1)
- **Rate**: Up to 44Hz (DMX refresh rate)
- **Data**: 512 channels per universe

---

## Core Data Models (`config/models.py`)

### Key Classes (Shared by Show Creator and Visualizer)

**Configuration** - Root container for all project data
- `universes: Dict[int, Universe]` - DMX universe configurations
- `fixtures: Dict[str, Fixture]` - All fixtures by name
- `groups: Dict[str, FixtureGroup]` - Fixture groups
- `shows: Dict[str, Show]` - Shows with song structure
- `stage_width`, `stage_depth`, `stage_height` - Stage dimensions

**Fixture** - Individual lighting fixture
- `universe`, `address` - DMX addressing
- `manufacturer`, `model` - QLC+ fixture definition reference
- `current_mode`, `available_modes` - Channel modes
- `type` - PAR, MH (Moving Head), WASH, BAR
- `x, y, z, rotation` - Stage position

**FixtureGroup** - Group of fixtures controlled together
- `fixtures: List[Fixture]`
- `capabilities: FixtureGroupCapabilities` - Auto-detected
- `color: str` - Group color for UI

**Universe** - DMX universe configuration
- `output_type` - E1.31, ArtNet, DMX USB
- `ip`, `port`, `subnet` - Network settings

### Sublane Block Models

- **DimmerBlock**: `intensity`, `effect_type`, `effect_speed`
- **ColourBlock**: `color` (RGB), `color_mode`, presets
- **MovementBlock**: `shape`, `pan/tilt`, `size`, `speed`
- **SpecialBlock**: `gobo_index`, `prism_enabled`, `focus`, `zoom`

---

## Show Creator GUI

### Tab System

1. **ConfigurationTab** - Universe management (E1.31, ArtNet, DMX USB)
2. **FixturesTab** - Fixture inventory, groups, QLC+ definition import
3. **StageTab** - Visual stage layout with drag-and-drop
4. **ShowsTab** - Timeline editing with sublanes

### Sublane System

| Sublane | Controls | Can Overlap? |
|---------|----------|--------------|
| **Dimmer** | Intensity, strobe, iris | Yes (cross-fade) |
| **Colour** | RGB, color wheel, CMY | Yes (cross-fade) |
| **Movement** | Pan/tilt, shapes, speed | No |
| **Special** | Gobo, prism, focus, zoom | No |

---

## Visualizer

### Purpose

Real-time 3D visualization of lighting effects for:
- Previewing shows during creation
- Testing without physical fixtures
- Debugging DMX output
- Client presentations

### Features

- **3D Stage Rendering**: Floor grid matching stage dimensions
- **Fixture Models**: LED bars, moving heads, washes, sunstrips
- **Volumetric Beams**: Ray-traced light beams with color/intensity
- **Pan/Tilt Animation**: Moving heads follow DMX values
- **Orbiting Camera**: Mouse-controlled view
- **Dual Input**: TCP for config, ArtNet for DMX

### Rendering Approach

- **Engine**: ModernGL (modern OpenGL bindings)
- **Beams**: Cone geometry with volumetric fragment shaders
- **Blending**: Additive for overlapping beams
- **Performance Target**: 60 FPS with 10+ active beams

### Fixture Rendering

| Type | Visualization |
|------|---------------|
| LED Bar | 10 RGBW segments in a row |
| Moving Head | Base + rotating head with beam |
| Wash | Box shape with front color glow |
| Sunstrip | Strip with warm white segments |

---

## Shared Code

The following modules are shared between Show Creator and Visualizer:

| Module | Purpose |
|--------|---------|
| `config/models.py` | All data models |
| `utils/fixture_utils.py` | QXF file parsing |
| `utils/sublane_presets.py` | Channel categorization |

This ensures consistency and reduces code duplication.

---

## Current Status (December 2025)

### Show Creator - Working
- Universe configuration (E1.31, ArtNet, DMX USB)
- Fixture import from QLC+ definitions
- Fixture groups with color coding
- Stage planning with visual placement
- In-app show structure creation (Structure tab)
- Shows directory management with audio file integration
- Timeline with sublane-based effects
- All sublane edit dialogs (Dimmer, Colour, Movement, Special)
- Copy/paste effects
- Export to QLC+ workspace
- ArtNet DMX output for live preview
- TCP server for Visualizer communication
- Auto-save effects on edit
- Toolbar status indicators for TCP/ArtNet
- Color wheel support with preset-to-wheel mapping

### Visualizer - Working
- TCP client receives stage/fixture configuration
- ArtNet listener receives DMX data
- 3D stage rendering with grid
- Orbiting camera with mouse controls
- Fixture rendering (PAR, LED Bar, Moving Head, Sunstrip)
- Color wheel support for fixtures without RGB
- Volumetric beam rendering for moving heads
- Pan/tilt animation from DMX values
- Launch from Stage tab button

### Visualizer - Future Enhancements
- Floor projection for beams
- Advanced volumetric fog effects
- More fixture types (Wash, etc.)

---

## Development Workflow

### Environment Setup

```bash
# Create conda environment
conda env create -f environment.yml
conda activate QLCAutoShow

# Or install manually
pip install -r requirements.txt

# Run Show Creator
python main.py

# Run Visualizer (when implemented)
python visualizer/main.py
```

### Testing

```bash
# Show Creator visual tests
python tests/visual/test_sublane_blocks.py
python tests/visual/test_sublane_ui.py

# Visualizer tests (when implemented)
python visualizer/tests/test_tcp_client.py
python visualizer/tests/test_artnet_listener.py
```

---

## Files to Know

| File | Purpose | When to Read |
|------|---------|--------------|
| `config/models.py` | All data models | Understanding data flow |
| `utils/fixture_utils.py` | Fixture parsing | Shared by both apps |
| `timeline_ui/light_block_widget.py` | Effect interaction | UI debugging |
| `utils/to_xml/shows_to_xml.py` | QLC+ export | Export issues |
| `visualizer/renderer/engine.py` | 3D rendering | Visualizer work |
| `visualizer/tcp/client.py` | Config sync | TCP integration |

---

## Quick References

### Sublane Colors (UI)
- Dimmer: Amber (#FFC107)
- Colour: Purple (#9C27B0)
- Movement: Blue (#2196F3)
- Special: Orange (#FF5722)

### Network Ports
- ArtNet: UDP 6454
- TCP Config: TBD (suggest 7654)

### DMX Protocols
- E1.31 (sACN): Network-based, multicast
- ArtNet: Network-based, broadcast
- DMX USB: Serial interface (FTDI, etc.)
