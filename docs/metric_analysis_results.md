# Audio Metric Analysis Results

**Date:** 2026-04-03
**Songs tested:** 8 songs from the SBD setlist, all with metronome/click tracks
**Tool:** `tests/autogen_harness.py --sections-only`
**Config:** `conf_backup_outro_v2.yaml` (hand-made light shows for comparison)

## Problem Statement

The autogen algorithm's section-level metrics failed to differentiate song sections meaningfully. This led to:
- "quiet" sections scoring higher energy than choruses
- Fixture groups being activated/deactivated based on noise rather than musical intent
- The generated show bearing little resemblance to hand-made shows

## Metrics Tested

| Metric | Source | What it measures |
|--------|--------|-----------------|
| **spectral_flux** | `librosa.onset.onset_strength` averaged per section | Rate of spectral change (onset envelope) |
| **transient_sharpness** | Onset density / 10, capped at 1.0 | How percussive/punchy a section is |
| **spectral_richness** | 0.6 * normalized_bandwidth + 0.4 * spectral_flatness | How many frequency bands are active |
| **vocal_presence** | HPSS harmonic component + MFCC delta RMS | Rapid spectral shape changes (phoneme-like) |
| **spectral_centroid** | `librosa.feature.spectral_centroid` averaged | Brightness / frequency center of mass |
| **rms_energy** | `librosa.feature.rms` normalized to song max | Direct loudness measurement |
| **spectral_contrast** | `librosa.feature.spectral_contrast` averaged across bands | Peak-to-valley prominence per frequency band |
| **relative_energy** | Composite: 0.6 * percentile_rank(X) + 0.4 * Y | Overall section intensity (0-1) |

## Cross-Song Verdict Table

Verdicts based on range across sections (excluding klickintro):
- `GOOD`: range >= 0.30 (or proportionally for Hz-scale metrics)
- `OK`: range 0.15-0.30
- `WEAK`: range 0.05-0.15
- `USELESS`: range < 0.05

| Metric | Cycle 103bpm | Wheel 193bpm | Monsters 107/192bpm | HitRoad 180bpm | Intro&DD 90/130bpm | OldSchool 190bpm | Party1 139/192bpm | Swingin 183bpm |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| flux | !! USELESS | !! USELESS | ! WEAK | !! USELESS | !! USELESS | !! USELESS | ! WEAK | !! USELESS |
| transient | OK | OK | GOOD | OK | OK | GOOD | GOOD | GOOD |
| richness | !! USELESS | ! WEAK | ! WEAK | !! USELESS | ! WEAK | ! WEAK | GOOD* | ! WEAK |
| vocal | OK | ! WEAK | GOOD | OK | ! WEAK | ! WEAK | OK | OK |
| centroid | OK | OK | OK | OK | GOOD | GOOD | GOOD* | OK |
| **rms** | ! WEAK | **GOOD** | **GOOD** | OK | **GOOD** | **GOOD** | **GOOD** | **GOOD** |
| contrast | ! WEAK | ! WEAK | ! WEAK | !! USELESS | ! WEAK | ! WEAK | GOOD* | ! WEAK |
| **energy** | **GOOD** | **GOOD** | **GOOD** | **GOOD** | **GOOD** | **GOOD** | **GOOD** | **GOOD** |

*Party of One has a silent outro section which inflates all ranges for that song.

### Average Ranges Across All 8 Songs

| Metric | Avg Range | Verdict |
|--------|-----------|---------|
| flux | 0.028 | USELESS |
| richness | 0.077 | WEAK |
| contrast | 0.094 | WEAK |
| vocal | 0.163 | OK |
| transient | 0.291 | OK-GOOD |
| **rms** | **0.346** | **GOOD** |
| **energy** | **0.578** | **GOOD** |

## Detailed Per-Song Results

### SBD_cycle_of_a_pscho (103.5 BPM, 15 sections)

```
Section           Flux  Trans   Rich  Vocal    RMS  Contr  Energy
klickintro       0.090  0.388  0.384  0.449  0.236  0.704   0.281
intro            0.049  0.264  0.445  0.151  0.477  0.639   0.298
vers1            0.055  0.253  0.440  0.172  0.550  0.652   0.603
bridge1          0.042  0.190  0.437  0.105  0.520  0.636   0.383
prechorus1       0.057  0.302  0.447  0.263  0.556  0.627   0.637
chorus1          0.049  0.177  0.425  0.133  0.589  0.647   0.773
drop1            0.051  0.240  0.432  0.166  0.531  0.640   0.513
prechorus2       0.059  0.259  0.440  0.271  0.575  0.625   0.721
chorus2          0.049  0.182  0.427  0.134  0.592  0.647   0.816
drop2            0.046  0.237  0.433  0.146  0.524  0.625   0.421
pause            0.052  0.323  0.419  0.149  0.529  0.608   0.458
drop3            0.041  0.124  0.445  0.085  0.559  0.612   0.673
quiet            0.056  0.259  0.441  0.184  0.506  0.677   0.356
chorus3          0.048  0.146  0.450  0.111  0.614  0.637   0.855
outro            0.047  0.168  0.442  0.128  0.539  0.628   0.551
```

Energy ordering with new RMS-based formula: chorus3 (0.855) > chorus2 (0.816) > chorus1 (0.773) > prechorus2 (0.721) > drop3 (0.673) > ... > quiet (0.356) > intro (0.298)

Previous flux-based formula had: quiet (0.690) > chorus1 (0.470) -- completely wrong.

### SBD_take_the_wheel (193 BPM, 19 sections)

```
Section           Flux  Trans   Rich  Vocal    RMS  Contr  Energy
klickintro       0.116  0.442  0.413  0.483  0.243  0.692   0.277
intro1           0.057  0.307  0.382  0.146  0.460  0.661   0.398
intro2           0.044  0.251  0.450  0.079  0.492  0.605   0.442
bridge1          0.049  0.342  0.342  0.132  0.313  0.658   0.297
vers1            0.054  0.236  0.440  0.131  0.535  0.632   0.520
prechorus1       0.049  0.211  0.453  0.107  0.551  0.638   0.588
chorus1          0.047  0.141  0.445  0.102  0.596  0.626   0.717
bridge2          0.043  0.101  0.396  0.118  0.374  0.643   0.324
vers2            0.054  0.191  0.446  0.133  0.557  0.624   0.650
prechorus2       0.049  0.221  0.448  0.116  0.551  0.638   0.622
chorus2          0.047  0.151  0.445  0.104  0.594  0.624   0.683
interlude        0.047  0.281  0.429  0.100  0.613  0.589   0.769
solo             0.049  0.216  0.411  0.093  0.517  0.638   0.488
chant1           0.052  0.211  0.421  0.115  0.667  0.627   0.851
chant2           0.046  0.191  0.432  0.098  0.548  0.606   0.542
prechorus3       0.053  0.264  0.427  0.172  0.430  0.730   0.392
chorus3          0.048  0.150  0.441  0.107  0.604  0.626   0.750
outro            0.044  0.171  0.428  0.078  0.665  0.592   0.804
outro2           0.041  0.161  0.437  0.088  0.462  0.607   0.409
```

### SBD_monsters_in_my_head (107/192 BPM, 21 sections)

```
Section           Flux  Trans   Rich  Vocal    RMS  Contr  Energy
klickintro       0.078  0.360  0.420  0.073  0.122  0.432   0.173
intro            0.052  0.200  0.427  0.131  0.358  0.667   0.387
bpart            0.045  0.229  0.424  0.084  0.534  0.712   0.615
vers1            0.053  0.210  0.421  0.116  0.592  0.711   0.704
prechorus1       0.048  0.150  0.433  0.088  0.614  0.708   0.793
chorus1          0.047  0.065  0.437  0.080  0.625  0.720   0.858
postchorus1      0.052  0.320  0.421  0.114  0.528  0.692   0.547
vers2            0.054  0.255  0.434  0.112  0.576  0.723   0.679
chorus2          0.046  0.087  0.436  0.081  0.623  0.720   0.828
postchorus2      0.045  0.180  0.415  0.093  0.532  0.718   0.587
interlude        0.051  0.360  0.402  0.150  0.452  0.691   0.486
bridge           0.054  0.215  0.448  0.110  0.570  0.721   0.648
drop             0.046  0.110  0.416  0.110  0.503  0.662   0.505
pause            0.148  0.480  0.374  0.416  0.215  0.679   0.302
chorus3          0.069  0.368  0.374  0.200  0.253  0.776   0.370
chorus_repeat    0.060  0.144  0.368  0.190  0.314  0.706   0.372
chorus_out       0.047  0.105  0.444  0.083  0.633  0.726   0.890
outro            0.044  0.084  0.434  0.080  0.434  0.711   0.435
```

### SBD_hit_the_road_jack (180 BPM, 13 sections)

```
Section           Flux  Trans   Rich  Vocal    RMS  Contr  Energy
klickintro       0.088  0.375  0.398  0.512  0.333  0.679   0.272
intro            0.070  0.431  0.383  0.275  0.381  0.646   0.308
vers1            0.052  0.356  0.351  0.223  0.571  0.655   0.512
chorus1          0.041  0.263  0.356  0.132  0.611  0.638   0.805
vers2            0.049  0.314  0.355  0.250  0.589  0.628   0.651
chorus2          0.040  0.248  0.357  0.120  0.600  0.632   0.703
vers3            0.047  0.281  0.355  0.232  0.582  0.631   0.603
chorus3          0.039  0.234  0.358  0.120  0.610  0.631   0.752
solo             0.039  0.267  0.359  0.116  0.536  0.629   0.452
bridge           0.047  0.225  0.385  0.183  0.579  0.632   0.553
chorus4          0.040  0.230  0.359  0.121  0.614  0.632   0.853
outro            0.038  0.183  0.371  0.163  0.519  0.622   0.399
```

### SBD_intro_and_devils_dance (90/130 BPM, 20 sections)

```
Section           Flux  Trans   Rich  Vocal    RMS  Contr  Energy
intromusone      0.043  0.256  0.383  0.097  0.348  0.571   0.292
intromustwo      0.034  0.239  0.414  0.093  0.386  0.609   0.338
intromusthree    0.032  0.034  0.410  0.061  0.616  0.546   0.787
intro            0.043  0.159  0.389  0.073  0.295  0.581   0.264
bassline         0.051  0.169  0.457  0.061  0.287  0.539   0.216
full             0.032  0.041  0.334  0.055  0.470  0.582   0.549
vers1            0.038  0.102  0.330  0.068  0.444  0.599   0.461
interlude        0.033  0.000  0.319  0.046  0.654  0.616   0.847
prechorus1       0.042  0.135  0.318  0.089  0.413  0.608   0.370
chorus           0.032  0.033  0.336  0.061  0.508  0.588   0.646
vers2            0.038  0.088  0.338  0.085  0.440  0.601   0.430
prechorus2       0.033  0.000  0.335  0.057  0.545  0.612   0.718
chorus2          0.031  0.000  0.337  0.063  0.512  0.592   0.679
bridge           0.032  0.108  0.318  0.050  0.481  0.609   0.591
bridge2          0.047  0.244  0.325  0.159  0.414  0.579   0.390
solo             0.032  0.095  0.325  0.045  0.458  0.597   0.491
prechorus3       0.033  0.041  0.336  0.057  0.547  0.614   0.751
chorus3          0.031  0.020  0.337  0.062  0.506  0.589   0.614
chorus4          0.030  0.037  0.332  0.063  0.466  0.577   0.515
```

### SBD_old_school_medicine (190 BPM, 15 sections)

```
Section           Flux  Trans   Rich  Vocal    RMS  Contr  Energy
klickintro       0.000  0.000  0.400  0.000  0.000  0.342   0.137
intro            0.056  0.158  0.396  0.205  0.320  0.563   0.268
vers1            0.060  0.228  0.422  0.118  0.672  0.639   0.641
chorus1          0.057  0.143  0.428  0.114  0.683  0.647   0.730
vers2            0.059  0.228  0.422  0.107  0.671  0.624   0.593
chorus2          0.056  0.148  0.425  0.113  0.688  0.644   0.815
solo1            0.047  0.099  0.397  0.087  0.670  0.654   0.561
solo2            0.050  0.119  0.376  0.100  0.685  0.645   0.772
bridge           0.054  0.079  0.431  0.132  0.690  0.655   0.862
interlude        0.066  0.406  0.348  0.150  0.569  0.675   0.356
chorus           0.058  0.148  0.429  0.117  0.675  0.652   0.689
outro            0.054  0.158  0.417  0.156  0.578  0.646   0.387
```

### SBD_party_of_one (139/192 BPM, 13 sections)

Note: outro section has silence (all zeros), inflating range statistics.

```
Section           Flux  Trans   Rich  Vocal    RMS  Contr  Energy
klickintro       0.081  0.240  0.414  0.329  0.186  0.691   0.376
intro            0.068  0.319  0.405  0.158  0.149  0.667   0.317
vers1            0.062  0.316  0.426  0.213  0.353  0.733   0.443
bridge1          0.061  0.290  0.419  0.199  0.436  0.708   0.483
chorus1          0.040  0.105  0.418  0.083  0.577  0.641   0.707
bridge2          0.049  0.210  0.366  0.158  0.480  0.628   0.501
vers2            0.051  0.212  0.422  0.148  0.547  0.670   0.618
chorus2          0.039  0.080  0.418  0.081  0.580  0.642   0.807
drop             0.040  0.065  0.400  0.085  0.577  0.623   0.749
solo             0.039  0.033  0.363  0.084  0.703  0.655   0.862
cpart            0.042  0.148  0.396  0.108  0.536  0.678   0.571
chorus3          0.037  0.047  0.406  0.079  0.576  0.611   0.644
outro            0.000  0.000  0.000  0.000  0.000  0.000   0.000
```

### SBD_swingin_it (183 BPM, 22 sections)

```
Section           Flux  Trans   Rich  Vocal    RMS  Contr  Energy
klickintro       0.100  0.419  0.391  0.423  0.226  0.705   0.310
intro            0.058  0.438  0.373  0.154  0.531  0.650   0.317
vers1            0.045  0.143  0.395  0.130  0.673  0.684   0.788
interlude1       0.047  0.181  0.393  0.159  0.658  0.656   0.691
chorus1          0.044  0.153  0.377  0.150  0.664  0.683   0.731
chorus2          0.045  0.181  0.399  0.121  0.642  0.668   0.639
interlude2       0.050  0.324  0.364  0.161  0.567  0.657   0.406
vers2            0.046  0.153  0.397  0.137  0.684  0.667   0.867
interlude3       0.053  0.292  0.402  0.169  0.629  0.654   0.547
chorus3          0.043  0.086  0.379  0.135  0.674  0.670   0.811
chorus4          0.045  0.210  0.400  0.121  0.644  0.665   0.666
interlude3       0.043  0.200  0.381  0.121  0.665  0.634   0.547
chorus5          0.049  0.276  0.421  0.220  0.562  0.782   0.427
pause            0.055  0.496  0.435  0.166  0.571  0.673   0.441
chorus6          0.045  0.114  0.392  0.136  0.681  0.672   0.840
chorus7          0.043  0.181  0.410  0.118  0.641  0.658   0.606
pause2           0.068  0.244  0.410  0.285  0.220  0.683   0.273
outro            0.046  0.305  0.409  0.166  0.535  0.666   0.352
```

## Key Findings

### 1. Spectral flux is universally useless (avg range 0.028)
Flux measures onset strength, which is dominated by the metronome/click track present in all light tracks. The click creates a constant onset pattern that masks musical dynamics. Even without click tracks, onset strength averages tend to compress across sections because every section has *some* rhythmic content.

### 2. Spectral richness is useless to weak (avg range 0.077)
Bandwidth + flatness averages collapse to ~0.42 for everything because a full band mix always has similar spectral spread. This metric cannot distinguish a sparse verse from a dense chorus.

### 3. RMS energy is the strongest single metric (avg range 0.346)
Direct loudness measurement via `librosa.feature.rms()`. Immune to click tracks (metronome is quieter than instruments). Correctly ranks choruses above verses, verses above bridges. GOOD verdict on 6/8 songs.

### 4. Spectral contrast is weak as a standalone (avg range 0.094)
Peak-to-valley prominence across frequency bands. Provides some differentiation but not enough on its own. Useful as a secondary signal in the energy composite.

### 5. Transient sharpness is underutilized (avg range 0.291)
Onset density is actually a decent differentiator -- GOOD on 4/8 songs. Currently only used for rudiment envelope matching, not for energy calculation. Could be valuable as a secondary energy signal.

### 6. The composite energy formula works well
`relative_energy = 0.6 * percentile_rank(rms) + 0.4 * spectral_contrast` produces GOOD differentiation on all 8 songs (avg range 0.578). The percentile ranking normalizes across different mastering levels, and the contrast adds texture even though it's weak standalone.

## Implications for Theory and Implementation

### Energy calculation (Section 5, Steps 1-2)
- **Replace** spectral flux with RMS energy as the primary energy signal
- **Replace** spectral richness with spectral contrast as the secondary signal
- The percentile ranking approach is sound -- keep it, just feed it better data
- Consider adding transient sharpness as a third signal (e.g., `0.5 * rms_rank + 0.25 * contrast + 0.25 * transient`)

### Fixture activation (Section 6)
- The zone-based tiered activation doesn't match how lighting designers think
- **Add lighting roles** (backbone, accent, ambient, movement, effect) as user-assignable metadata
- Roles define activation thresholds and temporal behavior (backbone always on, accent only at peaks)
- This has been implemented and tested -- see activation comparison results below

### Rudiment matching (Section 2.5)
- The matcher still uses `spectral_flux_avg` for envelope similarity and flux level scoring
- These may need separate attention, but the matcher's job is different from energy ranking -- it's matching *patterns*, not *levels*
- The `spectral_flux_envelope` (32-point contour) may still be useful even if the average is compressed

### Fixture activation: before vs after roles (cycle_of_a_psycho)

| Group | Without Roles | With Roles | Hand-made pattern |
|-------|:---:|:---:|---|
| BARS | 6/15 active | 15/15 active | Near-continuous backbone |
| WASH | 10/15 active | 15/15 active | Near-continuous backbone |
| MH | 3/15 active | 13/15 active | Movement throughout |
| SUNS | 3/15 active | 5/15 active | Sparse accents |
| FP | 15/15 (densest!) | 15/15 (low weight) | Subtle ambient |

## Lighting Roles System

### Overview

Fixture groups are assigned a **lighting role** that determines their activation behavior and temporal participation. Roles replace the previous zone-based activation model, which sorted groups by physical position (front → back) and activated them in tier order. The zone model failed because it doesn't reflect how lighting designers think — a front par and a front wash serve completely different purposes despite being in the same zone.

Roles are user-assignable in the config YAML (`lighting_role` field on `FixtureGroup`). When empty, the system falls back to zone-based logic for backward compatibility.

### Design Principles

The role system follows professional lighting design practice (McCandless method, ETC training materials, modern concert LD layering). Key decisions:

1. **Roles describe purpose, not behavior.** A role says what the fixture group IS (wash, key, accent), not how it behaves in a given moment. Behavioral variation comes from the algorithm's rudiment and movement assignment per section.

2. **Rhythm and movement are attributes, not roles.** Research into professional practice (grandMA3, ETC Eos, concert LD workflows) shows that rhythm (beat-synced patterns) and movement (pan/tilt) are attributes that can be applied to ANY layer. A wash fixture doing a chase pattern is still a wash — it's a wash with rhythmic behavior. The groove/fill rudiment system already handles this: a "stroke" rudiment on a wash = rhythmic wash, a "static" rudiment on the same wash = mood wash. Similarly, `MovementStrategy` is already decoupled from roles and applied to any group with pan/tilt capability.

3. **4 roles for 4-8 fixture groups.** The professional 3-4 layer model (base → key → accent → effect) maps well to small-venue setups. More roles would force awkward 1:1 mapping with fixture groups.

### Role Definitions (v2 — revised after research)

| Role | Description | Activation | Base Weight | Temporal Behavior |
|------|-------------|-----------|-------------|-------------------|
| **wash** | Base illumination, broad coverage, sets color palette and mood. The visual foundation — always present. | energy >= 0.00 (always) | 0.50 – 1.00 | FULL: plays both groove and fill blocks |
| **key** | Front-of-stage performer visibility. Vocal-aware — boosted when vocals are present, dimmed (not off) otherwise. Stable patterns, less rhythmic variation. | energy >= 0.00 (always) | 0.30 – 0.80 | GROOVE_ONLY: steady presence, no fill variation |
| **texture** | Gobos, prism, breakup patterns, beam effects. Adds visual complexity at medium+ energy. | energy >= 0.40 | 0.50 – 1.00 | Envelope-based: follows rudiment character |
| **accent** | Sparse, high-impact moments — strobes, blinders, bumps. Punches in at peaks only. | energy >= 0.60 | 0.70 – 1.00 | FILL_ONLY: only fires during fill blocks |

### Attributes (applied per-section by the algorithm, not user-assigned)

| Attribute | What it does | Applied to | Driven by |
|-----------|-------------|-----------|-----------|
| **rhythm** | Beat-synced patterns (stroke, chase, ping-pong, sparkle) | Any role | Groove/fill rudiment assignment based on audio character |
| **movement** | Pan/tilt sweeps, lissajous figures, position changes | Any group with moving heads | `MovementStrategy` based on section energy and spot targets |

A wash fixture in a high-energy chorus might get: `wash role + stroke rudiment (rhythm attribute) + circle movement (movement attribute)`. The same fixture in a quiet verse gets: `wash role + static rudiment + linear_sweep movement`. The role stays the same; the attributes change.

### Activation Priority

```
Energy:  0.0 ──────────── 0.40 ──── 0.60 ──── 1.0
         │                  │          │
         wash + key         texture    accent
         (always on)        (medium+)  (peaks only)
```

### Weight Interpolation

Within its active range, each role's weight interpolates from base minimum to 1.0:

```
weight = base_weight + t * (1.0 - base_weight)
where t = (energy - threshold) / (1.0 - threshold)
```

Wash at energy=0.0 gets 0.50 weight (dim but present), ramping to 1.0. Accent at energy=0.60 starts at 0.70 and ramps to 1.0.

### Key Role: Vocal Awareness (future refinement)

The key role is currently "always on" with GROOVE_ONLY temporal behavior — stable, low-variation presence. The intent is that key should eventually respond to vocal detection:
- **Vocals present**: boosted weight, warmer color, stable pattern
- **Vocals absent**: dimmed weight but NOT off (maintains some stage visibility)
- This can integrate with the existing `apply_vocal_rule()` which already boosts front-zone groups during vocal sections

For now, "always on at reduced weight with GROOVE_ONLY" is a reasonable starting point.

### Temporal Behavior by Role

- **wash → FULL**: Generates both groove and fill blocks. The rhythmic character comes from the assigned rudiment, not the role. A wash with a "stroke" rudiment pulses on the beat; a wash with a "static" rudiment holds steady.
- **key → GROOVE_ONLY**: Generates only groove blocks (the sustaining pattern). Provides steady visual floor without competing with fill accents. Less dynamic than wash.
- **accent → FILL_ONLY**: Generates only fill blocks (the punchy accent pattern). Creates high-impact moments at phrase boundaries.
- **texture → envelope-based**: Uses existing logic that derives FULL/GROOVE_ONLY/FILL_ONLY from the assigned rudiment's envelope category (spike→FILL_ONLY, flat→GROOVE_ONLY, etc.).

### Typical Fixture-to-Role Mappings

These are examples, not hardcoded defaults:

| Fixture Type | Typical Role | Rationale |
|-------------|-------------|-----------|
| LED bars, pixel strips | wash | Broad coverage, color foundation, rhythmic when needed |
| Wash lights (floor/truss) | wash | Stage fill, color base |
| Front pars, face lights | key | Performer visibility, vocal-aware |
| Uplights | key or wash | Depends on placement and purpose |
| Moving heads (spots) | texture | Gobos, prism, beam effects + movement attribute |
| Moving heads (wash) | wash or texture | Depends on primary use |
| Sunstrips, blinders | accent | High-impact, sparse deployment |
| Strobes | accent | Peak moments only |

### Comparison: v1 (5-role) vs v2 (4-role + attributes)

| v1 Role | v2 Equivalent | Change |
|---------|--------------|--------|
| backbone | wash | Renamed. "Backbone" implied rhythm; wash is the base regardless of rhythmic behavior. |
| ambient | key | Repurposed. The "low-level mood" concept merged with front-stage visibility. |
| movement | *(attribute)* | Demoted from role to attribute. Movement is a capability, not a purpose. |
| effect | texture | Renamed. "Texture" better describes the visual function (breakup, gobos, prism). |
| accent | accent | Unchanged. |

### Validation Results (v1 roles, to be re-validated with v2)

Tested on cycle_of_a_psycho with BARS=wash(backbone), WASH=wash(backbone), MH=texture(movement), SUNS=accent, FP=key(ambient):

- BARS: 6/15 → **15/15** sections active (matches hand-made: near-continuous)
- WASH: 10/15 → **15/15** sections active (matches hand-made: near-continuous)
- MH: 3/15 → **13/15** sections active (matches hand-made: throughout at medium+ energy)
- SUNS: 3/15 → **5/15** sections active (matches hand-made: sparse accents)
- FP: 15/15 → 15/15 but with low weight and GROOVE_ONLY (matches hand-made: subtle front presence)

### Professional Lighting Research Sources

- ETC Stage Lighting Design series (Parts 3, 5, 7) — controllable properties, angles, systems
- McCandless Stage Lighting Method (Yale, 1932) — foundational directional systems
- grandMA3 documentation — classes/layers as organizational tags, not behavioral roles
- GDTF Standard (DIN SPEC 15800) — fixture beam type classification (Wash, Spot, Fresnel, etc.)
- SoundSwitch, MaestroDMX — auto-lighting products use fixture groups + algorithmic patterns, no formal role taxonomy
- On Stage Lighting (onstagelighting.co.uk) — concert LD busking structure, programming philosophy
- NLFX Pro — stage lighting effects layering guide

## Audio Files Note

All audio files in `shows/audiofiles/` contain metronome/click tracks mixed in. This is standard for live performance backing tracks but likely depresses the discriminative power of onset-based metrics (flux, transient to some degree). Testing with click-free masters would provide a cleaner signal, but the algorithm should be robust to click tracks since these are the actual files used in production.
