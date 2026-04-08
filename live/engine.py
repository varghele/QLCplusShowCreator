"""
Live Show Engine — real-time riff generation driven by live audio.

Accumulates audio features into a sliding window, synthesizes a
SectionAnalysis-compatible profile, and runs a groove+fill riff cycle
that auto-generates lighting blocks matching the incoming sound.
"""

import time
import threading
import colorsys
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, List, Callable

from audio.realtime_spectral import LiveFeatureFrame
from audio.spectral_analysis import SectionAnalysis
from autogen.matcher import select_rudiments_per_group, match_rudiments_to_section
from autogen.spatial import (
    classify_fixture_groups, apply_vocal_rule, compute_richness_weights,
    assign_group_roles, get_gobo_prism_groups, ActivationRole,
)
from rudiments.block_converter import rudiment_to_dimmer_block, rudiment_to_movement_block
from config.models import DimmerBlock, ColourBlock, MovementBlock, SpecialBlock, Configuration


# How many feature frames to keep (~86 frames/sec at 44100/512)
_WINDOW_SECONDS = 45
_FRAMES_PER_SEC = 86  # approximate
_MAX_WINDOW = _WINDOW_SECONDS * _FRAMES_PER_SEC


@dataclass
class LiveCycleState:
    """Tracks where we are in the current groove+fill cycle."""
    cycle_start_time: float = 0.0
    bar_index: int = 0          # 0..groove_bars (last = fill)
    is_fill: bool = False
    groove_rudiment: str = "static"
    fill_rudiment: str = "stroke"


class LiveShowEngine:
    """Core engine for live audio-reactive lighting.

    Thread model:
    - on_feature_frame() called from analysis thread
    - tick() called from DMX thread at 30Hz
    - UI setters called from Qt main thread
    All shared state protected by _lock.
    """

    def __init__(self, config: Configuration, fixture_definitions: dict):
        self.config = config
        self.fixture_definitions = fixture_definitions

        # Audio feature sliding window
        self._window: deque = deque(maxlen=_MAX_WINDOW)
        self._lock = threading.Lock()

        # Classify fixture groups once
        self._group_classifications = classify_fixture_groups(config)
        self._group_names = list(config.groups.keys())

        # Riff cycle state
        self._bpm: float = 120.0
        self._groove_bars: int = 3
        self._cycle = LiveCycleState()
        self._per_group_rudiments: Dict[str, Tuple[str, str]] = {}
        self._previous_rudiments: Dict[str, str] = {}
        self._running = False
        self._engine_time: float = 0.0  # monotonic engine clock

        # User controls
        self._energy_sensitivity: float = 0.7
        self._color_override: Optional[Tuple[int, int, int]] = None
        self._group_submasters: Dict[str, float] = {g: 1.0 for g in self._group_names}
        self._heavy_threshold: float = 0.85
        self._riff_palette_overrides: Dict[int, Optional[str]] = {i: None for i in range(8)}

        # Auto color state
        self._auto_color_rgb: Tuple[int, int, int] = (255, 255, 255)

        # Active block tracking (lane_key -> block_type -> registered)
        self._active_lanes: set = set()

        # DMX manager reference (set by LiveDMXController)
        self._dmx_manager = None

        # Callbacks for UI updates
        self._on_riffs_updated: Optional[Callable[[List[str]], None]] = None
        self._on_state_changed: Optional[Callable[[], None]] = None

        # Top rudiment names for palette
        self._top_rudiments: List[str] = []

        # Last heavy interrupt time (prevent rapid re-triggers)
        self._last_heavy_time: float = 0.0

    # ── Public setters (called from Qt main thread) ──

    def set_dmx_manager(self, dmx_manager):
        """Set the DMXManager to register blocks with."""
        self._dmx_manager = dmx_manager

    def set_bpm(self, bpm: float):
        with self._lock:
            self._bpm = max(30.0, min(300.0, bpm))

    def set_groove_bars(self, bars: int):
        with self._lock:
            self._groove_bars = max(1, min(16, bars))

    def set_energy_sensitivity(self, value: float):
        with self._lock:
            self._energy_sensitivity = max(0.0, min(1.0, value))

    def set_color_override(self, rgb: Optional[Tuple[int, int, int]]):
        with self._lock:
            self._color_override = rgb

    def set_group_submaster(self, group_name: str, value: float):
        with self._lock:
            if group_name in self._group_submasters:
                self._group_submasters[group_name] = max(0.0, min(1.0, value))

    def set_heavy_threshold(self, value: float):
        with self._lock:
            self._heavy_threshold = max(0.0, min(1.0, value))

    def set_riff_override(self, slot: int, rudiment_name: Optional[str]):
        with self._lock:
            if 0 <= slot < 8:
                self._riff_palette_overrides[slot] = rudiment_name

    def set_on_riffs_updated(self, callback: Optional[Callable[[List[str]], None]]):
        self._on_riffs_updated = callback

    def set_on_state_changed(self, callback: Optional[Callable[[], None]]):
        self._on_state_changed = callback

    # ── Properties for UI reading ──

    @property
    def bpm(self) -> float:
        with self._lock:
            return self._bpm

    @property
    def current_bar(self) -> int:
        with self._lock:
            return self._cycle.bar_index

    @property
    def is_fill(self) -> bool:
        with self._lock:
            return self._cycle.is_fill

    @property
    def current_groove_name(self) -> str:
        with self._lock:
            return self._cycle.groove_rudiment

    @property
    def groove_bars(self) -> int:
        with self._lock:
            return self._groove_bars

    @property
    def top_rudiments(self) -> List[str]:
        with self._lock:
            return list(self._top_rudiments)

    # ── Audio feature input (called from analysis thread) ──

    def on_feature_frame(self, frame: LiveFeatureFrame):
        """Append a feature frame to the sliding window."""
        with self._lock:
            self._window.append(frame)

            # Check heavy interrupt
            if (self._running
                    and not self._cycle.is_fill
                    and frame.rms > self._heavy_threshold
                    and (time.monotonic() - self._last_heavy_time) > 1.0):
                self._trigger_heavy_interrupt()

    # ── Engine tick (called from DMX thread at 30Hz) ──

    def start(self):
        """Start the engine cycle."""
        with self._lock:
            self._running = True
            self._engine_time = time.monotonic()
            self._start_new_cycle()

    def stop(self):
        """Stop the engine and clear all blocks."""
        with self._lock:
            self._running = False
            self._end_all_blocks()

    def tick(self, current_time: float):
        """Advance the engine. Called at 30Hz from DMX thread.

        Args:
            current_time: monotonic time
        """
        with self._lock:
            if not self._running:
                return

            self._engine_time = current_time
            beat_duration = 60.0 / self._bpm
            bar_duration = 4.0 * beat_duration
            total_cycle_bars = self._groove_bars + 1  # groove + fill

            elapsed = current_time - self._cycle.cycle_start_time
            current_bar = int(elapsed / bar_duration)

            if current_bar >= total_cycle_bars:
                # Cycle complete → start new one
                self._end_all_blocks()
                self._start_new_cycle()
                return

            if current_bar != self._cycle.bar_index:
                # Bar boundary crossed
                self._cycle.bar_index = current_bar
                self._cycle.is_fill = (current_bar >= self._groove_bars)

                # End previous bar blocks and start new ones
                self._end_all_blocks()
                bar_start = self._cycle.cycle_start_time + current_bar * bar_duration
                bar_end = bar_start + bar_duration
                self._create_all_blocks(bar_start, bar_end)

                if self._on_state_changed:
                    try:
                        self._on_state_changed()
                    except Exception:
                        pass

    def force_fill(self):
        """Immediately transition to fill bar, then start new cycle."""
        with self._lock:
            if not self._running:
                return

            beat_duration = 60.0 / self._bpm
            bar_duration = 4.0 * beat_duration

            self._end_all_blocks()
            self._cycle.is_fill = True
            self._cycle.bar_index = self._groove_bars

            # Set cycle_start_time so the fill bar ends after one bar from now
            now = self._engine_time
            self._cycle.cycle_start_time = now - self._groove_bars * bar_duration

            bar_start = now
            bar_end = now + bar_duration
            self._create_all_blocks(bar_start, bar_end)

    # ── Internal methods ──

    def _trigger_heavy_interrupt(self):
        """Handle heavy energy spike — immediate fill then new riff."""
        self._last_heavy_time = time.monotonic()
        # Switch to fill bar
        self._end_all_blocks()
        self._cycle.is_fill = True
        self._cycle.bar_index = self._groove_bars

        beat_duration = 60.0 / self._bpm
        bar_duration = 4.0 * beat_duration
        now = self._engine_time
        self._cycle.cycle_start_time = now - self._groove_bars * bar_duration

        bar_start = now
        bar_end = now + bar_duration
        self._create_all_blocks(bar_start, bar_end)

    def _start_new_cycle(self):
        """Select new riffs and start a fresh groove+fill cycle."""
        self._cycle.cycle_start_time = self._engine_time
        self._cycle.bar_index = 0
        self._cycle.is_fill = False

        # Build profile from sliding window
        profile = self._build_window_profile()

        # Select riffs per group
        self._select_next_riffs(profile)

        # Update auto color from centroid
        self._update_auto_color(profile)

        # Create first bar blocks
        beat_duration = 60.0 / self._bpm
        bar_duration = 4.0 * beat_duration
        bar_start = self._cycle.cycle_start_time
        bar_end = bar_start + bar_duration
        self._create_all_blocks(bar_start, bar_end)

    def _build_window_profile(self) -> SectionAnalysis:
        """Synthesize a SectionAnalysis from the sliding window."""
        if not self._window:
            return SectionAnalysis(
                name="live", start_time=0.0, end_time=1.0,
                spectral_flux_avg=0.5, transient_sharpness=0.5,
                spectral_richness=0.5, vocal_presence=0.0,
                rms_energy=0.5, spectral_contrast_avg=0.5,
                spectral_centroid_avg=1000.0,
                spectral_flux_envelope=[0.5] * 32,
            )

        frames = list(self._window)
        flux_vals = [f.flux for f in frames]
        transient_vals = [f.transient for f in frames]
        richness_vals = [f.richness for f in frames]
        vocal_vals = [f.vocal for f in frames]
        centroid_vals = [f.centroid for f in frames]
        rms_vals = [f.rms for f in frames]
        contrast_vals = [f.contrast for f in frames]

        # Resample flux to 32-point envelope
        flux_arr = np.array(flux_vals, dtype=np.float32)
        if len(flux_arr) >= 32:
            indices = np.linspace(0, len(flux_arr) - 1, 32).astype(int)
            envelope = flux_arr[indices].tolist()
        else:
            envelope = flux_vals + [0.0] * (32 - len(flux_vals))

        return SectionAnalysis(
            name="live",
            start_time=0.0,
            end_time=float(len(frames)) / _FRAMES_PER_SEC,
            spectral_flux_avg=float(np.mean(flux_vals)),
            spectral_flux_envelope=envelope,
            transient_sharpness=float(np.mean(transient_vals)),
            spectral_richness=float(np.mean(richness_vals)),
            vocal_presence=float(np.mean(vocal_vals)),
            spectral_centroid_avg=float(np.mean(centroid_vals)) * 8000,  # denormalize from 0-1 to Hz-ish
            rms_energy=float(np.mean(rms_vals)),
            spectral_contrast_avg=float(np.mean(contrast_vals)),
        )

    def _select_next_riffs(self, profile: SectionAnalysis):
        """Use the autogen matcher to select riffs per group."""
        # Get scores for palette
        scores = match_rudiments_to_section(
            profile, self._bpm,
            previous_section_rudiments=self._previous_rudiments,
            section_type="generic",
        )
        self._top_rudiments = list(scores.keys())[:8]

        # Check for manual overrides
        forced_groove = None
        for slot in range(8):
            override = self._riff_palette_overrides.get(slot)
            if override is not None:
                forced_groove = override
                break

        if forced_groove:
            # Use forced riff for all groups (simplified)
            # Pick a contrasting fill
            fill = self._top_rudiments[1] if len(self._top_rudiments) > 1 else "stroke"
            if fill == forced_groove and len(self._top_rudiments) > 2:
                fill = self._top_rudiments[2]
            self._per_group_rudiments = {
                g: (forced_groove, fill) for g in self._group_names
            }
        else:
            # Normal per-group selection
            self._per_group_rudiments = select_rudiments_per_group(
                profile, self._bpm, self._group_names,
                previous_section_rudiments=self._previous_rudiments,
                section_type="generic",
            )

        # Store for next cycle's contrast
        self._previous_rudiments = {
            g: r[0] for g, r in self._per_group_rudiments.items()
        }

        # Set cycle state from first group (for display)
        if self._per_group_rudiments:
            first = next(iter(self._per_group_rudiments.values()))
            self._cycle.groove_rudiment = first[0]
            self._cycle.fill_rudiment = first[1]

        # Notify UI
        if self._on_riffs_updated:
            try:
                self._on_riffs_updated(list(self._top_rudiments))
            except Exception:
                pass

    def _update_auto_color(self, profile: SectionAnalysis):
        """Generate color from spectral centroid."""
        # Map centroid (0-8000 Hz range) to hue (0-1)
        centroid_normalized = min(1.0, profile.spectral_centroid_avg / 8000.0)
        hue = centroid_normalized * 0.8  # Stay in 0-288 degree range (avoid wrapping red-red)
        saturation = 0.7 + 0.3 * profile.spectral_richness
        value = 0.8 + 0.2 * profile.rms_energy

        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        self._auto_color_rgb = (int(r * 255), int(g * 255), int(b * 255))

    def _get_color_for_block(self) -> Tuple[int, int, int]:
        """Get current color (override or auto)."""
        if self._color_override is not None:
            return self._color_override
        return self._auto_color_rgb

    def _create_all_blocks(self, bar_start: float, bar_end: float):
        """Create and register blocks for all groups for the current bar."""
        if not self._dmx_manager:
            return

        profile = self._build_window_profile()
        relative_energy = profile.rms_energy * self._energy_sensitivity

        # Spatial rules
        vocal_weights = apply_vocal_rule(self._group_classifications, profile.vocal_presence)
        richness_weights = compute_richness_weights(
            self._group_classifications, profile.spectral_richness,
            profile.spectral_flux_avg, relative_energy,
        )
        roles = assign_group_roles(
            self._per_group_rudiments, relative_energy, self._group_classifications,
        )
        gobo_prism = get_gobo_prism_groups(
            self._group_classifications, profile.spectral_richness,
        )

        color = self._get_color_for_block()

        for group_name in self._group_names:
            if group_name not in self._per_group_rudiments:
                continue

            groove_name, fill_name = self._per_group_rudiments[group_name]
            role = roles.get(group_name, ActivationRole.FULL)

            # Determine which rudiment to use this bar
            if self._cycle.is_fill:
                if role == ActivationRole.GROOVE_ONLY:
                    continue  # Skip groove-only groups during fill
                rudiment_name = fill_name
            else:
                if role == ActivationRole.FILL_ONLY:
                    continue  # Skip fill-only groups during groove
                rudiment_name = groove_name

            # Compute intensity with weights and submaster
            base_weight = richness_weights.get(group_name, 1.0)
            vocal_weight = vocal_weights.get(group_name, 1.0)
            submaster = self._group_submasters.get(group_name, 1.0)
            intensity = base_weight * vocal_weight * submaster

            # Create dimmer block
            params = {"intensity": intensity, "speed": 1.0}
            dimmer_block = rudiment_to_dimmer_block(
                rudiment_name, params, bar_start, bar_end,
            )

            # Create colour block
            colour_block = ColourBlock(
                start_time=bar_start,
                end_time=bar_end,
                red=color[0],
                green=color[1],
                blue=color[2],
            )

            # Get fixtures for this group
            group = self.config.groups.get(group_name)
            if not group:
                continue

            lane_key = f"live_{group_name}"

            # Register blocks with DMX manager
            self._dmx_manager.block_started(
                lane_key, group.fixtures, dimmer_block, 'dimmer', bar_start,
            )
            self._dmx_manager.block_started(
                lane_key, group.fixtures, colour_block, 'colour', bar_start,
            )
            self._active_lanes.add(lane_key)

            # Special blocks (gobo/prism)
            gp = gobo_prism.get(group_name, {})
            if gp.get("gobo") or gp.get("prism"):
                special_block = SpecialBlock(
                    start_time=bar_start,
                    end_time=bar_end,
                    gobo_index=3 if gp.get("gobo") else 0,
                    prism_enabled=gp.get("prism", False),
                )
                self._dmx_manager.block_started(
                    lane_key, group.fixtures, special_block, 'special', bar_start,
                )

            # Movement block for groups with moving heads
            gc = self._group_classifications.get(group_name)
            if gc and gc.has_moving_heads:
                movement_name = "circle" if relative_energy > 0.4 else "static"
                amplitude = 0.3 + 0.5 * relative_energy
                mov_params = {
                    "amplitude": amplitude,
                    "speed": 1.0,
                }
                try:
                    movement_block = rudiment_to_movement_block(
                        movement_name, mov_params, bar_start, bar_end,
                    )
                    self._dmx_manager.block_started(
                        lane_key, group.fixtures, movement_block, 'movement', bar_start,
                    )
                except Exception:
                    pass  # Not all movement rudiments may be registered

    def _end_all_blocks(self):
        """Unregister all active blocks from DMXManager."""
        if not self._dmx_manager:
            return

        for lane_key in list(self._active_lanes):
            for block_type in ('dimmer', 'colour', 'movement', 'special'):
                try:
                    self._dmx_manager.block_ended(lane_key, block_type)
                except Exception:
                    pass

        self._active_lanes.clear()
