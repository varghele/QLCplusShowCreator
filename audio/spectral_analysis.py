"""Audio analysis module for algorithmic show generation.

Extracts spectral flux, transient sharpness, spectral richness,
vocal presence, and spectral centroid from audio files, segmented
by the operator-provided song structure.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


@dataclass
class SectionAnalysis:
    """Audio analysis results for one section of a song."""
    name: str
    start_time: float
    end_time: float
    spectral_flux_avg: float = 0.0
    spectral_flux_envelope: List[float] = field(default_factory=list)
    transient_sharpness: float = 0.0       # 0.0 (sustained) to 1.0 (percussive)
    spectral_richness: float = 0.0         # 0.0 (sparse) to 1.0 (dense)
    vocal_presence: float = 0.0            # 0.0 to 1.0 (ratio of section with vocals)
    spectral_centroid_avg: float = 0.0     # Hz, for color mapping


@dataclass
class SongAnalysis:
    """Complete audio analysis for a song."""
    sections: List[SectionAnalysis] = field(default_factory=list)
    global_flux_range: Tuple[float, float] = (0.0, 1.0)
    sample_rate: int = 22050
    duration: float = 0.0


def analyze_song(audio_path: str, song_structure) -> SongAnalysis:
    """Run full spectral analysis on a song file.

    Args:
        audio_path: Path to the audio file (mp3, wav, etc.)
        song_structure: SongStructure instance with parts defining section boundaries

    Returns:
        SongAnalysis with per-section results

    Raises:
        ImportError: If librosa is not installed
        FileNotFoundError: If audio file doesn't exist
    """
    if not LIBROSA_AVAILABLE:
        raise ImportError("librosa is required for audio analysis. Install with: pip install librosa")

    # Load audio
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    # Compute global features
    hop_length = 512
    n_fft = 2048

    # Spectral flux (onset strength envelope)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length, n_fft=n_fft)

    # Onset detection for transient sharpness
    onset_frames = librosa.onset.onset_detect(
        y=y, sr=sr, hop_length=hop_length, onset_envelope=onset_env, backtrack=True
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)

    # Spectral centroid
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length, n_fft=n_fft)[0]

    # Spectral bandwidth (for richness)
    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length, n_fft=n_fft)[0]

    # Spectral flatness (for richness — flat = noise-like = rich)
    spectral_flatness = librosa.feature.spectral_flatness(y=y, hop_length=hop_length, n_fft=n_fft)[0]

    # STFT for vocal detection and spectral richness
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # Frame times
    frame_times = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr, hop_length=hop_length)

    # Global normalization ranges
    flux_min = float(np.min(onset_env))
    flux_max = float(np.max(onset_env))
    centroid_max = float(np.max(spectral_centroid)) if len(spectral_centroid) > 0 else 1.0
    bandwidth_max = float(np.max(spectral_bandwidth)) if len(spectral_bandwidth) > 0 else 1.0

    # Analyze each section
    sections = []
    for part in song_structure.parts:
        section = _analyze_section(
            part_name=part.name,
            start_time=part.start_time,
            end_time=part.start_time + part.duration,
            onset_env=onset_env,
            onset_times=onset_times,
            spectral_centroid=spectral_centroid,
            spectral_bandwidth=spectral_bandwidth,
            spectral_flatness=spectral_flatness,
            S=S,
            freqs=freqs,
            frame_times=frame_times,
            sr=sr,
            hop_length=hop_length,
            flux_min=flux_min,
            flux_max=flux_max,
            centroid_max=centroid_max,
            bandwidth_max=bandwidth_max,
        )
        sections.append(section)

    return SongAnalysis(
        sections=sections,
        global_flux_range=(flux_min, flux_max),
        sample_rate=sr,
        duration=duration,
    )


def _analyze_section(
    part_name: str,
    start_time: float,
    end_time: float,
    onset_env: np.ndarray,
    onset_times: np.ndarray,
    spectral_centroid: np.ndarray,
    spectral_bandwidth: np.ndarray,
    spectral_flatness: np.ndarray,
    S: np.ndarray,
    freqs: np.ndarray,
    frame_times: np.ndarray,
    sr: int,
    hop_length: int,
    flux_min: float,
    flux_max: float,
    centroid_max: float,
    bandwidth_max: float,
) -> SectionAnalysis:
    """Analyze a single section of the song."""

    # Get frame indices for this section
    mask = (frame_times >= start_time) & (frame_times < end_time)
    if not np.any(mask):
        return SectionAnalysis(name=part_name, start_time=start_time, end_time=end_time)

    section_frames = np.where(mask)[0]
    section_onset_env = onset_env[section_frames] if len(section_frames) <= len(onset_env) else onset_env[mask[:len(onset_env)]]

    # 1. Spectral flux — normalized average
    flux_range = flux_max - flux_min
    if flux_range > 0 and len(section_onset_env) > 0:
        normalized_flux = (section_onset_env - flux_min) / flux_range
        spectral_flux_avg = float(np.mean(normalized_flux))
        # Subsample envelope to 32 points for matching
        envelope_32 = _resample_to_n(normalized_flux, 32)
    else:
        spectral_flux_avg = 0.0
        envelope_32 = [0.0] * 32

    # 2. Transient sharpness — onset density and strength
    section_onsets = onset_times[(onset_times >= start_time) & (onset_times < end_time)]
    section_duration = end_time - start_time
    if section_duration > 0 and len(section_onsets) > 0:
        onset_density = len(section_onsets) / section_duration  # onsets per second
        # Normalize: ~0-10 onsets/sec mapped to 0-1
        transient_sharpness = min(1.0, onset_density / 10.0)
    else:
        transient_sharpness = 0.0

    # 3. Spectral richness — combination of bandwidth and flatness
    section_bandwidth = spectral_bandwidth[section_frames] if len(section_frames) <= len(spectral_bandwidth) else spectral_bandwidth[mask[:len(spectral_bandwidth)]]
    section_flatness = spectral_flatness[section_frames] if len(section_frames) <= len(spectral_flatness) else spectral_flatness[mask[:len(spectral_flatness)]]

    if len(section_bandwidth) > 0 and bandwidth_max > 0:
        norm_bandwidth = float(np.mean(section_bandwidth)) / bandwidth_max
    else:
        norm_bandwidth = 0.0
    if len(section_flatness) > 0:
        avg_flatness = float(np.mean(section_flatness))
    else:
        avg_flatness = 0.0

    # Richness = weighted combination of bandwidth and flatness
    spectral_richness = min(1.0, 0.6 * norm_bandwidth + 0.4 * avg_flatness)

    # 4. Vocal presence — energy ratio in vocal frequency band (300Hz-3kHz)
    vocal_low_idx = np.searchsorted(freqs, 300)
    vocal_high_idx = np.searchsorted(freqs, 3000)
    total_low_idx = np.searchsorted(freqs, 50)

    S_section = S[:, section_frames] if section_frames[-1] < S.shape[1] else S[:, mask[:S.shape[1]]]

    if S_section.size > 0:
        vocal_energy = np.sum(S_section[vocal_low_idx:vocal_high_idx, :] ** 2, axis=0)
        total_energy = np.sum(S_section[total_low_idx:, :] ** 2, axis=0)

        # Frame-level vocal ratio
        with np.errstate(divide='ignore', invalid='ignore'):
            vocal_ratio = np.where(total_energy > 0, vocal_energy / total_energy, 0.0)

        # Vocal presence = fraction of frames where vocal band dominates
        # Threshold: vocal band has >40% of total energy
        vocal_frames = np.sum(vocal_ratio > 0.4)
        vocal_presence = float(vocal_frames / len(vocal_ratio)) if len(vocal_ratio) > 0 else 0.0
    else:
        vocal_presence = 0.0

    # 5. Spectral centroid average (for color mapping)
    section_centroid = spectral_centroid[section_frames] if len(section_frames) <= len(spectral_centroid) else spectral_centroid[mask[:len(spectral_centroid)]]
    if len(section_centroid) > 0:
        centroid_avg = float(np.mean(section_centroid))
    else:
        centroid_avg = 0.0

    return SectionAnalysis(
        name=part_name,
        start_time=start_time,
        end_time=end_time,
        spectral_flux_avg=spectral_flux_avg,
        spectral_flux_envelope=envelope_32,
        transient_sharpness=transient_sharpness,
        spectral_richness=spectral_richness,
        vocal_presence=vocal_presence,
        spectral_centroid_avg=centroid_avg,
    )


@dataclass
class FrameFeatures:
    """Per-frame audio features at ~43fps (hop=512, sr=22050).

    Used by the Generation Inspector for the 3D flux/transient plot.
    Designed for pre-computation now, but the interface supports
    future real-time computation by accepting partial data.
    """
    times: List[float] = field(default_factory=list)
    flux: List[float] = field(default_factory=list)        # normalized onset strength (0-1)
    transient: List[float] = field(default_factory=list)    # per-frame transient sharpness (0-1)
    sample_rate: int = 22050
    hop_length: int = 512
    duration: float = 0.0


def compute_frame_features(audio_path: str, max_display_points: int = 1000) -> FrameFeatures:
    """Compute per-frame spectral flux and transient sharpness from audio.

    Args:
        audio_path: Path to audio file
        max_display_points: Downsample to this many points for display performance

    Returns:
        FrameFeatures with arrays at ~43fps, downsampled for display
    """
    if not LIBROSA_AVAILABLE:
        raise ImportError("librosa required for audio analysis")

    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    hop_length = 512
    n_fft = 2048

    # Onset strength envelope — per-frame spectral flux
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length, n_fft=n_fft)
    frame_times = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr, hop_length=hop_length)

    # Normalize flux to 0-1
    flux_min, flux_max = float(np.min(onset_env)), float(np.max(onset_env))
    if flux_max > flux_min:
        norm_flux = (onset_env - flux_min) / (flux_max - flux_min)
    else:
        norm_flux = np.zeros_like(onset_env)

    # Per-frame transient sharpness: local peakiness of onset envelope
    # Ratio of each frame to its local average (~100ms window = 5 frames at 43fps)
    from scipy.ndimage import uniform_filter1d
    window = max(3, int(0.1 * sr / hop_length))  # ~100ms window
    local_avg = uniform_filter1d(onset_env.astype(float), window)
    transient_raw = np.where(local_avg > 1e-6, onset_env / local_avg, 0.0)
    # Normalize to 0-1
    t_max = float(np.max(transient_raw)) if len(transient_raw) > 0 else 1.0
    if t_max > 0:
        norm_transient = np.clip(transient_raw / t_max, 0.0, 1.0)
    else:
        norm_transient = np.zeros_like(transient_raw)

    # Downsample for display if needed
    n_frames = len(frame_times)
    if n_frames > max_display_points:
        indices = np.linspace(0, n_frames - 1, max_display_points, dtype=int)
        frame_times = frame_times[indices]
        norm_flux = norm_flux[indices]
        norm_transient = norm_transient[indices]

    return FrameFeatures(
        times=[float(t) for t in frame_times],
        flux=[float(f) for f in norm_flux],
        transient=[float(t) for t in norm_transient],
        sample_rate=sr,
        hop_length=hop_length,
        duration=duration,
    )


def _resample_to_n(data: np.ndarray, n: int) -> List[float]:
    """Resample a 1D array to exactly n points by averaging bins."""
    if len(data) == 0:
        return [0.0] * n
    if len(data) <= n:
        # Pad with last value
        result = list(data) + [float(data[-1])] * (n - len(data))
        return result[:n]

    # Bin and average
    result = []
    bin_size = len(data) / n
    for i in range(n):
        start = int(i * bin_size)
        end = int((i + 1) * bin_size)
        if end > start:
            result.append(float(np.mean(data[start:end])))
        else:
            result.append(float(data[start]))
    return result
