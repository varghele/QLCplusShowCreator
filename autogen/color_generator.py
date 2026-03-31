"""Color palette generator for algorithmic show generation.

Implements the two-axis color model from the theory:
- Axis 1 (Brightness): spectral centroid → lighter/darker hues
- Axis 2 (Mood): key signature + centroid + tempo → warm/cool colors

Generates 2-4 color palettes per section with cross-section contrast.
"""

import colorsys
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

from audio.spectral_analysis import SectionAnalysis


@dataclass
class SectionPalette:
    """Color palette for a section."""
    colors: List[Tuple[int, int, int]] = field(default_factory=list)  # RGB tuples
    mood_position: float = 0.0       # -1.0 (dark/cool) to 1.0 (bright/warm)
    brightness_position: float = 0.5  # 0.0 (low) to 1.0 (high)


# ──────────────────────────────────────────────
# Mood calculation
# ──────────────────────────────────────────────

def _key_signature_mood(key_signature: Optional[str]) -> float:
    """Map key signature to mood value. Major=+0.5, Minor=-0.5, None=0.0."""
    if not key_signature:
        return 0.0
    key_lower = key_signature.lower()
    if "major" in key_lower or "maj" in key_lower:
        return 0.5
    elif "minor" in key_lower or "min" in key_lower:
        return -0.5
    return 0.0


def _centroid_mood(centroid_avg: float, global_centroid_range: Tuple[float, float]) -> float:
    """Map spectral centroid to mood. High centroid=bright=+, Low=dark=-.

    Returns -0.3 to +0.3.
    """
    low, high = global_centroid_range
    if high <= low:
        return 0.0
    normalized = (centroid_avg - low) / (high - low)
    return (normalized - 0.5) * 0.6  # -0.3 to +0.3


def _tempo_mood(bpm: float) -> float:
    """Map tempo to mood. Fast=warm=+, Slow=cool=-.

    Returns -0.2 to +0.2.
    """
    # 60 BPM → -0.2, 120 BPM → 0.0, 180+ BPM → +0.2
    normalized = max(0.0, min(1.0, (bpm - 60.0) / 120.0))
    return (normalized - 0.5) * 0.4  # -0.2 to +0.2


def compute_mood(
    section: SectionAnalysis,
    bpm: float,
    key_signature: Optional[str] = None,
    global_centroid_range: Tuple[float, float] = (500.0, 5000.0),
) -> float:
    """Compute mood position for a section.

    Returns:
        -1.0 (dark/cool) to 1.0 (bright/warm)
    """
    mood = (
        _key_signature_mood(key_signature)
        + _centroid_mood(section.spectral_centroid_avg, global_centroid_range)
        + _tempo_mood(bpm)
    )
    return max(-1.0, min(1.0, mood))


# ──────────────────────────────────────────────
# Brightness calculation
# ──────────────────────────────────────────────

def compute_brightness(
    section: SectionAnalysis,
    global_centroid_range: Tuple[float, float] = (500.0, 5000.0),
) -> float:
    """Compute brightness position from spectral centroid.

    Returns:
        0.0 (low/dark) to 1.0 (high/bright)
    """
    low, high = global_centroid_range
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, (section.spectral_centroid_avg - low) / (high - low)))


# ──────────────────────────────────────────────
# Palette generation
# ──────────────────────────────────────────────

def _mood_to_base_hue(mood: float) -> float:
    """Map mood position to a base hue (0-360 degrees).

    Warm mood → warm hues (reds, oranges, yellows: 0-60)
    Neutral → greens, teals (90-180)
    Cool mood → cool hues (blues, purples: 210-300)
    """
    # mood: -1.0 (cool) to +1.0 (warm)
    # Map to hue: warm=30 (orange), neutral=150 (teal), cool=250 (blue-purple)
    if mood >= 0:
        # Warm side: 30 (orange) → 0 (red) as mood increases
        hue = 30 - mood * 30
    else:
        # Cool side: 150 (teal) → 270 (purple) as mood decreases
        hue = 150 + abs(mood) * 120
    return hue % 360


def _generate_complementary_hues(
    base_hue: float,
    num_colors: int,
    complementary_range: Tuple[float, float] = (30.0, 120.0),
) -> List[float]:
    """Generate complementary hues within a range of the base hue.

    Colors are spread within the complementary range to be cohesive
    but not uniform.
    """
    if num_colors <= 1:
        return [base_hue]

    min_offset, max_offset = complementary_range
    hues = [base_hue]

    # Spread additional hues within the complementary range
    for i in range(1, num_colors):
        # Alternate sides of the base hue
        fraction = i / num_colors
        offset = min_offset + fraction * (max_offset - min_offset)
        if i % 2 == 1:
            hues.append((base_hue + offset) % 360)
        else:
            hues.append((base_hue - offset) % 360)

    return hues


def generate_palette(
    section: SectionAnalysis,
    bpm: float,
    key_signature: Optional[str] = None,
    num_colors: int = 3,
    global_centroid_range: Tuple[float, float] = (500.0, 5000.0),
    complementary_range: Tuple[float, float] = (30.0, 120.0),
) -> SectionPalette:
    """Generate a color palette for a section based on audio mood.

    Args:
        section: Audio analysis results for the section
        bpm: Section BPM
        key_signature: Optional key signature (e.g., "C major", "A minor")
        num_colors: Number of colors in palette (2-4)
        global_centroid_range: Min/max spectral centroid across song for normalization
        complementary_range: Hue angle range for complementary colors (degrees)

    Returns:
        SectionPalette with colors and mood/brightness positions
    """
    num_colors = max(2, min(4, num_colors))

    mood = compute_mood(section, bpm, key_signature, global_centroid_range)
    brightness = compute_brightness(section, global_centroid_range)

    base_hue = _mood_to_base_hue(mood)
    hues = _generate_complementary_hues(base_hue, num_colors, complementary_range)

    # Convert to RGB
    colors = []
    for i, hue in enumerate(hues):
        # Saturation: warm mood → more saturated, cool → less saturated
        # Base saturation 0.6-1.0
        saturation = 0.6 + 0.4 * abs(mood)

        # Slight variation per color
        saturation = max(0.3, min(1.0, saturation + (i * 0.05 - 0.05)))

        # Lightness from brightness axis
        # Range: 0.3 (dark) to 0.8 (bright)
        lightness = 0.3 + brightness * 0.5

        # Slight variation per color
        lightness = max(0.2, min(0.9, lightness + (i * 0.08 - 0.08)))

        r, g, b = colorsys.hls_to_rgb(hue / 360.0, lightness, saturation)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))

    return SectionPalette(
        colors=colors,
        mood_position=mood,
        brightness_position=brightness,
    )


# ──────────────────────────────────────────────
# Cross-section contrast
# ──────────────────────────────────────────────

def _hue_distance(h1: float, h2: float) -> float:
    """Compute minimum angular distance between two hues (0-180)."""
    diff = abs(h1 - h2) % 360
    return min(diff, 360 - diff)


def _palette_avg_hue(palette: SectionPalette) -> float:
    """Get average hue of a palette."""
    if not palette.colors:
        return 0.0
    hues = []
    for r, g, b in palette.colors:
        h, _, _ = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        hues.append(h * 360)
    return sum(hues) / len(hues)


def ensure_section_contrast(
    palettes: Dict[str, SectionPalette],
    section_types: Dict[str, str],
    min_contrast: float = 0.3,
) -> Dict[str, SectionPalette]:
    """Adjust palettes to ensure sufficient contrast between different section types.

    Sections of the same type (e.g., two verses) can share similar palettes,
    but different types (verse vs chorus) should be visually distinct.

    Args:
        palettes: {section_name: palette}
        section_types: {section_name: type} e.g. {"Verse 1": "verse", "Chorus": "chorus"}
        min_contrast: Minimum required hue distance (0-1, fraction of 180 degrees)

    Returns:
        Adjusted palettes
    """
    min_hue_distance = min_contrast * 180  # Convert to degrees

    # Group sections by type
    type_palettes: Dict[str, List[str]] = {}
    for name, stype in section_types.items():
        type_palettes.setdefault(stype, []).append(name)

    # Check contrast between each pair of different section types
    type_hues: Dict[str, float] = {}
    for stype, names in type_palettes.items():
        # Use the first section of each type as representative
        if names[0] in palettes:
            type_hues[stype] = _palette_avg_hue(palettes[names[0]])

    types_list = list(type_hues.keys())
    for i in range(len(types_list)):
        for j in range(i + 1, len(types_list)):
            t1, t2 = types_list[i], types_list[j]
            dist = _hue_distance(type_hues[t1], type_hues[t2])

            if dist < min_hue_distance:
                # Shift the second type's palette away
                shift = min_hue_distance - dist + 10  # Extra margin
                for name in type_palettes[t2]:
                    if name in palettes:
                        palette = palettes[name]
                        shifted_colors = []
                        for r, g, b in palette.colors:
                            h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
                            h = ((h * 360 + shift) % 360) / 360.0
                            r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
                            shifted_colors.append((int(r2 * 255), int(g2 * 255), int(b2 * 255)))
                        palette.colors = shifted_colors

    return palettes
