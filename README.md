# QLC+ Show Creator

A visual tool for creating light shows for [QLC+](https://www.qlcplus.org/), featuring timeline-based editing with audio synchronization.

## Features

- **Universe Configuration**: E1.31, ArtNet, and DMX USB support
- **Fixture Management**: Import from QLC+ fixture definitions
- **Stage Planning**: Visual fixture placement with drag-and-drop
- **Timeline Editing**: Sublane-based effects (Dimmer, Colour, Movement, Special)
- **QLC+ Export**: Generate workspace files (.qxw)

## Installation

### Using Conda (Recommended)

```bash
# Create environment
conda env create -f environment.yml

# Activate environment
conda activate QLCAutoShow

# Run
python main.py
```

### Using pip

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

### System Requirements

- Python 3.12+
- Linux: Install PortAudio for audio features
  ```bash
  sudo apt-get install portaudio19-dev  # Ubuntu/Debian
  ```

## Quick Start

1. **Configure Universes**: Set up DMX output (Configuration tab)
2. **Add Fixtures**: Import from QLC+ definitions (Fixtures tab)
3. **Plan Stage**: Position fixtures visually (Stage tab)
4. **Create Show**: Load structure, add effects (Shows tab)
5. **Export**: Generate QLC+ workspace file

## Project Structure

```
QLCplusShowCreator/
├── main.py              # Entry point
├── config/              # Data models
├── gui/                 # UI components
├── timeline/            # Timeline logic
├── timeline_ui/         # Timeline widgets
├── effects/             # Effect functions
├── utils/               # Utilities and export
├── shows/               # Show structure files
└── custom_fixtures/     # User fixture definitions
```

## License

GPL-3.0 - See [LICENSE](LICENSE) for details.

## Contributing

This project is under active development. See `.claude/` folder for development documentation.
