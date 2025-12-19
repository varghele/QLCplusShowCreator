# QLC+ Show Creator

A visual tool for creating light shows for QLC+, featuring timeline-based editing with audio synchronization.

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

### Manual Installation (pip)

```bash
pip install PyQt6 pyyaml numpy pandas

# Optional audio support
pip install pyaudio soundfile librosa
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
