# Live Mode — Patch / Rework Backlog

Items uncovered while reading `live/`, `audio/live_*`, `audio/realtime_spectral.py`,
and the menu wiring in `gui/gui.py`. Energy-fader wiring (#1) is already fixed.

---

## 1. Energy fader was a one-shot — DONE

`EnergySensitivityFader.sensitivity_changed` was emitted but never connected.
`LiveShowEngine.set_energy_sensitivity()` was only called once on Start.
Now wired to `_on_energy_sensitivity_changed` in `live/window.py`.

---

## 2. Auto-fill heavy interrupt removed — DONE

The heavy-RMS auto-trigger fired far too often during shows. Removed entirely:
`_heavy_threshold`, `_last_heavy_time`, `set_heavy_threshold`, the check in
`on_feature_frame`, and `_trigger_heavy_interrupt` are gone from `live/engine.py`.
Manual FILL NOW button is unaffected.

---

## 2b. Twitchy 0/1 metric readout — DONE

Root cause: `_EMANormalizer` in `audio/realtime_spectral.py` updated *both*
`running_min` and `running_max` toward the current value with the same alpha,
so the range collapsed to ~`1e-10` and every value clipped to 0 or 1.

Fix: replaced with an envelope follower (fast attack on new peaks/troughs,
slow decay back). Default decay raised 3 s → 15 s so the dynamic-range
estimate spans a section, not a transient. Added `_OutputSmoother`, a single-
pole low-pass (~600 ms) on the normalised output of every metric, so emitted
values have gradual curves for both the UI readout and the engine's
window-mean calculations.

---

## 3. `_on_riffs_updated_from_engine` is cross-thread without a signal

**Where:** `live/window.py:556-559`. Engine calls the callback from the DMX thread;
the window stores it in `self._pending_riff_update` and reads it from the 20 Hz UI tick.

**Problem:** Works in practice (GIL + Python attr writes) but not strictly safe.
A `pyqtSignal(object)` would be the canonical fix, and would also let us drop the
`_pending_riff_update` attribute.

**Proposed fix:** Add `riffs_updated = pyqtSignal(object)` to `LiveModeWindow`,
wire `_on_riffs_updated_from_engine` to `emit()`, connect signal to the existing
update logic in `_update_ui`.

---

## 4. `_update_ui` takes the engine lock five times per tick

**Where:** `live/window.py:578-588`. Each property access (`bpm`, `current_bar`,
`is_fill`, `current_groove_name`, `groove_bars`) acquires `_lock`.

**Problem:** Minor — 100 lock acquires/sec is fine. Worth tidying for readability.

**Proposed fix:** Add an `engine.snapshot()` method returning a small dataclass
(`bpm, bar_index, total_bars, is_fill, groove_name`) under one lock acquire.

---

## 5. Centroid "denormalization" in `_build_window_profile` was fake Hz — DONE

**Symptom:** Live shows trended toward a bluish hue regardless of music.

**Root cause:** Engine multiplied the *normalized rank* of centroid by 8000.
The envelope-follower normalizer maps centroid into a 0-1 rank that converges
around 0.5 over a 45 s window for typical signals → `spectral_centroid_avg`
≈ 4000 Hz → `hue = 0.5 * 0.8 = 0.4` → cyan/blue, every cycle.

**Fix:** Added `centroid_hz: float` to `LiveFeatureFrame` (raw Hz, unnormalized,
unsmoothed). `_build_window_profile` now uses `mean(centroid_hz_vals)` directly
for `spectral_centroid_avg`, matching the offline pipeline's units.

The normalized `frame.centroid` is unchanged — UI meter and metrics chart still
display the rank.

---

## 6 + 7 + 9. Session persistence + visualiser-mirror toggle — DONE

New module `live/settings.py` — `LiveModeSettings` dataclass + load/save against
`~/.qlcautoshow/live_mode_settings.json` (matches the convention already used
by `audio/waveform_analyzer.py`). Load on window construction, save on
`closeEvent`. Persists: target IP, universe map, input device (by name),
mirror-to-visualiser toggle, BPM, groove bars, energy sensitivity, target
plane, max movement speed, color override (active + hue + saturation),
per-group constraints, per-group submasters.

Added "Mirror to visualiser broadcast" checkbox in the ArtNet panel — wired
to `LiveDMXController.set_mirror_to_visualizer()` both at controller construction
and live during a running session. Default still on.

The IP field's `editingFinished` signal now calls `set_target_ip()` on the
running controller so edits apply without stop/start.

Public widget setters added so window.py doesn't poke privates:
`HSVColorWheel.set_state`/`get_hue_saturation`,
`GroupRiffConstraintPanel.set_constraint`/`get_constraints`,
`EnergySensitivityFader.set_value`,
`GroupSubmasterPanel.get_values`.

---

## 8. `_select_next_riffs` runs on the DMX thread

**Where:** `live/engine.py:312` — `_start_new_cycle()` calls `_select_next_riffs()`,
which runs `match_rudiments_to_section` + `select_rudiments_per_group`. Both
called from `tick()` on the DMX thread, with `_lock` held.

**Problem:** Matcher scoring isn't free; bar-boundary lock-hold can stall the
UI's property reads and the analysis thread's `on_feature_frame` append. With
many groups and tight BPMs this could occasionally dent DMX timing.

**Proposed fix:** Either (a) precompute the next cycle's selection on the
analysis thread between bars and hand the result over via a queue, or (b)
release `_lock` around the matcher call (snapshot the inputs, call matcher
unlocked, re-acquire to assign results). (b) is the smaller refactor.

