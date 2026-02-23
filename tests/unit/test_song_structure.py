# tests/unit/test_song_structure.py
"""Unit tests for timeline/song_structure.py - timing and BPM calculations."""

import pytest
from config.models import ShowPart
from timeline.song_structure import SongStructure


@pytest.fixture
def two_part_structure():
    """SongStructure with two instant-transition parts."""
    parts = [
        ShowPart(name="Intro", color="#FF0000", signature="4/4",
                 bpm=120.0, num_bars=4, transition="instant"),
        ShowPart(name="Verse", color="#00FF00", signature="4/4",
                 bpm=140.0, num_bars=8, transition="instant"),
    ]
    ss = SongStructure()
    ss.load_from_show_parts(parts)
    return ss


@pytest.fixture
def gradual_structure():
    """SongStructure with a gradual BPM transition."""
    parts = [
        ShowPart(name="Intro", color="#FF0000", signature="4/4",
                 bpm=120.0, num_bars=4, transition="instant"),
        ShowPart(name="Build", color="#00FF00", signature="4/4",
                 bpm=160.0, num_bars=8, transition="gradual"),
    ]
    ss = SongStructure()
    ss.load_from_show_parts(parts)
    return ss


class TestSongStructureBasics:

    def test_empty_structure(self):
        ss = SongStructure()
        assert ss.get_total_duration() == 0.0
        assert ss.get_part_at_time(0.0) is None

    def test_default_bpm(self):
        ss = SongStructure()
        assert ss.default_bpm == 120.0

    def test_load_calculates_start_times(self, two_part_structure):
        ss = two_part_structure
        assert ss.parts[0].start_time == 0.0
        assert ss.parts[1].start_time > 0.0

    def test_instant_duration_4_4(self, two_part_structure):
        """4 bars of 4/4 at 120 BPM = 16 beats * 0.5s = 8.0s."""
        ss = two_part_structure
        assert abs(ss.parts[0].duration - 8.0) < 0.001

    def test_instant_duration_verse(self, two_part_structure):
        """8 bars of 4/4 at 140 BPM = 32 beats * (60/140) = ~13.71s."""
        ss = two_part_structure
        expected = 32 * (60.0 / 140.0)
        assert abs(ss.parts[1].duration - expected) < 0.01


class TestTimeSignatures:

    def test_3_4_signature(self):
        parts = [ShowPart(name="Waltz", color="#FFF", signature="3/4",
                          bpm=120.0, num_bars=4, transition="instant")]
        ss = SongStructure()
        ss.load_from_show_parts(parts)
        # 3/4: 3 beats per bar, 4 bars = 12 beats at 0.5s each = 6.0s
        assert abs(ss.parts[0].duration - 6.0) < 0.001

    def test_6_8_signature(self):
        parts = [ShowPart(name="Jig", color="#FFF", signature="6/8",
                          bpm=120.0, num_bars=4, transition="instant")]
        ss = SongStructure()
        ss.load_from_show_parts(parts)
        # 6/8: (6*4)/8 = 3 beats per bar, 4 bars = 12 beats
        assert abs(ss.parts[0].duration - 6.0) < 0.001

    def test_invalid_signature_fallback(self):
        parts = [ShowPart(name="Bad", color="#FFF", signature="invalid",
                          bpm=120.0, num_bars=2, transition="instant")]
        ss = SongStructure()
        ss.load_from_show_parts(parts)
        # Should fall back to 4 beats per bar: 2 bars * 4 beats * 0.5s = 4.0s
        assert abs(ss.parts[0].duration - 4.0) < 0.001


class TestGetPartAtTime:

    def test_at_start(self, two_part_structure):
        part = two_part_structure.get_part_at_time(0.0)
        assert part.name == "Intro"

    def test_midway(self, two_part_structure):
        part = two_part_structure.get_part_at_time(4.0)
        assert part.name == "Intro"

    def test_second_part(self, two_part_structure):
        ss = two_part_structure
        part = ss.get_part_at_time(ss.parts[1].start_time + 1.0)
        assert part.name == "Verse"

    def test_past_end_returns_last(self, two_part_structure):
        part = two_part_structure.get_part_at_time(9999.0)
        assert part.name == "Verse"

    def test_before_start_returns_none(self, two_part_structure):
        part = two_part_structure.get_part_at_time(-1.0)
        assert part is None


class TestGetBpmAtTime:

    def test_instant_transition(self, two_part_structure):
        ss = two_part_structure
        assert ss.get_bpm_at_time(0.0) == 120.0
        assert ss.get_bpm_at_time(ss.parts[1].start_time + 0.1) == 140.0

    def test_no_parts_returns_default(self):
        ss = SongStructure()
        assert ss.get_bpm_at_time(5.0) == ss.default_bpm

    def test_gradual_transition_interpolates(self, gradual_structure):
        ss = gradual_structure
        # At the start of the gradual part, BPM should be close to previous (120)
        build_start = ss.parts[1].start_time
        bpm_start = ss.get_bpm_at_time(build_start + 0.001)
        assert bpm_start < 160.0  # Should not be at target yet
        # Near the end, should be close to 160
        bpm_end = ss.get_bpm_at_time(build_start + ss.parts[1].duration - 0.001)
        assert bpm_end > bpm_start


class TestTotalDuration:

    def test_total_duration(self, two_part_structure):
        ss = two_part_structure
        total = ss.get_total_duration()
        expected = ss.parts[-1].start_time + ss.parts[-1].duration
        assert abs(total - expected) < 0.001

    def test_single_part(self):
        parts = [ShowPart(name="Solo", color="#FFF", signature="4/4",
                          bpm=120.0, num_bars=2, transition="instant")]
        ss = SongStructure()
        ss.load_from_show_parts(parts)
        assert abs(ss.get_total_duration() - 4.0) < 0.001


class TestFindNearestBeatTime:

    def test_snaps_to_beat(self):
        parts = [ShowPart(name="A", color="#FFF", signature="4/4",
                          bpm=120.0, num_bars=4, transition="instant")]
        ss = SongStructure()
        ss.load_from_show_parts(parts)
        # Beats at 0.0, 0.5, 1.0, 1.5, ...
        snapped = ss.find_nearest_beat_time(0.3)
        assert snapped in (0.0, 0.5)

    def test_empty_structure_default_grid(self):
        ss = SongStructure()
        # With default 120 BPM, beats at 0.5s intervals
        snapped = ss.find_nearest_beat_time(0.7)
        assert snapped in (0.5, 1.0)

    def test_negative_time(self):
        parts = [ShowPart(name="A", color="#FFF", signature="4/4",
                          bpm=120.0, num_bars=4, transition="instant")]
        ss = SongStructure()
        ss.load_from_show_parts(parts)
        snapped = ss.find_nearest_beat_time(-1.0)
        assert snapped == 0.0


class TestGetBeatTimesInRange:

    def test_returns_beat_times(self, two_part_structure):
        beats = two_part_structure.get_beat_times_in_range(0.0, 2.0)
        assert len(beats) > 0
        # Each entry is (time, is_bar)
        times = [t for t, _ in beats]
        assert times[0] == 0.0

    def test_bar_boundaries_marked(self, two_part_structure):
        beats = two_part_structure.get_beat_times_in_range(0.0, 2.0)
        # First beat should be a bar boundary
        assert beats[0][1] is True

    def test_empty_range(self, two_part_structure):
        # Range completely outside the song
        beats = two_part_structure.get_beat_times_in_range(9999.0, 10000.0)
        assert len(beats) == 0
