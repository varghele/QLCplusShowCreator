# Light Show Visualizer

A real-time 3D DMX light show visualizer that receives ArtNet data and renders accurate beam visualizations for stage lighting fixtures.

## Project Overview

This visualizer is designed to work alongside:
- **QLC+** - Open-source lighting control software
- **Show Creator** - Custom Python-based show creation tool

The visualizer reads stage configuration from YAML files, parses QLC+ fixture definitions (`.qxf` files) for channel mappings, and listens for live ArtNet DMX data to render real-time 3D beam visualizations.

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│    QLC+         │     │  Show Creator   │
│  (DMX Control)  │     │    (Python)     │
└────────┬────────┘     └────────┬────────┘
         │ ArtNet                │ Config
         │ (UDP 6454)            │ (YAML)
         │ 127.0.0.1             │
         ▼                       ▼
┌─────────────────────────────────────────┐
│           Light Show Visualizer         │
│  ┌───────────────────────────────────┐  │
│  │         ArtNet Listener           │  │
│  │      (Universe 0 & 1, UDP)        │  │
│  └───────────────┬───────────────────┘  │
│                  │                      │
│  ┌───────────────▼───────────────────┐  │
│  │        DMX Processor              │  │
│  │  (Channel → Fixture Mapping)      │  │
│  └───────────────┬───────────────────┘  │
│                  │                      │
│  ┌───────────────▼───────────────────┐  │
│  │       3D Rendering Engine         │  │
│  │  (OpenGL + Ray-traced Beams)      │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Technical Specifications

### Input Sources
| Source | Format | Purpose |
|--------|--------|---------|
| Stage Config | YAML (`conf_test.yaml`) | Stage size, fixture positions, groups |
| Fixture Definitions | QLC+ `.qxf` XML files | Channel mappings, capabilities |
| DMX Data | ArtNet (UDP port 6454) | Real-time lighting values |

### Supported Fixtures (from config)
| Type | Model | Channels | Segments |
|------|-------|----------|----------|
| LED BAR | Varghele LED BAR | 40 | 10 × RGBW |
| Moving Head | Varytec Hero Spot 60 | 14 | Pan/Tilt/Color/Gobo |
| Sunstrip | Showtec Sunstrip Active | 10 | Blinder segments |
| Wash | Stairville Wild Wash Pro 648 | 6 | RGB wash |

### ArtNet Configuration
- **Protocol:** ArtNet (Art-Net 4)
- **IP:** 127.0.0.1 (localhost)
- **Port:** 6454 (UDP)
- **Universes:** 0 and 1 (expandable)

### 3D Rendering
- **Engine:** OpenGL (via ModernGL or PyOpenGL)
- **Beams:** Ray-traced volumetric light beams
- **Stage:** Grid floor matching stage dimensions
- **Camera:** Orbiting camera with mouse rotation
- **Background:** Dark/black

### UI Elements
- Main 3D viewport (resizable window)
- Connect/Disconnect button with status indicator
- FPS counter
- Mouse controls for camera rotation

---

## Configuration File Structure

The visualizer reads from `conf_test.yaml`:

```yaml
# Stage dimensions (to be added)
stage:
  width: 10.0   # meters
  depth: 6.0    # meters
  height: 4.0   # meters

fixtures:
  - name: B1
    type: BAR
    address: 1
    universe: 1
    x: 4.5
    y: -2.5
    z: 0.0
    current_mode: "40 Channels Mode"
    # ... additional fixture properties

groups:
  BARS:
    color: '#ffb6c1'
    fixtures: [...]
```

### QLC+ Fixture File Structure (`.qxf`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FixtureDefinition>
  <Model>Hero Spot 60</Model>
  <Manufacturer>Varytec</Manufacturer>
  <Channel Name="Pan">
    <Group Byte="0">Pan</Group>
  </Channel>
  <Channel Name="Tilt">
    <Group Byte="0">Tilt</Group>
  </Channel>
  <Mode Name="14 Channel">
    <Channel Number="0">Pan</Channel>
    <Channel Number="1">Pan Fine</Channel>
    <!-- ... -->
  </Mode>
</FixtureDefinition>
```

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.10+ | Consistency with Show Creator |
| 3D Rendering | ModernGL + PyGLM | Modern OpenGL bindings, performant |
| Window/UI | PyQt6 or PySide6 | Native look, OpenGL integration |
| ArtNet | stupidArtnet or custom | Lightweight ArtNet receiver |
| Config Parsing | PyYAML | YAML configuration |
| XML Parsing | lxml or ElementTree | QLC+ fixture files |

### Alternative: JavaScript/Electron
If Python 3D performance is insufficient:
- Three.js for WebGL rendering
- Electron for desktop packaging
- Better ray-tracing via WebGL shaders

---

## Implementation Phases

### Phase 1: Project Foundation
- [ ] Set up Python project structure
- [ ] Create virtual environment and dependencies
- [ ] Implement YAML config parser
- [ ] Implement QLC+ `.qxf` fixture file parser
- [ ] Create data models for fixtures, channels, stage

### Phase 2: ArtNet Receiver
- [ ] Implement ArtNet UDP listener
- [ ] Parse ArtNet packets (OpDmx)
- [ ] Map DMX values to fixture channels
- [ ] Handle universe routing (0 and 1)
- [ ] Connection status detection

### Phase 3: 3D Rendering Foundation
- [ ] Set up PyQt6 + ModernGL window
- [ ] Implement orbiting camera with mouse controls
- [ ] Render stage floor with grid
- [ ] Create basic fixture representations (placeholder shapes)
- [ ] Add FPS counter

### Phase 4: Fixture Rendering
- [ ] Render LED bar segments (10 × RGBW pixels)
- [ ] Render moving head base + head with pan/tilt
- [ ] Render sunstrip segments
- [ ] Render wash light
- [ ] Apply DMX color values to fixtures

### Phase 5: Beam Visualization
- [ ] Implement volumetric beam rendering (cone geometry)
- [ ] Add ray-traced beam effect (additive blending)
- [ ] Moving head beam follows pan/tilt
- [ ] Beam color from DMX RGB values
- [ ] Beam intensity from dimmer channel
- [ ] Beam projection on floor

### Phase 6: UI Polish
- [ ] Connect/Disconnect button
- [ ] Connection status indicator (green/red)
- [ ] Resizable window handling
- [ ] Smooth camera controls
- [ ] Performance optimization

### Phase 7: Testing & Integration
- [ ] Test with QLC+ ArtNet output
- [ ] Test with Show Creator config
- [ ] Verify fixture channel accuracy
- [ ] Performance testing (target: 60 FPS)

---

## File Structure

```
light-show-visualizer/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── config/
│   └── conf_test.yaml      # Stage configuration
├── fixtures/               # QLC+ fixture definitions (.qxf)
│   ├── varytec-hero-spot-60.qxf
│   ├── varghele-led-bar.qxf
│   └── ...
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── yaml_parser.py      # YAML config loader
│   │   └── qxf_parser.py       # QLC+ fixture file parser
│   ├── artnet/
│   │   ├── __init__.py
│   │   ├── listener.py         # ArtNet UDP receiver
│   │   └── protocol.py         # ArtNet packet parsing
│   ├── dmx/
│   │   ├── __init__.py
│   │   ├── processor.py        # DMX to fixture mapping
│   │   └── universe.py         # Universe management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── fixture.py          # Fixture base class
│   │   ├── led_bar.py          # LED bar fixture
│   │   ├── moving_head.py      # Moving head fixture
│   │   ├── sunstrip.py         # Sunstrip fixture
│   │   └── wash.py             # Wash fixture
│   ├── renderer/
│   │   ├── __init__.py
│   │   ├── engine.py           # Main OpenGL renderer
│   │   ├── camera.py           # Orbiting camera
│   │   ├── stage.py            # Stage floor/grid
│   │   ├── beams.py            # Volumetric beam rendering
│   │   └── shaders/
│   │       ├── beam.vert       # Beam vertex shader
│   │       ├── beam.frag       # Beam fragment shader
│   │       └── ...
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py      # PyQt main window
│       └── widgets.py          # Custom UI widgets
└── tests/
    ├── test_artnet.py
    ├── test_qxf_parser.py
    └── ...
```

---

## Claude Sonnet Implementation Prompts

Use these prompts sequentially with Claude Sonnet to implement each phase.

---

### Prompt 1: Project Setup and Configuration Parsing

```
I'm building a Python desktop application for visualizing DMX light shows in real-time.

**Project Context:**
- This visualizer receives ArtNet DMX data and renders 3D beam visualizations
- It reads stage configuration from YAML files
- It parses QLC+ fixture definition files (.qxf XML format) for channel mappings

**Task:** Set up the project foundation with these components:

1. Create `requirements.txt` with these dependencies:
   - PyQt6 (UI framework)
   - ModernGL (OpenGL rendering)
   - PyGLM (OpenGL mathematics)
   - PyYAML (config parsing)
   - numpy (numerical operations)

2. Create the YAML config parser (`src/config/yaml_parser.py`):
   - Load fixture positions, types, DMX addresses, universes
   - Load stage dimensions (width, depth, height)
   - Load fixture groups
   - Return structured data models

3. Create the QLC+ fixture parser (`src/config/qxf_parser.py`):
   - Parse .qxf XML files to extract:
     - Channel definitions (name, type: Pan/Tilt/Dimmer/Red/Green/Blue/etc.)
     - Available modes and their channel layouts
     - Physical properties (beam angle, pan/tilt ranges)
   - Map channel numbers to channel functions for a given mode

4. Create data models (`src/models/`):
   - `Fixture` base class with position, rotation, DMX address, universe
   - `FixtureCapabilities` class with channel mappings from .qxf
   - `Stage` class with dimensions

Here's my current YAML config structure:
[Include contents of conf_test.yaml]

The QLC+ .qxf files follow this structure:
- XML with <FixtureDefinition> root
- <Channel Name="X"> elements with <Group> child indicating type
- <Mode Name="X"> elements listing channel order

Please implement these components with proper error handling and type hints.
```

---

### Prompt 2: ArtNet Receiver Implementation

```
I'm continuing development of my DMX light show visualizer. I now need to implement the ArtNet receiver.

**Context:**
- The visualizer needs to receive live DMX data via ArtNet protocol
- ArtNet uses UDP port 6454
- I need to support Universe 0 and Universe 1
- Data comes from QLC+ or other ArtNet sources on 127.0.0.1

**Task:** Implement the ArtNet listener with these components:

1. Create `src/artnet/protocol.py`:
   - Define ArtNet packet structures (focus on Art-DMX / OpOutput packets)
   - Art-DMX packet format:
     - Bytes 0-7: Art-Net header ("Art-Net\0")
     - Bytes 8-9: OpCode (0x5000 for OpDmx, little-endian)
     - Byte 10-11: Protocol version
     - Byte 12: Sequence
     - Byte 13: Physical
     - Byte 14-15: Universe (little-endian, 15-bit)
     - Byte 16-17: Length (big-endian)
     - Bytes 18+: DMX data (512 bytes max)
   - Function to parse raw UDP data into structured packet

2. Create `src/artnet/listener.py`:
   - UDP socket listener on port 6454
   - Non-blocking/async operation (use threading or asyncio)
   - Filter packets by universe (0 and 1)
   - Callback mechanism to notify when DMX data updates
   - Connection status tracking (connected if receiving packets)
   - Graceful start/stop

3. Create `src/dmx/universe.py`:
   - Store 512 channels per universe
   - Thread-safe access to channel values
   - Method to get channel value by address

4. Create `src/dmx/processor.py`:
   - Map DMX values to fixture properties using channel definitions
   - Extract pan, tilt, dimmer, RGB values based on fixture mode
   - Normalize values (0-255 to 0.0-1.0 for colors, degrees for pan/tilt)

The listener should be efficient and handle high-frequency updates (44Hz typical for DMX).

Please implement with proper threading, error handling, and type hints.
```

---

### Prompt 3: 3D Rendering Foundation

```
I'm continuing my DMX light show visualizer. I now need the 3D rendering foundation.

**Context:**
- Using PyQt6 for the window and ModernGL for OpenGL rendering
- Need an orbiting camera controlled by mouse drag
- Stage floor with grid lines matching stage dimensions
- Dark background
- Must integrate with PyQt6 event loop

**Task:** Implement the 3D rendering foundation:

1. Create `src/renderer/camera.py`:
   - Orbiting camera around stage center
   - Mouse drag to rotate (left button: orbit, right button: pan)
   - Scroll wheel to zoom
   - Smooth movement
   - Return view and projection matrices

2. Create `src/renderer/stage.py`:
   - Render a floor plane matching stage dimensions
   - Grid lines every 1 meter (or 0.5m for detail)
   - Floor color: dark gray (#1a1a1a)
   - Grid lines: lighter gray (#333333)
   - Generate vertex buffer with grid geometry

3. Create `src/renderer/engine.py`:
   - ModernGL context setup
   - Main render loop
   - Clear to dark background (#0a0a0a)
   - Render stage floor
   - Handle window resize (update viewport/projection)
   - Return FPS counter value

4. Create `src/ui/main_window.py`:
   - PyQt6 QMainWindow with QOpenGLWidget
   - Integrate ModernGL renderer
   - Toolbar with:
     - Connect/Disconnect button
     - Connection status indicator (colored dot or icon)
   - Status bar with FPS counter
   - Resizable window (minimum 800x600)
   - Mouse event forwarding to camera

5. Create `main.py`:
   - Application entry point
   - Initialize Qt application
   - Load configuration
   - Start ArtNet listener
   - Show main window
   - Clean shutdown

Stage dimensions from config: width=10m, depth=6m
Camera should start at a 45-degree angle looking at stage center.

Please implement with proper OpenGL practices (VAOs, VBOs, shaders).
```

---

### Prompt 4: Fixture Rendering

```
I'm continuing my DMX light show visualizer. I now need to render the fixtures.

**Context:**
- Fixtures are positioned in 3D space (x, y, z from config)
- Each fixture type needs a distinct visual representation
- Fixtures receive DMX values that control their appearance
- Using ModernGL for rendering

**Fixture Types to Render:**

1. **LED Bar** (10 segments, 40 channels = 10 × RGBW):
   - Render as a horizontal bar with 10 distinct segments
   - Each segment is a small cube or rectangle
   - Each segment lit with its RGBW color
   - Bar dimensions: ~1m wide, 0.1m tall, 0.1m deep

2. **Moving Head** (14 channels):
   - Render base (stationary cylinder/box)
   - Render head (rotatable box/cylinder)
   - Head rotates based on pan (Y-axis) and tilt (X-axis)
   - Show beam origin point on head
   - Dimensions: base ~0.3m, head ~0.2m

3. **Sunstrip** (10 channels, blinder-style):
   - Render as a strip with 5 lamp segments
   - Each segment glows based on intensity
   - Warm white color (tungsten)
   - Dimensions: ~1m wide

4. **Wash** (6 channels, RGB):
   - Render as a box/par-can shape
   - Front face shows current RGB color
   - Dimensions: ~0.4m cube

**Task:** Implement fixture rendering:

1. Update `src/models/fixture.py`:
   - Add methods to get current color, intensity, pan, tilt from DMX
   - Use channel mappings from QXF parser

2. Create fixture-specific model classes with render methods:
   - `src/models/led_bar.py`
   - `src/models/moving_head.py`
   - `src/models/sunstrip.py`
   - `src/models/wash.py`

3. Update `src/renderer/engine.py`:
   - Load fixture positions from config
   - Create fixture renderers for each fixture
   - Render all fixtures each frame
   - Update fixture colors/positions from DMX processor

4. Create shaders for fixtures:
   - Basic lit shader with emissive color support
   - Fixtures should "glow" based on their intensity

Use instanced rendering where appropriate for performance.
```

---

### Prompt 5: Volumetric Beam Rendering

```
I'm continuing my DMX light show visualizer. I now need ray-traced volumetric beam rendering.

**Context:**
- Moving heads and other fixtures project visible light beams
- Beams should look volumetric (like light through haze)
- Beam color comes from fixture's RGB DMX values
- Beam intensity from dimmer channel
- Moving head beams follow pan/tilt
- Beams should project onto the floor

**Task:** Implement volumetric beam rendering:

1. Create `src/renderer/beams.py`:
   - Beam geometry: cone from fixture to floor (or max distance)
   - Beam angle from fixture definition (typically 15-30 degrees for spots)
   - Volumetric effect using additive blending
   - Multiple passes or raymarching in fragment shader

2. Create beam shaders (`src/renderer/shaders/`):
   - `beam.vert`: Transform cone geometry, pass world position
   - `beam.frag`: Volumetric light effect
     - Soft edges (fade at cone boundary)
     - Falloff with distance from source
     - Additive blending for overlapping beams
     - Atmospheric scattering approximation

3. Beam rendering approach (choose one):

   **Option A: Cone mesh with raymarching**
   - Render cone as mesh
   - Fragment shader raymarches through cone volume
   - Accumulate density based on distance from cone axis

   **Option B: Billboard slices**
   - Render multiple transparent circular billboards
   - Stack along beam direction
   - Each slice slightly smaller (cone shape)
   - Additive blend all slices

4. Update `src/renderer/engine.py`:
   - Render beams after fixtures (for proper blending)
   - Enable additive blending for beam pass
   - Disable depth writing for beams
   - Calculate beam direction from pan/tilt for moving heads

5. Floor projection:
   - When beam hits floor, render a circular spotlight effect
   - Color and size based on beam properties
   - Soft edges on the projection

**Performance target:** 60 FPS with 4 moving head beams active.

Please implement with proper OpenGL blending and efficient shaders.
```

---

### Prompt 6: UI Polish and Integration

```
I'm finishing my DMX light show visualizer. I need to polish the UI and ensure everything integrates properly.

**Current State:**
- 3D rendering with fixtures and beams works
- ArtNet receiver works
- Config parsing works

**Task:** Polish and integrate:

1. Update `src/ui/main_window.py`:
   - **Connect/Disconnect button:**
     - Toggle ArtNet listener on/off
     - Button text changes: "Connect" / "Disconnect"
   - **Connection status indicator:**
     - Green dot/icon when receiving ArtNet packets
     - Red dot/icon when disconnected or no data
     - Yellow when connected but no recent packets (timeout 2s)
   - **FPS counter in status bar:**
     - Update every 500ms
     - Format: "FPS: 60"
   - **Universe indicator:**
     - Show which universes have active data
     - "U0: ● U1: ○" style

2. Camera improvements (`src/renderer/camera.py`):
   - Smooth interpolation for rotation (lerp)
   - Limit vertical rotation (don't flip upside down)
   - Reset view button/shortcut (Home key)
   - Sensible zoom limits

3. Window handling:
   - Remember window size/position (QSettings)
   - Proper handling of minimize/maximize
   - Graceful handling of OpenGL context loss

4. Error handling:
   - Show message if config file not found
   - Show message if fixture .qxf file not found
   - Handle ArtNet socket binding errors (port in use)
   - Log errors to console/file

5. Performance:
   - Only re-render when DMX values change or camera moves
   - Limit update rate to 60 FPS
   - Profile and optimize any bottlenecks

6. Command-line arguments:
   - `--config PATH` to specify config file
   - `--fixtures PATH` to specify fixtures directory
   - `--universe X` to filter specific universe

Please implement these final polish items.
```

---

## Quick Start (After Implementation)

```bash
# Clone and setup
git clone <repository>
cd light-show-visualizer
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Copy QLC+ fixture files
cp /path/to/qlcplus/fixtures/*.qxf fixtures/

# Run visualizer
python main.py --config config/conf_test.yaml

# In QLC+: Enable ArtNet output to 127.0.0.1
```

---

## Future Enhancements

- [ ] TCP socket for real-time config updates from Show Creator
- [ ] Support for more universes (configurable)
- [ ] Fixture library browser
- [ ] Record/playback for debugging
- [ ] sACN protocol support
- [ ] Fog/haze density control
- [ ] Multiple camera presets
- [ ] Gobo projection for moving heads

---

## License

[Your license here]

---

## Contributing

[Contribution guidelines]
