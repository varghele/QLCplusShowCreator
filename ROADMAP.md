# Roadmap

Themed milestones. Order within a milestone is rough; order *across* milestones is roughly chronological. Estimates are intentionally absent: this is a hobby project and shipping dates would lie. Numbered items link to working backlog files where applicable.

If you want to influence the order, open an issue or pick something up.

---

## v1.0 - first community release (current focus)

What's left before the version on `main` is tagged `v1.0`.

- [ ] Merge the `v1.0.5-fixture-rewrite` branch into `main`.
- [ ] Replace the in-repo `voll_mit_vox_*` audio + `shows/renders/` material with a small distributable demo show set. Local working-tree litter is already suppressed via `.gitignore`.
- [ ] **Sequence-step compaction in the QLC+ exporter.** Profiling `workspace_generated.qxw` (41.85 MiB) shows 44.1% of all `(fixture, channel, value)` triples are zero-valued and are emitted unconditionally. QLC+'s own saver (`engine/src/chaserstep.cpp::saveXML`) skips zeros and the loader treats absent channels as zero, so dropping them is byte-identical playback. Expected file shrink: ~30% (41.85 MiB to ~29.5 MiB). Change site: `utils/to_xml/unified_sequence.py` per-fixture value emission. A coarser time-grid for static lanes is the bigger structural win and slips to v1.1.
- [ ] **QLC+ target-version stamp** in the Workspace Options dialog. The XML schema is *unchanged* between QLC+ 4.x (4.14.4) and 5.x (5.2.1): stock `Sample.qxw` and `engine/src/doc.cpp` are byte-identical between those tags. The selector therefore only stamps `<Creator><Version>` so QLC+'s built-in compat banner doesn't fire on import.
- [ ] **Runtime verification in actual QLC+ 4.14.4 and 5.2.1.** Open the same exported `.qxw` in both, confirm functions populate, virtual console renders, sequences play, fixtures are patched correctly. Manual step; no headless harness for the QLC+ binary.
- [ ] **CI / release pipeline.** GitHub Actions on tag push (`v*`): `windows-latest` PyInstaller build via the existing `qlcshowcreator.spec`, `ubuntu-latest` build with `portaudio19-dev` + GL deps installed at build time. Artifacts attached to a draft GitHub Release. Smoke-test the Linux build path on a clean container first (the spec has only been used on Windows).
- [ ] Virtual-console export positioning, known to be not bug-free (carried over from the v0.9.5 notes).
- [ ] Screenshots + a short demo video for the README.

---

## v1.1 - Stage tab and rig data

The Stage tab models a flat rig today. Two practical problems hurt real-world use: you can't put two fixtures above each other, and there's no way to move a rig between projects without retyping every DMX address.

- [ ] **Stage layers (vertical stacking).** Multiple Z-planes per stage (e.g. ground stack, mid-truss, top-truss). Per-layer visibility toggle on the Stage tab, layer assignment per fixture, and consistent treatment in the 3D visualizer. Today the Z coordinate exists on `Fixture` but the 2D Stage tab collapses it, so two PARs at the same X,Y on different trusses overlap unrecognisably.
- [ ] **Fixture list import / export.** Round-trip a rig as CSV or JSON (manufacturer, model, mode, universe, address, group, position, orientation). Use cases: send the patch to QLC+ users on a different rig, pre-fill a stage from a venue's spec sheet, version-control just the rig without the whole show. The serializer already deduplicates fixture definitions, so the export format can reference QLC+ library entries by name.
- [ ] **Stage plot export.** Currently the toolbar action exists but is non-functional. Wire it to a PDF / PNG export of the 2D stage with fixture symbols, group colour, DMX address, universe, layer, and orientation tick. The "stage plot" that touring engineers hand to the venue. Expect this to be a chunk of work on its own (label collision avoidance, multi-layer legend, scale + dimensions, paper-size presets) which is why it slips from v1.0 to here.

---

## v1.2a - Stage-relative movement (focus geometry)

Today, moving-head pan / tilt is stored as raw DMX values (or normalised 0-1 equivalents). That breaks the moment the fixture moves an inch: the values point at empty air. It also blocks morphing entirely, because any new rig will have fixtures in different positions and the pan / tilt numbers carry no meaning across rigs.

v1.2a reworks how movement is authored and stored so that focus is geometric, not arbitrary.

- [ ] **World-space targets on `MovementBlock`.** A movement block stores a stage position (X, Y, Z in metres) or a named spot, not pan / tilt numbers. Static positions, paths (circle / figure-8 / lissajous / sweep), and named-spot sequences are all expressed in stage coordinates.
- [ ] **Per-fixture pan / tilt resolution at playback / export.** Given a fixture's position and orientation (yaw / pitch / roll, mounting) and the target world-space point, compute the pan / tilt DMX values via inverse kinematics. The `orientation.py` utilities already do half of this for the visualizer; the export pipeline needs the same path.
- [ ] **Named spots as first-class authoring primitives.** The data model already has a `spots: Dict[str, Spot]` on `Configuration` (used today only by autogen). Promote it to the timeline: "point movers at SPOT_LEAD_VOX" instead of "pan=127, tilt=200" so a show is readable independent of any rig.
- [ ] **Migration path for existing shows.** Existing `MovementBlock` data is pan / tilt. Provide an in-app converter that snapshots the current rig, traces where each beam lands, and rewrites the block to the world-space equivalent.
- [ ] **Authoring UX.** Picking a target in the Stage tab or the embedded visualizer (click on the stage, get a world-space point) rather than dialling pan / tilt sliders. Sliders stay as a fallback.
- [ ] **Calibration helper.** For a brand-new venue, the operator points each moving head at a known reference (centre stage, downstage-left corner) and the app derives the fixture's effective orientation so the rest of the show's spots resolve correctly.

This is foundational for v1.2b but useful on its own, even without morphing. It is the difference between "redo every movement cue after every rig change" and "the focus is correct once the stage is correct".

---

## v1.2b - Show morphing (venue adaptation)

With v1.2a in place, focus is portable. v1.2b tackles the rest: lane retargeting, type substitution, group remapping. The mechanics are the smaller half. The bigger half is figuring out *what a show even is* in a way that survives a rig change.

### Open questions

- **What rig do you author the first show on?** A maximal "reference rig" (PARs + washes + movers + bars + specials) so every venue is a subset? A "minimal viable rig" (just PARs and washes) so every venue is a superset? Or the actual rig you happen to own, with morphing assumed to lose detail in either direction?
- **What transfers, and what doesn't?** Structure, BPM, transitions, section markers obviously transfer. Riffs probably transfer (they're abstract patterns). Movement transfers via v1.2a. Colour transfers. Special effects (gobo index, prism on) need a per-rig opinion. Need a tier-list of "always transfers / transfers if compatible / always re-authored".
- **How do you handle missing fixture types?** Venue has no moving heads, but the show has a movement lane on the chorus. Options: drop the lane entirely, demote it to a static colour wash on a substitute group, redirect to a pixel bar's per-cell chase, or flag it for the user to resolve. Probably some combination triggered by the lane's "importance" tag (which doesn't exist yet and would need to).
- **How do you handle *extra* fixture types?** Venue has eight movers when the show was authored for two. Mirror them? Spread the pattern? Leave the extras dark and let the user fill them in? Same question for pixel matrices added on top of a PAR-only show.
- **Is there a baseline a show can declare?** A show could carry a "minimum requirements" manifest (this many washes, this many movers, these capabilities) so morphing to an undersized rig becomes an explicit error rather than a silent degradation. Similar in spirit to a media query.

### Likely shape (subject to the questions above)

- [ ] **Lane retargeting by role.** Lanes already target groups; the morph pass remaps group definitions to whatever fixtures in rig B fill the same role.
- [ ] **Capability-based fixture substitution.** Moving wash substitutes for a moving head minus the gobo / prism blocks, PAR substitutes for a wash, etc.
- [ ] **Show requirements manifest.** Declarable "minimum rig" the morph engine validates against.
- [ ] **Per-lane importance tier.** Tells the morph pass what to drop first when the target rig is undersized.
- [ ] **Morph report.** Same shape as autogen's `GenerationReport`: every retarget, substitution, dropped block, with reasons. Editable post-hoc.
- [ ] **Side-by-side preview.** Original show on rig A vs. morphed show on rig B in the embedded visualizer, scrubbable, before the user commits.

Depends on v1.1 (stable groups / roles, fixture-list import-export) and v1.2a (focus survives rig changes).

---

## v1.3 - Live operations and clock sync

A show that runs from a button press is fine until the band restarts the song, the bassist breaks a string, or the singer holds a note three bars long. Today the playhead is fire-and-forget. v1.3 adds the operator-side surface and the clock plumbing.

- [ ] **Live tab** for the show operator. Not the same as Auto Mode (which generates lighting); this tab is the runtime view for an authored show. Goals:
  - Big visible playhead, current section, next section, bars remaining in the current part.
  - Per-show start / pause / restart / next-cue / previous-cue buttons.
  - Queue list of cue points the operator can jump to mid-song.
  - "Hold" button that pauses the timeline at a bar boundary until released (for unscripted pauses).
  - Manual nudge (+/- one bar, +/- one beat) to recover from drift without rebuilding the show.
  - Visible link status: ArtNet output, MIDI clock, audio device.
- [ ] **MIDI clock input (slave mode).** Backing track or DAW sends 24 PPQ MIDI clock; the playback engine follows. Handles tempo changes, start / stop / continue messages, and song-position pointer. This is the answer to "what happens when we restart the song" and "what if the band lags": the playhead stays locked to whatever's driving the audio.
- [ ] **MIDI clock output (master mode).** Show Creator emits clock so a connected DAW or backing-track rig can chase the show. Useful when lighting is the master tempo source.
- [ ] **MTC (MIDI Time Code) support** as a fallback for environments without MIDI clock.
- [ ] **Tempo-map handling.** Real songs aren't a single BPM. The Live tab and the clock-sync code need to honour the per-part BPM already in the structure data, including transitions.
- [ ] **Persistence of operator state.** If the app crashes mid-set, the next launch resumes at the last known cue position, not from bar 0.

---

## v1.4 - Autogen polish

The automatic show generator runs end-to-end today, but the matcher is a black box. This milestone makes it *legible* so the algorithm can be tuned with evidence rather than guesswork. Source: `v1_theory_and_implementation_plan/autofuture.md`.

- [ ] **Decision logging system.** Every rudiment considered, its score breakdown, why one was picked, why iterative selection stabilised. Exportable as a Markdown report alongside the generated show.
- [ ] **Generation Inspector UI pass.** The dialog exists and the `GenerationReport` already carries the data; the v1.4 work is to make it interactive (click a generated block, see why), surface the colour palette decisions, and add a side-by-side "what changed when I tweaked this parameter" view.
- [ ] **Colour palette presets** in the autogen dialog. The API supports preset palettes but the UI only exposes the audio-derived path.
- [ ] **Matcher tuning.** Once the inspector exists, revisit the scoring weights for envelope similarity vs. repetition rate fit vs. coherence.
- [ ] **Per-section overrides.** Let the user lock a specific rudiment or role for a named section before re-running generation, instead of editing the output.

---

## v1.5 - Auto Mode hardening

Auto Mode (live audio-reactive) works but is labelled "experimental" for real reasons. Source: `todo/auto_mode_patches.md`.

- [ ] **Cross-thread signal cleanup.** `_on_riffs_updated_from_engine` is called from the DMX worker thread and currently goes through an atomic-capture-and-clear into a pending slot. Replace with a queued `pyqtSignal(object)` so Qt's event loop handles the hand-off, same pattern already used by `EmbeddedVisualizer._dmx_frame`.
- [ ] **Engine snapshot API.** The 20 Hz UI tick currently acquires the engine lock five times per frame (one per property read). Add `AutoShowEngine.snapshot()` returning a dataclass under a single lock acquire.
- [ ] **Move matcher work off the DMX thread.** `_select_next_riffs` runs inside the DMX-tick lock; the matcher's scoring can dent timing at bar boundaries with many groups + tight BPMs.
- [ ] **First-class ASIO control panel.** When the user picks an ASIO host API, surface a button that launches the driver's panel via `sd.asio.show_control_panel(device_id)`, hide the misleading buffer-size + sample-rate controls, and handle exclusive-access errors when another DAW has the device open.
- [ ] **Persisted Auto Mode profiles.** Colour overrides, BPM, per-group constraints, plane bias as a named profile so a busking set can be set up once and recalled.

---

## v1.6 - Visualizer breadth

Round out the composable renderer to cover the fixture types that currently fall back to a generic point. Source: `docs/fixture_taxonomy.md` §1.4 and §4.

- [ ] **`MOVING_BAR` chassis silhouette.** Fixtures like Ayrton MagicBlade-R are correctly detected as "moving cell bar" today but render with a yoke silhouette. Add a dedicated chassis variant.
- [ ] **Particle plumes** (hazer, smoke, fan). `ParticlePlumeRunner` is stubbed; the renderer needs a billowing-volume shader.
- [ ] **Laser vector rendering.** `LaserVectorRunner` stub exists. Vector path / pattern channels need a beam-line shader rather than a cone.
- [ ] **Scanner archetype.** Mirror-based beam steering, geometrically distinct from a moving head.
- [ ] **Effect / flower fixtures.** Centipede, derby, sweeper, butterfly. Multi-beam fixed-pattern.
- [ ] **Strobe.** Currently renders as a steady PAR; wants a high-frequency emission path.
- [ ] **Floor projection for non-MH beams.** Currently only moving heads get a projected spotlight.

---

## v2.0 - Algorithmic generation v2

The bigger autogen rethink. Out of scope for v1.x. Tracked in `v1_theory_and_implementation_plan/theory-algorithmic-show-generation.md`.

- [ ] **Rolling-window analysis for prepared mode.** Currently each section is scored in isolation; v2 looks across section boundaries to keep transitions coherent.
- [ ] **Multi-pass generation.** First pass picks rudiments per section, second pass adjusts for cross-section diversity / repetition penalties.
- [ ] **Story arcs.** Explicit "build", "release", "false climax" annotations on the song structure that the generator respects.
- [ ] **Operator-trainable matcher.** When the user replaces a generated block, log the substitution and use it as training data for the matcher's weights.
- [ ] **Auto Mode parity.** Collapse the prepared / live distinction so the same engine drives both, with prepared mode just being a recorded analysis pass.

---

## Out of scope (for now)

These come up periodically and the answer is "not yet, but not no":

- **Custom fixture-definition editor in-app.** Authoring `.qxf` files belongs in QLC+ itself.
- **OSC input/output** beyond ArtNet. No demand yet.
- **Web UI / remote control.** The app is Qt-native by design.
- **Live console mode** (no prepared show, no Auto Mode, just a mappable surface). Possibly v2.x.

---

## How to follow along

- The current working branch is `v1.0.5-fixture-rewrite`.
- Issues and progress live on GitHub (link in README once the repo is published).
- The `todo/` and `v1_theory_and_implementation_plan/` directories are the working backlog: they're more detailed than this roadmap and update faster.
