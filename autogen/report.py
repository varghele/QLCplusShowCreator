"""Generation report — captures all decisions made during auto-generation.

Used by the Generation Inspector dashboard to visualize why the algorithm
chose specific rudiments, roles, colors, and activation patterns.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class MatchScoreEntry:
    """One candidate's scoring breakdown."""
    rudiment_name: str
    total_score: float
    envelope_similarity: float = 0.0
    repetition_rate_fit: float = 0.0
    flux_level_fit: float = 0.0
    coherence_score: float = 0.0


@dataclass
class GroupSectionReport:
    """Decisions made for one fixture group in one section."""
    weight: float = 0.0              # richness weight (0=inactive)
    vocal_weight: float = 1.0
    role: str = "full"               # "full", "groove", "fill"
    groove_rudiment: str = "static"
    fill_rudiment: str = "static"
    groove_category: str = "flat"    # envelope category of groove rudiment
    effect_speed: str = "1"
    # Top match candidates with sub-score breakdown
    match_scores: List[MatchScoreEntry] = field(default_factory=list)


@dataclass
class SectionReport:
    """All decisions for one song section."""
    name: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    # Audio analysis values
    spectral_flux: float = 0.0
    transient_sharpness: float = 0.0
    spectral_richness: float = 0.0
    vocal_presence: float = 0.0
    spectral_centroid: float = 0.0
    relative_energy: float = 0.0
    # Per-group decisions
    group_reports: Dict[str, GroupSectionReport] = field(default_factory=dict)
    # Section-level decisions
    movement_shape: str = "static"
    movement_amplitude: float = 50.0
    movement_target: str = ""
    color_rgb: List[Tuple[int, int, int]] = field(default_factory=list)


@dataclass
class GenerationReport:
    """Complete record of all decisions made during show generation."""
    sections: List[SectionReport] = field(default_factory=list)
    song_palette_rgb: List[Tuple[int, int, int]] = field(default_factory=list)
    group_names: List[str] = field(default_factory=list)

    def get_section_at(self, time: float) -> Optional[SectionReport]:
        """Find the section report active at a given time."""
        for section in self.sections:
            if section.start_time <= time < section.end_time:
                return section
        # Check last section (end boundary)
        if self.sections and time >= self.sections[-1].start_time:
            return self.sections[-1]
        return None
