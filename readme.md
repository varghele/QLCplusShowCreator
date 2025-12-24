# QLC+ Show Creator

A visual tool for creating light shows for QLC+, featuring timeline-based editing with audio synchronization.

## Features

### Sublane-Based Timeline
- **Dimmer Effects**: Static, strobe, twinkle, ping-pong, waterfall effects with adjustable speed and intensity
- **Color Control**: RGB/RGBW color mixing with automatic color wheel fallback for non-RGB fixtures
- **Movement Effects**: Pan/tilt positioning with shapes (circle, lissajous, diamond, square, triangle, figure-8, bounce, random)
- **Special Effects**: Gobo selection, prism control, beam focus, and zoom

### Movement Effects
- **Shape Generation**: 9 different movement patterns with customizable parameters
- **Adaptive Step Density**: Automatically optimizes step count based on speed (24 steps/second max to prevent QLC+ overload)
- **Multi-Channel Integration**: Combines pan/tilt with dimmer, color, and special effects in single sequences
- **Phase Offset**: Synchronized multi-fixture effects with adjustable phase

### Smart Export
- **Color Wheel Mapping**: Automatically maps RGB colors to closest color wheel position for fixtures without RGB
- **Dynamic Effects**: Strobe and twinkle effects work with movement sequences
- **Optimized Performance**: Speed-based step density (64 steps/cycle for slow, 32 for medium, 16 for fast movements)
- **QLC+ Compatible**: Generates valid workspace files that open without crashes

### Audio Synchronization
- BPM and time signature detection
- Visual beat grid alignment
- Song structure with multiple parts

## Installation

### Using Conda (recommended)

```bash
# Create environment from file
conda env create -f environment.yml

# Activate environment
conda activate QLCAutoShow
```

### Required Packages

**Core dependencies** (included in environment.yml):
- Python 3.12+
- PyQt6 - GUI framework
- PyYAML - Configuration file handling
- NumPy - Numerical operations
- Pandas - Data handling

**Audio dependencies** (optional, for audio playback features):
```bash
pip install pyaudio soundfile librosa
```
[gui.py](gui/gui.py)
Or with conda:
```bash
conda install -c conda-forge pyaudio soundfile librosa
```

Note: On Linux, you may need to install PortAudio first:
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev

# Fedora
sudo dnf install portaudio-devel
```

**USB DMX device detection** (optional, for DMX USB protocol support):
```bash
pip install pyserial
```

Or with conda:
```bash
conda install -c conda-forge pyserial
```

This enables automatic detection of USB DMX interfaces in the configuration tab.

### Manual Installation (pip)

```bash
pip install PyQt6 pyyaml numpy pandas

# Optional audio support
pip install pyaudio soundfile librosa

# Optional USB DMX device detection
pip install pyserial
```

## Running

```bash
python main.py
```

## Project Structure

```
QLCplusShowCreator/
├── main.py              # Application entry point
├── audio/               # Audio playback and waveform display
├── config/              # Configuration and data models
├── effects/             # Light effect definitions
├── gui/                 # Main GUI and tab widgets
├── timeline/            # Timeline data structures
├── timeline_ui/         # Timeline visualization widgets
└── utils/               # Utility functions
```
