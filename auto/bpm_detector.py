"""
BPM detection for Auto mode — tap tempo and auto-detection from audio.
"""

import time
import numpy as np
from typing import Optional, List
from audio.realtime_spectral import LiveFeatureFrame


class TapBPM:
    """Compute BPM from user tap intervals.

    Stores the last N tap timestamps, computes median interval,
    discards outliers, and returns BPM.
    """

    def __init__(self, max_taps: int = 8, timeout: float = 3.0):
        self._max_taps = max_taps
        self._timeout = timeout
        self._timestamps: List[float] = []

    def tap(self) -> Optional[float]:
        """Register a tap and return computed BPM (or None if not enough taps).

        Returns:
            BPM if >= 3 taps within timeout, else None
        """
        now = time.monotonic()

        # Reset if too long since last tap
        if self._timestamps and (now - self._timestamps[-1]) > self._timeout:
            self._timestamps.clear()

        self._timestamps.append(now)

        # Keep only last N taps
        if len(self._timestamps) > self._max_taps:
            self._timestamps = self._timestamps[-self._max_taps:]

        if len(self._timestamps) < 3:
            return None

        # Compute intervals
        intervals = []
        for i in range(1, len(self._timestamps)):
            intervals.append(self._timestamps[i] - self._timestamps[i - 1])

        # Remove outliers (> 2σ from median)
        median = np.median(intervals)
        std = np.std(intervals)
        if std > 0:
            filtered = [iv for iv in intervals if abs(iv - median) < 2.0 * std]
        else:
            filtered = intervals

        if not filtered:
            return None

        avg_interval = np.mean(filtered)
        if avg_interval <= 0:
            return None

        bpm = 60.0 / avg_interval
        return float(np.clip(bpm, 30.0, 300.0))

    def reset(self):
        """Clear tap history."""
        self._timestamps.clear()


class AutoBPMDetector:
    """Automatic BPM detection from live audio onset flux.

    Uses autocorrelation of the onset strength function to find
    the dominant tempo. Updates every ~2 seconds.
    """

    def __init__(self, analysis_rate_hz: float = 86.0, window_seconds: float = 8.0):
        """
        Args:
            analysis_rate_hz: How many LiveFeatureFrames per second (~86 at 44100/512)
            window_seconds: How much history to analyze
        """
        self._rate = analysis_rate_hz
        self._window_size = int(window_seconds * analysis_rate_hz)
        self._flux_buffer = np.zeros(self._window_size, dtype=np.float32)
        self._write_pos = 0
        self._count = 0
        self._last_analysis_time = 0.0
        self._analysis_interval = 2.0  # seconds between updates
        self._current_bpm: Optional[float] = None
        self._confidence: float = 0.0

    def on_feature(self, frame: LiveFeatureFrame):
        """Process a feature frame."""
        self._flux_buffer[self._write_pos] = frame.flux
        self._write_pos = (self._write_pos + 1) % self._window_size
        self._count += 1

        # Re-analyze periodically
        now = time.monotonic()
        if (now - self._last_analysis_time) >= self._analysis_interval:
            self._last_analysis_time = now
            self._analyze()

    def get_bpm(self) -> Optional[float]:
        """Get current BPM estimate, or None if confidence is low."""
        if self._confidence < 0.3:
            return None
        return self._current_bpm

    @property
    def confidence(self) -> float:
        """Confidence of current BPM estimate (0-1)."""
        return self._confidence

    def reset(self):
        """Clear all state."""
        self._flux_buffer[:] = 0
        self._write_pos = 0
        self._count = 0
        self._current_bpm = None
        self._confidence = 0.0

    def _analyze(self):
        """Run autocorrelation-based tempo estimation."""
        if self._count < self._window_size // 2:
            return  # Not enough data

        # Get the flux time series in order
        if self._count >= self._window_size:
            # Buffer is full, read in order
            signal = np.roll(self._flux_buffer, -self._write_pos)
        else:
            signal = self._flux_buffer[:self._count]

        if len(signal) < 100:
            return

        # Remove DC offset
        signal = signal - np.mean(signal)

        # Autocorrelation via FFT
        n = len(signal)
        fft = np.fft.rfft(signal, n=2 * n)
        acf = np.fft.irfft(fft * np.conj(fft))[:n]

        # Normalize
        if acf[0] > 0:
            acf = acf / acf[0]
        else:
            return

        # Search for peaks in the BPM range 50-240 — wide enough to
        # cover slow ballads (≈50 BPM, half-time feels) and fast
        # punk / drum-and-bass (≈220-240 BPM) without going so wide
        # that octave errors dominate. The spinbox accepts 30-300 so
        # extreme tempi are still settable manually via TAP.
        min_lag = int(self._rate * 60.0 / 240.0)  # 240 BPM
        max_lag = int(self._rate * 60.0 / 50.0)    # 50 BPM
        max_lag = min(max_lag, n - 1)

        if min_lag >= max_lag:
            return

        search = acf[min_lag:max_lag + 1]
        if len(search) == 0:
            return

        # Find the strongest peak
        peak_idx = np.argmax(search)
        peak_value = search[peak_idx]
        lag = min_lag + peak_idx

        if lag <= 0:
            return

        bpm = 60.0 * self._rate / lag
        self._confidence = float(np.clip(peak_value, 0.0, 1.0))
        self._current_bpm = float(np.clip(bpm, 50.0, 240.0))
