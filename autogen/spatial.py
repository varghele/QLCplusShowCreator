"""Spatial lighting model for algorithmic show generation.

Implements Section 6 of the theory: fixture group classification by
stage position, vocal focus rules, density scaling, and gobo/prism activation.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from config.models import Configuration, FixtureGroup, Spot


@dataclass
class GroupClassification:
    """Stage position classification for a fixture group."""
    name: str
    zone: str  # "front", "mid", "back", "overhead"
    has_moving_heads: bool = False
    has_gobos: bool = False
    has_prism: bool = False


def classify_fixture_groups(config: Configuration) -> Dict[str, GroupClassification]:
    """Classify each fixture group by stage position.

    Classification based on average Y and Z positions of group's fixtures,
    relative to stage dimensions.

    Returns:
        {group_name: GroupClassification}
    """
    stage_depth = config.stage_height  # Y axis = depth
    stage_z = 4.0  # Default ceiling height estimate

    classifications = {}
    for group_name, group in config.groups.items():
        if not group.fixtures:
            continue

        # Average position
        avg_y = sum(f.y for f in group.fixtures) / len(group.fixtures)
        avg_z = sum(
            f.get_effective_z(group) if hasattr(f, 'get_effective_z') else getattr(f, 'z', 0.0)
            for f in group.fixtures
        ) / len(group.fixtures)

        # Classify zone
        if avg_z > stage_z * 0.5:
            zone = "overhead"
        elif stage_depth > 0 and avg_y < stage_depth * 0.33:
            zone = "front"
        elif stage_depth > 0 and avg_y > stage_depth * 0.66:
            zone = "back"
        else:
            zone = "mid"

        # Detect capabilities
        has_mh = any(
            getattr(f, 'type', '') in ('MH', 'WASH')
            for f in group.fixtures
        )

        capabilities = group.capabilities
        has_special = False
        if capabilities:
            has_special = getattr(capabilities, 'has_special', False)
        # If no capabilities detected, infer from fixture type (MH/WASH often have gobos)
        if not has_special and has_mh:
            has_special = True
        has_gobos = has_special
        has_prism = has_special

        classifications[group_name] = GroupClassification(
            name=group_name,
            zone=zone,
            has_moving_heads=has_mh,
            has_gobos=has_gobos,
            has_prism=has_prism,
        )

    return classifications


def apply_vocal_rule(
    group_classifications: Dict[str, GroupClassification],
    vocal_presence: float,
) -> Dict[str, float]:
    """Compute intensity weight per group based on vocal presence.

    When vocals are present, front-stage groups get boosted.
    When absent, back/overhead groups get boosted.

    Returns:
        {group_name: weight} where weight is 0.0-1.0 multiplier
    """
    weights = {}
    for name, gc in group_classifications.items():
        if vocal_presence > 0.5:
            # Vocals present — prioritize front
            if gc.zone == "front":
                weights[name] = 1.0
            elif gc.zone == "mid":
                weights[name] = 0.7
            elif gc.zone == "back":
                weights[name] = 0.4
            else:  # overhead
                weights[name] = 0.5
        else:
            # No vocals — atmospheric
            if gc.zone == "front":
                weights[name] = 0.4
            elif gc.zone == "mid":
                weights[name] = 0.6
            elif gc.zone == "back":
                weights[name] = 1.0
            else:  # overhead
                weights[name] = 0.9

    return weights


def compute_richness_weights(
    group_classifications: Dict[str, GroupClassification],
    spectral_richness: float,
    spectral_flux: float = 0.5,
    relative_energy: float = 0.5,
) -> Dict[str, float]:
    """Compute intensity weight per group based on relative energy level.

    Uses tiered activation: quiet sections have fewer groups active.
    Returns 0.0 for groups that should be inactive (no blocks generated).

    Args:
        relative_energy: 0.0-1.0, this section's energy relative to the song's range.
            Computed by the generator from spectral flux normalization.

    Returns:
        {group_name: weight} where 0.0 = inactive, 0.1-1.0 = active
    """
    if not group_classifications:
        return {}

    # Sort groups by activation priority: front first, back last
    zone_priority = {"front": 0, "mid": 1, "overhead": 2, "back": 3}
    sorted_groups = sorted(
        group_classifications.items(),
        key=lambda x: zone_priority.get(x[1].zone, 2)
    )

    total = len(sorted_groups)
    weights = {}

    if relative_energy < 0.15:
        # Very quiet: only 1 primary group, dimmed
        for i, (name, gc) in enumerate(sorted_groups):
            weights[name] = 0.3 if i == 0 else 0.0
    elif relative_energy < 0.35:
        # Low: 1-2 groups, primary full, secondary dimmed
        num_active = max(1, min(2, total))
        for i, (name, gc) in enumerate(sorted_groups):
            if i < num_active:
                weights[name] = 0.7 if i == 0 else 0.4
            else:
                weights[name] = 0.0
    elif relative_energy < 0.65:
        # Medium: most groups active, back dimmed
        num_active = max(2, int(total * 0.75))
        for i, (name, gc) in enumerate(sorted_groups):
            if i < num_active:
                weights[name] = 1.0 - i * 0.1
            else:
                weights[name] = 0.0
    else:
        # High: all groups active
        for name in group_classifications:
            weights[name] = 1.0

    return weights


def get_gobo_prism_groups(
    group_classifications: Dict[str, GroupClassification],
    spectral_richness: float,
    gobo_threshold: float = 0.7,
    prism_threshold: float = 0.8,
) -> Dict[str, Dict[str, bool]]:
    """Determine which groups should have gobos/prisms activated.

    Returns:
        {group_name: {"gobo": bool, "prism": bool}}
    """
    result = {}
    for name, gc in group_classifications.items():
        result[name] = {
            "gobo": gc.has_gobos and spectral_richness >= gobo_threshold,
            "prism": gc.has_prism and spectral_richness >= prism_threshold,
        }
    return result


def ensure_default_spots(config: Configuration) -> List[str]:
    """Create default plane-center spots if none exist. Returns list of spot names.

    Creates center spots for sweep planes:
    - "Crowd" — center of audience area (y=0), moving heads sweep across with amplitude
    - "Stage" — center of stage area, for atmospheric sweeps
    User-defined spots are preserved and take priority.
    """
    if config.spots:
        return list(config.spots.keys())

    stage_w = config.stage_width if hasattr(config, 'stage_width') and config.stage_width else 8.0
    stage_d = config.stage_height if hasattr(config, 'stage_height') and config.stage_height else 6.0

    # Plane center spots — shapes sweep around these with amplitude controlling width
    default_spots = {
        "Crowd": Spot(name="Crowd", x=0.0, y=0.0, z=0.0),
        "Stage": Spot(name="Stage", x=0.0, y=stage_d * 0.5, z=0.0),
    }

    for name, spot in default_spots.items():
        config.spots[name] = spot

    return list(default_spots.keys())
