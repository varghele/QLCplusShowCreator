# QLC+ Show Creator - Claude Re-instruction Prompts

**Last Updated:** December 2024

This file contains copy-paste prompts for different development scenarios. Use these to quickly bring Claude up to speed on specific tasks.

---

## Quick Start Prompt

> Copy this for any new session:

```
I'm working on QLC+ Show Creator, a PyQt6 app for creating light shows.

Please read these files to understand the project:
- .claude/OVERVIEW.md - Project context and architecture
- .claude/PHASE_PLAN.md - Development roadmap

Branch: refactorplustimeline
```

---

## Task-Specific Prompts

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

### New Feature - ArtNet Output

```
I'm working on QLC+ Show Creator and want to add real-time ArtNet DMX output.

Goal:
- Send DMX via ArtNet during playback (for preview/testing)
- Don't need to replace QLC+ for live shows, just for previewing

Current state:
- Timeline playback exists (timeline/playback_engine.py)
- Universe configuration stores ArtNet settings

Please:
1. Read .claude/OVERVIEW.md
2. Read timeline/playback_engine.py
3. Read config/models.py (Universe class)
4. Help me implement ArtNet packet sending
```

### New Feature - TCP Visualizer Connection

```
I'm working on QLC+ Show Creator and want to add TCP support for an external visualizer.

Goal:
- Show Creator acts as TCP server
- Sends stage layout and fixture info to visualizer
- Visualizer is a separate application (different repo)

Data to send:
- Stage dimensions
- Fixture positions and types
- Current DMX values during playback

Please:
1. Read .claude/OVERVIEW.md
2. Read config/models.py (Configuration, Fixture, Stage data)
3. Help me design the TCP protocol and server implementation
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

---

## Testing Prompts

### Running Visual Tests

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

1. **Start with OVERVIEW.md** - Always read this first for context
2. **Check PHASE_PLAN.md** - Understand what's done vs planned
3. **models.py is key** - Most data flows through these classes
4. **light_block_widget.py is complex** - Take time to understand it
5. **shows_to_xml.py is critical** - Export issues often live here
6. **Test visually** - Use the test scripts to verify UI changes
