# UI Modernization Plan

## Context

The app currently opens at a fixed 1250×900 floating window with per-widget inline styling, separately scrolled timeline regions in the Shows tab (Master / Audio / Lanes — three independent QScrollAreas synced via signals so columns don't actually align), tables that look like default Qt, and a 3D visualizer that is only available as a launched subprocess. The user wants:

1. Maximized startup tuned for a PC display.
2. A small embedded visualizer in the Shows tab and Stage tab so they can preview lighting/orientation without a separate window — the standalone subprocess + TCP/ArtNet path stays for QLC+ interop. In Stage tab, while no show is playing, fixtures should render with all DMX channels at full so the user can actually see what they are positioning.
3. Selectable light + dark themes (not a single unified theme), persisted across sessions.
4. A unified timeline grid in the Shows (and Structure) tab so the master ruler, audio waveform, and light lanes share one horizontal scrollbar and one column of headers — no more triple scrollbars / drift.
5. A modernized audio player widget.
6. Live Mode folded in as a tab (today it's a separate `QMainWindow` opened from `Live > Open Live Mode... (Ctrl+L)`), so the user doesn't have to track a second window.

## Shape of the change

```
                           ┌───────── MainWindow (maximized) ─────────┐
                           │                                          │
                           │  toolbar (status pills + actions)        │
                           │  ┌──────────── tabs ────────────────────────┐ │
                           │  │ Cfg │ Fix │ Stage │ Struct │ Shows │ Live │ │
                           │  └─────┬──────────┬─────────┬─────────┬──────┘ │
                           │        │          │         │           │
   global theme.qss ───────┼──► applied once via app.setStyleSheet   │
                           │        │          │         │           │
                           └────────┼──────────┼─────────┼───────────┘
                                    │          │         │
                Stage tab                      │         │           Shows tab
       ┌──────────┴───────────────┐            │         │   ┌──────────┴──────────┐
       │ ctrls │  StageView (2/3) │ vis + orient (1/3)   │   │ TimelineGrid (NEW)  │
       │       │  2D top-down     │ ┌──────────────────┐ │   │  ┌────────────────┐ │
       │       │  building        │ │ EmbeddedVisualizer│ │   │  │ master ruler   │ │
       │       │  (full-on lights │ │ (mini)            │ │   │  │ audio waveform │ │
       │       │   in vis when    │ ├──────────────────┤ │   │  │ light lane 1   │ │
       │       │   not playing)   │ │ OrientationPanel │ │   │  │ light lane 2   │ │
       └───────┴──────────────────┘ └──────────────────┘ │   │  └────────────────┘ │
                                    │          │         │   │  one shared HScroll │
                                    ▼          ▼         ▼   │  + side dock: mini  │
                            EmbeddedVisualizer ◄── feeds ──► │    visualizer       │
                            (RenderEngine widget,            └─────────────────────┘
                             reused by both tabs;
                             fed by VisualizerFeed)
                                  ▲
                                  │ in-process
                       ShowsArtNetController ──► VisualizerFeed.broadcast_dmx(uni, bytes)
                                  │
                                  └────► (separately, still serves TCP/ArtNet to standalone)
```

## 1. Maximized startup

- `main.py:42-43`: replace `window.show()` with `window.showMaximized()`.
- `gui/Ui_MainWindow.py:10`: drop the hard `MainWindow.resize(1250, 900)` (or keep as a fallback for first non-maximized restore — set to 1600×1000).
- `gui/Ui_MainWindow.py`: add `View` menu with a `Toggle Fullscreen` action (F11) that switches between `showMaximized` and `showFullScreen`, wired in `gui/gui.py::_connect_signals`.

## 2. Selectable themes (light + dark)

- New files:
  - `resources/themes/dark.qss` — dark theme covering `QMainWindow`, `QToolBar`, `QTabWidget::pane`, `QTabBar::tab`, `QPushButton` (primary/secondary/destructive variants via `[role="primary"]` dynamic properties), `QTableView`/`QHeaderView` (rounded corners, alternating rows, no harsh gridlines), `QLineEdit`, `QComboBox`, `QSpinBox`, `QSlider`, `QScrollBar`, `QGroupBox`, `QStatusBar`, `QMenu`/`QMenuBar`. Pulls existing accent palette (greens `#4CAF50`, blues `#2196F3`, reds `#f44336`, neutrals `#2d2d2d`/`#3d3d3d`).
  - `resources/themes/light.qss` — same selectors and structure, light surface palette (e.g. `#fafafa`/`#ffffff` panels, `#e0e0e0` borders, `#222` text), same accents so green/blue/red status meanings carry over.
  - `gui/theme_manager.py` — `ThemeManager`:
    - `available_themes() -> ["dark", "light"]`
    - `apply(app, name)` — loads `resources/themes/{name}.qss`, calls `app.setStyleSheet(...)`. Then iterates top-level widgets and calls `style().unpolish(w); style().polish(w)` so dynamic-property styling (status pills, primary buttons) re-evaluates.
    - `current()` / `set_current(name)` persists via `QSettings("QLCShowCreator", "QLCShowCreator")` under key `ui/theme`.
- `main.py` (after `QApplication(sys.argv)`): `ThemeManager().apply(app, ThemeManager().current() or "dark")`.
- `gui/Ui_MainWindow.py` / `gui/gui.py`: add `View > Theme` submenu with a `QActionGroup` of mutually exclusive radio actions (Dark, Light) wired to `ThemeManager.apply` + `set_current`. Also expose in `Settings` menu for discoverability.
- Theme-aware widget code: anywhere code currently hard-codes colors that need to flip with theme (e.g. the time display `color:#0f0; background:#333` in `shows_tab._create_playback_controls`, group default gray `#808080` in `fixtures_tab`), switch to QSS classes (`time_label.setObjectName("TimeReadout")`) so each theme file defines them differently. Hard-coded data colors (group color tints, song-part colors) stay as-is — they're data, not chrome.
- Strip the now-redundant inline `setStyleSheet` blocks from:
  - `gui/Ui_MainWindow.py:65-77, 94-105` (status pills — keep dynamic ON/OFF colors via dynamic properties + `style().polish()` instead of full re-sheet rewrites in `gui/gui.py:67-162`).
  - `gui/tabs/shows_tab.py:196-280, 290-336` (toolbar + transport buttons).
  - `gui/tabs/structure_tab.py:212-283` (add/delete/structure header).
  - `timeline_ui/audio_lane_widget.py:93-99, 154-209, 222-238` (frame, file path, mute, volume slider).
  - `timeline_ui/light_lane_widget.py:61-67, 128-153, 166-189` (frame, name, remove button).
  - Tables — replace `setStyleSheet` blocks at `gui/tabs/structure_tab.py:276+`, `gui/tabs/configuration_tab.py` with QSS `QTableView` rules.
- Keep dynamic-state styles (mute checked, group row colors in `fixtures_tab._update_row_colors`, color-picker preview in `structure_tab.ColorButton`) — those are data-driven, not theme.

## 3. Tables polish (Fixtures + Configuration)

- New helper `gui/widgets/modern_table.py` with `apply_modern_table_style(table)`:
  - `setShowGrid(False)`, `setAlternatingRowColors(True)`, `verticalHeader().setVisible(False)`.
  - `setSelectionBehavior(SelectRows)`, `setSelectionMode(SingleSelection)` where applicable.
  - Default row height ≈ 32 px; header height ≈ 36 px with bold, slightly muted text.
  - Padding via QSS (delegated to theme.qss `QTableView::item { padding: 6px 10px; }`).
- Apply in `fixtures_tab._setup_table` (line 138) and `configuration_tab.setup_ui` (line 94).
- Group row tinting (existing logic in `fixtures_tab._update_row_colors`) keeps working — it sets `item.setBackground(color)` which overrides QSS at the item level.

## 4. Embedded mini-visualizer (Stage + Shows)

### Reusable widget

- New file `gui/widgets/embedded_visualizer.py` defining `EmbeddedVisualizer(QWidget)`:
  - Wraps a `visualizer.renderer.RenderEngine` (already a `QOpenGLWidget`, see `visualizer/renderer/engine.py:19`) directly in-process.
  - Holds a reference to the active `Configuration` and refreshes via `set_config(config)` → calls `engine.set_stage_size`, `engine.set_grid_size`, and `engine.update_fixtures(...)`.
  - Provides a `feed_dmx(universe: int, dmx_bytes: bytes)` slot that calls `engine.update_dmx(universe, dmx_bytes)`.
  - Toolbar row (compact): `Reset Camera`, `Pop Out` (launches the standalone visualizer subprocess via existing `stage_tab._launch_visualizer`), `FPS` label.

### Fixture-data helper (no TCP round-trip)

- Add `build_fixtures_payload(config) -> list[dict]` in `utils/tcp/protocol.py` next to the existing `create_fixtures_message` (line 644) — extract the dict-building it already does so we can call it without JSON encode/decode. Then have `create_fixtures_message` reuse the new helper. Embedded visualizer calls `build_fixtures_payload(config)` directly.

### Live DMX bridge

- Add a `VisualizerFeed` (a `pyqtSignal(int, bytes)`) on `ShowsTab` (or a tiny new `gui/widgets/visualizer_feed.py`).
- In `utils/artnet/shows_artnet_controller.py::_send_all_universes` (line 439): after sending the ArtNet packet, also emit/forward the universe id + bytes. Implementation: accept an optional `local_dmx_callback: Callable[[int, bytes], None]` in `ShowsArtNetController.__init__` and invoke it inside `_send_all_universes`. ShowsTab wires the callback to the embedded visualizer instances. This adds zero overhead when the callback is `None`.
- The standalone visualizer continues to receive DMX via ArtNet exactly as today — both paths run from the same `_send_all_universes`.

### Stage tab integration

- `gui/tabs/stage_tab.py::setup_ui` (line 43): replace the current `[control_panel | stage_view_container]` layout with a top-level `QHBoxLayout` of `[control_panel | main_splitter]` where `main_splitter` is a `QSplitter(Qt.Horizontal)` set to ~2:1:
  - **Left pane (≈2/3)**: the existing `StageView` — 2D top-down stage building.
  - **Right pane (≈1/3)**: a `QSplitter(Qt.Vertical)` stacking `EmbeddedVisualizer` (top) and `OrientationPanel` (bottom). Initial split ≈ 60 / 40.
  - Use `splitter.setStretchFactor(0, 2); setStretchFactor(1, 1)` and persist sizes via `QSettings` (`stage/main_splitter`, `stage/right_splitter`).
- "Build mode" full-on preview: when the Stage tab is active and no playback is running, the embedded visualizer should show every fixture lit so the user can see what they're positioning.
  - `gui/widgets/embedded_visualizer.py::EmbeddedVisualizer` exposes a `set_preview_mode(mode: str)` accepting `"build"` or `"live"`.
  - In `"build"` mode, the widget builds a synthetic 512-byte DMX buffer per universe with all channels at `0xFF` and pushes it via `engine.update_dmx(uni, buf)` once whenever `set_config` is called or fixtures change. (For colored fixtures this lights them white; for movers it sets pan/tilt to a sensible mid value — provide a small per-channel-type override map keyed off `FixtureType` so the preview is sane: dimmer 255, RGB(W) 255, pan/tilt 128, gobo/strobe 0.)
  - `StageTab.on_tab_activated` calls `embedded_visualizer.set_preview_mode("build")`. When ShowsTab signals playback start (via existing `shows_tab` references), Stage tab's preview switches to `"live"` so it follows real DMX. Default is `"build"` since playback is in another tab.
  - `EmbeddedVisualizer.feed_dmx` is ignored while in `"build"` mode.
- Refactor `gui/dialogs/orientation_dialog.py::OrientationDialog` so its inner controls + `OrientationPreviewWidget` live in a `OrientationPanel(QWidget)` that the dialog wraps. The Stage tab uses `OrientationPanel` directly, persistently visible. The right-click "Set Orientation" flow in `stage_tab._open_orientation_dialog` (line 495) re-binds the inline panel to the selected fixtures instead of opening a modal; the modal stays as a fallback for multi-edit-confirm if a future use needs it.
- Bind `stage_view.fixtures_changed` (already emitted) to a slot that calls `embedded_visualizer.set_config(self.config)` so position/orientation moves update the 3D preview live. While in build mode, the synthetic full-on DMX is re-pushed inside the same slot so the new fixture lights up immediately.

### Shows tab integration

- `gui/tabs/shows_tab.py::setup_ui` (line 135): wrap the timeline area in a `QSplitter(Qt.Horizontal)` with the timeline on the left and a small `EmbeddedVisualizer` (default ~360 px wide, collapsible) on the right. State persists across show switches.
- Wire `ShowsArtNetController` (instantiated in `_on_artnet_toggle` / its lazy init path — search for `self.artnet_controller = ShowsArtNetController(`) so it forwards DMX to the embedded view via the new `local_dmx_callback`.

## 5. Unified timeline grid (Shows + Structure)

This is the big refactor. Goal: one `QScrollArea`, one ruler, one column of left headers, all tracks aligned.

### New widget: `TimelineGrid`

- New file `timeline_ui/timeline_grid.py`:
  - `class TimelineGrid(QWidget)` — composite that owns:
    - A 320 px-wide left header column (`QVBoxLayout`) holding a stack of `TrackHeader` widgets (one per row: master, audio, each light lane).
    - A right scrollable timeline canvas (`QScrollArea` with `setWidgetResizable(False)`).
    - Inside the canvas, a single inner `QWidget` (the "stripe") with a `QVBoxLayout` of stripe rows: `MasterTimelineWidget`, `AudioTimelineWidget`, then each lane's `TimelineWidget`.
    - All inner timeline widgets share the same `pixels_per_second` and `total_width`. When the timeline shifts horizontally, every stripe shifts together — they're literally in the same scroll area.
  - One vertical scrollbar manages the lanes only (master + audio rows are pinned above the QScrollArea via a `QWidget` glued on top of the same horizontal-scrolling viewport using a child `QScrollArea` with `ScrollBarAlwaysOff` whose horizontal value is mirrored, OR — preferred — by putting master/audio inside the same scroll widget but anchored above an inner `QScrollArea` for lanes).
  - Diagram of internal layout:

    ```
    ┌──────────────────── TimelineGrid ────────────────────┐
    │ ┌── headers ──┐ │ ┌──── shared horizontal scroll ──┐ │
    │ │ master hdr  │ │ │ master ruler                   │ │
    │ │ audio hdr   │ │ │ audio waveform timeline        │ │
    │ │ ─ split ─   │ │ │ ─────────────────────────────  │ │
    │ │ lane 1 hdr  │ │ │ lane 1 stripe                  │ │
    │ │ lane 2 hdr  │ │ │ lane 2 stripe   (V-scrolls)    │ │
    │ │ …           │ │ │ …                              │ │
    │ └─────────────┘ │ └────────────────────────────────┘ │
    │                 │ shared horizontal scrollbar        │
    └──────────────────────────────────────────────────────┘
    ```

  - Public API mirrors today's containers so the surrounding code doesn't have to change much:
    - `set_song_structure`, `set_playhead_position`, `set_zoom_factor`, `add_lane(lane_widget_or_lane)`, `remove_lane(...)`, `set_audio_file`, plus signals `playhead_moved`, `zoom_changed`, `audio_file_changed`.

### Changes to existing timeline widgets

- `timeline_ui/master_timeline_widget.py`: keep `MasterTimelineWidget` (the painter), drop `MasterTimelineContainer` (its scroll/header role moves into `TimelineGrid`). Anything still importing `MasterTimelineContainer` (`gui/tabs/shows_tab.py:16`, `gui/tabs/structure_tab.py:18`) switches to `TimelineGrid`.
- `timeline_ui/audio_lane_widget.py`: keep `AudioTimelineWidget` painter; reduce `AudioLaneWidget` to two pieces — a `AudioTrackHeader` (the controls) used as the header, and the bare `AudioTimelineWidget` placed in the stripe. Modernize the controls (load button, volume slider, mute) via theme.qss only — no inline gradients.
- `timeline_ui/light_lane_widget.py`: split similarly into `LightLaneHeader` (the 320 px controls box) and the existing `TimelineWidget` stripe. Constructor still takes a `LightLane`; `LightLaneWidget` becomes a small façade returning `(header, stripe)` for `TimelineGrid` to consume.
- Remove all the `scroll_position_changed` cross-wiring in `gui/tabs/shows_tab.py::connect_signals` (lines 372-382) and `gui/tabs/structure_tab.py` — single scrollbar means it's no longer needed.

### Audio player modernization

- New `timeline_ui/audio_track_header.py`: redesigned controls — single row with a transport-style load icon button, file name (eliding), volume slider with monospace dB-ish percent, mute toggle, ‘🠒’ open file location. All styling lives in `theme.qss` selector `AudioTrackHeader`. Reuse the existing `_on_load_clicked`, `_on_volume_changed`, `_on_mute_toggled` signal logic verbatim.

### Shows tab + Structure tab use the new grid

- `gui/tabs/shows_tab.py::setup_ui`:
  - Drop the trio: `MasterTimelineContainer`, `AudioLaneWidget`, `lanes_scroll`/`lanes_container`/`lanes_layout`.
  - Replace with `self.timeline_grid = TimelineGrid()`.
  - `_add_new_lane`, `_load_show`, lane-removal, riff drop, paste, marquee selection — adapt to call `timeline_grid.add_lane / .remove_lane`. Selection overlay (`SelectionOverlay`) reparents to the inner stripe widget so its rubber band still aligns with lane time positions.
- `gui/tabs/structure_tab.py::setup_ui` (line 183): same swap — `MasterTimelineContainer` + `AudioLaneWidget` → one `TimelineGrid` with no light lanes.
- Playback / position-slider / playhead-sync logic in `shows_tab` keeps working since `TimelineGrid` exposes `set_playhead_position` and emits `playhead_moved`.

## 6. Live Mode as a tab

Today `live/window.py::LiveModeWindow` is a `QMainWindow` whose body is fully built in `_setup_ui` on a `central = QWidget()` (line 74-76). All audio/engine lifecycle (`_on_start`, `_on_stop`, `_cleanup` at lines 413/484/507) is attached to that window instance.

- New file `gui/tabs/live_tab.py` defining `LiveTab(BaseTab)`. Move the body of `LiveModeWindow._setup_ui` into `LiveTab.setup_ui` and the lifecycle methods (`_populate_devices`, `_on_start`, `_on_stop`, `_cleanup`, `_update_ui`, all the `_on_*_changed` slots, `_settings`, `_meter_bars`, `_engine`, `_dmx_controller`, etc.) onto `LiveTab`. The fastest path is extraction not duplication — refactor `LiveModeWindow` so its body lives in `LiveTab` and the window simply hosts the tab as its central widget for backwards-compat. Concretely:
  - Create `LiveTab(BaseTab)` containing all the UI + engine logic from `LiveModeWindow`, taking `config` and `fixture_definitions` (loaded lazily on first activation, see below).
  - `LiveModeWindow` becomes a thin `QMainWindow` wrapper that wraps a `LiveTab` instance — used only if a future flow wants to detach. We can drop it entirely if the user doesn't ask for detach later; for this pass, delete it and the menu action.
- Lazy fixture-definition load: `LiveTab.on_tab_activated` (overrides `BaseTab`) loads fixture definitions on first activation via `utils.fixture_utils.load_fixture_definitions_from_qlc` (same call already in `gui/gui.py:_open_live_mode`, line 877), so opening the app doesn't pay that cost up front.
- Pause when not visible: `LiveTab.on_tab_deactivated` does NOT auto-stop the engine (Live Mode is performance-oriented and should keep running while you peek at another tab) but does stop the 50 Hz `_ui_timer` to save cycles. `on_tab_activated` resumes it.
- Tab integration:
  - `gui/Ui_MainWindow.py`: add a sixth tab `self.tab_live = QWidget()` after `tab_2`, label "Live", and register in `retranslateUi`.
  - `gui/gui.py::_create_tabs`: instantiate `self.live_tab = LiveTab(self.config, self)` and attach it to `self.tab_live`. Add `tab_map[5] = self.live_tab` in `_on_tab_changed` (line 422) so activation/deactivation hooks fire.
  - Remove the `Live` menu and `Ctrl+L` shortcut in `_connect_signals` (lines 412-417) plus the `_open_live_mode` method (lines 869-891). Keep `Ctrl+L` repurposed as "go to Live tab": new action `actionGotoLive` calling `self.tabWidget.setCurrentIndex(5)`.
- Theme alignment: Live Mode's status frame and BPM display use hard-coded dark colors (e.g. `#1a1a2e`, `#e0e0e0`, `#ff6b6b` at lines 137-144). Convert these to QSS classes (`#StatusFrame`, `.bpm-display`, etc.) defined in both theme files so the tab matches the active theme.
- Cleanup: `MainWindow.closeEvent` calls `self.shows_tab.cleanup()` (line 972). Add `self.live_tab.cleanup()` (delegates to existing `_cleanup`) so audio device/DMX threads shut down.

## 7. Files to add / modify

### Add
- `resources/themes/dark.qss`, `resources/themes/light.qss`
- `gui/theme_manager.py`
- `gui/widgets/__init__.py`, `gui/widgets/modern_table.py`, `gui/widgets/embedded_visualizer.py`
- `timeline_ui/timeline_grid.py`
- `timeline_ui/audio_track_header.py`
- `gui/tabs/live_tab.py`

### Modify
- `main.py` — apply selected theme via `ThemeManager`, `showMaximized`.
- `gui/Ui_MainWindow.py` — remove fixed resize, drop inline styles, add `View > Fullscreen` (F11) action and `View > Theme` submenu (Dark / Light), expose dynamic-property hooks for ArtNet/TCP pills.
- `gui/gui.py` — hook fullscreen and theme actions (the latter via `ThemeManager`); rewrite `_update_toolbar_status` to set dynamic properties + `style().polish()` instead of full stylesheets so it works for both themes.
- `gui/tabs/shows_tab.py` — replace timeline trio with `TimelineGrid`, add embedded visualizer split, drop scroll-sync wiring, drop inline button styling.
- `gui/tabs/structure_tab.py` — replace `MasterTimelineContainer + AudioLaneWidget` with `TimelineGrid`, drop inline styles.
- `gui/tabs/stage_tab.py` — horizontal splitter `[StageView | (EmbeddedVisualizer / OrientationPanel)]` at ~2:1; drive build-mode preview lighting.
- `live/window.py` — extraction target: body moves to `gui/tabs/live_tab.py`; this file shrinks to a thin host (or is deleted if no detach flow remains).
- `gui/Ui_MainWindow.py` — add the Live tab placeholder; remove the `Live` menu.
- `gui/gui.py::_create_tabs`, `_connect_signals`, `_on_tab_changed`, `closeEvent` — instantiate `LiveTab`, route activation, delete `_open_live_mode` and the menu, repurpose `Ctrl+L` to switch to the tab, call `live_tab.cleanup()` on close.
- `gui/tabs/fixtures_tab.py`, `gui/tabs/configuration_tab.py` — apply `apply_modern_table_style`, drop inline table styles.
- `gui/dialogs/orientation_dialog.py` — extract `OrientationPanel` from the dialog body so Stage tab can embed it.
- `timeline_ui/master_timeline_widget.py`, `timeline_ui/audio_lane_widget.py`, `timeline_ui/light_lane_widget.py` — split painter from header, drop inline styles, expose composable parts to `TimelineGrid`.
- `timeline_ui/__init__.py` — export `TimelineGrid` (and stop exporting `MasterTimelineContainer`).
- `utils/tcp/protocol.py` — extract `build_fixtures_payload(config)` helper used both by JSON message and embedded visualizer.
- `utils/artnet/shows_artnet_controller.py` — accept and call `local_dmx_callback` in `_send_all_universes`.

## 7. Order of execution (so each commit is runnable)

1. Add `resources/themes/{dark,light}.qss` + `gui/theme_manager.py`, wire into `main.py`, switch to `showMaximized`. App still works with old layouts — visual change + theme menu only.
2. Add `apply_modern_table_style`, apply to Fixtures + Configuration. Drop redundant inline table CSS.
3. Strip inline styles from buttons/toolbars/headers across tabs; replace ON/OFF pill logic with dynamic-property polish so it works in both themes.
4. Land `TimelineGrid` plus the audio/light header splits; cut `MasterTimelineContainer` and the multi-scroll setup in Shows + Structure tabs.
5. Extract `OrientationPanel` from `OrientationDialog`.
6. Add `EmbeddedVisualizer` (with `set_preview_mode`) and `build_fixtures_payload`; embed it in Stage tab in the right-side splitter beside the orientation panel; default `build` mode lights everything up.
7. Add `local_dmx_callback` to `ShowsArtNetController`; embed `EmbeddedVisualizer` in Shows tab and feed it from the callback (live mode).
8. Add `View > Fullscreen` menu/F11 toggle.
9. Extract `LiveTab` from `LiveModeWindow`, register as the sixth tab, remove the `Live` menu, repurpose `Ctrl+L` to focus the tab.

## 8. Verification

- `python main.py` opens maximized, default theme applied, no debug console errors.
- `View > Theme > Light` and `View > Theme > Dark` swap themes live; restart and confirm the chosen theme is restored from `QSettings`.
- Configuration tab — 8-column table renders with new styling, alternating rows, sortable; readable in both themes; round-trip a save/load.
- Fixtures tab — add, remove, duplicate fixture; group color tinting still applies on top of either theme; mode change still recomputes channels.
- Stage tab — left ≈2/3 hosts the 2D StageView, right ≈1/3 stacks EmbeddedVisualizer over OrientationPanel. With no playback, all fixtures in the embedded visualizer are lit (build mode). Drag a fixture: 2D view updates, embedded 3D preview reflects the move with full-on lighting. Right-click → Set Orientation updates the embedded orientation panel. Pop Out launches the standalone visualizer subprocess and TCP path still works.
- Shows tab — load `light_track_cycle_of_a_psycho_test_wo_klick.mp3` from repo root via the audio header; master ruler, waveform, and at least 3 light lanes share a single horizontal scrollbar; playhead drag updates all stripes simultaneously; zoom (Shift+wheel) keeps everything aligned; ArtNet toggle on → embedded visualizer beams flicker in sync with playback.
- Structure tab — add/edit a part; ruler + waveform stay aligned; show selection still syncs with Shows tab via `MainWindow.on_show_selected`.
- Run `pytest -q` (the repo has a `tests/` dir + `pytest.ini`) — adapt any tests that import `MasterTimelineContainer`.
- Toggle `View > Fullscreen` (F11) — switches and restores cleanly.
- Launch the standalone visualizer (`Stage tab > Pop Out` or via TCP toggle) — confirm it still receives stage/fixtures over TCP and DMX over ArtNet, independent of the embedded view.
- Live tab — `Ctrl+L` switches focus to it; pressing Start with a microphone selected drives meters/BPM and DMX; switching away to another tab keeps the engine running but suspends the 50 Hz UI timer; pressing Stop cleans up; closing the app calls `live_tab.cleanup()`.