# QLC+ Show Creator - Claude Re-instruction Prompts

**Last Updated:** December 2024

This file contains copy-paste prompts for different development scenarios. Use these to quickly bring Claude up to speed on specific tasks.

---

## Quick Start Prompt

> Copy this for any new session:

```
I'm working on QLC+ Show Creator, a PyQt6 app for creating light shows.
The project includes a 3D Visualizer that receives data via TCP + ArtNet.

Please read these files to understand the project:
- .claude/OVERVIEW.md - Project context and architecture
- .claude/PHASE_PLAN.md - Development roadmap

Branch: ui_improvements_plus_qlc_workspacer
```

---

## Show Creator Prompts

### Bug Fixing - Universe Configuration

```
I'm working on QLC+ Show Creator and need to fix bugs in the universe configuration.

Context:
- The app uses PyQt6 with a tab-based GUI
- Universe configuration is in `gui/tabs/configuration_tab.py`
- Data models are in `config/models.py` (see Universe class)
- Universe types: E1.31, ArtNet, DMX USB

Please:
1. Read .claude/OVERVIEW.md for project context
2. Read gui/tabs/configuration_tab.py
3. Read the Universe class in config/models.py
4. Help me investigate and fix the issues

Known issues: [describe specific bugs here]
```

### Bug Fixing - Effects/Sublanes

```
I'm working on QLC+ Show Creator and need to fix bugs in the effects/sublane system.

Context:
- Effects use a sublane architecture (Dimmer, Colour, Movement, Special)
- Main widget: timeline_ui/light_block_widget.py (65KB, complex)
- Data models: config/models.py (see LightBlock, *Block classes)
- Edit dialogs: timeline_ui/*_block_dialog.py

Please:
1. Read .claude/OVERVIEW.md for project context
2. Read the relevant files based on the issue
3. Help me debug and fix

Issue: [describe specific bug here]
```

### QLC+ Export Issues

```
I'm working on QLC+ Show Creator and need to fix issues with QLC+ export.

Context:
- Export logic is in utils/to_xml/shows_to_xml.py
- Generates QLC+ workspace XML files (.qxw)
- Must produce valid XML that QLC+ can open without crashing

Please:
1. Read .claude/OVERVIEW.md for project context
2. Read utils/to_xml/shows_to_xml.py
3. Help me fix the export issue

Issue: [describe specific export problem]
```

### New Feature - Show Structure Editor

```
I'm working on QLC+ Show Creator and want to implement in-app show structure creation.

Current state:
- Show structures are loaded from CSV files (shows/*.csv)
- CSV format: columns for part name, start time, duration, etc.
- Users must manually create these CSV files

Goal:
- Add UI to create show structures directly in the app
- Should integrate with the existing timeline
- Keep CSV import as an option

Please:
1. Read .claude/OVERVIEW.md and .claude/PHASE_PLAN.md
2. Read timeline/song_structure.py
3. Look at existing CSV files in shows/ directory
4. Help me design and implement this feature
```

### New Feature - Riffs System

```
I'm working on QLC+ Show Creator and want to implement a "Riffs" system.

Concept:
- A "Riff" is a predefined sequence of light effects
- Should be reusable across shows
- Can be applied quickly to timeline

Current effect system:
- Uses sublane blocks (Dimmer, Colour, Movement, Special)
- Multiple blocks per sublane in a LightBlock envelope
- See config/models.py for data structures

Please:
1. Read .claude/OVERVIEW.md and .claude/PHASE_PLAN.md
2. Read config/models.py (LightBlock and related classes)
3. Help me design the Riff data model and UI
```

### New Feature - ArtNet Output (Show Creator)

```
I'm working on QLC+ Show Creator and want to add real-time ArtNet DMX output.

Goal:
- Send DMX via ArtNet during playback
- Enable preview in the Visualizer without QLC+
- Also allow QLC+ to receive the same ArtNet data

Current state:
- Timeline playback exists (timeline/playback_engine.py)
- Universe configuration stores ArtNet settings
- Visualizer will listen on UDP 6454

Please:
1. Read .claude/OVERVIEW.md
2. Read timeline/playback_engine.py
3. Read config/models.py (Universe class)
4. Create utils/artnet/sender.py with ArtNet packet generation
5. Rate limit to 44Hz max to avoid overloading receivers

ArtNet OpDmx packet format:
- Bytes 0-7: "Art-Net\0"
- Bytes 8-9: OpCode 0x5000 (little-endian)
- Byte 10-11: Protocol version (0x000e)
- Byte 12: Sequence (0-255)
- Byte 13: Physical port (0)
- Byte 14-15: Universe (little-endian, 15-bit)
- Byte 16-17: Length (big-endian, max 512)
- Bytes 18+: DMX data
```

### New Feature - TCP Server (Show Creator)

```
I'm working on QLC+ Show Creator and want to add TCP server for the Visualizer.

Goal:
- Show Creator acts as TCP server on port 7654
- Sends stage layout and fixture info to Visualizer
- Updates Visualizer when configuration changes
- Visualizer is in visualizer/ folder (same repo)

Data to send (JSON format):
- Stage: { width, depth, height }
- Fixtures: [{ name, type, x, y, z, rotation, universe, address, mode, ... }]
- Groups: [{ name, color, fixture_names }]

Protocol:
- Message format: 4-byte length prefix + JSON payload
- Message types: STAGE_UPDATE, FIXTURES_UPDATE, GROUPS_UPDATE, FULL_SYNC

Please:
1. Read .claude/OVERVIEW.md
2. Read config/models.py (Configuration, Fixture, Stage data)
3. Create utils/tcp/server.py
4. Create utils/tcp/protocol.py with message definitions
5. Add connection status indicator to MainWindow
```

---

## Visualizer Prompts

### Visualizer - Project Setup

```
I'm setting up the Visualizer component for QLC+ Show Creator.

Context:
- Visualizer goes in visualizer/ folder at repo root
- Reuses shared modules: config/models.py, utils/fixture_utils.py
- Uses PyQt6 for UI, ModernGL for 3D rendering
- Receives config via TCP from Show Creator
- Receives DMX via ArtNet from Show Creator or QLC+

Please:
1. Read .claude/OVERVIEW.md and .claude/PHASE_PLAN.md (Visualizer Phases)
2. Create the basic project structure:
   - visualizer/main.py (entry point)
   - visualizer/__init__.py
   - Basic PyQt6 window
3. Add imports from shared modules
4. Test that shared imports work correctly
```

### Visualizer - TCP Client

```
I'm implementing the TCP client for the Visualizer to receive config from Show Creator.

Context:
- Show Creator runs TCP server on port 7654
- Messages: 4-byte length prefix + JSON payload
- Message types: STAGE_UPDATE, FIXTURES_UPDATE, GROUPS_UPDATE, FULL_SYNC
- Visualizer should store received config for rendering

Please:
1. Read .claude/OVERVIEW.md (Communication Architecture section)
2. Create visualizer/tcp/client.py with:
   - Async TCP client (QTcpSocket or asyncio)
   - Message parsing
   - Store config in local data structures
   - Connection status callbacks
3. Create visualizer/tcp/protocol.py with message definitions
4. Handle reconnection on disconnect
```

### Visualizer - ArtNet Receiver

```
I'm implementing the ArtNet receiver for the Visualizer to receive live DMX.

Context:
- ArtNet on UDP port 6454
- Can receive from Show Creator or QLC+
- Need to support Universe 0 and 1 (configurable)
- Must be thread-safe (rendering on main thread, ArtNet on separate thread)

Please:
1. Read .claude/OVERVIEW.md
2. Create visualizer/artnet/listener.py with:
   - UDP socket listener on port 6454
   - Parse OpDmx packets (OpCode 0x5000)
   - Thread-safe DMX value storage (512 channels per universe)
   - Connection status detection (receiving/not receiving)
3. Create visualizer/artnet/protocol.py with packet parsing

ArtNet OpDmx packet format:
- Bytes 0-7: "Art-Net\0"
- Bytes 8-9: OpCode 0x5000 (little-endian)
- Byte 14-15: Universe (little-endian)
- Byte 16-17: Length (big-endian)
- Bytes 18+: DMX data
```

### Visualizer - 3D Rendering Foundation

```
I'm implementing the 3D rendering foundation for the Visualizer.

Context:
- Using ModernGL with PyQt6 QOpenGLWidget
- Need orbiting camera, stage floor with grid
- Dark background (#0a0a0a)
- Stage dimensions come from TCP (width, depth, height)

Please:
1. Read .claude/OVERVIEW.md (Visualizer section)
2. Create visualizer/renderer/engine.py with:
   - ModernGL context setup
   - Main render loop
   - FPS counter
   - Window resize handling
3. Create visualizer/renderer/camera.py with:
   - Orbiting camera around stage center
   - Mouse drag to rotate (left button)
   - Scroll to zoom
   - Home key to reset view
4. Create visualizer/renderer/stage.py with:
   - Floor plane matching stage dimensions
   - Grid lines every 1 meter
   - Floor color: dark gray, grid: lighter gray
```

### Visualizer - Fixture Rendering

```
I'm implementing fixture rendering for the Visualizer.

Context:
- Fixtures received via TCP with positions and types
- Channel mappings from utils/fixture_utils.py (shared)
- DMX values from ArtNet listener
- Need to render different fixture types

Fixture types:
- LED Bar: 10 RGBW segments in a row (~1m wide)
- Moving Head: Base + rotating head (pan/tilt from DMX)
- Wash: Box shape with front color glow
- Sunstrip: Strip with warm white segments

Please:
1. Read .claude/OVERVIEW.md
2. Read utils/fixture_utils.py to understand channel mapping
3. Create visualizer/renderer/fixtures.py with:
   - Fixture base class
   - LED Bar renderer
   - Moving Head renderer (with pan/tilt rotation)
   - Wash renderer
   - Sunstrip renderer
4. Apply DMX color/intensity to fixtures
```

### Visualizer - Volumetric Beams

```
I'm implementing volumetric beam rendering for the Visualizer.

Context:
- Beams project from fixtures (especially moving heads)
- Should look volumetric (like light through haze)
- Color from RGB DMX channels
- Intensity from dimmer channel
- Moving head beams follow pan/tilt

Please:
1. Read .claude/OVERVIEW.md (Visualizer section)
2. Create visualizer/renderer/beams.py with:
   - Cone geometry from fixture to floor
   - Beam angle from fixture definition (~15-30 degrees for spots)
3. Create GLSL shaders in visualizer/renderer/shaders/:
   - beam.vert: Transform cone, pass world position
   - beam.frag: Volumetric effect with soft edges and falloff
4. Use additive blending for overlapping beams
5. Disable depth writing for beams
6. Target: 60 FPS with 10+ active beams
```

---

## Architecture Reference Prompts

### Understanding the Tab System

```
I need to understand the GUI tab architecture in QLC+ Show Creator.

Please read:
- gui/gui.py (MainWindow orchestration)
- gui/tabs/base_tab.py (BaseTab class)
- gui/tabs/*.py (all tab implementations)

Explain:
1. How tabs are initialized
2. How cross-tab communication works
3. The lifecycle methods (setup_ui, update_from_config, save_to_config)
```

### Understanding Sublane System

```
I need to understand the sublane effect system in QLC+ Show Creator.

Please read:
- config/models.py (LightBlock, DimmerBlock, ColourBlock, etc.)
- timeline_ui/light_block_widget.py
- utils/sublane_presets.py

Explain:
1. The four sublane types and their purposes
2. How capability detection works
3. How blocks are rendered and interacted with
4. The overlap prevention logic
```

### Understanding QLC+ Export

```
I need to understand how QLC+ export works in this project.

Please read:
- utils/to_xml/shows_to_xml.py
- utils/fixture_utils.py (fixture definition parsing)

Explain:
1. The XML structure generated
2. How sequences are built from sublane blocks
3. Step density and timing calculations
4. Color wheel fallback logic
```

### Understanding Communication Architecture

```
I need to understand how Show Creator and Visualizer communicate.

Please read:
- .claude/OVERVIEW.md (Communication Architecture section)

Explain:
1. What data goes over TCP vs ArtNet
2. The message format for TCP
3. How ArtNet packets are structured
4. When to use Show Creator vs QLC+ as ArtNet source
```

---

## Testing Prompts

### Running Visual Tests (Show Creator)

```
I want to test the sublane UI in QLC+ Show Creator.

Run these commands and report results:
- python tests/visual/test_sublane_blocks.py
- python tests/visual/test_sublane_ui.py
- python tests/visual/test_capability_detection.py

What to check:
- Sublane rendering (different heights per fixture type)
- Block creation via drag
- Overlap prevention (should show RED preview)
- Selection and resize handles
```

### Testing Export

```
I want to test QLC+ export in QLC+ Show Creator.

Steps:
1. Load a test configuration
2. Create some effects on the timeline
3. Export to workspace (.qxw)
4. Open in QLC+ and verify:
   - No crashes
   - Sequences contain expected steps
   - Fixture channels are correct
```

### Testing TCP Communication

```
I want to test the TCP communication between Show Creator and Visualizer.

Steps:
1. Start Show Creator (runs TCP server)
2. Start Visualizer (connects as TCP client)
3. In Show Creator:
   - Add fixtures and verify they appear in Visualizer
   - Move fixtures on stage and verify position updates
   - Change groups and verify color updates
4. Test reconnection:
   - Stop Visualizer, restart, verify reconnects
   - Stop Show Creator, restart, verify Visualizer reconnects
```

### Testing ArtNet Communication

```
I want to test ArtNet DMX communication.

Steps:
1. Start Visualizer (listens on UDP 6454)
2. Option A - Test with Show Creator:
   - Play a show with effects
   - Verify fixtures in Visualizer respond to DMX
3. Option B - Test with QLC+:
   - Configure QLC+ to output ArtNet to 127.0.0.1
   - Control fixtures in QLC+
   - Verify Visualizer shows the same state
```

---

## Code Review Prompts

### Review Changes

```
Please review the changes I made to [file/feature].

Check for:
- Logic errors
- Edge cases
- Performance issues
- Code style consistency
- Missing error handling
```

### Suggest Improvements

```
I've implemented [feature]. Please review and suggest improvements.

Focus on:
- Architecture/design
- Code organization
- Potential bugs
- Missing functionality
- User experience
```

---

## Tips for Claude

### General
1. **Start with OVERVIEW.md** - Always read this first for context
2. **Check PHASE_PLAN.md** - Understand what's done vs planned
3. **models.py is key** - Most data flows through these classes

### Show Creator
4. **light_block_widget.py is complex** - Take time to understand it
5. **shows_to_xml.py is critical** - Export issues often live here
6. **Test visually** - Use the test scripts to verify UI changes

### Visualizer
7. **Reuse shared modules** - Don't duplicate fixture parsing
8. **TCP first, then rendering** - Get communication working before 3D
9. **Thread safety** - ArtNet runs on separate thread from rendering
10. **ModernGL examples** - Check ModernGL docs for OpenGL patterns
