"""
Thread-safe ring buffer for live audio capture.
Pre-allocates memory to avoid allocations in the audio callback path.
"""

import numpy as np
import threading


class AudioRingBuffer:
    """Lock-based circular buffer for audio samples.

    Designed for single-writer (audio input callback) / single-reader (analysis thread)
    with minimal lock hold time.
    """

    def __init__(self, max_seconds: float = 5.0, sample_rate: int = 44100, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._capacity = int(max_seconds * sample_rate)
        self._buffer = np.zeros((self._capacity, channels), dtype=np.float32)
        self._write_pos = 0
        self._total_written = 0  # monotonic counter for overflow detection
        self._lock = threading.Lock()

    @property
    def capacity(self) -> int:
        """Total capacity in samples."""
        return self._capacity

    def write(self, data: np.ndarray) -> None:
        """Write samples into the ring buffer.

        Called from the audio input callback — must be fast.

        Args:
            data: Audio samples, shape (n_samples,) or (n_samples, channels)
        """
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        n = data.shape[0]
        if n == 0:
            return

        with self._lock:
            if n >= self._capacity:
                # Data larger than buffer — keep only the last _capacity samples
                self._buffer[:] = data[-self._capacity:]
                self._write_pos = 0
                self._total_written += n
                return

            end = self._write_pos + n
            if end <= self._capacity:
                self._buffer[self._write_pos:end] = data
            else:
                # Wrap around
                first = self._capacity - self._write_pos
                self._buffer[self._write_pos:] = data[:first]
                self._buffer[:n - first] = data[first:]

            self._write_pos = end % self._capacity
            self._total_written += n

    def read_latest(self, num_samples: int) -> np.ndarray:
        """Read the most recent N samples without consuming them.

        Args:
            num_samples: Number of samples to read

        Returns:
            numpy array of shape (num_samples, channels), zero-padded if not enough data
        """
        with self._lock:
            available = min(num_samples, self._total_written, self._capacity)
            if available == 0:
                return np.zeros((num_samples, self.channels), dtype=np.float32)

            start = (self._write_pos - available) % self._capacity
            result = np.empty((available, self.channels), dtype=np.float32)

            if start + available <= self._capacity:
                result[:] = self._buffer[start:start + available]
            else:
                first = self._capacity - start
                result[:first] = self._buffer[start:]
                result[first:] = self._buffer[:available - first]

        # Zero-pad if we requested more than available
        if available < num_samples:
            padded = np.zeros((num_samples, self.channels), dtype=np.float32)
            padded[num_samples - available:] = result
            return padded

        return result

    def read_consume(self, num_samples: int) -> np.ndarray:
        """Read and consume N samples from the buffer.

        Returns the oldest unread samples. Used by the analysis thread
        to process sequential chunks without gaps.

        Args:
            num_samples: Number of samples to read

        Returns:
            numpy array of shape (actual_available, channels)
        """
        with self._lock:
            available = min(num_samples, self._total_written, self._capacity)
            if available == 0:
                return np.zeros((0, self.channels), dtype=np.float32)

            # Read from the oldest data (write_pos is newest)
            read_start = (self._write_pos - min(self._total_written, self._capacity)) % self._capacity
            to_read = min(available, num_samples)
            result = np.empty((to_read, self.channels), dtype=np.float32)

            if read_start + to_read <= self._capacity:
                result[:] = self._buffer[read_start:read_start + to_read]
            else:
                first = self._capacity - read_start
                result[:first] = self._buffer[read_start:]
                result[first:] = self._buffer[:to_read - first]

            # Reduce total_written to mark data as consumed
            self._total_written = max(0, self._total_written - to_read)

        return result

    def available(self) -> int:
        """Number of samples available for reading."""
        with self._lock:
            return min(self._total_written, self._capacity)

    def clear(self) -> None:
        """Clear the buffer."""
        with self._lock:
            self._write_pos = 0
            self._total_written = 0

    @property
    def total_written(self) -> int:
        """Monotonic count of total samples written (for overflow detection)."""
        with self._lock:
            return self._total_written
