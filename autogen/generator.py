"""Main show generator — orchestrates the full algorithm.

Implements the algorithm from theory Section 5 (Steps 1-11):
1. Analyze audio
2. Define section targets
3. Define phrase structure
4. Assign rudiments per fixture group
5. Assign grooves and fills
6-7. Score and select
8. Handle transitions
9. Apply spatial rules
10-11. Generate blocks on timeline
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from config.models import (
    Configuration, LightLane, LightBlock, DimmerBlock, ColourBlock,
    MovementBlock, SpecialBlock, ShowPart,
)
from timeline.song_structure import SongStructure
from audio.spectral_analysis import analyze_song, SongAnalysis, SectionAnalysis
from autogen.color_generator import (
    SongPalette, SectionColorAssignment,
    generate_palette_from_audio, assign_section_colors,
    get_preset_palette,
)
from autogen.matcher import (
    match_rudiments_to_section, select_groove_and_fill,
    select_rudiments_per_group, AutogenConfig,
)
from autogen.spatial import (
    classify_fixture_groups, apply_vocal_rule, compute_richness_weights,
    get_gobo_prism_groups, GroupClassification, ensure_default_spots,
)
from rudiments.registry import get_intensity_rudiments, get_movement_rudiments
from rudiments.block_converter import rudiment_to_dimmer_block, rudiment_to_movement_block


def generate_show(
    audio_path: str,
    song_structure: SongStructure,
    config: Configuration,
    autogen_config: Optional[AutogenConfig] = None,
    key_signature: Optional[str] = None,
    song_palette: Optional[SongPalette] = None,
) -> List[LightLane]:
    """Generate a complete light show for a song.

    Returns a list of LightLanes populated with blocks,
    ready to be placed on the timeline.

    Args:
        audio_path: Path to audio file
        song_structure: SongStructure with parts
        config: Show creator configuration (fixtures, groups, etc.)
        autogen_config: Generation parameters
        key_signature: Optional key signature for color mood

    Returns:
        List of LightLanes with generated blocks
    """
    if autogen_config is None:
        autogen_config = AutogenConfig()

    # Step 1: Analyze audio
    analysis = analyze_song(audio_path, song_structure)

    # Compute global centroid range for normalization
    all_centroids = [s.spectral_centroid_avg for s in analysis.sections if s.spectral_centroid_avg > 0]
    if all_centroids:
        centroid_range = (min(all_centroids), max(all_centroids))
    else:
        centroid_range = (500.0, 5000.0)

    # Step 2: Ensure spots exist for movement targeting, classify groups
    spot_names = ensure_default_spots(config)
    group_classifications = classify_fixture_groups(config)
    if not group_classifications:
        return []

    # Step 3-7: Per-section rudiment selection and block generation
    section_rudiments: Dict[str, Dict[str, str]] = {}
    previous_section_type = None
    previous_rudiments = None

    # Song-level color palette (max 3 colors + white for entire song)
    if song_palette is None:
        avg_bpm = sum(p.bpm for p in song_structure.parts) / max(1, len(song_structure.parts))
        song_palette = generate_palette_from_audio(
            analysis, avg_bpm, key_signature,
            num_colors=2, include_white=True,
        )

    # Assign colors per section type
    section_types = {p.name: p.name.lower().split()[0] for p in song_structure.parts}
    section_color_assignments = assign_section_colors(song_palette, section_types)

    # Build lanes — one per fixture group
    lanes: Dict[str, LightLane] = {}
    for group_name in group_classifications:
        lane = LightLane(
            name=f"Auto - {group_name}",
            fixture_targets=[group_name],
            muted=False,
            solo=False,
            light_blocks=[],
        )
        lanes[group_name] = lane

    # Process each section
    for part in song_structure.parts:
        section = _find_section(analysis, part)
        if section is None:
            continue

        color_assignment = section_color_assignments.get(part.name)
        section_type = section_types.get(part.name, "generic")

        # All groups are always active — richness scales intensity
        richness_weights = compute_richness_weights(group_classifications, section.spectral_richness)
        vocal_weights = apply_vocal_rule(group_classifications, section.vocal_presence)
        gobo_prism = get_gobo_prism_groups(
            group_classifications, section.spectral_richness,
            autogen_config.spectral_richness_gobo_threshold,
            autogen_config.spectral_richness_prism_threshold,
        )

        # Select different groove+fill rudiments per fixture group (visual diversity)
        group_names = list(group_classifications.keys())
        per_group_rudiments = select_rudiments_per_group(
            section, part.bpm, group_names, autogen_config,
            previous_section_rudiments=previous_rudiments,
            section_type=section_type,
            previous_section_type=previous_section_type,
        )

        # Select movement strategy for moving heads
        section_idx = song_structure.parts.index(part)
        movement = _select_movement_strategy(section, part.bpm, spot_names, section_idx)

        # Store primary group's rudiment for cross-section contrast
        primary_groove = per_group_rudiments[group_names[0]][0] if group_names else "static"
        current_rudiments = {"intensity": primary_groove, "movement": movement.shape}
        section_rudiments[part.name] = current_rudiments
        previous_rudiments = current_rudiments
        previous_section_type = section_type

        # Generate blocks for ALL fixture groups (each with its own rudiment)
        for group_idx, (group_name, gc) in enumerate(group_classifications.items()):
            if group_name not in lanes:
                continue

            groove_name, fill_name = per_group_rudiments.get(
                group_name, (primary_groove, primary_groove)
            )

            # Combine vocal and richness weights
            vocal_w = vocal_weights.get(group_name, 1.0)
            richness_w = richness_weights.get(group_name, 1.0)
            combined_weight = vocal_w * richness_w

            # Compute speed: BPM + energy, with per-group offset for variation
            speed_offset = (group_idx % 3) - 1  # -1, 0, +1
            effect_speed = _compute_effect_speed(part.bpm, section, offset=speed_offset)

            _generate_section_blocks(
                lane=lanes[group_name],
                part=part,
                groove_name=groove_name,
                fill_name=fill_name,
                movement_strategy=movement if gc.has_moving_heads else None,
                color_assignment=color_assignment,
                gobo_prism=gobo_prism.get(group_name, {}),
                weight=combined_weight,
                config=autogen_config,
                color_index=group_idx % 3,
                effect_speed=effect_speed,
            )

    return list(lanes.values())


def _find_section(analysis: SongAnalysis, part: ShowPart) -> Optional[SectionAnalysis]:
    """Find the SectionAnalysis matching a ShowPart by name."""
    for section in analysis.sections:
        if section.name == part.name:
            return section
    return None


@dataclass
class MovementStrategy:
    """Movement decision for a section."""
    shape: str = "circle"
    target_spot: Optional[str] = None
    amplitude: float = 50.0  # Pan/tilt amplitude, scaled by energy


def _select_movement_strategy(
    section: SectionAnalysis,
    bpm: float,
    spot_names: List[str],
    section_index: int = 0,
) -> MovementStrategy:
    """Select movement shape, spot targeting, and amplitude based on section character.

    Uses plane-style targeting: center spot + wide amplitude = sweep across area.
    Vocal focus only when vocals are prominent AND instrumentation is sparse (solo moment).
    """
    energy = section.spectral_flux_avg + section.transient_sharpness

    # Amplitude scales with energy: 15 (calm) to 80 (intense)
    amplitude = 15.0 + energy * 40.0
    amplitude = max(15.0, min(80.0, amplitude))

    # Plane spots: "Crowd" and "Stage" center spots for sweeping
    crowd_spots = [s for s in spot_names if "crowd" in s.lower()]
    stage_spots = [s for s in spot_names if "stage" in s.lower()]

    # Vocal focus: only when vocals are prominent AND instrumentation is sparse
    # This targets solo/intimate moments, not full-band choruses
    vocal_solo = section.vocal_presence > 0.4 and section.spectral_richness < 0.5

    if energy > 1.0:
        # High energy: wide dynamic shapes, sweep across crowd plane
        spot = crowd_spots[0] if crowd_spots else None
        wide_amplitude = min(80.0, amplitude * 1.3)  # Extra wide for high energy
        if energy > 1.4:
            return MovementStrategy(shape="circle", target_spot=spot, amplitude=wide_amplitude)
        else:
            return MovementStrategy(shape="figure_8", target_spot=spot, amplitude=wide_amplitude)
    elif energy > 0.6:
        # Medium energy: dynamic shape sweeping crowd or stage
        spot = crowd_spots[0] if crowd_spots else (stage_spots[0] if stage_spots else None)
        return MovementStrategy(shape="bounce", target_spot=spot, amplitude=amplitude)
    else:
        # Low energy
        if vocal_solo and crowd_spots:
            # Sparse vocal solo: gentle sweep across crowd (not a fixed stare)
            return MovementStrategy(shape="circle", target_spot=crowd_spots[0], amplitude=amplitude)
        elif stage_spots:
            # Calm/atmospheric: sweep stage area
            return MovementStrategy(shape="linear_sweep", target_spot=stage_spots[0], amplitude=amplitude)
        else:
            return MovementStrategy(shape="circle", amplitude=amplitude)


VALID_SPEEDS = ["1/4", "1/2", "1", "2", "4"]
SPEED_VALUES = [0.25, 0.5, 1.0, 2.0, 4.0]


def _compute_effect_speed(bpm: float, section: SectionAnalysis, offset: int = 0) -> str:
    """Compute effect speed from BPM + section energy.

    Args:
        bpm: Section BPM
        section: Audio analysis for energy scaling
        offset: Speed step offset for per-group variation (-1, 0, +1)

    Returns:
        Speed string like "1/2", "1", "2"
    """
    base_speed = bpm / 120.0
    energy = section.spectral_flux_avg + section.transient_sharpness
    energy_multiplier = 1.0 + energy * 0.3
    raw_speed = base_speed * energy_multiplier

    # Find closest valid speed
    best_idx = 0
    best_dist = abs(SPEED_VALUES[0] - raw_speed)
    for i, sv in enumerate(SPEED_VALUES):
        dist = abs(sv - raw_speed)
        if dist < best_dist:
            best_dist = dist
            best_idx = i

    # Apply group offset (shift up/down one step)
    best_idx = max(0, min(len(VALID_SPEEDS) - 1, best_idx + offset))
    return VALID_SPEEDS[best_idx]


def _generate_section_blocks(
    lane: LightLane,
    part: ShowPart,
    groove_name: str,
    fill_name: str,
    movement_strategy: Optional[MovementStrategy],
    color_assignment: Optional[SectionColorAssignment],
    gobo_prism: Dict[str, bool],
    weight: float,
    config: AutogenConfig,
    color_index: int,
    effect_speed: str = "1",
):
    """Generate LightBlocks for one fixture group in one section.

    Splits section into phrases (groove + fill) per the theory.
    Respects the part's time signature and bar count.
    """
    section_start = part.start_time
    section_end = part.start_time + part.duration

    if section_end <= section_start:
        return

    # Parse time signature for beats per bar
    beats_per_bar = 4  # Default
    try:
        sig_parts = part.signature.split('/')
        beats_per_bar = int(sig_parts[0])
    except (ValueError, IndexError, AttributeError):
        pass

    seconds_per_beat = 60.0 / part.bpm
    seconds_per_bar = seconds_per_beat * beats_per_bar

    # Determine phrase structure from section bar count
    total_section_bars = part.num_bars
    phrase_bars = min(config.phrase_length_bars, total_section_bars)

    # If section is too short for groove + fill, use all groove
    groove_bars = int(phrase_bars * config.groove_fill_ratio)
    fill_bars = phrase_bars - groove_bars

    if total_section_bars < config.phrase_length_bars:
        # Section shorter than one phrase — all groove, no fill
        groove_bars = total_section_bars
        fill_bars = 0

    groove_duration = groove_bars * seconds_per_bar
    fill_duration = fill_bars * seconds_per_bar
    phrase_duration = groove_duration + fill_duration

    # Calculate how many full phrases fit and handle remainder
    if phrase_duration > 0:
        full_phrases = total_section_bars // phrase_bars
        remainder_bars = total_section_bars % phrase_bars
    else:
        full_phrases = 0
        remainder_bars = total_section_bars

    # Generate full phrases
    current_time = section_start
    for _ in range(full_phrases):
        # Groove portion
        groove_end = current_time + groove_duration
        _add_light_block(
            lane, current_time, groove_end,
            groove_name, movement_strategy, color_assignment,
            gobo_prism, weight, part.bpm, color_index, effect_speed,
        )

        # Fill portion (if any)
        if fill_duration > 0:
            fill_start = groove_end
            fill_end = fill_start + fill_duration
            _add_light_block(
                lane, fill_start, fill_end,
                fill_name, movement_strategy, color_assignment,
                gobo_prism, weight, part.bpm, color_index, effect_speed,
            )
            current_time = fill_end
        else:
            current_time = groove_end

    # Remainder bars — all groove (too short for groove + fill)
    if remainder_bars > 0:
        remainder_duration = remainder_bars * seconds_per_bar
        remainder_end = min(current_time + remainder_duration, section_end)
        _add_light_block(
            lane, current_time, remainder_end,
            groove_name, movement_strategy, color_assignment,
            gobo_prism, weight, part.bpm, color_index, effect_speed,
        )


def _add_light_block(
    lane: LightLane,
    start_time: float,
    end_time: float,
    intensity_rudiment: str,
    movement_strategy: Optional[MovementStrategy],
    color_assignment: Optional[SectionColorAssignment],
    gobo_prism: Dict[str, bool],
    weight: float,
    bpm: float,
    color_index: int,
    effect_speed: str = "1",
):
    """Create and add a single LightBlock to a lane."""
    # Dimmer block
    dimmer = rudiment_to_dimmer_block(
        intensity_rudiment,
        {"intensity": weight},
        start_time, end_time,
    )
    dimmer.effect_speed = effect_speed
    dimmer_blocks = [dimmer]

    # Colour block from section color assignment
    colour_blocks = []
    if color_assignment and color_assignment.colors:
        color = color_assignment.colors[color_index % len(color_assignment.colors)]
        colour_blocks.append(ColourBlock(
            start_time=start_time,
            end_time=end_time,
            red=float(color[0]),
            green=float(color[1]),
            blue=float(color[2]),
            white=255.0 if color == (255, 255, 255) else 0.0,
        ))

    # Movement block (if applicable) — movement is 1 speed step slower than dimmer
    movement_blocks = []
    if movement_strategy:
        # Compute movement speed: one step slower than dimmer
        try:
            dimmer_idx = VALID_SPEEDS.index(effect_speed)
        except ValueError:
            dimmer_idx = 2  # Default to "1"
        movement_speed_idx = max(0, dimmer_idx - 1)
        movement_speed = VALID_SPEEDS[movement_speed_idx]

        mb = rudiment_to_movement_block(
            movement_strategy.shape,
            {"amplitude": movement_strategy.amplitude},
            start_time, end_time,
        )
        mb.effect_speed = movement_speed
        if movement_strategy.target_spot:
            mb.target_spot_name = movement_strategy.target_spot
        movement_blocks.append(mb)

    # Special block (gobo/prism)
    special_blocks = []
    if gobo_prism.get("gobo") or gobo_prism.get("prism"):
        special_blocks.append(SpecialBlock(
            start_time=start_time,
            end_time=end_time,
            gobo_index=3 if gobo_prism.get("gobo") else 0,
            prism_enabled=gobo_prism.get("prism", False),
        ))

    light_block = LightBlock(
        start_time=start_time,
        end_time=end_time,
        effect_name=f"auto.{intensity_rudiment}",
        dimmer_blocks=dimmer_blocks,
        colour_blocks=colour_blocks,
        movement_blocks=movement_blocks,
        special_blocks=special_blocks,
    )

    lane.light_blocks.append(light_block)
