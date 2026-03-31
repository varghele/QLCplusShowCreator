# Algorithmic Show Generation — Implementation Guide

**Companion to:** `docs/theory-algorithmic-show-generation.md`
**Target location:** `.claude/AUTOSHOW_IMPLEMENTATION.md`
**Last Updated:** March 2026

---

## Purpose

This document maps the theoretical framework (see theory doc) to concrete implementation tasks within the QLC+ Show Creator codebase. It is written for Claude Code sessions and assumes familiarity with the project architecture documented in `docs/architecture.md`.

**Important:** The theory document is the source of truth for *what* the system should do. This document covers *how* to build it within the existing codebase. Always consult the theory doc for conceptual questions.

---

## Prerequisites

Before starting implementation, these must already be working:

- [x] Sublane block system (DimmerBlock, ColourBlock, MovementBlock, SpecialBlock) — Phase 5–7
- [x] Effects system with BPM-aware timing — Phase 15
- [x] Fixture groups with capability detection — Phase 5
- [x] Fixture orientation and 3D positions — Phase 14
- [x] Song structure with BPM, time signature, bars per section — Phase 11
- [x] Riff system with beat-based timing — existing in `riffs/`
- [x] ArtNet output and QLC+ export — Phase 8–9, 12
- [x] Multi-target lanes — Phase 14.10

---

## Implementation Phases

The implementation is split into sub-phases that can be tackled incrementally. Each sub-phase produces working, testable code.

### Phase 16.1: Rudiment Data Model

**Goal:** Define the rudiment as a first-class data object in the codebase.

**New file:** `rudiments/rudiment.py`

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

class RudimentType(Enum):
    INTENSITY = "intensity"
    MOVEMENT = "movement"

class EnvelopeCategory(Enum):
    FLAT = "flat"           # Static, constant
    SPIKE = "spike"         # Single sharp peak (one-shot)
    OSCILLATING = "oscillating"  # Repeating symmetric (cycling)
    RAMP = "ramp"           # Monotonic increase/decrease (one-shot)
    ROLLING = "rolling"     # Continuous sequential (cycling)
    STOCHASTIC = "stochastic"  # Irregular, random (cycling)

class CycleMode(Enum):
    CYCLING = "cycling"     # Envelope = one cycle, repeats in block
    ONE_SHOT = "one_shot"   # Envelope = full block duration, plays once

@dataclass
class FluxEnvelope:
    """Normalized flux envelope for a rudiment.
    
    For cycling rudiments: describes one cycle.
    For one-shot rudiments: describes the full duration.
    Values normalized to 0.0-1.0, sampled at `resolution` points.
    """
    samples: List[float]        # Normalized 0.0-1.0
    category: EnvelopeCategory
    cycle_mode: CycleMode
    resolution: int = 32        # Number of sample points

@dataclass
class RudimentParameter:
    """Definition of a configurable parameter on a rudiment."""
    name: str
    param_type: str             # "float", "int", "enum", "direction"
    default: Any
    min_value: Any = None
    max_value: Any = None
    enum_values: List[str] = field(default_factory=list)
    description: str = ""

@dataclass
class Rudiment:
    """Atomic lighting pattern definition."""
    name: str                   # e.g. "chase", "pulse", "circle"
    rudiment_type: RudimentType # INTENSITY or MOVEMENT
    envelope: FluxEnvelope
    parameters: List[RudimentParameter]
    description: str = ""
    
    # For matching
    average_flux: float = 0.0   # Computed from envelope samples
    
    def compute_average_flux(self):
        if self.envelope.samples:
            self.average_flux = sum(self.envelope.samples) / len(self.envelope.samples)
```

**New file:** `rudiments/__init__.py`

Export the core classes.

**Tests:** `tests/test_rudiment_model.py`
- Create rudiments with envelopes, verify serialization
- Test `compute_average_flux()`
- Test envelope category classification

---

### Phase 16.2: Rudiment Registry

**Goal:** A central registry of all available rudiments with their envelopes and parameters.

**New file:** `rudiments/registry.py`

This file defines every intensity and movement rudiment listed in the theory doc Section 2.2 and 2.3. Each rudiment gets:
- A unique name string (used as key everywhere)
- An envelope with concrete sample values
- Parameter definitions with defaults and ranges
- Envelope category and cycle mode

```python
# Structure:
INTENSITY_RUDIMENTS: Dict[str, Rudiment] = {}
MOVEMENT_RUDIMENTS: Dict[str, Rudiment] = {}

def register_intensity_rudiments():
    """Build all intensity rudiment definitions."""
    # Example:
    INTENSITY_RUDIMENTS["static"] = Rudiment(
        name="static",
        rudiment_type=RudimentType.INTENSITY,
        envelope=FluxEnvelope(
            samples=[1.0] * 32,
            category=EnvelopeCategory.FLAT,
            cycle_mode=CycleMode.ONE_SHOT,
        ),
        parameters=[
            RudimentParameter("intensity", "float", 1.0, 0.0, 1.0),
        ],
        description="All fixtures at constant intensity",
    )
    
    INTENSITY_RUDIMENTS["chase"] = Rudiment(
        name="chase",
        rudiment_type=RudimentType.INTENSITY,
        envelope=FluxEnvelope(
            samples=_generate_chase_envelope(),  # Sawtooth shape
            category=EnvelopeCategory.ROLLING,
            cycle_mode=CycleMode.CYCLING,
        ),
        parameters=[
            RudimentParameter("intensity", "float", 1.0, 0.0, 1.0),
            RudimentParameter("speed", "float", 1.0, 0.25, 4.0),
            RudimentParameter("direction", "direction", "left_to_right"),
            RudimentParameter("tail_length", "float", 0.3, 0.0, 1.0),
        ],
        description="Sequential fixture activation in one direction",
    )
    # ... all 14 intensity rudiments from theory doc Section 2.2

def register_movement_rudiments():
    """Build all movement rudiment definitions."""
    # ... all 11 movement rudiments from theory doc Section 2.3

def get_rudiment(name: str) -> Optional[Rudiment]:
    return INTENSITY_RUDIMENTS.get(name) or MOVEMENT_RUDIMENTS.get(name)

def get_intensity_rudiments() -> Dict[str, Rudiment]:
    return INTENSITY_RUDIMENTS

def get_movement_rudiments() -> Dict[str, Rudiment]:
    return MOVEMENT_RUDIMENTS
```

**Envelope generation helpers:** Private functions that generate the 32-point envelope arrays for each rudiment type (sine, sawtooth, square, ramp, etc.). These are computed once at registry initialization.

**Tests:** `tests/test_rudiment_registry.py`
- All rudiments register without error
- Each rudiment has a valid envelope with correct sample count
- Envelope categories match expected values
- All parameters have valid defaults within their ranges

---

### Phase 16.3: Rudiment-to-Block Converter

**Goal:** Convert a rudiment + parameters + timing into concrete sublane blocks.

**New file:** `rudiments/block_converter.py`

This is the bridge between the rudiment system and the existing block system. Each rudiment name maps to a function that produces one or more sublane blocks.

```python
def rudiment_to_dimmer_block(
    rudiment_name: str,
    params: Dict[str, Any],
    start_time: float,
    duration: float,
    bpm: float,
) -> DimmerBlock:
    """Convert an intensity rudiment to a DimmerBlock."""
    # Map rudiment names to existing effect types where possible:
    # "static" -> DimmerBlock with effect_type="static"
    # "strobe" -> DimmerBlock with effect_type="strobe"
    # "chase"  -> DimmerBlock with effect_type="chase" (new or extended)
    # etc.

def rudiment_to_movement_block(
    rudiment_name: str,
    params: Dict[str, Any],
    start_time: float,
    duration: float,
    bpm: float,
) -> MovementBlock:
    """Convert a movement rudiment to a MovementBlock."""
    # Map rudiment names to existing movement shapes:
    # "circle" -> MovementBlock with shape="circle"
    # "figure_8" -> MovementBlock with shape="figure_8"
    # etc.
```

**Key mapping decisions:**

| Intensity Rudiment | Existing Effect Type | Notes |
|-------------------|---------------------|-------|
| static | `static` | Direct mapping |
| strobe | `strobe` | Direct mapping |
| twinkle/sparkle | `twinkle` | Direct mapping |
| ping_pong | `ping_pong_smooth` | Already exists in Phase 15 |
| waterfall | `waterfall_down` / `waterfall_up` | Already exists in Phase 15 |
| chase | New effect type needed | Sequential activation logic |
| wave | New effect type needed | Smooth propagation with decay |
| stroke | New effect type needed | Single pulse with attack/decay |
| fill | New effect type needed | Progressive fill-in |
| random_stroke | New effect type needed | Random fixture activation |
| pulse | New effect type needed | Sine-based dimming |
| fade_in / fade_out | New effect type needed | Linear ramp |
| cascade | New effect type needed | Build + release |

For rudiments that don't have an existing effect type, new effect functions need to be added to `effects/dimmers.py`. This is the main body of work in this phase.

| Movement Rudiment | Existing Shape | Notes |
|------------------|---------------|-------|
| static_position | `static` | Direct mapping |
| circle | `circle` | Direct mapping |
| figure_8 | `figure_8` | Direct mapping |
| lissajous | `lissajous` | Direct mapping |
| diamond | `diamond` | Direct mapping |
| square | `square` | Direct mapping |
| triangle | `triangle` | Direct mapping |
| random | `random` | Direct mapping |
| bounce | `bounce` | Direct mapping |
| linear_sweep | New shape needed | Back-and-forth on one axis |
| fan | New shape needed | Coordinated spread/converge |

Movement rudiments map much more cleanly since most shapes already exist.

**Tests:** `tests/test_block_converter.py`
- Each rudiment produces a valid block with correct time range
- Parameters propagate correctly to block fields
- BPM affects speed/timing as expected

---

### Phase 16.4: New Effect Functions

**Goal:** Implement the dimmer effect functions for rudiments that don't have existing mappings.

**Modified file:** `effects/dimmers.py`

New functions to add (following the existing pattern in this file):

```python
def chase(fixtures, t, bpm, speed, intensity, direction, tail_length, **kwargs):
    """Sequential fixture activation in one direction."""
    # Calculate which fixture is active based on t, bpm, speed
    # Apply tail_length for trailing glow on previous fixtures
    # Direction determines fixture ordering

def wave(fixtures, t, bpm, speed, intensity, direction, decay_rate, **kwargs):
    """Smooth intensity propagation with decaying tail."""
    # Sine-based intensity moving through fixture positions
    # Decay applied to trailing edge

def stroke(fixtures, t, bpm, intensity, attack, decay, **kwargs):
    """Single pulse — all fixtures, fast attack, configurable decay."""
    # One-shot: ramp up over attack, decay over remainder

def fill_in(fixtures, t, bpm, speed, intensity, direction, **kwargs):
    """Progressive activation of fixtures."""
    # Fixtures turn on one by one and stay on

def random_stroke(fixtures, t, bpm, intensity, density, **kwargs):
    """Random fixture activation creating organic texture."""
    # Deterministic pseudo-random (seeded) for repeatability

def pulse(fixtures, t, bpm, speed, intensity_min, intensity_max, **kwargs):
    """Sine-based rhythmic dimming."""
    # All fixtures follow same sine curve

def fade_in(fixtures, t, duration, intensity_start, intensity_end, **kwargs):
    """Linear intensity ramp up over block duration."""

def fade_out(fixtures, t, duration, intensity_start, intensity_end, **kwargs):
    """Linear intensity ramp down over block duration."""

def cascade(fixtures, t, bpm, speed, intensity, build_speed, release_speed, **kwargs):
    """Accumulative build followed by release."""
    # Ramp up over build_speed fraction, sharp drop over release_speed fraction
```

**Important:** All effect functions must follow the existing signature pattern used by `dmx_manager.py` for real-time computation. Check the existing `static`, `strobe`, `twinkle`, `ping_pong_smooth`, `waterfall_down` functions for the exact calling convention.

**Modified file:** `utils/artnet/dmx_manager.py`

Register new effect types in the effect dispatch logic so they can be computed in real-time during ArtNet playback.

**Modified file:** `utils/to_xml/shows_to_xml.py`

Add export support for new effect types to QLC+ sequences. Each new effect needs step generation logic.

**Tests:** `tests/test_dimmer_effects.py`
- Each new effect produces correct DMX values at various time points
- BPM scaling works correctly
- Edge cases: t=0, t=duration, very fast/slow BPM

---

### Phase 16.5: Rudiment Selection UI

**Goal:** Allow users to manually assign rudiments to blocks in the timeline editor.

**Modified file:** `timeline_ui/dimmer_block_dialog.py`

Add a rudiment selector (dropdown or categorized list) that:
1. Shows all registered intensity rudiments
2. When selected, populates the block's parameters with the rudiment's defaults
3. Replaces the current effect type dropdown (or wraps it, keeping backward compatibility)

**Modified file:** `timeline_ui/movement_block_dialog.py`

Same approach for movement rudiments — the existing shape dropdown already maps closely to movement rudiments. This may just need relabeling and ensuring all movement rudiments are available.

**Ensure backward compatibility:** Existing blocks saved with old effect type names must still load correctly. The rudiment name should be stored alongside the effect type, not replacing it.

**New field on blocks:** Add an optional `rudiment_name` field to DimmerBlock and MovementBlock in `config/models.py`. When present, it indicates the block was created from a rudiment. When absent (legacy blocks), behavior is unchanged.

---

### Phase 16.6: Integration Verification

**Goal:** Verify the full pipeline works end-to-end.

Test the following flow manually:
1. Open a show in the timeline editor
2. Create a new DimmerBlock on a lane
3. Select a rudiment (e.g., "chase") from the dialog
4. Verify parameters populate correctly
5. Play back via ArtNet — verify the effect renders correctly in the Visualizer
6. Export to QLC+ — verify the sequence plays correctly in QLC+
7. Save and reload — verify the rudiment name persists

---

## Phase 24 Implementation (Automatic Show Generation)

**Prerequisite:** Phase 16 complete (all rudiments registered, block converter working, effects implemented).

This phase implements the algorithm described in the theory doc Sections 3–6. It is a separate, later effort.

### Phase 24.1: Audio Analysis Module

**New file:** `audio/spectral_analysis.py`

Dependencies: `librosa` (add to requirements.txt)

```python
@dataclass
class SectionAnalysis:
    """Audio analysis results for one section of a song."""
    start_time: float
    end_time: float
    spectral_flux_avg: float
    spectral_flux_envelope: List[float]  # Normalized contour
    transient_sharpness: float           # 0.0 (sustained) to 1.0 (percussive)
    spectral_richness: float             # 0.0 (sparse) to 1.0 (dense)
    vocal_presence: float                # 0.0 to 1.0 (ratio of section)
    spectral_centroid_avg: float         # Hz, for color mapping
    
@dataclass
class SongAnalysis:
    """Complete audio analysis for a song."""
    sections: List[SectionAnalysis]
    global_flux_range: Tuple[float, float]  # Min/max for normalization
    bpm_detected: Optional[float]

def analyze_song(
    audio_path: str,
    song_structure: SongStructure,  # From timeline/song_structure.py
) -> SongAnalysis:
    """Run full spectral analysis on a song file.
    
    Uses the operator-provided song structure for section boundaries.
    """
    # 1. Load audio with librosa
    # 2. Compute spectral flux (librosa.onset.onset_strength)
    # 3. Compute onset sharpness (librosa.onset.onset_detect with backtrack)
    # 4. Compute spectral richness (count significant peaks in STFT)
    # 5. Detect vocal presence (spectral isolation in 300Hz-3kHz band)
    # 6. Compute spectral centroid (librosa.feature.spectral_centroid)
    # 7. Segment by song structure sections
    # 8. Average per section
```

**Tests:** `tests/test_spectral_analysis.py`
- Analyze a test audio file with known characteristics
- Verify section boundaries align with song structure
- Verify flux normalization

---

### Phase 24.2: Color Palette Generator

**New file:** `autogen/color_generator.py`

Implements the two-axis color model from theory doc Section 4.

```python
@dataclass
class SectionPalette:
    """Color palette for a section."""
    colors: List[Tuple[int, int, int]]  # 2-4 RGB colors
    mood_position: float                 # -1.0 (dark/cool) to 1.0 (bright/warm)
    brightness_position: float           # 0.0 (low) to 1.0 (high)

def generate_palette(
    section: SectionAnalysis,
    key_signature: str,         # From operator input, e.g. "C major"
    num_colors: int = 3,
) -> SectionPalette:
    """Generate a color palette for a section based on audio mood."""
    # 1. Map key signature to major/minor
    # 2. Combine with spectral centroid and tempo for mood axis
    # 3. Map spectral centroid to brightness axis
    # 4. Select base hue from mood position
    # 5. Generate complementary colors within color_complementary_range
    # 6. Return palette

def ensure_section_contrast(
    palettes: Dict[str, SectionPalette],  # section_name -> palette
    min_contrast: float,
) -> Dict[str, SectionPalette]:
    """Adjust palettes to ensure sufficient contrast between different section types."""
```

**Color space:** Use HSL internally for palette generation (hue rotation for complements, saturation for mood, lightness for brightness). Convert to RGB for block storage.

---

### Phase 24.3: Rudiment Matching Engine

**New file:** `autogen/matcher.py`

Implements the three-dimensional matching from theory doc Section 2.5 and the candidate scoring from Section 5, Steps 4–6.

```python
@dataclass
class MatchScore:
    """Scoring result for a rudiment candidate."""
    rudiment_name: str
    envelope_similarity: float    # 0.0 to 1.0
    repetition_rate_fit: float    # 0.0 to 1.0 (cycling only)
    flux_level_fit: float         # 0.0 to 1.0
    fidelity_score: float         # Weighted combination
    coherence_score: float        # Musical coherence
    total_score: float            # Final combined score

def match_rudiments_to_section(
    section: SectionAnalysis,
    available_rudiments: Dict[str, Rudiment],
    fixture_group_capabilities: Dict[str, FixtureGroupCapabilities],
    config: AutogenConfig,
) -> Dict[str, str]:
    """Select best rudiment for each fixture group in a section.
    
    Returns: {group_name: rudiment_name}
    """
    # 1. For each fixture group:
    #    a. Filter rudiments by capability (intensity for all, movement for MH only)
    #    b. Filter by transient character (envelope category)
    #    c. Score remaining candidates (three-dimensional matching)
    # 2. Evaluate combined output across groups
    # 3. Return highest-scoring combination

def score_envelope_similarity(
    rudiment_envelope: List[float],
    target_envelope: List[float],
) -> float:
    """Compare rudiment envelope shape to target flux contour.
    
    Uses cosine similarity on normalized vectors.
    """

def score_repetition_rate(
    rudiment: Rudiment,
    target_flux_frequency: float,
    bpm: float,
    speed_range: Tuple[float, float] = (0.25, 4.0),
) -> float:
    """Score how well the cycle rate matches audio flux frequency.
    
    Only applicable to cycling rudiments.
    """

def score_musical_coherence(
    groove_rudiment: str,
    fill_rudiment: str,
    previous_section_rudiments: Dict[str, str],
    section_type: str,
    previous_section_type: str,
) -> float:
    """Score musical coherence of a rudiment selection.
    
    Penalizes: identical selections across different section types,
    fills with lower flux than grooves.
    Rewards: within-section consistency, cross-section contrast.
    """
```

---

### Phase 24.4: Show Generator

**New file:** `autogen/generator.py`

The main orchestrator that implements the full algorithm (theory doc Section 5, Steps 1–11).

```python
@dataclass
class AutogenConfig:
    """Configuration for automatic show generation."""
    groove_fill_ratio: float = 0.75
    phrase_length_bars: int = 4
    fidelity_weight: float = 0.6
    coherence_weight: float = 0.4
    tolerance_band_width: float = 0.2
    spectral_richness_gobo_threshold: float = 0.7
    spectral_richness_prism_threshold: float = 0.8
    vocal_detection_debounce_ms: int = 500
    cross_section_contrast_min: float = 0.3
    color_complementary_range: Tuple[float, float] = (30.0, 120.0)

def generate_show(
    audio_path: str,
    song_structure: SongStructure,
    config: Configuration,        # Existing show creator config (fixtures, groups, etc.)
    autogen_config: AutogenConfig,
) -> List[LightLane]:
    """Generate a complete light show for a song.
    
    Returns a list of LightLanes populated with blocks,
    ready to be placed on the timeline.
    
    Algorithm steps (see theory doc Section 5):
    1. Analyze audio
    2. Define section targets
    3. Define phrase structure
    4. Assign rudiments per fixture group
    5. Assign grooves and fills
    6. Score candidates
    7. Select best combination
    8. Handle transitions
    9. Apply spatial rules
    10. Generate blocks
    """
    # Step 1
    analysis = analyze_song(audio_path, song_structure)
    
    # Step 2
    section_targets = define_section_targets(analysis, song_structure)
    
    # Steps 3-7: Per section
    section_selections = {}
    for section in song_structure.parts:
        target = section_targets[section.name]
        
        # Step 3: phrase structure
        phrases = build_phrases(section, autogen_config)
        
        # Steps 4-7: rudiment selection
        selection = match_rudiments_to_section(
            target, get_intensity_rudiments(), get_movement_rudiments(),
            get_group_capabilities(config), autogen_config,
        )
        section_selections[section.name] = selection
    
    # Step 8: transitions
    apply_transitions(section_selections, song_structure)
    
    # Step 9: spatial rules
    apply_spatial_rules(section_selections, analysis, config)
    
    # Step 10: generate blocks
    lanes = generate_blocks(section_selections, song_structure, config, autogen_config)
    
    return lanes
```

---

### Phase 24.5: Spatial Rules Engine

**New file:** `autogen/spatial.py`

Implements the spatial lighting model from theory doc Section 6.

```python
def classify_fixture_groups(
    config: Configuration,
) -> Dict[str, str]:
    """Classify each fixture group by stage position.
    
    Returns: {group_name: "front" | "mid" | "back" | "overhead"}
    
    Classification based on average Y and Z positions of group's fixtures,
    relative to stage dimensions.
    """

def apply_vocal_rule(
    section_selections: Dict,
    vocal_presence: float,
    group_classifications: Dict[str, str],
):
    """Increase front-stage group activity when vocals present."""

def apply_density_scaling(
    section_selections: Dict,
    spectral_richness: float,
    all_groups: List[str],
):
    """Scale number of active fixture groups to spectral richness."""

def apply_gobo_prism_activation(
    section_selections: Dict,
    spectral_richness: float,
    gobo_threshold: float,
    prism_threshold: float,
    group_capabilities: Dict,
):
    """Activate gobos/prisms when spectral richness exceeds thresholds.
    
    Generates SpecialBlock entries for capable fixture groups.
    """
```

---

### Phase 24.6: Generator UI

**Goal:** Add a "Generate Show" action to the Shows tab.

**Modified file:** `gui/tabs/shows_tab.py`

Add a toolbar button or menu action "Auto-Generate" that:
1. Opens a configuration dialog for `AutogenConfig` parameters
2. Runs `generate_show()` in a background thread (QThread)
3. Shows a progress dialog
4. On completion, populates the timeline with generated lanes/blocks
5. User can then review, edit, or regenerate

**New file:** `gui/dialogs/autogen_dialog.py`

Configuration dialog with:
- Spinboxes/sliders for all `AutogenConfig` tunables
- Genre preset dropdown (loads preset values)
- "Generate" button
- Progress bar
- Option to regenerate individual sections

**Important UX principle:** The generated blocks are normal timeline blocks. The user can edit, move, delete, or add to them freely. The auto-generation is a starting point, not a locked result. The `rudiment_name` field on blocks tracks their origin for reference.

---

## File Structure Summary

New files to create:

```
rudiments/
├── __init__.py
├── rudiment.py            # Data model (Rudiment, FluxEnvelope, etc.)
├── registry.py            # All rudiment definitions
└── block_converter.py     # Rudiment → sublane block conversion

autogen/                   # Phase 24 (later)
├── __init__.py
├── generator.py           # Main orchestrator
├── matcher.py             # Rudiment matching engine
├── spatial.py             # Spatial rules
└── color_generator.py     # Color palette from mood analysis

audio/
└── spectral_analysis.py   # Audio analysis (Phase 24)

gui/dialogs/
└── autogen_dialog.py      # Generation config UI (Phase 24)

tests/
├── test_rudiment_model.py
├── test_rudiment_registry.py
├── test_block_converter.py
├── test_dimmer_effects.py
├── test_spectral_analysis.py  # Phase 24
└── test_matcher.py            # Phase 24
```

Files to modify:

```
config/models.py              # Add rudiment_name field to DimmerBlock, MovementBlock
effects/dimmers.py            # New effect functions for missing rudiments
utils/artnet/dmx_manager.py   # Register new effect types
utils/to_xml/shows_to_xml.py  # Export support for new effects
timeline_ui/dimmer_block_dialog.py   # Rudiment selector
timeline_ui/movement_block_dialog.py # Rudiment selector
gui/tabs/shows_tab.py         # Auto-generate button (Phase 24)
requirements.txt               # Add librosa (Phase 24)
```

---

## Implementation Order

**Phase 16 (Rudiments — do first):**
1. `16.1` Rudiment data model → pure data, no dependencies
2. `16.2` Rudiment registry → depends on 16.1
3. `16.4` New effect functions → can be done in parallel with 16.2
4. `16.3` Block converter → depends on 16.1, 16.2, 16.4
5. `16.5` Rudiment selection UI → depends on 16.2, 16.3
6. `16.6` Integration verification → depends on all above

**Phase 24 (Auto-generation — do later, after Phase 16 complete):**
1. `24.1` Audio analysis → independent, can start early if desired
2. `24.2` Color palette generator → depends on 24.1
3. `24.3` Rudiment matching engine → depends on 16.2 (registry)
4. `24.4` Show generator → depends on 24.1, 24.2, 24.3
5. `24.5` Spatial rules → depends on 24.4
6. `24.6` Generator UI → depends on 24.4

---

## Key Design Decisions

### Backward Compatibility

The rudiment system is additive. Existing blocks without a `rudiment_name` field continue to work exactly as before. The rudiment name is metadata — it does not change how a block is rendered or exported. The effect type on the block is what drives DMX computation, same as today.

### Rudiment ≠ Effect Type

A rudiment is a theoretical concept with an envelope, parameters, and classification. An effect type is a concrete implementation in `effects/dimmers.py` that computes DMX values. Multiple rudiments could map to the same effect type with different default parameters (though in practice they're mostly 1:1).

### Registry Is Static

The rudiment registry is defined in code, not loaded from config files. Users don't create new rudiments — they create riffs (compositions of blocks). If a new rudiment is needed, it's added to the codebase. This keeps the vocabulary controlled and the matching engine predictable.

### Auto-Generation Output Is Editable

Generated blocks are identical to manually created blocks. There is no "auto-generated" lock or special rendering. The user can freely edit the result. The `rudiment_name` field is informational only.

### Audio Analysis Is Offline

For prepared mode, audio analysis runs once when the user triggers generation. Results can be cached per song (keyed by audio file hash) to avoid re-analysis on regeneration. Live mode analysis is a separate, future implementation.

---

## Dependencies

### Phase 16 (Rudiments)
- No new external dependencies
- Uses only existing project infrastructure

### Phase 24 (Auto-generation)
- `librosa` — audio analysis (spectral flux, onset detection, spectral centroid)
- `numpy` — already likely present as librosa dependency
- `scipy` — for cosine similarity, DTW (optional, can use simplified version)

Add to `requirements.txt` when Phase 24 begins:
```
librosa>=0.10.0
```

---

## Reference: Theory Doc Sections → Implementation Mapping

| Theory Section | Implementation Phase | Key Files |
|---------------|---------------------|-----------|
| 2.1 Classification Rule | 16.1 | `rudiments/rudiment.py` |
| 2.2 Intensity Rudiments | 16.2, 16.4 | `rudiments/registry.py`, `effects/dimmers.py` |
| 2.3 Movement Rudiments | 16.2 | `rudiments/registry.py` |
| 2.5 Flux Envelope | 16.1 | `rudiments/rudiment.py` (FluxEnvelope) |
| 3.1–3.4 Audio Analysis | 24.1 | `audio/spectral_analysis.py` |
| 4. Color System | 24.2 | `autogen/color_generator.py` |
| 5. The Algorithm | 24.3, 24.4 | `autogen/matcher.py`, `autogen/generator.py` |
| 6. Spatial Model | 24.5 | `autogen/spatial.py` |
| 8. Tunables | 24.4 | `autogen/generator.py` (AutogenConfig) |
