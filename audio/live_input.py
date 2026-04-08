"""
Live audio input capture using sounddevice.
Captures audio from an input device into a ring buffer for real-time analysis.
"""

import sounddevice as sd
import numpy as np
from typing import Optional
from .ring_buffer import AudioRingBuffer


class LiveAudioInput:
    """Captures live audio from an input device into a ring buffer.

    Separate from AudioEngine (output-only) to avoid ASIO exclusivity issues
    where some drivers cannot open the same device for both input and output.
    """

    def __init__(self, sample_rate: int = 44100, channels: int = 1,
                 buffer_size: int = 512, ring_buffer_seconds: float = 5.0):
        """
        Args:
            sample_rate: Input sample rate in Hz
            channels: Number of input channels (1=mono, recommended for analysis)
            buffer_size: Frames per callback buffer
            ring_buffer_seconds: Ring buffer duration in seconds
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_size = buffer_size

        self._ring_buffer = AudioRingBuffer(
            max_seconds=ring_buffer_seconds,
            sample_rate=sample_rate,
            channels=channels,
        )
        self._stream: Optional[sd.InputStream] = None
        self._is_initialized = False

    @property
    def ring_buffer(self) -> AudioRingBuffer:
        """Access the ring buffer containing captured audio."""
        return self._ring_buffer

    def initialize(self, device_index: Optional[int] = None) -> bool:
        """Initialize the input stream.

        Args:
            device_index: Input device to use (None = default)

        Returns:
            True if initialization successful
        """
        try:
            if self._is_initialized:
                return True

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.buffer_size,
                device=device_index,
                channels=self.channels,
                dtype='float32',
                callback=self._input_callback,
            )

            self._is_initialized = True
            return True

        except Exception as e:
            print(f"Failed to initialize live audio input: {e}")
            self.cleanup()
            return False

    def start(self) -> bool:
        """Start capturing audio.

        Returns:
            True if capture started successfully
        """
        if not self._is_initialized or not self._stream:
            return False

        try:
            if not self._stream.active:
                self._ring_buffer.clear()
                self._stream.start()
            return True
        except Exception as e:
            print(f"Failed to start live audio input: {e}")
            return False

    def stop(self) -> None:
        """Stop capturing audio."""
        if self._stream and self._stream.active:
            try:
                self._stream.abort()
            except Exception as e:
                print(f"Error stopping live audio input: {e}")

    def cleanup(self) -> None:
        """Release all resources."""
        self.stop()

        if self._stream:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        self._is_initialized = False

    def is_active(self) -> bool:
        """Check if currently capturing."""
        return self._stream is not None and self._stream.active

    def _input_callback(self, indata, frames, time, status):
        """sounddevice input callback — writes captured audio to ring buffer.

        Must be fast: no allocations, no blocking I/O, minimal GIL hold time.
        """
        if status:
            if status.input_overflow:
                pass  # Dropped frames, acceptable for live monitoring
            else:
                print(f"Live input status: {status}")

        # Write directly to ring buffer (numpy copy into pre-allocated array)
        self._ring_buffer.write(indata)
