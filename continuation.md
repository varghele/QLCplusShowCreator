# Continuation Context for Next Claude Code Session

**Date:** 2026-03-31
**Branch:** v0.9.5
**Last Session:** Implemented Phase 16 (Rudiments) and Phase 24 (Auto-Show Generation)

---

## What Was Built This Session

### 1. Effect Extraction Refactor (Prerequisite)
All effect computation logic was extracted from `utils/artnet/dmx_manager.py` (~2045 lines) into a standalone `effects/` module:

- `effects/types.py` — `DimmerContext`, `DimmerResult`, `MovementContext`, `MovementResult` dataclasses
- `effects/timing.py` — `parse_speed()`, `get_bpm()` helpers
- `effects/dimmer_effects.py` — 15 pure dimmer effect functions + `DIMMER_REGISTRY` dict
- `effects/movement_effects.py` — 11 pure movement shape functions + `MOVEMENT_REGISTRY` dict
- `effects/__init__.py` — public API

`dmx_manager.py` now uses registry-based dispatch (~860 lines) instead of 1200-line if/elif chains.

### 2. Effect Rename to Rudiment Vocabulary
All effect_type strings across the entire codebase were renamed to match the theory's rudiment naming:

| Old Name | New Name | Notes |
|---|---|---|
| hit | stroke | |
| pulse (old, 70% floor) | throb | |
| ping_pong_smooth | ping_pong | |
| snake + zigzag | chase | Merged, `chase_scope` param: "fixture" or "global" |
| wave_travel | wave | |
| waterfall_down + waterfall_up | waterfall | Merged, `direction` param: "down" or "up" |
| fill_unfill | fill | |
| random_strobe | random_stroke | |
| twinkle | sparkle | |
| breathing_sync + pulse_staggered | pulse | Merged, `phase_offset_per_fixture` param |
| heartbeat_pulse | heartbeat | |
| *(new)* | fade | direction="in" or "out" |
| *(new)* | cascade | build_fraction param |

Updated in: effects module, dmx_manager, XML export (unified_sequence.py, shows_to_xml.py, preset_scenes_to_xml.py), dimmer_block_dialog, movement_block_dialog, tests, 6 YAML configs (~3300 replacements), riff JSON files.

### 3. Phase 16: Rudiment System
- `rudiments/rudiment.py` — `Rudiment`, `FluxEnvelope`, `RudimentParameter` dataclasses, enums (`RudimentType`, `EnvelopeCategory`, `CycleMode`)
- `rudiments/registry.py` — 15 intensity + 11 movement rudiments with flux envelopes and parameter definitions
- `rudiments/block_converter.py` — `rudiment_to_dimmer_block()`, `rudiment_to_movement_block()`
- `rudiments/__init__.py`

### 4. Phase 24: Automatic Show Generation
- `audio/spectral_analysis.py` — Extracts spectral flux, transient sharpness, spectral richness, vocal presence, spectral centroid per section using librosa
- `autogen/color_generator.py` — Song-level palette system (max 3 colors + white), 10 preset palettes, section color assignment
- `autogen/matcher.py` — Three-dimensional rudiment matching (envelope similarity, repetition rate, flux level), iterative per-group selection with diversity penalties and complement bonuses (max 10 rounds, stops when stable)
- `autogen/spatial.py` — Fixture group zone classification (front/mid/back/overhead), tiered activation based on relative energy, vocal rules, gobo/prism activation, auto-spot creation for plane targeting
- `autogen/generator.py` — Main orchestrator implementing full algorithm: audio analysis → color palette → per-group rudiment selection → movement strategy → phrase structure → block generation
- `gui/dialogs/autogen_dialog.py` — Config dialog with key signature, color scheme (presets + custom), phrase structure, matching weights, effect thresholds
- Shows tab — Purple "Auto-Generate" button, background thread generation, replace/append UI

### 5. DimmerBlock Model Extensions
Added to `config/models.py` `DimmerBlock`:
- `direction: str = "down"` — for waterfall and fade
- `chase_scope: str = "fixture"` — for chase effect
- `phase_offset_per_fixture: bool = False` — for pulse effect
- `build_fraction: float = 0.7` — for cascade effect

Serialization: non-default values only, backward compatible loading.

### 6. Dimmer Dialog UI Extensions
`timeline_ui/dimmer_block_dialog.py` — Added rudiment-specific controls that show/hide based on selected effect type:
- Direction combo (waterfall: down/up, fade: in/out)
- Chase scope combo (fixture/global)
- Phase offset checkbox (pulse)
- Build fraction spinner (cascade)

---

## Current State of Auto-Generation

### What Works:
- Full pipeline: audio → analysis → palette → rudiment matching → block generation → timeline
- Per-group rudiment diversity (iterative selection with complement bonuses)
- Tiered group activation (quiet sections = fewer groups active)
- Movement shape variety (4 energy-based pools, section rotation)
- Plane-style sweep targeting (center spot + amplitude)
- Song-level color coherence (max 3 colors + white, preset palettes)
- BPM + energy speed matching (per-group variation)
- Phrase structure from song structure (respects time signature, bar count)
- Special effects (gobo/prism) for capable fixtures at richness thresholds

### Known Limitations / Future Work:
- **Investigation system needed** — Algorithm is a black box, need decision logging (see `v1_theory_and_implementation_plan/autofuture.md`)
- **Color transitions** — No crossfade between sections, just hard cuts
- **Transition rudiments** — No special handling for section boundaries (e.g., build into chorus)
- **Live mode** — Not implemented (prepared mode only)
- **Genre presets** — No pre-tuned parameter sets for different music genres
- **XML export** for new effects — `unified_sequence.py` needs step generation logic for: chase, wave, stroke, fill, pulse, fade, cascade, heartbeat, throb (currently only the old effect names have QLC+ export)
- **Movement amplitude to pan/tilt mapping** — The amplitude value (0-80) maps to DMX pan/tilt amplitude but the relationship between amplitude degrees and stage sweep width depends on fixture mounting distance

---

## Test Status
- **429 unit tests passing** (1 pre-existing failure: `imageio_ffmpeg` not installed)
- Key test files:
  - `tests/unit/test_effects.py` — 42 tests for all dimmer + movement effects
  - `tests/unit/test_spectral_analysis.py` — 9 tests for audio analysis
  - `tests/unit/test_dmx_manager.py` — 17 tests for DMX manager

---

## File Map (New/Modified Files)

### New Files Created:
```
effects/
├── __init__.py
├── types.py
├── timing.py
├── dimmer_effects.py
└── movement_effects.py

rudiments/
├── __init__.py
├── rudiment.py
├── registry.py
└── block_converter.py

autogen/
├── __init__.py
├── generator.py
├── matcher.py
├── spatial.py
└── color_generator.py

audio/spectral_analysis.py
gui/dialogs/autogen_dialog.py
tests/unit/test_effects.py
tests/unit/test_spectral_analysis.py
v1_theory_and_implementation_plan/autofuture.md
```

### Key Modified Files:
```
utils/artnet/dmx_manager.py          — Refactored to use effect registries
config/models.py                      — DimmerBlock extended with new fields
timeline_ui/dimmer_block_dialog.py    — Added rudiment-specific controls
timeline_ui/movement_block_dialog.py  — Added linear_sweep, fan to combo
gui/tabs/shows_tab.py                 — Added Auto-Generate button + handler
utils/to_xml/unified_sequence.py      — Effect names renamed
utils/to_xml/shows_to_xml.py          — Effect names renamed
utils/to_xml/preset_scenes_to_xml.py  — Display names renamed
tests/unit/test_compact_serializer.py — Updated test data
```

### Config Files Updated (effect name rename):
```
conf_new_test.yaml, conf_v2.yaml, conf_v4.yaml,
conf_SBD_WASHONLY.yaml, conf_backup_outro.yaml, conf_backup_outro_v2.yaml
riffs/builds/pulse_build_4bar.json, riffs/loops/pulse_4bar.json, riffs/loops/twinkle_4bar.json
```

---

## Architecture Overview

```
User clicks "Auto-Generate" in Shows Tab
  → AutogenDialog (configure: key, palette, phrase, matching, thresholds)
  → AutogenWorker (QThread)
    → analyze_song()              [audio/spectral_analysis.py]
       Returns: SectionAnalysis per part (flux, transients, richness, vocal, centroid)
    → generate_palette_from_audio() OR preset   [autogen/color_generator.py]
       Returns: SongPalette (1-3 colors + white)
    → assign_section_colors()     [autogen/color_generator.py]
       Returns: per-section color assignments from song palette
    → For each section:
       → compute_richness_weights() [autogen/spatial.py]
          Returns: per-group activation weights (0.0 = inactive)
       → select_rudiments_per_group() [autogen/matcher.py]
          Iterative: scores → diversity adjustments → until stable (max 10 rounds)
          Returns: {group: (groove_rudiment, fill_rudiment)}
       → _select_movement_strategy() [autogen/generator.py]
          Energy-based shape pool + section rotation + plane targeting
          Returns: MovementStrategy(shape, target_spot, amplitude)
       → For each active group:
          → _generate_section_blocks() → _add_light_block()
             Creates LightBlock with DimmerBlock + ColourBlock + MovementBlock + SpecialBlock
  → Lanes added to timeline
```

---

## Memory Files
The `.claude/projects/.../memory/` directory has these entries:
- `user_profile.md` — User role and context
- `project_roadmap.md` — Release plans
- `feedback_local_pipeline.md` — Prefers local build scripts
- `project_rudiment_system.md` — Phase 16 implementation status (created this session)
