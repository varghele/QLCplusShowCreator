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
from autogen.color_generator import generate_palette, ensure_section_contrast, SectionPalette
from autogen.matcher import (
    match_rudiments_to_section, select_groove_and_fill, AutogenConfig,
)
from autogen.spatial import (
    classify_fixture_groups, apply_vocal_rule, select_active_groups,
    get_gobo_prism_groups, GroupClassification,
)
from rudiments.registry import get_intensity_rudiments, get_movement_rudiments
from rudiments.block_converter import rudiment_to_dimmer_block, rudiment_to_movement_block


def generate_show(
    audio_path: str,
    song_structure: SongStructure,
    config: Configuration,
    autogen_config: Optional[AutogenConfig] = None,
    key_signature: Optional[str] = None,
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

    # Step 2: Classify fixture groups spatially
    group_classifications = classify_fixture_groups(config)
    if not group_classifications:
        return []

    # Step 3-7: Per-section rudiment selection and block generation
    section_rudiments: Dict[str, Dict[str, str]] = {}
    section_palettes: Dict[str, SectionPalette] = {}
    previous_section_type = None
    previous_rudiments = None

    # Generate palettes for all sections
    for part in song_structure.parts:
        section = _find_section(analysis, part)
        if section is None:
            continue
        palette = generate_palette(
            section, part.bpm, key_signature,
            num_colors=3, global_centroid_range=centroid_range,
            complementary_range=autogen_config.color_complementary_range,
        )
        section_palettes[part.name] = palette

    # Ensure cross-section contrast
    section_types = {p.name: p.name.lower().split()[0] for p in song_structure.parts}
    ensure_section_contrast(section_palettes, section_types, autogen_config.cross_section_contrast_min)

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

        palette = section_palettes.get(part.name)
        section_type = section_types.get(part.name, "generic")

        # Select active groups based on spectral richness
        active_groups = select_active_groups(group_classifications, section.spectral_richness)
        vocal_weights = apply_vocal_rule(group_classifications, section.vocal_presence)
        gobo_prism = get_gobo_prism_groups(
            group_classifications, section.spectral_richness,
            autogen_config.spectral_richness_gobo_threshold,
            autogen_config.spectral_richness_prism_threshold,
        )

        # Select groove and fill rudiments
        groove_name, fill_name = select_groove_and_fill(
            section, part.bpm, autogen_config,
            previous_section_rudiments=previous_rudiments,
            section_type=section_type,
            previous_section_type=previous_section_type,
        )

        # Select movement rudiment for moving heads
        movement_rudiments = get_movement_rudiments()
        movement_name = _select_movement_rudiment(section, part.bpm)

        # Store for cross-section contrast
        current_rudiments = {"intensity": groove_name, "movement": movement_name}
        section_rudiments[part.name] = current_rudiments
        previous_rudiments = current_rudiments
        previous_section_type = section_type

        # Generate blocks for each active group
        for group_name in active_groups:
            if group_name not in lanes:
                continue

            gc = group_classifications[group_name]
            weight = vocal_weights.get(group_name, 1.0)

            # Build phrase structure
            _generate_section_blocks(
                lane=lanes[group_name],
                part=part,
                groove_name=groove_name,
                fill_name=fill_name,
                movement_name=movement_name if gc.has_moving_heads else None,
                palette=palette,
                gobo_prism=gobo_prism.get(group_name, {}),
                weight=weight,
                config=autogen_config,
                color_index=list(group_classifications.keys()).index(group_name) % 3,
            )

    return list(lanes.values())


def _find_section(analysis: SongAnalysis, part: ShowPart) -> Optional[SectionAnalysis]:
    """Find the SectionAnalysis matching a ShowPart by name."""
    for section in analysis.sections:
        if section.name == part.name:
            return section
    return None


def _select_movement_rudiment(section: SectionAnalysis, bpm: float) -> str:
    """Select a movement rudiment based on section energy.

    Higher energy → more dynamic shapes. Lower energy → static or slow.
    """
    energy = section.spectral_flux_avg + section.transient_sharpness
    if energy > 1.2:
        return "circle"
    elif energy > 0.8:
        return "figure_8"
    elif energy > 0.5:
        return "bounce"
    elif energy > 0.3:
        return "linear_sweep"
    else:
        return "static"


def _generate_section_blocks(
    lane: LightLane,
    part: ShowPart,
    groove_name: str,
    fill_name: str,
    movement_name: Optional[str],
    palette: Optional[SectionPalette],
    gobo_prism: Dict[str, bool],
    weight: float,
    config: AutogenConfig,
    color_index: int,
):
    """Generate LightBlocks for one fixture group in one section.

    Splits section into phrases (groove + fill) per the theory.
    """
    section_start = part.start_time
    section_end = part.start_time + part.duration

    if section_end <= section_start:
        return

    # Calculate phrase timing
    beats_per_bar = 4  # Assume 4/4
    seconds_per_beat = 60.0 / part.bpm
    seconds_per_bar = seconds_per_beat * beats_per_bar
    phrase_bars = config.phrase_length_bars
    phrase_duration = phrase_bars * seconds_per_bar

    groove_bars = int(phrase_bars * config.groove_fill_ratio)
    fill_bars = phrase_bars - groove_bars
    groove_duration = groove_bars * seconds_per_bar
    fill_duration = fill_bars * seconds_per_bar

    # Generate phrases
    current_time = section_start
    while current_time < section_end - 0.01:
        remaining = section_end - current_time

        if remaining < phrase_duration:
            # Last partial phrase — all groove
            groove_end = min(current_time + remaining, section_end)
            _add_light_block(
                lane, current_time, groove_end,
                groove_name, movement_name, palette,
                gobo_prism, weight, part.bpm, color_index,
            )
            break

        # Groove portion
        groove_end = current_time + groove_duration
        _add_light_block(
            lane, current_time, groove_end,
            groove_name, movement_name, palette,
            gobo_prism, weight, part.bpm, color_index,
        )

        # Fill portion
        fill_start = groove_end
        fill_end = fill_start + fill_duration
        _add_light_block(
            lane, fill_start, fill_end,
            fill_name, movement_name, palette,
            gobo_prism, weight, part.bpm, color_index,
        )

        current_time = fill_end


def _add_light_block(
    lane: LightLane,
    start_time: float,
    end_time: float,
    intensity_rudiment: str,
    movement_rudiment: Optional[str],
    palette: Optional[SectionPalette],
    gobo_prism: Dict[str, bool],
    weight: float,
    bpm: float,
    color_index: int,
):
    """Create and add a single LightBlock to a lane."""
    # Dimmer block
    dimmer = rudiment_to_dimmer_block(
        intensity_rudiment,
        {"intensity": weight, "speed": 1.0},
        start_time, end_time,
    )
    dimmer_blocks = [dimmer]

    # Colour block from palette
    colour_blocks = []
    if palette and palette.colors:
        color = palette.colors[color_index % len(palette.colors)]
        colour_blocks.append(ColourBlock(
            start_time=start_time,
            end_time=end_time,
            red=float(color[0]),
            green=float(color[1]),
            blue=float(color[2]),
        ))

    # Movement block (if applicable)
    movement_blocks = []
    if movement_rudiment:
        mb = rudiment_to_movement_block(
            movement_rudiment, {"speed": 1.0},
            start_time, end_time,
        )
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
