"""
PyAudio-based audio playback engine for QuickMIDI.
Manages audio stream and provides sample-accurate playback.
"""

import pyaudio
import numpy as np
import threading
import queue
from typing import Optional, Callable
from .audio_mixer import AudioMixer


class AudioCommand:
    """Commands for audio engine"""
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    SEEK = "seek"


class AudioEngine:
    """Core audio playback engine using PyAudio"""

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        self.py_audio: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.mixer: Optional[AudioMixer] = None

        # Playback state
        self._current_frame = 0
        self._is_playing = False
        self._is_initialized = False

        # Thread safety
        self._lock = threading.Lock()
        self._command_queue = queue.Queue()

        # Seeking
        self._seek_pending = False
        self._seek_target_frame = 0

        # Position callback
        self._position_callback: Optional[Callable[[float], None]] = None

    def initialize(self, device_index: Optional[int] = None) -> bool:
        """
        Initialize PyAudio and create audio stream

        Args:
            device_index: Audio device to use (None = default)

        Returns:
            True if initialization successful
        """
        try:
            if self._is_initialized:
                return True

            self.py_audio = pyaudio.PyAudio()

            # Open stream
            self.stream = self.py_audio.open(
                format=pyaudio.paFloat32,
                channels=2,  # Stereo
                rate=self.sample_rate,
                output=True,
                output_device_index=device_index,
                frames_per_buffer=self.buffer_size,
                stream_callback=self._audio_callback,
                start=False  # Don't auto-start the stream
            )

            self._is_initialized = True
            return True

        except Exception as e:
            print(f"Failed to initialize audio engine: {e}")
            self.cleanup()
            return False

    def cleanup(self):
        """Cleanup audio resources"""
        self.stop_playback()

        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None

        if self.py_audio:
            try:
                self.py_audio.terminate()
            except:
                pass
            self.py_audio = None

        self._is_initialized = False

    def set_mixer(self, mixer: AudioMixer):
        """Set the audio mixer to use"""
        with self._lock:
            self.mixer = mixer

    def set_position_callback(self, callback: Callable[[float], None]):
        """Set callback for position updates"""
        self._position_callback = callback

    def start_playback(self, start_position: float = 0.0) -> bool:
        """
        Start audio playback

        Args:
            start_position: Starting position in seconds

        Returns:
            True if playback started
        """
        if not self._is_initialized:
            return False

        with self._lock:
            # Seek to start position
            start_frame = int(start_position * self.sample_rate)
            self._current_frame = start_frame

            if self.mixer:
                self.mixer.seek_all_lanes(start_position)

            self._is_playing = True

        # Start the stream if not already running
        if not self.stream.is_active():
            self.stream.start_stream()

        return True

    def stop_playback(self):
        """Stop playback and reset to beginning"""
        with self._lock:
            self._is_playing = False
            self._current_frame = 0

            if self.mixer:
                self.mixer.reset_all_lanes()

        if self.stream and self.stream.is_active():
            self.stream.stop_stream()

    def pause_playback(self):
        """Pause playback at current position"""
        with self._lock:
            self._is_playing = False

        if self.stream and self.stream.is_active():
            self.stream.stop_stream()

    def seek(self, time_seconds: float):
        """
        Seek to specific time position

        Args:
            time_seconds: Target position in seconds
        """
        with self._lock:
            self._seek_target_frame = int(time_seconds * self.sample_rate)
            self._seek_pending = True

    def get_current_position(self) -> float:
        """Get current playback position in seconds"""
        with self._lock:
            return self._current_frame / self.sample_rate

    def is_playing(self) -> bool:
        """Check if currently playing"""
        with self._lock:
            return self._is_playing

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio callback - called from audio thread

        This runs on a separate thread and must be fast and lock-free as much as possible
        """
        # Handle any status flags (suppress to avoid spam)
        if status and status != 4:  # Suppress output underflow warnings (common during init)
            print(f"Audio callback status: {status}")

        # Check for seek command
        with self._lock:
            if self._seek_pending:
                self._execute_seek()
                self._seek_pending = False

            # Check if playing
            if not self._is_playing or not self.mixer:
                # Return silence
                output_data = np.zeros((frame_count, 2), dtype=np.float32)
                return (output_data.tobytes(), pyaudio.paContinue)

        # Mix audio from all lanes
        try:
            mixed_audio = self.mixer.mix_frames(frame_count)

            with self._lock:
                self._current_frame += frame_count

            # Periodically report position (every ~100ms)
            if self._position_callback and self._current_frame % 4410 == 0:
                try:
                    position = self._current_frame / self.sample_rate
                    self._position_callback(position)
                except:
                    pass  # Don't let callback errors crash audio thread

            return (mixed_audio.tobytes(), pyaudio.paContinue)

        except Exception as e:
            print(f"Error in audio callback: {e}")
            # Return silence on error
            output_data = np.zeros((frame_count, 2), dtype=np.float32)
            return (output_data.tobytes(), pyaudio.paContinue)

    def _execute_seek(self):
        """Execute pending seek operation (called from audio callback)"""
        try:
            self._current_frame = self._seek_target_frame

            if self.mixer:
                seek_time = self._current_frame / self.sample_rate
                self.mixer.seek_all_lanes(seek_time)

        except Exception as e:
            print(f"Error executing seek: {e}")
