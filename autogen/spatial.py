"""Spatial lighting model for algorithmic show generation.

Implements Section 6 of the theory: fixture group classification by
stage position, vocal focus rules, density scaling, and gobo/prism activation.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from config.models import Configuration, FixtureGroup


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
        has_gobos = False
        has_prism = False
        if capabilities:
            has_gobos = getattr(capabilities, 'has_gobo', False)
            has_prism = getattr(capabilities, 'has_prism', False)

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


def select_active_groups(
    group_classifications: Dict[str, GroupClassification],
    spectral_richness: float,
) -> List[str]:
    """Select which fixture groups are active based on spectral richness.

    Low richness → fewer groups. High richness → all groups.

    Returns:
        List of active group names
    """
    all_groups = sorted(group_classifications.keys())
    if not all_groups:
        return []

    # Scale: richness 0.0 → 1 group, richness 1.0 → all groups
    num_active = max(1, int(len(all_groups) * (0.3 + 0.7 * spectral_richness)))
    return all_groups[:num_active]


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
