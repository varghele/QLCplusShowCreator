"""
Simple audio player using pygame for low-latency playback.
This is a lightweight alternative to the PyAudio-based engine.
"""

import os
import threading
import time
from typing import Optional, Callable

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("pygame not available - install with: pip install pygame")


class SimpleAudioPlayer:
    """
    Lightweight audio player using pygame.mixer.

    Much simpler than PyAudio - pygame handles all the threading internally.
    No callbacks, no locks, just play/pause/seek.
    """

    def __init__(self):
        self._is_initialized = False
        self._is_playing = False
        self._current_file: Optional[str] = None
        self._duration: float = 0.0
        self._start_time: float = 0.0  # When playback started (wall clock)
        self._start_position: float = 0.0  # Position when playback started
        self._paused_position: float = 0.0

        # Position tracking thread
        self._position_callback: Optional[Callable[[float], None]] = None
        self._position_thread: Optional[threading.Thread] = None
        self._stop_position_thread = False

    def initialize(self, frequency: int = 44100, buffer_size: int = 2048) -> bool:
        """Initialize pygame mixer."""
        if not PYGAME_AVAILABLE:
            print("pygame not available")
            return False

        try:
            # Initialize pygame mixer only (not full pygame)
            pygame.mixer.init(frequency=frequency, size=-16, channels=2, buffer=buffer_size)
            self._is_initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize pygame mixer: {e}")
            return False

    def cleanup(self):
        """Clean up pygame mixer."""
        self.stop()
        if self._is_initialized:
            try:
                pygame.mixer.quit()
            except:
                pass
            self._is_initialized = False

    def load(self, file_path: str) -> bool:
        """Load an audio file."""
        if not self._is_initialized:
            if not self.initialize():
                return False

        if not os.path.exists(file_path):
            print(f"Audio file not found: {file_path}")
            return False

        try:
            # Stop any current playback
            self.stop()

            # Load the file
            pygame.mixer.music.load(file_path)
            self._current_file = file_path

            # Get duration using a Sound object (temporary)
            try:
                sound = pygame.mixer.Sound(file_path)
                self._duration = sound.get_length()
                del sound  # Free memory
            except:
                # Fallback: estimate from file size (rough)
                self._duration = 300.0  # Default 5 minutes

            self._paused_position = 0.0
            return True

        except Exception as e:
            print(f"Failed to load audio file: {e}")
            return False

    def set_position_callback(self, callback: Callable[[float], None]):
        """Set callback for position updates (called ~10 times per second)."""
        self._position_callback = callback

    def _position_update_loop(self):
        """Background thread that reports position."""
        while not self._stop_position_thread and self._is_playing:
            if self._position_callback:
                try:
                    pos = self.get_current_position()
                    self._position_callback(pos)
                except:
                    pass
            time.sleep(0.1)  # Update 10 times per second

    def play(self, start_position: float = 0.0) -> bool:
        """Start playback from position."""
        if not self._is_initialized or not self._current_file:
            return False

        try:
            # pygame.mixer.music.play() takes start position in seconds
            pygame.mixer.music.play(start=start_position)
            self._is_playing = True
            self._start_time = time.time()
            self._start_position = start_position

            # Start position update thread
            self._stop_position_thread = False
            self._position_thread = threading.Thread(target=self._position_update_loop, daemon=True)
            self._position_thread.start()

            return True
        except Exception as e:
            print(f"Failed to start playback: {e}")
            return False

    def pause(self):
        """Pause playback."""
        if self._is_playing:
            self._paused_position = self.get_current_position()
            pygame.mixer.music.pause()
            self._is_playing = False
            self._stop_position_thread = True

    def unpause(self):
        """Resume from pause."""
        if not self._is_playing and self._current_file:
            pygame.mixer.music.unpause()
            self._is_playing = True
            self._start_time = time.time()
            self._start_position = self._paused_position

            # Restart position thread
            self._stop_position_thread = False
            self._position_thread = threading.Thread(target=self._position_update_loop, daemon=True)
            self._position_thread.start()

    def stop(self):
        """Stop playback."""
        self._stop_position_thread = True
        self._is_playing = False
        self._paused_position = 0.0
        try:
            pygame.mixer.music.stop()
        except:
            pass

    def seek(self, position: float):
        """Seek to position in seconds."""
        if not self._current_file:
            return

        was_playing = self._is_playing

        # pygame doesn't have a seek function, need to restart from position
        try:
            pygame.mixer.music.stop()
            if was_playing:
                pygame.mixer.music.play(start=position)
                self._start_time = time.time()
                self._start_position = position
            else:
                self._paused_position = position
        except Exception as e:
            print(f"Seek failed: {e}")

    def get_current_position(self) -> float:
        """Get current playback position in seconds."""
        if not self._is_playing:
            return self._paused_position

        # Calculate position from wall clock
        elapsed = time.time() - self._start_time
        position = self._start_position + elapsed

        # Clamp to duration
        return min(position, self._duration)

    def get_duration(self) -> float:
        """Get audio duration in seconds."""
        return self._duration

    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._is_playing

    def is_loaded(self) -> bool:
        """Check if a file is loaded."""
        return self._current_file is not None


# Quick test
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python simple_audio_player.py <audio_file>")
        sys.exit(1)

    player = SimpleAudioPlayer()
    if not player.initialize():
        print("Failed to initialize")
        sys.exit(1)

    if not player.load(sys.argv[1]):
        print("Failed to load file")
        sys.exit(1)

    print(f"Duration: {player.get_duration():.2f}s")
    print("Playing... Press Ctrl+C to stop")

    player.set_position_callback(lambda p: print(f"\rPosition: {p:.2f}s", end="", flush=True))
    player.play()

    try:
        while player.is_playing():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    player.cleanup()
    print("\nDone")
