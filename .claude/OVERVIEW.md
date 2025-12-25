# QLC+ Show Creator - Project Overview

**Last Updated:** December 2024

---

## Initial Prompter for Claude

> **Copy this section when starting a new Claude session:**
>
> I'm working on **QLC+ Show Creator**, a PyQt6 application for creating light shows for QLC+ (open-source lighting control software). The app features:
> - Timeline-based editing with audio synchronization
> - Fixture/universe configuration (E1.31, ArtNet, DMX USB)
> - Stage planning with visual fixture placement
> - Sublane-based effect system (Dimmer, Colour, Movement, Special)
> - Export to QLC+ workspace files (.qxw)
>
> **Key files to understand the architecture:**
> - `.claude/OVERVIEW.md` - This file (project context)
> - `.claude/PHASE_PLAN.md` - Current development roadmap
> - `.claude/PROMPTS.md` - Specific task prompts
> - `config/models.py` - Core data models
> - `gui/gui.py` - Main window orchestration
>
> **Current branch:** `refactorplustimeline`
>
> **Tech stack:** Python 3.12, PyQt6, pandas, numpy, PyYAML

---

## Project Purpose

QLC+ Show Creator is a visual tool for creating light shows that export to QLC+ workspace files. It bridges the gap between:
- **Manual QLC+ programming** (time-consuming, complex)
- **Automated show generation** (future goal with audio analysis)

The app enables users to:
1. Configure DMX universes and fixtures
2. Plan stage layouts visually
3. Load song structures (currently CSV, future: in-app creation)
4. Design effects using a timeline with sublanes
5. Export complete QLC+ workspace files

---

## Architecture Overview

```
QLCplusShowCreator/
├── main.py                    # Application entry point
├── config/
│   └── models.py              # Core data models (40KB - most important!)
├── gui/
│   ├── gui.py                 # MainWindow orchestration (~270 lines)
│   ├── Ui_MainWindow.py       # Qt Designer UI
│   ├── StageView.py           # Stage visualization widget
│   └── tabs/                  # Modular tab system
│       ├── base_tab.py        # Abstract base for all tabs
│       ├── configuration_tab.py  # Universe/DMX setup
│       ├── fixtures_tab.py    # Fixture management
│       ├── stage_tab.py       # Stage layout
│       └── shows_tab.py       # Timeline/effects editing
├── timeline/
│   ├── light_lane.py          # Lane runtime logic
│   ├── song_structure.py      # Show structure data
│   └── playback_engine.py     # Playback control
├── timeline_ui/
│   ├── master_timeline_widget.py
│   ├── timeline_widget.py     # Base timeline canvas
│   ├── light_lane_widget.py   # Lane container widget
│   ├── light_block_widget.py  # Effect block widget (65KB - complex!)
│   ├── *_block_dialog.py      # Sublane edit dialogs
│   └── effect_clipboard.py    # Copy/paste support
├── effects/
│   ├── dimmers.py             # Dimmer effect functions
│   ├── bars.py                # Bar/LED effects
│   ├── moving_heads.py        # Movement patterns
│   └── multicolor.py          # Color effects
├── utils/
│   ├── fixture_utils.py       # Fixture definition parsing
│   ├── sublane_presets.py     # QLC+ preset categorization
│   └── to_xml/
│       └── shows_to_xml.py    # QLC+ export (most complex)
├── audio/                     # Audio playback/analysis (optional)
├── shows/                     # Show structure CSV files
└── custom_fixtures/           # User fixture definitions
```

---

## Core Data Models (`config/models.py`)

### Key Classes

**Configuration** - Root container for all project data
- `universes: Dict[int, Universe]` - DMX universe configurations
- `fixtures: Dict[str, Fixture]` - All fixtures by name
- `groups: Dict[str, FixtureGroup]` - Fixture groups
- `shows: Dict[str, Show]` - Shows with song structure
- `stage_*` - Stage dimensions

**Fixture** - Individual lighting fixture
- `universe`, `address` - DMX addressing
- `manufacturer`, `model` - QLC+ fixture definition reference
- `current_mode`, `available_modes` - Channel modes
- `type` - PAR, MH (Moving Head), WASH, BAR
- `x, y, z, rotation` - Stage position

**FixtureGroup** - Group of fixtures controlled together
- `fixtures: List[Fixture]`
- `capabilities: FixtureGroupCapabilities` - Auto-detected

**LightBlock** - Effect envelope on timeline
- `start_time`, `end_time` - Timing
- `dimmer_blocks: List[DimmerBlock]`
- `colour_blocks: List[ColourBlock]`
- `movement_blocks: List[MovementBlock]`
- `special_blocks: List[SpecialBlock]`

### Sublane Block Models

Each sublane type has independent timing within the envelope:

- **DimmerBlock**: `intensity`, `effect_type` (static/strobe/twinkle), `effect_speed`
- **ColourBlock**: `color` (RGB), `color_mode`, preset options
- **MovementBlock**: `shape`, `pan/tilt`, `size`, `speed`, `interpolate_gaps`
- **SpecialBlock**: `gobo_index`, `prism_enabled`, `focus`, `zoom`

---

## GUI Architecture

### Tab System

The MainWindow uses a **modular tab architecture** (refactored Dec 2024):

1. **ConfigurationTab** - Universe management (E1.31, ArtNet, DMX USB)
2. **FixturesTab** - Fixture inventory, groups, QLC+ definition import
3. **StageTab** - Visual stage layout with drag-and-drop
4. **ShowsTab** - Timeline editing with sublanes

### Cross-Tab Communication

```
FixturesTab modifies groups
    ↓
MainWindow.on_groups_changed()
    ↓
├── StageTab.update_from_config()
└── ShowsTab.update_from_config()
```

---

## Sublane System

The effect system uses **four sublane types** based on fixture capabilities:

| Sublane | Controls | Can Overlap? |
|---------|----------|--------------|
| **Dimmer** | Intensity, strobe, iris | Yes (cross-fade) |
| **Colour** | RGB, color wheel, CMY | Yes (cross-fade) |
| **Movement** | Pan/tilt, shapes, speed | No (one position at a time) |
| **Special** | Gobo, prism, focus, zoom | No (one setting at a time) |

### Capability Detection

Fixture capabilities are **auto-detected** from QLC+ fixture definition files (`.qxf`):
- Channel `Preset` attributes are categorized into sublanes
- See `utils/sublane_presets.py` for full mapping
- Groups show only applicable sublanes

---

## QLC+ Export

Export logic is in `utils/to_xml/shows_to_xml.py`:

1. Creates QLC+ workspace XML structure
2. Generates sequences from sublane blocks
3. Maps fixtures to channels based on modes
4. Handles color wheel fallback for non-RGB fixtures
5. Implements adaptive step density (24 steps/sec max)
6. Supports dynamic dimmer effects (strobe, twinkle)

---

## Current Status (December 2024)

### Working Features
- Universe configuration (E1.31, ArtNet, DMX USB)
- Fixture import from QLC+ definitions
- Fixture groups with color coding
- Stage planning with visual placement
- CSV-based show structure import
- Timeline with sublane-based effects
- All sublane edit dialogs (dimmer, colour, movement, special)
- Copy/paste effects
- Export to QLC+ workspace

### Known Issues
- Universe configuration has some bugs (needs investigation)
- Only CSV import for show structure (no in-app creation)
- Some effects still need polish/bug fixes

### Not Yet Implemented
- In-app show structure creation
- ArtNet DMX output from the app
- TCP connection for external visualizer
- "Riffs" (predefined effect sequences)
- AI-assisted show generation

---

## Development Workflow

### Environment Setup

```bash
# Create conda environment
conda env create -f environment.yml
conda activate QLCAutoShow

# Or install manually
pip install -r requirements.txt

# Run the application
python main.py
```

### Testing

```bash
# Visual tests (interactive)
python tests/visual/test_sublane_blocks.py
python tests/visual/test_sublane_ui.py
python tests/visual/test_capability_detection.py
```

### Key Commands

```bash
# Git
git checkout refactorplustimeline
git pull origin refactorplustimeline

# Running
python main.py

# With specific config
python main.py --config path/to/config.yaml
```

---

## Files to Know

| File | Purpose | When to Read |
|------|---------|--------------|
| `config/models.py` | All data models | Understanding data flow |
| `timeline_ui/light_block_widget.py` | Effect interaction | UI debugging |
| `utils/to_xml/shows_to_xml.py` | QLC+ export | Export issues |
| `gui/tabs/*.py` | Tab implementations | Tab-specific work |
| `utils/fixture_utils.py` | Fixture parsing | Capability issues |

---

## External Dependencies

- **QLC+**: Target lighting software (https://www.qlcplus.org/)
- **Fixture definitions**: QLC+ `.qxf` files define fixture capabilities
- **Audio files**: For timeline synchronization (optional)

---

## Quick References

### Sublane Colors (UI)
- Dimmer: Amber (#FFC107)
- Colour: Purple (#9C27B0)
- Movement: Blue (#2196F3)
- Special: Orange (#FF5722)

### Effect Speeds
- 1/4, 1/2, 1, 2, 4 (beats per step)

### DMX Protocols
- E1.31 (sACN): Network-based, multicast
- ArtNet: Network-based, broadcast
- DMX USB: Serial interface (FTDI, etc.)
