# timeline/song_structure.py
# Adapted from midimaker_and_show_structure/core/song_structure.py
# Modified to use ShowPart from config.models instead of internal SongPart

from typing import List, Optional
from config.models import ShowPart


class SongStructure:
    """Manages song structure timing and BPM calculations.

    Works with ShowPart objects from the main configuration and calculates
    timing information (start_time, duration) for each part.
    """

    def __init__(self):
        self.parts: List[ShowPart] = []
        self.default_bpm = 120.0

    def load_from_show_parts(self, show_parts: List[ShowPart]):
        """Load structure from a list of ShowPart objects.

        Calculates start_time and duration for each part.

        Args:
            show_parts: List of ShowPart objects from configuration
        """
        self.parts = show_parts.copy()

        current_time = 0.0
        previous_bpm = None

        for part in self.parts:
            part.start_time = current_time

            # Calculate duration based on BPM transition
            duration = self.calculate_part_duration(part, previous_bpm)
            part.duration = duration

            current_time += duration
            previous_bpm = part.bpm

    def calculate_part_duration(self, part: ShowPart, previous_bpm: Optional[float]) -> float:
        """Calculate the duration of a song part in seconds.

        Args:
            part: The ShowPart to calculate duration for
            previous_bpm: BPM of the previous part (for gradual transitions)

        Returns:
            Duration in seconds
        """
        if part.transition == "instant" or previous_bpm is None:
            # Simple calculation for instant transition
            beats_per_bar = self._get_beats_per_bar(part.signature)
            total_beats = part.num_bars * beats_per_bar
            seconds_per_beat = 60.0 / part.bpm
            return total_beats * seconds_per_beat

        elif part.transition == "gradual":
            # Complex calculation for gradual BPM transition
            return self._calculate_gradual_transition_duration(part, previous_bpm)

        else:
            # Fall back to instant for unknown transition types
            beats_per_bar = self._get_beats_per_bar(part.signature)
            total_beats = part.num_bars * beats_per_bar
            seconds_per_beat = 60.0 / part.bpm
            return total_beats * seconds_per_beat

    def _get_beats_per_bar(self, signature: str) -> float:
        """Calculate beats per bar from time signature.

        Args:
            signature: Time signature string (e.g., "4/4")

        Returns:
            Number of beats per bar
        """
        try:
            numerator, denominator = map(int, signature.split('/'))
            return (numerator * 4) / denominator
        except (ValueError, ZeroDivisionError):
            return 4.0  # Default to 4/4

    def _calculate_gradual_transition_duration(self, part: ShowPart, start_bpm: float) -> float:
        """Calculate duration for gradual BPM transition.

        Uses a curved progression (progress^0.52) for smooth acceleration/deceleration.

        Args:
            part: The ShowPart with gradual transition
            start_bpm: The BPM at the start of the part

        Returns:
            Duration in seconds
        """
        beats_per_bar = self._get_beats_per_bar(part.signature)
        total_duration = 0.0

        for bar in range(part.num_bars):
            # Calculate BPM progression using curved formula
            current_progress = (bar / part.num_bars) ** 0.52
            current_bpm = start_bpm + (part.bpm - start_bpm) * current_progress

            # Calculate time for this bar
            seconds_per_beat = 60.0 / current_bpm
            bar_duration = beats_per_bar * seconds_per_beat
            total_duration += bar_duration

        return total_duration

    def get_bpm_at_time(self, time: float) -> float:
        """Get the BPM at a specific time, accounting for gradual transitions.

        Args:
            time: Time position in seconds

        Returns:
            BPM at the specified time
        """
        current_part = self.get_part_at_time(time)
        if not current_part:
            return self.default_bpm

        if current_part.transition == "instant":
            return current_part.bpm

        # For gradual transitions, calculate interpolated BPM
        part_index = self.parts.index(current_part)
        previous_bpm = (self.parts[part_index - 1].bpm
                        if part_index > 0 else current_part.bpm)

        # Calculate progress within the part
        time_in_part = time - current_part.start_time
        if current_part.duration > 0:
            progress = time_in_part / current_part.duration
            progress = min(1.0, max(0.0, progress))
        else:
            progress = 0.0

        # Apply the same curve as in duration calculation
        curved_progress = progress ** 0.52
        interpolated_bpm = previous_bpm + (current_part.bpm - previous_bpm) * curved_progress

        return interpolated_bpm

    def get_part_at_time(self, time: float) -> Optional[ShowPart]:
        """Get the song part at a specific time.

        Args:
            time: Time position in seconds

        Returns:
            ShowPart at the specified time, or None if outside all parts
        """
        for part in self.parts:
            if part.start_time <= time < part.start_time + part.duration:
                return part
        # Return last part if time is at or past the end
        if self.parts and time >= self.parts[-1].start_time + self.parts[-1].duration:
            return self.parts[-1]
        return None

    def get_total_duration(self) -> float:
        """Get total duration of the song structure.

        Returns:
            Total duration in seconds
        """
        if not self.parts:
            return 0.0
        last_part = self.parts[-1]
        return last_part.start_time + last_part.duration

    def find_nearest_beat_time(self, target_time: float) -> float:
        """Find the nearest beat time for snap-to-grid functionality.

        Args:
            target_time: The time to snap

        Returns:
            Nearest beat time in seconds
        """
        if not self.parts:
            # No song structure, snap to default grid (120 BPM)
            seconds_per_beat = 60.0 / self.default_bpm
            beat_index = round(target_time / seconds_per_beat)
            return beat_index * seconds_per_beat

        # Find which part contains the target time
        target_part = self.get_part_at_time(target_time)
        if not target_part:
            # Time is before first part or after last
            if target_time < 0:
                return 0.0
            return target_time

        # Calculate beat positions for this part
        beats_per_bar = self._get_beats_per_bar(target_part.signature)

        if target_part.transition == "instant":
            # Simple beat calculation
            seconds_per_beat = 60.0 / target_part.bpm
            time_in_part = target_time - target_part.start_time
            beat_in_part = time_in_part / seconds_per_beat

            # Get floor and ceiling beats
            floor_beat = int(beat_in_part)
            ceil_beat = floor_beat + 1

            floor_time = target_part.start_time + (floor_beat * seconds_per_beat)
            ceil_time = target_part.start_time + (ceil_beat * seconds_per_beat)

            # Return closest
            if abs(target_time - floor_time) <= abs(target_time - ceil_time):
                return floor_time
            return ceil_time
        else:
            # For gradual transitions, use simpler snap to part boundaries or mid-bar
            # (Precise beat snapping in gradual transitions is complex)
            return target_time

    def get_beat_times_in_range(self, start_time: float, end_time: float) -> List[tuple]:
        """Get all beat times in a time range for grid drawing.

        Args:
            start_time: Start of range in seconds
            end_time: End of range in seconds

        Returns:
            List of (time, is_bar) tuples where is_bar indicates bar boundary
        """
        beat_times = []

        for part in self.parts:
            part_end = part.start_time + part.duration

            # Skip parts outside our range
            if part_end < start_time or part.start_time > end_time:
                continue

            beats_per_bar = self._get_beats_per_bar(part.signature)
            total_beats = int(part.num_bars * beats_per_bar)

            if part.transition == "instant":
                seconds_per_beat = 60.0 / part.bpm

                for beat_index in range(total_beats + 1):
                    beat_time = part.start_time + (beat_index * seconds_per_beat)

                    if start_time <= beat_time <= end_time:
                        is_bar = (beat_index % beats_per_bar) == 0
                        beat_times.append((beat_time, is_bar))
            else:
                # For gradual transitions, just mark bar boundaries
                part_index = self.parts.index(part)
                previous_bpm = (self.parts[part_index - 1].bpm
                               if part_index > 0 else part.bpm)

                accumulated_time = part.start_time
                for bar in range(part.num_bars + 1):
                    if start_time <= accumulated_time <= end_time:
                        beat_times.append((accumulated_time, True))

                    if bar < part.num_bars:
                        progress = (bar / part.num_bars) ** 0.52
                        current_bpm = previous_bpm + (part.bpm - previous_bpm) * progress
                        seconds_per_beat = 60.0 / current_bpm
                        bar_duration = beats_per_bar * seconds_per_beat
                        accumulated_time += bar_duration

        return beat_times
