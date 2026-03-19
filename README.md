# QLC+ Show Creator

A visual tool for creating light shows for [QLC+](https://www.qlcplus.org/), featuring timeline-based editing with audio synchronization, real-time ArtNet preview, and a 3D Visualizer.

## Features

### Show Creator
- **Universe Configuration**: E1.31, ArtNet, and DMX USB support
- **Fixture Management**: Import from QLC+ fixture definitions (.qxf)
- **Stage Planning**: Visual fixture placement with 3D orientation system
- **Show Structure**: In-app creation of song parts with BPM, time signature, transitions
- **Timeline Editing**: Sublane-based effects (Dimmer, Colour, Movement, Special)
- **Riff System**: Reusable beat-based effect patterns with drag-and-drop
- **Multi-Target Lanes**: Lanes can target multiple fixture groups or individual fixtures
- **ArtNet Output**: Real-time DMX preview at 44Hz during playback
- **QLC+ Export**: Generate workspace files (.qxw)

### 3D Visualizer
- **Real-time Rendering**: ModernGL-based 3D stage visualization
- **Fixture Types**: LED bars, moving heads, PARs, sunstrips
- **Volumetric Beams**: Cone beams with floor projection spotlights
- **Effects**: Prism (3-facet beam split), gobo patterns, focus simulation
- **Dual Input**: TCP for config sync, ArtNet for live DMX

## Installation

### Using Conda (Recommended)

```bash
conda env create -f environment.yml
conda activate QLCAutoShow
python main.py
```

### Using pip

```bash
pip install -r requirements.txt
python main.py
```

### System Requirements

- Python 3.12+
- Linux: Install PortAudio for audio features
  ```bash
  sudo apt-get install portaudio19-dev  # Ubuntu/Debian
  ```

## Quick Start

1. **Configure Universes** - Set up DMX output (Configuration tab)
2. **Add Fixtures** - Import from QLC+ definitions (Fixtures tab)
3. **Plan Stage** - Position and orient fixtures (Stage tab)
4. **Create Structure** - Define song parts with BPM and timing (Structure tab)
5. **Build Show** - Add effects on the timeline, use riffs for quick patterns (Shows tab)
6. **Preview** - Enable ArtNet output and/or launch the 3D Visualizer from Stage tab
7. **Export** - Generate QLC+ workspace file (.qxw)

## Project Structure

```
QLCplusShowCreator/
├── main.py              # Application entry point
├── config/              # Data models and serialization
├── gui/                 # UI (tabs, dialogs, stage view)
├── timeline/            # Playback engine and song structure
├── timeline_ui/         # Timeline widgets and effect editors
├── riffs/               # Reusable effect library
├── utils/               # ArtNet, TCP, export, orientation
├── audio/               # Audio playback and waveform analysis
├── shows/               # Show data (CSV + audio files)
├── custom_fixtures/     # User fixture definitions (.qxf)
├── visualizer/          # 3D Visualizer application
└── docs/                # Documentation
```

## Documentation

- [Architecture](docs/architecture.md) - Project structure, data models, communication
- [ArtNet DMX Output](docs/artnet.md) - Real-time DMX preview system
- [TCP Protocol](docs/tcp-protocol.md) - Visualizer configuration sync
- [3D Visualizer](docs/visualizer.md) - Rendering, effects, camera controls
- [Fixture Orientation](docs/orientation.md) - 3D orientation and mounting system
- [Riff System](docs/riffs.md) - Reusable beat-based effect patterns

## License

GPL-3.0 - See [LICENSE](LICENSE) for details.
