# Algorithmic Light Show Generation — Theory & Framework

**Version:** 2.0
**Last Updated:** March 2026

---

## 1. Introduction

This document defines a theoretical framework for algorithmically generating light shows that follow live or recorded music. The core concept is analogous to drum rudiments: pre-defined, composable lighting patterns ("rudiments") that are intelligently selected and combined based on multi-dimensional audio analysis.

The system operates in two modes:

- **Prepared mode**: The operator pre-sets song structure (BPM, time signature, bar count, section markers). The algorithm generates a complete show ahead of time. The user can then review and edit the result in the timeline editor.
- **Live mode** (future): The algorithm runs in real-time, detecting audio input and generating lighting decisions on the fly. Live mode favors steady groove patterns without automatic fills, keeping the output homogeneous and predictable. A rolling analysis window smooths transitions by looking ahead and behind the current moment. The operator can override the algorithm via manual triggers (e.g., "play fill now", "vocals active") to inject intentional changes.

### 1.1 Design Principles

1. **Rudiments are atomic.** Every lighting pattern decomposes into one or more rudiments. If you can't describe a pattern as a rudiment or a sequence of rudiments, the vocabulary is incomplete.
2. **Intensity and movement are independent.** They occupy separate sublanes and are never combined into a single rudiment. They layer naturally because they control different fixture parameters.
3. **Color is not a rudiment property.** Color is determined by the mood/spectral analysis system and applied separately. A rudiment describes *how* intensity or position changes over time, never *what color* it is.
4. **Special effects are parameter-driven.** Gobos and prisms are activated by spectral richness thresholds, not by rudiment selection. Focus follows beam distance.
5. **The output is blocks on a timeline.** Rudiments produce sublane blocks (DimmerBlock, MovementBlock) that slot into the existing show editor. The user can always override, edit, or replace any generated block.

### 1.2 Naming Convention

| Term | Definition |
|------|-----------|
| **Rudiment** | The smallest atomic lighting pattern with a clearly defined intensity or movement logic. Analogous to a drum rudiment. |
| **Block** | A placed instance of a rudiment on the timeline, with concrete parameters (start time, duration, intensity, color, etc.). Maps to existing sublane blocks (DimmerBlock, ColourBlock, MovementBlock, SpecialBlock). |
| **Riff** | A named, reusable, beat-based composition of multiple blocks across sublanes. The existing riff system. A riff is to blocks what a drum fill is to individual strokes. |
| **Groove** | The repeating base lighting pattern for a section. Typically spans 3 bars of a 4-bar phrase. |
| **Fill** | A higher-flux transitional pattern at phrase boundaries. Typically the 4th bar. |
| **Section** | A structural division of the song (verse, chorus, bridge, etc.) defined by the operator or detected automatically. |
| **Fixture Group** | A named set of fixtures that receive the same rudiment assignment. Defined in the show creator. |

---

## 2. Rudiment System

### 2.1 Classification Rule

**If two patterns share the same underlying intensity or movement logic, they are variants of the same rudiment. If they require different logic, they are distinct rudiments.**

For example: a chase running left-to-right and a chase running top-to-bottom are spatial variants of the same "chase" rudiment. But a chase (sequential activation) and a ping pong (alternating activation) are distinct rudiments because their logic differs.

### 2.2 Intensity Rudiments

Intensity rudiments control the dimmer channel. Each rudiment defines how brightness changes over time across the fixtures in a group.

| Rudiment | Logic | Flux Envelope Shape | Parameters |
|----------|-------|-------------------|------------|
| **Static** | All fixtures at constant intensity | Flat | `intensity` |
| **Stroke** | All fixtures activate simultaneously, single pulse | Spike | `intensity`, `attack`, `decay` |
| **Ping Pong** | Intensity alternates between two discrete fixture subsets in a predictable sequence | Square oscillation | `intensity`, `speed`, `split_point` |
| **Chase** | Fixtures activate sequentially in one direction, continuously | Sawtooth (per fixture), rolling (aggregate) | `intensity`, `speed`, `direction`, `tail_length` |
| **Wave** | Intensity moves smoothly from one point to another with a decaying tail | Sine-like with decay | `intensity`, `speed`, `direction`, `decay_rate` |
| **Waterfall / Starfall** | Like wave but multi-point, with pronounced decay | Multi-peak with steep decay | `intensity`, `speed`, `direction`, `point_count`, `decay_rate` |
| **Fill / Infill** | Progressive fill-in or fill-out of fixture group | Ramp (up or down) | `intensity`, `speed`, `direction` |
| **Random Stroke** | Fixtures activate in unpredictable order, creating organic texture | Irregular spikes | `intensity`, `density`, `min_interval`, `max_interval` |
| **Sparkle / Twinkle** | Short random flashes of individual fixtures | Stochastic short pulses | `intensity`, `density`, `flash_duration` |
| **Pulse / Throb** | All or groups of fixtures rhythmically dim and brighten | Sine oscillation | `intensity_min`, `intensity_max`, `speed` |
| **Strobe** | Rapid discrete on/off flashing, synchronized | Square wave (high frequency) | `intensity`, `speed` |
| **Fade / Swell** | Smooth intensity ramp up or down | Linear ramp | `intensity_start`, `intensity_end` |
| **Cascade** | Accumulative intensity build followed by release | Ramp up → sharp drop | `intensity`, `build_speed`, `release_speed` |
| **Heartbeat** | Double-pulse pattern (bump-bump... pause...) mimicking a heartbeat rhythm | Double spike + rest | `intensity`, `speed` |
| **Throb** | Sharp attack with sustained high floor, rhythmic punch that stays bright | Spike with high floor | `intensity`, `speed`, `floor` |

**Spatial variants**: Each intensity rudiment can have spatial variants based on direction, axis, and fixture arrangement. For example:
- Chase: left→right, right→left, center→out, out→center, top→down, bottom→up
- Ping pong: horizontal, vertical, diagonal
- Wave: any directional axis

Spatial direction is a parameter of the rudiment, not a separate rudiment.

### 2.3 Movement Rudiments

Movement rudiments control pan and tilt channels on moving head fixtures. They define how the beam position changes over time.

| Rudiment | Logic | Parameters |
|----------|-------|------------|
| **Static Position** | Fixed pan/tilt | `pan`, `tilt` |
| **Circle** | Circular sweep | `center_pan`, `center_tilt`, `amplitude`, `speed` |
| **Figure-8** | Figure-eight pattern | `center_pan`, `center_tilt`, `amplitude`, `speed` |
| **Lissajous** | Configurable frequency ratio pattern | `center_pan`, `center_tilt`, `amplitude`, `speed`, `freq_ratio` |
| **Linear Sweep** | Back-and-forth along one axis | `start_pan`, `start_tilt`, `end_pan`, `end_tilt`, `speed` |
| **Diamond** | 4-corner diamond path | `center_pan`, `center_tilt`, `amplitude`, `speed` |
| **Square** | 4-corner square path | `center_pan`, `center_tilt`, `amplitude`, `speed` |
| **Triangle** | 3-corner triangular path | `center_pan`, `center_tilt`, `amplitude`, `speed` |
| **Random** | Smooth pseudo-random motion (multi-sine) | `center_pan`, `center_tilt`, `amplitude`, `speed` |
| **Bounce** | Triangle wave back and forth | `start_pan`, `start_tilt`, `end_pan`, `end_tilt`, `speed` |
| **Fan** | Synchronized spread/converge across fixture group | `center_pan`, `center_tilt`, `spread_angle`, `speed` |

Movement rudiments are assigned per fixture group. Different groups can run different movement rudiments simultaneously (e.g., front movers on circle, back movers on linear sweep).

### 2.4 What Is Not a Rudiment

- **Color**: Applied to blocks by the mood/color system (Section 4). Choosing a color is like choosing which drum to play a rudiment on.
- **Gobos**: Activated when spectral richness exceeds a threshold (Section 3.3). Gobo selection is parameter-driven.
- **Prisms**: Same as gobos — activated by spectral richness, not by rudiment selection.
- **Focus**: Follows beam-to-floor distance automatically.
- **Rotation** (gobo rotation): A continuous parameter, not a pattern.

### 2.5 Flux Envelope

Every rudiment has a characteristic **flux envelope** — a normalized curve describing how much visual change the rudiment produces over one cycle. The envelope is represented as a small time-series (normalized to 0.0–1.0 on both axes) sampled at a fixed resolution (e.g., 32 points).

#### Per-Cycle vs. Per-Duration Envelopes

Rudiments fall into two categories based on how their envelope relates to the block duration:

**Cycling rudiments** repeat their pattern multiple times within a block. The envelope describes **one cycle** of the pattern, independent of block duration or tempo. Examples: pulse, strobe, ping pong, chase, wave, sparkle. A pulse rudiment always has a single sine period as its envelope — whether the block plays that cycle 4 times or 64 times depends on BPM and speed multiplier, but the shape of each cycle is the same.

**One-shot rudiments** play their pattern exactly once across the entire block duration. The envelope describes the **full pattern**. Examples: static, fade in, fade out, cascade, fill, stroke. A fade-in rudiment always ramps from 0 to 1 over its block duration regardless of how long the block is.

#### Repetition Rate

For cycling rudiments, a second parameter is needed beyond the envelope shape: the **repetition rate** — how many cycles occur per bar (or per second). This is driven by `BPM × speed_multiplier`.

The repetition rate maps to the *frequency* of visual change:
- High spectral flux that changes rapidly → fast repetition rate (many cycles per bar)
- Low, steady spectral flux → slow repetition rate (one cycle per bar or slower)

The actual flux behavior of a block on the timeline is therefore: `envelope_shape × intensity`, repeating at the cycle rate. The envelope shape determines the *character* of the flux; the repetition rate determines the *frequency* of the flux.

#### Three-Dimensional Matching

When matching rudiments to audio analysis targets, three dimensions are compared:

1. **Envelope shape** — does the rudiment's single-cycle shape match the character of the audio? Percussive audio → spike/square-shaped envelopes. Sustained audio → smooth/sine-shaped envelopes. This comparison is tempo-independent.

2. **Repetition rate** — does the cycle frequency match the rate of change in the audio? High spectral flux frequency → fast cycling rudiments. This only applies to cycling rudiments; one-shot rudiments match by shape alone.

3. **Average flux level** — the single-cycle envelope's average value, combined with the repetition rate, gives the aggregate flux level over time. This must fall within the section's target flux range.

#### Envelope Shape Categories

For quick candidate filtering before detailed comparison, envelope shapes are classified into broad categories:
- **Flat**: Static, constant states (one-shot)
- **Spike**: Single sharp peaks — stroke, cascade release (one-shot)
- **Oscillating**: Repeating symmetric patterns — pulse, strobe, ping pong (cycling)
- **Ramp**: Monotonic increase or decrease — fade, swell, fill (one-shot)
- **Rolling**: Continuous sequential activity — chase, wave (cycling)
- **Stochastic**: Irregular, random patterns — sparkle, random stroke (cycling)

---

## 3. Audio Analysis

The algorithm extracts multiple parameters from the audio to drive lighting decisions. Each parameter maps to specific lighting dimensions.

### 3.1 Spectral Flux

**What it measures**: How much the frequency spectrum changes between consecutive time frames.

**What it drives**: Overall visual activity level, transition speed, and rudiment flux target.
- High spectral flux → more fixture changes, faster effects, higher-flux rudiments
- Low spectral flux → stability, slower transitions, lower-flux rudiments
- Average flux per section enables cross-section comparison

**Resolution**: Calculated per-frame (typically 43Hz at 1024-sample windows / 44.1kHz) and averaged per section for target definition.

### 3.2 Transient Sharpness

**What it measures**: How percussive (fast attack) versus sustained (slow attack) the sound is. Measured via onset detection algorithms.

**What it drives**: Rudiment type selection.
- High transient sharpness (percussive) → snappy rudiments: stroke, strobe, sparkle, chase
- Low transient sharpness (sustained) → flowing rudiments: wave, pulse, fade, swell

**Resolution**: Per-onset, averaged per section.

### 3.3 Spectral Richness

**What it measures**: How many distinct harmonic components or instruments are simultaneously present. Measured by counting significant spectral peaks or occupied frequency bandwidth.

**What it drives**:
- **Lighting density**: How many fixture groups are active simultaneously. Sparse instrumentation → fewer groups active. Dense arrangement → all groups active.
- **Gobo/prism activation**: When spectral richness exceeds a configurable threshold, gobos and prisms are activated on capable fixtures to add visual texture matching the audio complexity.

**Resolution**: Per-frame, averaged per section.

### 3.4 Vocal Presence Detection

**What it measures**: Whether a lead vocalist is currently singing. Detected via pitch detection in the vocal frequency range or spectral isolation techniques.

**What it drives**: Spatial focus rules (Section 6).
- Vocals present → prioritize front-stage lighting zones, increase front-stage density
- Vocals absent → shift to atmospheric/back/ambient fixtures

**Resolution**: Binary flag per time segment, with configurable debounce to avoid rapid switching.

### 3.5 Section Energy Profile

Beyond individual parameters, each section gets a composite energy profile that combines:
- Average spectral flux (overall activity)
- Transient character (percussive vs. sustained)
- Spectral richness (density)
- Vocal presence ratio (% of section with vocals)

This composite profile is what the algorithm matches rudiment combinations against.

---

## 4. Color System

Color is determined independently from rudiments. The algorithm assigns a color palette per section based on audio mood analysis, then applies colors to blocks generated by rudiment selection.

### 4.1 Two-Axis Color Model

**Axis 1 — Pitch/Brightness**:
- Higher dominant frequencies → lighter, brighter hues
- Lower dominant frequencies → darker, warmer hues
- Measured via spectral centroid (the "center of mass" of the frequency spectrum)

**Axis 2 — Mood**:
Derived from a combination of:
- Key signature (major vs. minor) — provided by operator or detected
- Spectral centroid (bright vs. dark timbres)
- Tempo (fast vs. slow)

Mapping:
- Major key + bright spectral content + fast tempo → warm, saturated colors (reds, oranges, yellows, bright whites)
- Minor key + dark spectral content + slow tempo → cool, desaturated colors (blues, purples, deep greens, cold whites)

### 4.2 Palette Generation

For each section, the color system generates a palette of 2–4 colors that:
1. Fit the mood axis position
2. Are **complementary but not uniform** — different fixture groups can receive different colors from the palette
3. Avoid stark contrasts within a section (colors should feel cohesive)
4. Provide **contrast between sections** — verse and chorus palettes should be noticeably different

### 4.3 Color Application Rules

- Colors are applied to ColourBlocks that accompany the DimmerBlocks and MovementBlocks generated by rudiments.
- Different fixture groups may receive different colors from the section palette.
- Color transitions between sections follow the section transition type (sharp cut vs. gradual crossfade).
- Within a section, color changes are minimal — the palette holds steady for the groove, with possible intensification during fills.

---

## 5. The Algorithm

### Step 1: Song-Level Analysis

**Inputs**: Audio file + operator-provided metadata (BPM, time signature, bar count per section, section markers and types).

**Process**:
1. Parse manual inputs to establish timeline structure.
2. Run spectral analysis across the full song.
3. Detect vocal presence across the song to identify front-stage emphasis zones.
4. Calculate per-section averages for all audio parameters.

**Output**: A structured representation of the song with per-section audio profiles.

### Step 2: Section-Level Target Definition

For each section, extract target values:

| Target | Source | Used By |
|--------|--------|---------|
| Target flux range | Spectral flux average ± tolerance | Rudiment selection |
| Target flux envelope shape | Spectral flux contour over section | Rudiment matching |
| Transient character | Onset sharpness average | Rudiment type filtering |
| Spectral richness | Peak count / bandwidth | Fixture group count, gobo/prism activation |
| Mood position | Key + centroid + tempo | Color palette |
| Vocal presence flag | Pitch detection | Spatial rules |
| Color palette | Mood model output | ColourBlock generation |

### Step 3: Phrase Structure Definition

Each section is divided into phrases based on bar count:
- **Prepared mode**: Phrases align with the operator-defined bar structure. Default: 4-bar phrases (3 bars groove + 1 bar fill). The groove/fill split is configurable but defaults to 75%/25% (3:1 ratio in a 4-bar phrase).
- **Live mode**: No automatic phrase subdivision. The algorithm maintains a steady groove pattern and does not inject fills on its own. Fills are only triggered by explicit operator input (see Section 9.3). This keeps the output homogeneous and avoids jarring changes without operator intent.

**Live mode rolling window**: In live mode, the algorithm uses a rolling analysis window (configurable, default ~4 bars) centered around the current playback position. The window averages audio parameters over its span, smoothing out momentary spikes and preventing the lighting from reacting to every transient. When the rolling window detects a sustained shift in audio character (e.g., spectral flux rising steadily over several bars), it triggers a gradual rudiment transition rather than a hard switch.

### Step 4: Rudiment Assignment per Fixture Group

For each fixture group in each section:

1. **Filter by capability**: Only consider intensity rudiments for all groups, movement rudiments only for groups containing moving heads.
2. **Filter by transient character**: Percussive sections → prefer snappy rudiments (spike/square envelopes). Sustained → prefer flowing rudiments (sine/ramp envelopes). Use envelope shape categories for fast filtering.
3. **Generate candidates**: Select rudiments within a loose tolerance band around the target flux range. The tolerance band is intentionally wide to ensure a diverse candidate pool.
4. **Three-dimensional matching** (see Section 2.5): Score each candidate on:
   - **Envelope shape similarity**: Compare the rudiment's single-cycle (cycling) or full-duration (one-shot) envelope against the target flux character. Score via cosine similarity or DTW on normalized curves.
   - **Repetition rate fit** (cycling rudiments only): Does the cycle rate at the section's BPM and a reasonable speed multiplier match the rate of spectral flux change in the audio?
   - **Average flux level**: Does the envelope's average value, combined with the repetition rate, fall within the section's target flux range?

Multiple fixture groups can (and should) receive different rudiments to create visual depth. The constraint is that the *combined* output across all groups should approximate the section's target flux profile.

### Step 5: Groove and Fill Assignment

**Prepared mode**: For each phrase within a section:
- **Groove (bars 1–3)**: Assign the selected rudiment(s) as a repeating base pattern.
- **Fill (bar 4)**: Select a higher-flux rudiment or variation for the fill bar. Fills must have higher flux or transient sharpness than the groove they punctuate.

**Live mode**: The groove runs continuously for the entire section. No fills are inserted automatically. When the operator triggers a fill (via manual input), the algorithm selects a higher-flux rudiment for the next bar, then returns to the groove. When the rolling window detects a significant audio character change, the algorithm crossfades to a new groove selection over 1–2 bars.

### Step 6: Dual-Criteria Scoring

Score each candidate combination on two weighted criteria:

**A. Parameter Fidelity (~60%)**:
- Flux envelope shape similarity to target
- Spectral richness → active fixture group count match
- Transient character → rudiment type appropriateness
- Color palette coherence (complementary, mood-appropriate)

**B. Musical Coherence (~40%)**:
- Groove-to-fill flow: Does the fill provide a natural punctuation?
- **Cross-section contrast**: Different sections (verse vs. chorus) must have noticeably different rudiment selections, color palettes, and flux levels. Repeated identical selections across distinct section types are penalized.
- **Within-section consistency**: Within a section, the groove pattern should remain relatively stable. Variation comes from fills and subtle parameter shifts, not wholesale rudiment changes bar-to-bar.
- Fill flux > groove flux (mandatory constraint, not just scored)

### Step 7: Selection

Select the highest-scoring combination across all fixture groups for the section.

### Step 8: Iteration

If the result is unsatisfactory (score below threshold, or manual review by operator):
- Adjust tolerance bands (wider = more candidates, more variety)
- Adjust fidelity/coherence weight ratio
- Lock certain fixture groups and regenerate others
- Regenerate with a different random seed for stochastic elements

### Step 9: Transition Handling

Analyze the transition type between adjacent sections (set by operator or inferred):

| Transition Type | Lighting Behaviour |
|----------------|-------------------|
| **Sharp** (e.g., verse → chorus) | Hard cut. New section's rudiments start immediately. Optional: a transition fill in the last bar of the outgoing section that bridges both sections' characters. |
| **Gradual** (build-up, fade) | Blend rudiment parameters across the boundary. Ramp flux and density over 1–2 bars. |
| **Fade-out** | Progressive reduction in active fixture groups and intensity. Chase/wave directions converge inward. |
| **Blackout** | All fixtures to zero, then new section starts fresh. |

Transitions are applied as post-processing on the generated block sequence. Future development: a dedicated transition rudiment library for common section boundaries.

### Step 10: Spatial Application

Apply the selected rudiments to fixture groups using the spatial model:

1. **Vocal rule**: When vocals are present, increase front-stage fixture group activity. Shift intensity balance toward front-stage groups.
2. **Atmospheric rule**: When vocals are absent, shift activity toward back and ambient fixture groups.
3. **Density matching**: Scale the number of active fixture groups to spectral richness. Low richness → 1–2 groups active. High richness → all groups active.
4. **Gobo/prism activation**: When spectral richness exceeds the configured threshold, activate gobos and prisms on capable fixtures (generates SpecialBlocks).

### Step 11: Block Generation

Convert the rudiment selections into concrete sublane blocks:

1. Each intensity rudiment → one or more **DimmerBlocks** with appropriate effect type, speed, and intensity parameters.
2. Each movement rudiment → one or more **MovementBlocks** with shape, speed, amplitude, and center position.
3. Color palette → **ColourBlocks** spanning the section, with per-group color assignments.
4. Gobo/prism decisions → **SpecialBlocks** when applicable.

Blocks are placed on the timeline in the existing LightLane/LightBlock structure, targeting the appropriate fixture groups. The user can then review, edit, or regenerate any part of the show.

---

## 6. Spatial Lighting Model

The system maintains a 3D stage model derived from the show creator's fixture configuration.

### 6.1 Data Available

Each fixture has:
- 3D position (x, y, z) in meters, origin at center stage floor
- Orientation (mounting, yaw, pitch, roll)
- Fixture group membership
- Fixture type and capabilities (from QXF definition)
- Beam direction vector (calculated from orientation)

### 6.2 Spatial Rules

| Rule | Condition | Action |
|------|-----------|--------|
| **Vocal focus** | Vocal presence detected | Increase intensity/activity of front-stage groups (lower Y values, closer to audience) |
| **Atmospheric** | No vocal presence | Shift activity to back-stage and overhead groups |
| **Density scaling** | Spectral richness level | Scale number of simultaneously active fixture groups proportionally |
| **Gobo/prism threshold** | Spectral richness > threshold | Activate gobos/prisms on capable fixtures |
| **Movement scaling** | Section energy | Higher energy → wider movement amplitudes, faster speeds |

### 6.3 Fixture Group Classification

For spatial rules, fixture groups are classified by their average position:
- **Front-stage**: Average Y position < stage_depth × 0.33
- **Mid-stage**: Average Y position between 0.33 and 0.66 × stage_depth
- **Back-stage**: Average Y position > stage_depth × 0.66
- **Overhead**: Average Z position > stage_height × 0.5

This classification is automatic based on fixture positions and used to apply the vocal/atmospheric rules.

---

## 7. Structural Analogy: Drum Theory → Light Theory

| Drum Concept | Lighting Equivalent |
|-------------|-------------------|
| Rudiment (paradiddle, flam, drag) | Light rudiment (stroke, chase, wave, ping pong) |
| Groove (repeating beat pattern) | Repeating base light pattern for a section (groove blocks) |
| Fill (transitional pattern at phrase end) | Higher-flux transitional pattern at phrase boundary (fill blocks) |
| 3 bars groove + 1 bar fill | Base rudiment blocks + fill rudiment in last bar of phrase |
| Section change fill (into chorus) | Transition handling at verse/chorus boundary |
| Which drum you play on | Color palette and fixture group assignment |
| Dynamics (ghost notes, accents) | Intensity variation within rudiment parameters |
| Orchestration (kick vs. snare vs. hi-hat) | Different rudiments on different fixture groups simultaneously |

---

## 8. Configuration & Tunables

These parameters should be exposed to the operator for tuning:

| Parameter | Default | Description |
|-----------|---------|------------|
| `groove_fill_ratio` | 0.75 (3:1) | Proportion of phrase spent on groove vs. fill (prepared mode only) |
| `phrase_length_bars` | 4 | Default phrase length in bars (prepared mode only) |
| `fidelity_weight` | 0.6 | Weight of parameter fidelity in scoring |
| `coherence_weight` | 0.4 | Weight of musical coherence in scoring |
| `tolerance_band_width` | 0.2 | How wide the candidate flux tolerance is (±fraction of target) |
| `spectral_richness_gobo_threshold` | 0.7 | Normalized richness level above which gobos activate |
| `spectral_richness_prism_threshold` | 0.8 | Normalized richness level above which prisms activate |
| `vocal_detection_debounce_ms` | 500 | Minimum vocal segment duration before triggering spatial shift |
| `cross_section_contrast_min` | 0.3 | Minimum required difference between section rudiment selections |
| `color_complementary_range` | 30–120° | Hue angle range for palette complementary colors |
| `live_rolling_window_bars` | 4 | Rolling analysis window size in bars (live mode only) |
| `live_transition_bars` | 2 | Number of bars over which to crossfade between grooves when audio character shifts (live mode only) |
| `live_fill_duration_bars` | 1 | How long a manually triggered fill lasts before returning to groove (live mode only) |

---

## 9. Open Questions & Future Development

### 9.1 Near-Term

- **Musical coherence formalization**: The coherence scoring rules need empirical testing and refinement. Starting rules: fills must have higher flux than grooves; adjacent sections must differ by at least `cross_section_contrast_min`; within-section grooves should maintain >80% rudiment consistency.
- **Weighting calibration**: The 60/40 fidelity/coherence split is a starting point. May need per-genre presets (e.g., electronic music might weight flux fidelity higher; ballads might weight coherence higher).
- **Color model refinement**: The two-axis model needs quantitative mapping from spectral centroid to hue. Needs a defined color space (HSL recommended) and concrete mapping curves.
- **Tolerance band sizing**: Empirical testing needed to find the sweet spot between too narrow (boring, repetitive) and too wide (incoherent).
- **Envelope comparison method**: Cosine similarity is simple and fast; DTW (Dynamic Time Warping) handles tempo variations better but is more expensive. Need to evaluate both.

### 9.2 Medium-Term

- **Transition rudiment library**: Dedicated transition patterns for common section boundaries (verse→chorus, chorus→bridge, etc.) would improve transition quality beyond parameter blending.
- **Genre presets**: Pre-tuned parameter sets for common genres (rock, EDM, ballad, jazz, ambient) that set appropriate defaults for tolerance bands, weights, and thresholds.
- **Fixture group role presets**: Named roles (key light, fill light, atmosphere, accent) with associated spatial and rudiment-selection biases.

### 9.3 Long-Term

- **Live auto-show mode**: Real-time audio analysis with on-the-fly rudiment selection. Requires low-latency spectral analysis and simplified scoring for real-time performance. Steady groove output with rolling analysis window for smooth transitions. Key design elements:
  - **Rolling analysis window** (default ~4 bars): Smooths audio parameters over time to prevent the lighting from chasing every transient. Sustained character shifts trigger gradual rudiment transitions.
  - **Operator override controls**: Physical or on-screen buttons for real-time overrides:
    - **"Fill now"**: Triggers a one-bar fill at the next bar boundary, then returns to groove. Allows the operator to punctuate moments the algorithm can't predict (audience reaction, performer cue).
    - **"Vocals active" (toggle)**: Manually signals vocal presence to the spatial system, overriding automatic vocal detection. Useful when detection is unreliable or for spoken-word segments.
    - **"Energy up/down"**: Bias the algorithm's flux target up or down by a configurable offset, allowing the operator to push or pull the show's energy level.
    - **"Blackout"**: Immediate all-off, overriding everything.
    - **"Next section"**: Force a section-change transition, useful when the operator knows a change is coming before the audio analysis detects it.
  - These controls inject events into the algorithm's decision loop. They take priority over automatic analysis but the algorithm resumes normal operation after the override expires.
- **Machine learning refinement**: Train scoring weights on operator-approved shows to improve automatic generation quality over time.
- **Audience energy feedback**: Integration with crowd noise or motion sensors to dynamically adjust show energy.

---

## Appendix A: Rudiment Flux Envelope Reference

Normalized envelope shapes for each intensity rudiment. Envelopes are normalized to 0.0–1.0 on both axes, sampled at 32 points per cycle.

**Cycling rudiments** — envelope describes one cycle; the cycle repeats at `BPM × speed_multiplier` rate:

| Rudiment | Shape Description | Single Cycle Profile |
|----------|------------------|---------------------|
| Ping Pong | Square wave oscillation | `█▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁` → `▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█` |
| Chase | Rolling sawtooth (aggregate) | `▂▃▄▅▆▇█▇▅▃▂▁▁▁▁▁` |
| Wave | Sine with decay tail | `▁▂▅█▆▃▁▁▁▁▁▁▁▁▁▁` |
| Waterfall | Multi-peak with steep decay | `█▅▂▁▁█▅▂▁▁█▅▂▁▁▁` |
| Random Stroke | Irregular spikes | `▁▃▁▁█▁▂▁▁▅▁▁▃▁█▁` |
| Sparkle | Stochastic short pulses | `▂▁▃▁▁▂▁▃▁▂▁▁▃▁▂▁` |
| Pulse | Sine oscillation | `▁▃▅█▅▃▁▁▁▁▁▁▁▁▁▁` |
| Strobe | High-frequency square wave | `████████▁▁▁▁▁▁▁▁` |

**One-shot rudiments** — envelope describes the full block duration; plays once and does not repeat:

| Rudiment | Shape Description | Full Duration Profile |
|----------|------------------|--------------------|
| Static | Flat line at target intensity | `████████████████` |
| Stroke | Sharp spike, fast decay | `▁▁▁▁▁▁▁█▅▂▁▁▁▁▁▁` |
| Fill | Progressive ramp up | `▁▁▂▂▃▃▄▄▅▅▆▆▇▇██` |
| Fade In | Smooth ramp up | `▁▁▂▂▃▃▄▅▅▆▆▇▇███` |
| Fade Out | Smooth ramp down | `███▇▇▆▆▅▅▄▃▃▂▂▁▁` |
| Cascade | Build up → sharp release | `▁▂▃▄▅▆▇██▇▅▃▁▁▁▁` |

These are reference shapes. Actual envelope curves are parameterized (speed, intensity, decay rate) and computed at runtime. For cycling rudiments, the block's aggregate flux is the envelope shape repeated at the cycle rate — the shape determines *character*, the rate determines *frequency*.

---

## Appendix B: Mapping to Existing Show Creator Architecture

| Theory Concept | Show Creator Implementation |
|---------------|---------------------------|
| Intensity rudiment | `effects/dimmer_effects.py` → DIMMER_REGISTRY → DimmerBlock |
| Movement rudiment | `effects/movement_effects.py` → MOVEMENT_REGISTRY → MovementBlock |
| Rudiment definition | `rudiments/rudiment.py` → Rudiment, FluxEnvelope |
| Rudiment registry | `rudiments/registry.py` → 15 intensity + 11 movement rudiments |
| Rudiment → Block | `rudiments/block_converter.py` → rudiment_to_dimmer_block/movement_block |
| Block | Sublane blocks: DimmerBlock, ColourBlock, MovementBlock, SpecialBlock |
| Riff | `riffs/riff_library.py` — beat-based reusable block compositions |
| Fixture group | `config/models.py` → FixtureGroup, resolved via `utils/target_resolver.py` |
| Fixture capabilities | `FixtureGroupCapabilities` class in sublane system |
| Timeline placement | LightLane → LightBlock → sublane blocks |
| Section structure | `timeline/song_structure.py` → ShowPart |
| BPM-aware timing | `SongStructure.get_bpm_at_time()` |
| ArtNet output | `utils/artnet/dmx_manager.py` → real-time effect computation via DIMMER_REGISTRY |
| QLC+ export | `utils/to_xml/shows_to_xml.py` → sequence generation |
| Spatial model | Fixture positions + orientation from `config/models.py` |
| Color wheel | QXF parsing in `utils/tcp/protocol.py`, DMX handling in `dmx_manager.py` |
| Gobo/prism | SpecialBlock with gobo_index, prism fields |

---

*Framework developed through theoretical exploration, March 2026.*
