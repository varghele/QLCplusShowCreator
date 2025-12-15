import json
from typing import List, Dict, Any
from .lane import Lane, AudioLane, MidiLane
from .song_structure import SongStructure


class Project:
    def __init__(self):
        self.lanes: List[Lane] = []
        self.song_structure: SongStructure = None
        self.project_name: str = "Untitled Project"
        self.bpm: float = 120.0

    def add_lane(self, lane_type: str, name: str = "") -> Lane:
        if lane_type == "audio":
            lane = AudioLane(name or f"Audio {len(self.get_audio_lanes()) + 1}")
        elif lane_type == "midi":
            lane = MidiLane(name or f"MIDI {len(self.get_midi_lanes()) + 1}")
        else:
            raise ValueError(f"Unknown lane type: {lane_type}")

        self.lanes.append(lane)
        return lane

    def remove_lane(self, lane: Lane):
        if lane in self.lanes:
            self.lanes.remove(lane)

    def get_audio_lanes(self) -> List[AudioLane]:
        return [lane for lane in self.lanes if isinstance(lane, AudioLane)]

    def get_midi_lanes(self) -> List[MidiLane]:
        return [lane for lane in self.lanes if isinstance(lane, MidiLane)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "bpm": self.bpm,
            "lanes": [lane.to_dict() for lane in self.lanes],
            "song_structure": self.song_structure.to_dict() if self.song_structure else None
        }

    def from_dict(self, data: Dict[str, Any]):
        self.project_name = data.get("project_name", "Untitled Project")
        self.bpm = data.get("bpm", 120.0)

        self.lanes.clear()
        for lane_data in data.get("lanes", []):
            if lane_data["type"] == "audio":
                lane = AudioLane("")
            else:
                lane = MidiLane("")
            lane.from_dict(lane_data)
            self.lanes.append(lane)

        if data.get("song_structure"):
            self.song_structure = SongStructure()
            self.song_structure.from_dict(data["song_structure"])
