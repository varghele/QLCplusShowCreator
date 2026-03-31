"""Rudiment matching engine for algorithmic show generation.

Implements three-dimensional rudiment matching (Section 2.5) and
dual-criteria scoring (Section 5, Steps 4-7) from the theory.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from audio.spectral_analysis import SectionAnalysis
from rudiments.rudiment import (
    Rudiment, RudimentType, EnvelopeCategory, CycleMode,
)
from rudiments.registry import get_intensity_rudiments, get_movement_rudiments


@dataclass
class MatchScore:
    """Scoring result for a rudiment candidate."""
    rudiment_name: str
    envelope_similarity: float = 0.0  # 0.0 to 1.0
    repetition_rate_fit: float = 0.0  # 0.0 to 1.0 (cycling only)
    flux_level_fit: float = 0.0       # 0.0 to 1.0
    fidelity_score: float = 0.0       # Weighted parameter fidelity
    coherence_score: float = 0.0      # Musical coherence
    total_score: float = 0.0


@dataclass
class AutogenConfig:
    """Configuration for automatic show generation."""
    groove_fill_ratio: float = 0.75
    phrase_length_bars: int = 4
    fidelity_weight: float = 0.6
    coherence_weight: float = 0.4
    tolerance_band_width: float = 0.2
    spectral_richness_gobo_threshold: float = 0.7
    spectral_richness_prism_threshold: float = 0.8
    cross_section_contrast_min: float = 0.3
    color_complementary_range: Tuple[float, float] = (30.0, 120.0)


# ──────────────────────────────────────────────
# Envelope comparison
# ──────────────────────────────────────────────

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors. Returns 0.0-1.0."""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return max(0.0, dot / (mag_a * mag_b))


def score_envelope_similarity(
    rudiment_envelope: List[float],
    target_envelope: List[float],
) -> float:
    """Compare rudiment envelope shape to target flux contour.

    Uses cosine similarity on normalized vectors.
    """
    return cosine_similarity(rudiment_envelope, target_envelope)


# ──────────────────────────────────────────────
# Transient character filtering
# ──────────────────────────────────────────────

# Percussive audio favors these envelope categories
PERCUSSIVE_CATEGORIES = {
    EnvelopeCategory.SPIKE,
    EnvelopeCategory.OSCILLATING,
    EnvelopeCategory.STOCHASTIC,
}

# Sustained audio favors these
SUSTAINED_CATEGORIES = {
    EnvelopeCategory.FLAT,
    EnvelopeCategory.RAMP,
    EnvelopeCategory.OSCILLATING,
    EnvelopeCategory.ROLLING,
}


def _transient_category_score(rudiment: Rudiment, transient_sharpness: float) -> float:
    """Score how well a rudiment's envelope category matches the transient character.

    Returns 0.0-1.0.
    """
    category = rudiment.envelope.category

    if transient_sharpness > 0.6:
        # Percussive — prefer spike/oscillating/stochastic
        return 1.0 if category in PERCUSSIVE_CATEGORIES else 0.4
    elif transient_sharpness < 0.3:
        # Sustained — prefer flat/ramp/oscillating/rolling
        return 1.0 if category in SUSTAINED_CATEGORIES else 0.4
    else:
        # Mixed — all categories acceptable
        return 0.8


# ──────────────────────────────────────────────
# Repetition rate scoring
# ──────────────────────────────────────────────

def score_repetition_rate(
    rudiment: Rudiment,
    target_flux_frequency: float,
    bpm: float,
    speed_range: Tuple[float, float] = (0.25, 4.0),
) -> float:
    """Score how well the cycle rate matches audio flux frequency.

    Only applicable to cycling rudiments. One-shot rudiments get 1.0.

    Args:
        rudiment: The rudiment to score
        target_flux_frequency: Estimated rate of spectral flux changes (cycles/sec)
        bpm: Section BPM
        speed_range: Allowed speed multiplier range

    Returns:
        0.0-1.0 score
    """
    if rudiment.envelope.cycle_mode == CycleMode.ONE_SHOT:
        return 1.0

    if bpm <= 0 or target_flux_frequency <= 0:
        return 0.5

    beats_per_sec = bpm / 60.0

    # Check if any speed multiplier in range produces a matching cycle rate
    best_match = 0.0
    for speed in [0.25, 0.5, 1.0, 2.0, 4.0]:
        if speed < speed_range[0] or speed > speed_range[1]:
            continue
        # Cycles per second at this speed (assuming 1 cycle per beat)
        cycle_rate = beats_per_sec * speed
        # How close to the target?
        if target_flux_frequency > 0:
            ratio = cycle_rate / target_flux_frequency
            # Perfect match = ratio of 1.0, score decreases with distance
            log_ratio = abs(math.log2(max(0.01, ratio)))
            match = max(0.0, 1.0 - log_ratio * 0.5)
            best_match = max(best_match, match)

    return best_match


# ──────────────────────────────────────────────
# Flux level scoring
# ──────────────────────────────────────────────

def score_flux_level(
    rudiment: Rudiment,
    target_flux: float,
    tolerance: float = 0.2,
) -> float:
    """Score how well the rudiment's average flux matches the target.

    Args:
        rudiment: The rudiment to score
        target_flux: Target flux level (0.0-1.0)
        tolerance: Tolerance band width

    Returns:
        0.0-1.0 score (1.0 = within tolerance, decreases outside)
    """
    diff = abs(rudiment.average_flux - target_flux)
    if diff <= tolerance:
        return 1.0
    # Smooth falloff outside tolerance
    return max(0.0, 1.0 - (diff - tolerance) / 0.5)


# ──────────────────────────────────────────────
# Musical coherence scoring
# ──────────────────────────────────────────────

def score_musical_coherence(
    groove_rudiment: str,
    fill_rudiment: Optional[str],
    previous_section_rudiments: Optional[Dict[str, str]],
    section_type: str,
    previous_section_type: Optional[str],
    groove_flux: float,
    fill_flux: float,
    config: AutogenConfig,
) -> float:
    """Score musical coherence of a rudiment selection.

    Rewards:
    - Cross-section contrast (different types get different rudiments)
    - Fill flux > groove flux

    Penalizes:
    - Identical selections across different section types
    """
    score = 0.5  # Baseline

    # Fill must have higher flux than groove
    if fill_rudiment and fill_flux > groove_flux:
        score += 0.2
    elif fill_rudiment and fill_flux <= groove_flux:
        score -= 0.3  # Penalty

    # Cross-section contrast
    if previous_section_rudiments and previous_section_type:
        if section_type != previous_section_type:
            # Different section type — reward different rudiment selection
            prev_rudiments = set(previous_section_rudiments.values())
            if groove_rudiment not in prev_rudiments:
                score += 0.3  # Good contrast
            else:
                score -= 0.2  # Same rudiment across different section types

    return max(0.0, min(1.0, score))


# ──────────────────────────────────────────────
# Main matching function
# ──────────────────────────────────────────────

def match_rudiments_to_section(
    section: SectionAnalysis,
    bpm: float,
    has_moving_heads: bool = False,
    previous_section_rudiments: Optional[Dict[str, str]] = None,
    section_type: str = "generic",
    previous_section_type: Optional[str] = None,
    config: Optional[AutogenConfig] = None,
) -> Dict[str, MatchScore]:
    """Select best intensity rudiment for a section.

    Applies the three-dimensional matching from theory Section 2.5:
    1. Filter by transient character
    2. Score envelope similarity
    3. Score repetition rate
    4. Score flux level

    Args:
        section: Audio analysis for this section
        bpm: Section BPM
        has_moving_heads: Whether fixture group has moving heads
        previous_section_rudiments: Rudiments used in previous section
        section_type: Section type (e.g., "verse", "chorus")
        previous_section_type: Previous section type
        config: Auto-generation configuration

    Returns:
        Dict of {rudiment_name: MatchScore} sorted by total_score descending
    """
    if config is None:
        config = AutogenConfig()

    intensity_rudiments = get_intensity_rudiments()
    target_flux = section.spectral_flux_avg
    target_envelope = section.spectral_flux_envelope
    transient = section.transient_sharpness

    # Estimate flux change frequency from envelope
    if len(target_envelope) > 1:
        # Count zero-crossings of derivative as proxy for frequency
        diffs = [target_envelope[i + 1] - target_envelope[i] for i in range(len(target_envelope) - 1)]
        zero_crossings = sum(1 for i in range(len(diffs) - 1) if diffs[i] * diffs[i + 1] < 0)
        section_duration = section.end_time - section.start_time
        target_flux_frequency = zero_crossings / max(0.1, section_duration) * 2
    else:
        target_flux_frequency = bpm / 60.0

    scores: Dict[str, MatchScore] = {}

    for name, rudiment in intensity_rudiments.items():
        ms = MatchScore(rudiment_name=name)

        # 1. Envelope shape similarity
        ms.envelope_similarity = score_envelope_similarity(
            rudiment.envelope.samples, target_envelope
        )

        # 2. Repetition rate fit
        ms.repetition_rate_fit = score_repetition_rate(
            rudiment, target_flux_frequency, bpm
        )

        # 3. Flux level fit
        ms.flux_level_fit = score_flux_level(
            rudiment, target_flux, config.tolerance_band_width
        )

        # Transient character bonus/penalty
        transient_score = _transient_category_score(rudiment, transient)

        # Fidelity score (weighted combination)
        ms.fidelity_score = (
            0.35 * ms.envelope_similarity
            + 0.25 * ms.repetition_rate_fit
            + 0.20 * ms.flux_level_fit
            + 0.20 * transient_score
        )

        # Coherence score
        ms.coherence_score = score_musical_coherence(
            groove_rudiment=name,
            fill_rudiment=None,
            previous_section_rudiments=previous_section_rudiments,
            section_type=section_type,
            previous_section_type=previous_section_type,
            groove_flux=rudiment.average_flux,
            fill_flux=0.0,
            config=config,
        )

        # Total score
        ms.total_score = (
            config.fidelity_weight * ms.fidelity_score
            + config.coherence_weight * ms.coherence_score
        )

        scores[name] = ms

    # Sort by total score descending
    scores = dict(sorted(scores.items(), key=lambda x: x[1].total_score, reverse=True))
    return scores


def select_groove_and_fill(
    section: SectionAnalysis,
    bpm: float,
    config: Optional[AutogenConfig] = None,
    previous_section_rudiments: Optional[Dict[str, str]] = None,
    section_type: str = "generic",
    previous_section_type: Optional[str] = None,
) -> Tuple[str, str]:
    """Select groove and fill rudiments for a section.

    The groove is the highest-scoring rudiment. The fill is the
    highest-scoring rudiment with higher flux than the groove.

    Returns:
        (groove_rudiment_name, fill_rudiment_name)
    """
    if config is None:
        config = AutogenConfig()

    scores = match_rudiments_to_section(
        section, bpm,
        previous_section_rudiments=previous_section_rudiments,
        section_type=section_type,
        previous_section_type=previous_section_type,
        config=config,
    )

    intensity_rudiments = get_intensity_rudiments()

    # Groove = highest scoring
    groove_name = next(iter(scores))
    groove_flux = intensity_rudiments[groove_name].average_flux

    # Fill = highest scoring with higher flux than groove
    fill_name = groove_name  # Fallback
    for name, ms in scores.items():
        if name == groove_name:
            continue
        if intensity_rudiments[name].average_flux > groove_flux:
            fill_name = name
            break

    return groove_name, fill_name
