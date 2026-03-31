"""Tests for audio spectral analysis module."""

import pytest
import numpy as np

from audio.spectral_analysis import (
    SectionAnalysis, SongAnalysis, _resample_to_n, LIBROSA_AVAILABLE,
)


class TestSectionAnalysis:
    def test_defaults(self):
        sa = SectionAnalysis(name="Test", start_time=0.0, end_time=4.0)
        assert sa.spectral_flux_avg == 0.0
        assert sa.transient_sharpness == 0.0
        assert sa.spectral_richness == 0.0
        assert sa.vocal_presence == 0.0
        assert sa.spectral_centroid_avg == 0.0
        assert sa.spectral_flux_envelope == []

    def test_values_stored(self):
        sa = SectionAnalysis(
            name="Chorus", start_time=10.0, end_time=20.0,
            spectral_flux_avg=0.7, transient_sharpness=0.9,
            spectral_richness=0.5, vocal_presence=0.8,
            spectral_centroid_avg=3000.0,
        )
        assert sa.name == "Chorus"
        assert sa.spectral_flux_avg == 0.7


class TestSongAnalysis:
    def test_defaults(self):
        sa = SongAnalysis()
        assert sa.sections == []
        assert sa.global_flux_range == (0.0, 1.0)
        assert sa.duration == 0.0


class TestResampleToN:
    def test_exact_length(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        result = _resample_to_n(data, 4)
        assert len(result) == 4

    def test_downsample(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        result = _resample_to_n(data, 4)
        assert len(result) == 4
        # First bin: avg(1,2) = 1.5
        assert result[0] == pytest.approx(1.5)

    def test_upsample_pads(self):
        data = np.array([1.0, 2.0])
        result = _resample_to_n(data, 4)
        assert len(result) == 4
        assert result[0] == 1.0
        assert result[1] == 2.0
        # Padded with last value
        assert result[2] == 2.0
        assert result[3] == 2.0

    def test_empty(self):
        result = _resample_to_n(np.array([]), 4)
        assert result == [0.0, 0.0, 0.0, 0.0]

    def test_output_length_always_n(self):
        for input_len in [1, 5, 32, 100, 1000]:
            data = np.random.rand(input_len)
            for n in [8, 16, 32]:
                result = _resample_to_n(data, n)
                assert len(result) == n, f"input={input_len}, n={n}, got {len(result)}"


@pytest.mark.skipif(not LIBROSA_AVAILABLE, reason="librosa not installed")
class TestAnalyzeSong:
    def test_analyze_with_synthetic_audio(self, tmp_path):
        """Test analysis with a synthetic audio file."""
        import soundfile as sf
        from audio.spectral_analysis import analyze_song
        from timeline.song_structure import SongStructure
        from config.models import ShowPart

        # Generate 10 seconds of synthetic audio
        sr = 22050
        duration = 10.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        # First 5s: low frequency sine (verse-like)
        # Next 5s: mixed frequencies (chorus-like)
        audio = np.zeros_like(t)
        audio[:int(sr * 5)] = 0.5 * np.sin(2 * np.pi * 220 * t[:int(sr * 5)])
        audio[int(sr * 5):] = (
            0.3 * np.sin(2 * np.pi * 440 * t[int(sr * 5):])
            + 0.3 * np.sin(2 * np.pi * 880 * t[int(sr * 5):])
            + 0.2 * np.sin(2 * np.pi * 1760 * t[int(sr * 5):])
        )

        # Save to temp file
        audio_path = str(tmp_path / "test_audio.wav")
        sf.write(audio_path, audio, sr)

        # Create song structure
        parts = [
            ShowPart(name="Verse", color="#00FF00", signature="4/4", bpm=120.0,
                     num_bars=2, transition="instant"),
            ShowPart(name="Chorus", color="#FF0000", signature="4/4", bpm=120.0,
                     num_bars=2, transition="instant"),
        ]
        ss = SongStructure()
        ss.load_from_show_parts(parts)

        # Analyze
        analysis = analyze_song(audio_path, ss)

        assert len(analysis.sections) == 2
        assert analysis.duration == pytest.approx(duration, abs=0.1)
        assert analysis.sample_rate == sr

        verse = analysis.sections[0]
        chorus = analysis.sections[1]

        assert verse.name == "Verse"
        assert chorus.name == "Chorus"

        # Both should have valid flux envelopes
        assert len(verse.spectral_flux_envelope) == 32
        assert len(chorus.spectral_flux_envelope) == 32

        # All values should be in valid ranges
        for section in analysis.sections:
            assert 0.0 <= section.spectral_flux_avg <= 1.0
            assert 0.0 <= section.transient_sharpness <= 1.0
            assert 0.0 <= section.spectral_richness <= 1.0
            assert 0.0 <= section.vocal_presence <= 1.0
            assert section.spectral_centroid_avg >= 0.0

        # Chorus should have higher spectral richness (more harmonics)
        assert chorus.spectral_richness > verse.spectral_richness
