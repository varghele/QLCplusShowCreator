import csv
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SongPart:
    name: str
    signature: str  # e.g., "4/4"
    bpm: float
    num_bars: int
    transition: str  # "instant" or "gradual"
    color: str  # hex color code
    start_time: float = 0.0  # calculated start time in seconds
    duration: float = 0.0  # calculated duration in seconds

    def get_beats_per_bar(self) -> float:
        """Calculate beats per bar from time signature"""
        numerator, denominator = map(int, self.signature.split('/'))
        return (numerator * 4) / denominator

    def get_total_beats(self) -> float:
        """Get total beats in this part"""
        return self.num_bars * self.get_beats_per_bar()


class SongStructure:
    def __init__(self):
        self.parts: List[SongPart] = []
        self.default_bpm = 120.0

    def load_from_csv(self, file_path: str) -> bool:
        """Load song structure from CSV file"""
        try:
            self.parts.clear()

            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                current_time = 0.0
                previous_bpm = None

                for row in reader:
                    # Parse CSV row
                    part = SongPart(
                        name=row['showpart'].strip(),
                        signature=row['signature'].strip(),
                        bpm=float(row['bpm']),
                        num_bars=int(row['num_bars']),
                        transition=row['transition'].strip().lower(),
                        color=row['color'].strip()
                    )

                    part.start_time = current_time

                    # Calculate duration based on BPM transition
                    duration = self.calculate_part_duration(
                        part, previous_bpm
                    )
                    part.duration = duration

                    self.parts.append(part)
                    current_time += duration
                    previous_bpm = part.bpm

            return True

        except Exception as e:
            print(f"Error loading CSV: {e}")
            return False

    def calculate_part_duration(self, part: SongPart, previous_bpm: Optional[float]) -> float:
        """Calculate the duration of a song part in seconds"""
        if part.transition == "instant" or previous_bpm is None:
            # Simple calculation for instant transition
            beats_per_bar = part.get_beats_per_bar()
            total_beats = part.num_bars * beats_per_bar
            seconds_per_beat = 60.0 / part.bpm
            return total_beats * seconds_per_beat

        elif part.transition == "gradual":
            # Complex calculation for gradual BPM transition
            return self.calculate_gradual_transition_duration(
                part, previous_bpm
            )

        else:
            raise ValueError(f"Unknown transition type: {part.transition}")

    def calculate_gradual_transition_duration(self, part: SongPart, start_bpm: float) -> float:
        """Calculate duration for gradual BPM transition"""
        beats_per_bar = part.get_beats_per_bar()
        total_duration = 0.0

        for bar in range(part.num_bars):
            # Calculate BPM progression using the same formula as your function
            current_progress = (bar / part.num_bars) ** 0.52
            current_bpm = start_bpm + (part.bpm - start_bpm) * current_progress

            # Calculate time for this bar
            seconds_per_beat = 60.0 / current_bpm
            bar_duration = beats_per_bar * seconds_per_beat
            total_duration += bar_duration

        return total_duration

    def get_bpm_at_time(self, time: float) -> float:
        """Get the BPM at a specific time, accounting for gradual transitions"""
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
        progress = time_in_part / current_part.duration
        progress = min(1.0, max(0.0, progress))

        # Apply the same curve as in your function
        curved_progress = progress ** 0.52
        interpolated_bpm = previous_bpm + (current_part.bpm - previous_bpm) * curved_progress

        return interpolated_bpm

    def get_part_at_time(self, time: float) -> Optional[SongPart]:
        """Get the song part at a specific time"""
        for part in self.parts:
            if part.start_time <= time < part.start_time + part.duration:
                return part
        return None

    def get_total_duration(self) -> float:
        """Get total duration of the song structure"""
        if not self.parts:
            return 0.0
        last_part = self.parts[-1]
        return last_part.start_time + last_part.duration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_bpm": self.default_bpm,
            "parts": [
                {
                    "name": part.name,
                    "signature": part.signature,
                    "bpm": part.bpm,
                    "num_bars": part.num_bars,
                    "transition": part.transition,
                    "color": part.color,
                    "start_time": part.start_time,
                    "duration": part.duration
                }
                for part in self.parts
            ]
        }

    def from_dict(self, data: Dict[str, Any]):
        self.default_bpm = data.get("default_bpm", 120.0)
        self.parts.clear()

        for part_data in data.get("parts", []):
            part = SongPart(
                name=part_data["name"],
                signature=part_data["signature"],
                bpm=part_data["bpm"],
                num_bars=part_data["num_bars"],
                transition=part_data["transition"],
                color=part_data["color"],
                start_time=part_data["start_time"],
                duration=part_data["duration"]
            )
            self.parts.append(part)
