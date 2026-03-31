"""Tests for group activation roles in auto-generation."""
import pytest

from autogen.spatial import (
    ActivationRole, GroupActivation, GroupClassification,
    compute_richness_weights,
)
from autogen.generator import _generate_section_blocks, MovementStrategy
from autogen.matcher import AutogenConfig
from config.models import LightLane, ShowPart


# ── Helpers ──────────────────────────────────────────────


def _make_classifications(with_mh=True):
    """Create a typical set of group classifications."""
    groups = {
        "Front Wash": GroupClassification("Front Wash", "front", has_moving_heads=False),
        "Bars": GroupClassification("Bars", "mid", has_moving_heads=False),
        "Moving Heads": GroupClassification("Moving Heads", "back", has_moving_heads=True),
    }
    if not with_mh:
        del groups["Moving Heads"]
    return groups


def _make_lane():
    return LightLane(
        name="Test", fixture_targets=["Test"], muted=False, solo=False, light_blocks=[]
    )


def _make_part(num_bars=8, bpm=120.0):
    return ShowPart(
        name="Test Section", color="#FFFFFF", signature="4/4",
        bpm=bpm, num_bars=num_bars, transition="instant",
        start_time=0.0, duration=num_bars * (60.0 / bpm) * 4,
    )


# ── Role Assignment Tests ────────────────────────────────


class TestRoleAssignment:

    def test_high_energy_all_full(self):
        groups = _make_classifications()
        result = compute_richness_weights(groups, 0.8, 0.8, relative_energy=0.8)
        for name, activation in result.items():
            assert activation.role == ActivationRole.FULL
            assert activation.weight > 0.0

    def test_medium_energy_mh_fill_only(self):
        groups = _make_classifications()
        result = compute_richness_weights(groups, 0.5, 0.5, relative_energy=0.5)
        mh = result["Moving Heads"]
        assert mh.role == ActivationRole.FILL_ONLY
        assert mh.weight > 0.0
        # Core groups should be FULL
        assert result["Front Wash"].role == ActivationRole.FULL

    def test_low_energy_core_groove_only(self):
        groups = _make_classifications()
        result = compute_richness_weights(groups, 0.3, 0.3, relative_energy=0.25)
        front = result["Front Wash"]
        assert front.role == ActivationRole.GROOVE_ONLY
        assert front.weight > 0.0

    def test_low_energy_mh_fill_only_above_threshold(self):
        groups = _make_classifications()
        result = compute_richness_weights(groups, 0.3, 0.3, relative_energy=0.30)
        mh = result["Moving Heads"]
        assert mh.role == ActivationRole.FILL_ONLY
        assert mh.weight > 0.0

    def test_low_energy_mh_inactive_below_threshold(self):
        groups = _make_classifications()
        result = compute_richness_weights(groups, 0.2, 0.2, relative_energy=0.20)
        mh = result["Moving Heads"]
        assert mh.weight <= 0.0

    def test_very_quiet_single_groove(self):
        groups = _make_classifications()
        result = compute_richness_weights(groups, 0.1, 0.1, relative_energy=0.1)
        active = [n for n, a in result.items() if a.weight > 0.0]
        assert len(active) == 1
        assert result[active[0]].role == ActivationRole.GROOVE_ONLY

    def test_no_moving_heads_no_fill_only(self):
        groups = _make_classifications(with_mh=False)
        result = compute_richness_weights(groups, 0.5, 0.5, relative_energy=0.5)
        for name, activation in result.items():
            if activation.weight > 0.0:
                assert activation.role != ActivationRole.FILL_ONLY

    def test_empty_groups(self):
        result = compute_richness_weights({}, 0.5, 0.5, 0.5)
        assert result == {}


# ── Block Generation Role Tests ──────────────────────────


class TestBlockGenerationRoles:

    def _count_blocks(self, role, num_bars=8, phrase_bars=4, ratio=0.75):
        lane = _make_lane()
        part = _make_part(num_bars=num_bars)
        config = AutogenConfig(phrase_length_bars=phrase_bars, groove_fill_ratio=ratio)
        _generate_section_blocks(
            lane=lane, part=part,
            groove_name="pulse", fill_name="stroke",
            movement_strategy=None,
            color_assignment=None,
            gobo_prism={},
            weight=1.0, config=config,
            color_index=0, effect_speed="1",
            role=role,
        )
        return len(lane.light_blocks)

    def test_full_role_generates_groove_and_fill(self):
        # 8 bars / 4-bar phrases = 2 phrases, each with groove + fill = 4 blocks
        count = self._count_blocks(ActivationRole.FULL)
        assert count == 4  # 2 groove + 2 fill

    def test_groove_only_skips_fills(self):
        # 2 phrases, groove only = 2 blocks
        count = self._count_blocks(ActivationRole.GROOVE_ONLY)
        assert count == 2

    def test_fill_only_skips_grooves(self):
        # 2 phrases, fill only = 2 blocks
        count = self._count_blocks(ActivationRole.FILL_ONLY)
        assert count == 2

    def test_fill_only_no_remainder_blocks(self):
        # 9 bars / 4-bar phrases = 2 full phrases + 1 remainder bar
        # Full: 2 groove + 2 fill + 1 remainder = 5
        # Fill-only: 2 fill + 0 remainder = 2
        full_count = self._count_blocks(ActivationRole.FULL, num_bars=9)
        fill_count = self._count_blocks(ActivationRole.FILL_ONLY, num_bars=9)
        assert full_count == 5
        assert fill_count == 2

    def test_groove_only_gets_remainder(self):
        # 9 bars: 2 groove + 1 remainder = 3
        count = self._count_blocks(ActivationRole.GROOVE_ONLY, num_bars=9)
        assert count == 3

    def test_short_section_fill_only_produces_nothing(self):
        # Section shorter than phrase: fill_bars=0, so fill-only has nothing
        count = self._count_blocks(ActivationRole.FILL_ONLY, num_bars=2, phrase_bars=4)
        assert count == 0

    def test_fill_only_block_names_are_fill(self):
        lane = _make_lane()
        part = _make_part(num_bars=8)
        config = AutogenConfig(phrase_length_bars=4, groove_fill_ratio=0.75)
        _generate_section_blocks(
            lane=lane, part=part,
            groove_name="pulse", fill_name="stroke",
            movement_strategy=None,
            color_assignment=None,
            gobo_prism={},
            weight=1.0, config=config,
            color_index=0, effect_speed="1",
            role=ActivationRole.FILL_ONLY,
        )
        for block in lane.light_blocks:
            assert "stroke" in block.effect_name
