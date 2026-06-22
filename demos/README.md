# Demo rigs

Reproducible, standard stage-lighting rigs for testing and as starter
projects. Each is a `Configuration` YAML under `rigs/`, generated
deterministically by [`generate_rigs.py`](generate_rigs.py).

Open one via **File → Open Configuration** (or load it in a test).

## Why these load anywhere

The rigs reference **only** the fixtures bundled in `custom_fixtures/`, so
they patch, classify, and render identically on any machine — no dependency
on the user's QLC+ install. (The stock QLC+ *Generic* manufacturer folder has
no moving heads, beams, strobes, or pixel bars, so it can't express these
layouts at all.)

## The rigs

| File | Fixtures | Shape | Exercises |
|------|---------:|-------|-----------|
| `club_band.yaml` | 9 | 4 front PARs, 2 rear washes, 2 movers, 1 blinder | Smallest viable rig; fast load path |
| `band_midsize.yaml` | 21 | Front/back PARs, spots, moving wash, LED bars, blinders, matrix | Every `lighting_role`; all four sublane types |
| `festival_mainstage.yaml` | 60 | Front-wash / mid-spot / back-beam truss rows, floor beams, blinders, matrix, side towers | Rows-of-movers look; multi-universe (3) export scale; visualizer archetype breadth |
| `dj_edm.yaml` | 20 | Beam array, moving wash, pixel bars, matrix, strobes | Movement-centric; matrix/beam chassis paths |
| `theatre_static.yaml` | 16 | Front PAR wash, rear cyc wash, side booms | Zero-movement export + capability detection |

## Coordinate convention

`X` left→right `[-W/2, +W/2]`; `Y` depth, **centred** (`y<0` downstage/front,
`y>0` upstage/back); `Z` height in metres. Truss fixtures sit overhead
(`z` ≈ 3–8 m), floor packages near `z≈0.2`.

## Regenerating

```sh
python -m demos.generate_rigs
```

Edit the `RIGS` table in `generate_rigs.py` to add or reshape a rig. Modes and
channel counts are read live from the `.qxf` files, so DMX addressing and
`available_modes` stay correct automatically. The generator auto-rolls to a new
universe at the 512-channel boundary.
