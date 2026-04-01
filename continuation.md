# Continuation Context for Next Claude Code Session

**Date:** 2026-04-01
**Branch:** v1.0
**Last Session:** Improved auto-generation with activation roles + Generation Inspector dashboard

---

## What Was Built This Session

### 1. Group Activation Roles (autogen/spatial.py, autogen/generator.py)

Instead of binary active/inactive per section, fixture groups now get **roles** that determine which parts of the phrase structure they play:

- **FULL** — plays both groove and fill blocks
- **GROOVE_ONLY** — plays only groove portions
- **FILL_ONLY** — plays only fill portions (punches in for dramatic fills, silent during grooves)

**Key design decision:** Roles are derived from the **groove rudiment's envelope category**, not from fixture type. A group assigned a SPIKE or STOCHASTIC groove rudiment gets FILL_ONLY at low/medium energy. A group with a FLAT/ROLLING/OSCILLATING groove gets FULL or GROOVE_ONLY. This means the same MH group can be FULL in one section and FILL_ONLY in another, depending on what the matcher assigned.

- `ActivationRole` enum and `assign_group_roles()` in `autogen/spatial.py`
- `compute_richness_weights()` reverted to return plain `Dict[str, float]` (weights only, no roles)
- `_generate_section_blocks()` in `generator.py` respects roles via `emit_groove`/`emit_fill` flags
- Fill-only groups get 1.3x intensity boost and 1.2x movement amplitude boost

### 2. Generation Inspector Dashboard (gui/dialogs/generation_inspector.py)

Live visualization window that shows all auto-generation decisions during playback. Toggled via blue "Inspector" button in Shows tab toolbar.

**Architecture:**
- `autogen/report.py` — `GenerationReport`, `SectionReport`, `GroupSectionReport`, `MatchScoreEntry` dataclasses that capture every decision during generation
- `autogen/generator.py` — `generate_show()` now returns `Tuple[List[LightLane], GenerationReport]`
- `gui/dialogs/autogen_dialog.py` — `AutogenWorker.finished` signal emits `(lanes, report)`
- `gui/tabs/shows_tab.py` — Stores report, Inspector toggle button, feeds playhead position to inspector at ~30Hz

**Inspector panels (5 QPainter-based widgets):**
1. `AudioFeaturesWidget` — 5 polyline plots (flux, transient, richness, vocal, centroid) with section backgrounds, energy fill, and red playhead cursor
2. `GroupActivationWidget` — Groups × sections heatmap colored by role (green=full, blue=groove, orange=fill). Click to select group.
3. `RudimentScoresWidget` — Top 5 match candidates with stacked sub-score bars (envelope similarity, flux fit, repetition rate, coherence)
4. `ColorPaletteWidget` — HSL color wheel with song palette dots and current section highlights
5. Section Info — HTML text panel with all decisions for the current section

**Update mechanism:** Cursor updates at ~30Hz (cheap), full panel redraws only on section change.

### 3. Frame-Level Audio Features (audio/spectral_analysis.py)

Added continuous frame-level feature computation for the inspector plots:

- `FrameFeatures` dataclass — all 5 features (flux, transient, richness, vocal, centroid) at frame resolution
- `compute_frame_features()` — computes from librosa at ~43fps, lightly smoothed (5-frame window), downsampled to ~800 points
- **Normalization fix:** smooth first, then normalize to 0-1 (was previously normalizing before smoothing, which compressed the range to ~0-0.3)

Also added (unused but present):
- `BeatFeatures` dataclass and `compute_beat_features()` — per-beat features using song structure BPM. Tried but abandoned in favor of frame-level (per-beat was still too averaged out)
- `FluxPlot3DWidget` — 3D trajectory plot (X=time, Y=flux, Z=transient) with QPainter perspective projection and orbit camera. Built but reverted to 2D plots for usability.

### 4. Test Coverage

- `tests/unit/test_autogen_roles.py` — 19 tests covering role assignment (from rudiment categories) and block generation with roles
- All 449 tests passing

---

## Current State

### Uncommitted Changes (4 files):
```
modified:   audio/spectral_analysis.py      — FrameFeatures, compute_frame_features(), BeatFeatures, compute_beat_features(), normalization fix
modified:   autogen/generator.py            — returns (lanes, report), computes frame features
modified:   autogen/report.py               — GenerationReport with frame_* arrays
modified:   gui/dialogs/generation_inspector.py — AudioFeaturesWidget uses frame data, FluxPlot3DWidget (unused)
```

### Already Committed (in "added inspector" and "testing rudiment splitting"):
```
modified:   autogen/spatial.py              — ActivationRole, assign_group_roles(), reverted compute_richness_weights
modified:   autogen/generator.py            — role system integration
modified:   gui/dialogs/autogen_dialog.py   — AutogenWorker emits (lanes, report)
modified:   gui/tabs/shows_tab.py           — Inspector button, report storage, playback hook
new:        autogen/report.py               — Report dataclasses
new:        gui/dialogs/generation_inspector.py — Inspector dashboard
new:        tests/unit/test_autogen_roles.py — Role tests
```

---

## Known Issues / TODO

- **Check theory alignment** — The activation role system and rudiment-based role assignment are new concepts not in the original theory document. Need to verify they align with the theory's intent or update the theory.
- **Inspector not tested end-to-end with playback** — The dashboard was built and compiles, but hasn't been tested with actual show playback (audio file was missing from test_conf.yaml). Need to test with a proper audio file.
- **FluxPlot3DWidget unused** — Built but reverted. Code remains in generation_inspector.py. Could be removed or revisited later.
- **BeatFeatures unused** — `compute_beat_features()` in spectral_analysis.py is no longer called. Could be removed.
- **compute_frame_features loads audio twice** — Once in `analyze_song()` and once in `compute_frame_features()`. Could be refactored to share the librosa load, but not urgent.
- **RuntimeWarning in transient calculation** — `invalid value encountered in divide` when onset local average is near zero. Harmless (caught by np.where), but should be suppressed.

---

## File Map

### New Files:
```
autogen/report.py                          — GenerationReport, SectionReport, GroupSectionReport, MatchScoreEntry
gui/dialogs/generation_inspector.py        — Inspector dashboard (AudioFeaturesWidget, GroupActivationWidget, RudimentScoresWidget, ColorPaletteWidget, FluxPlot3DWidget)
tests/unit/test_autogen_roles.py           — 19 tests for activation roles
```

### Key Modified Files:
```
audio/spectral_analysis.py                 — FrameFeatures, compute_frame_features(), BeatFeatures, compute_beat_features()
autogen/spatial.py                         — ActivationRole enum, assign_group_roles(), reverted compute_richness_weights
autogen/generator.py                       — Returns (lanes, report), role system, frame features
gui/dialogs/autogen_dialog.py              — AutogenWorker emits (lanes, report)
gui/tabs/shows_tab.py                      — Inspector button + toggle + playback hook
```

---

## Architecture: Generation Inspector Data Flow

```
User clicks "Auto-Generate"
  → AutogenWorker (QThread)
    → generate_show()
       → analyze_song()                    [section-level analysis]
       → compute_frame_features()          [frame-level for inspector]
       → per-section: rudiment selection, role assignment, block generation
       → builds GenerationReport with all decisions
    → emits (lanes, report)
  → ShowsTab stores report, enables Inspector button

User clicks "Inspector"
  → GenerationInspector window opens with report data
  → AudioFeaturesWidget reads report.frame_* arrays → builds polylines

During playback (~30Hz):
  → ShowsTab._update_playback()
    → inspector.update_position(time)
      → AudioFeaturesWidget: moves red cursor line (cheap)
      → On section change: all panels redraw with new section data
```
