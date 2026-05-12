# Auto Mode — Open Patch Backlog

Successor to `live_mode_patches.md` after the May 2026 rename
(`live/` → `auto/`, `LiveTab` → `AutoTab`, etc.). The closed items
have been removed; what remains here are the still-relevant proposals
with updated paths.

For historical context on the closed items (energy fader wiring,
auto-fill removal, EMA normalizer fix, centroid fake-Hz bug, settings
persistence, etc.) see commit history around 2026-04 / 2026-05.

---

## 1. `_on_riffs_updated_from_engine` is cross-thread without a queued signal

**Where:** `gui/tabs/auto_tab.py::_on_riffs_updated_from_engine` (stores
into `self._pending_riff_update`, drained by the 20 Hz UI tick).

**Problem:** The engine calls this callback from the DMX worker thread.
The current implementation does an atomic capture-and-clear in
`_update_ui` (the local-ref-then-null pattern landed during the May 12
audit), which is good enough to avoid lost writes, but it's not the
canonical Qt pattern. A queued `pyqtSignal(object)` would let us drop
`_pending_riff_update` entirely and have Qt's event loop schedule the
update on the main thread.

**Proposed fix:** Add `riffs_updated = pyqtSignal(object)` to `AutoTab`,
emit from `_on_riffs_updated_from_engine`, connect with
`Qt.ConnectionType.QueuedConnection` to a slot that calls
`self._riff_constraints.update_active_riffs(...)`. Mirrors the same
pattern now used by `EmbeddedVisualizer._dmx_frame`.

---

## 2. `_update_ui` takes the engine lock five times per tick

**Where:** `gui/tabs/auto_tab.py::_update_ui` reads `engine.bpm`,
`engine.current_bar`, `engine.is_fill`, `engine.current_groove_name`,
`engine.cycle_bars` — each property acquires `auto/engine.py`'s
`_lock` independently. 100 lock acquires/sec is fine in absolute
terms, just untidy.

**Proposed fix:** Add `AutoShowEngine.snapshot()` returning a small
dataclass (`bpm`, `bar_index`, `total_bars`, `is_fill`, `groove_name`)
under one lock acquire. UI tick calls `snapshot()` once and reads the
fields locally.

---

## 3. `_select_next_riffs` runs on the DMX thread with `_lock` held

**Where:** `auto/engine.py::_start_new_cycle` (called from `tick()` on
the DMX thread, inside `with self._lock`) invokes
`match_rudiments_to_section` and `select_rudiments_per_group`. Both
do non-trivial scoring work over the rudiment registry.

**Problem:** The lock-hold during matcher scoring blocks both the UI's
property reads and the analysis thread's `on_feature_frame`
appendwindow.append. With many groups + tight BPMs this could
occasionally dent DMX timing at a bar boundary.

**Proposed fix:** Either

(a) precompute the next cycle's selection on the analysis thread
    between bars and hand the result over via a `queue.Queue`; or
(b) release `_lock` around the matcher call: snapshot the inputs under
    the lock, run the matcher unlocked, re-acquire to assign results.

(b) is the smaller refactor.

---

## 4. First-class ASIO control panel + exclusive-access handling

**Where:** `gui/tabs/auto_tab.py` (audio input section) — when the user
selects an ASIO host API, the existing buffer-size and sample-rate
controls become misleading (ASIO sets those from the driver's own
control panel, not the application).

**Problem (deferred for now):** Once the user has a Focusrite or other
ASIO interface plugged in and ASIO appears as a host API, we want:

- A button that launches the ASIO driver's control panel via
  `sd.asio.show_control_panel(device_id)` so the user can adjust
  buffer size there.
- A status message "buffer size is controlled by the ASIO driver
  panel" when ASIO is selected, replacing the sample-rate / buffer
  controls.
- Graceful error handling for exclusive-access failures (other DAW
  has the ASIO device open).
- Optional `sd.AsioSettings(channel_selectors=[…])` UI for picking
  specific channels of a multichannel interface.

Out of scope until we can test against a real ASIO interface end-to-end.
