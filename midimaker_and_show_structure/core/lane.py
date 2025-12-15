from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .midi_block import MidiBlock


class Lane(ABC):
    def __init__(self, name: str):
        self.name = name
        self.muted = False
        self.solo = False

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def from_dict(self, data: Dict[str, Any]):
        pass


class AudioLane(Lane):
    def __init__(self, name: str):
        super().__init__(name)
        self.audio_file_path: Optional[str] = None
        self.volume = 1.0

    def set_audio_file(self, file_path: str):
        self.audio_file_path = file_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "audio",
            "name": self.name,
            "muted": self.muted,
            "solo": self.solo,
            "audio_file_path": self.audio_file_path,
            "volume": self.volume
        }

    def from_dict(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.muted = data.get("muted", False)
        self.solo = data.get("solo", False)
        self.audio_file_path = data.get("audio_file_path")
        self.volume = data.get("volume", 1.0)


class MidiLane(Lane):
    def __init__(self, name: str):
        super().__init__(name)
        self.midi_channel = 1
        self.channel_name = f"Channel {self.midi_channel}"
        self.midi_blocks: List[MidiBlock] = []

    def add_midi_block(self, start_time: float, duration: float) -> MidiBlock:
        block = MidiBlock(start_time, duration)
        self.midi_blocks.append(block)
        return block

    def remove_midi_block(self, block: MidiBlock):
        if block in self.midi_blocks:
            self.midi_blocks.remove(block)

    def set_midi_channel(self, channel: int, channel_name: str = ""):
        self.midi_channel = channel
        self.channel_name = channel_name or f"Channel {channel}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "midi",
            "name": self.name,
            "muted": self.muted,
            "solo": self.solo,
            "midi_channel": self.midi_channel,
            "channel_name": self.channel_name,
            "midi_blocks": [block.to_dict() for block in self.midi_blocks]
        }

    def from_dict(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.muted = data.get("muted", False)
        self.solo = data.get("solo", False)
        self.midi_channel = data.get("midi_channel", 1)
        self.channel_name = data.get("channel_name", f"Channel {self.midi_channel}")

        self.midi_blocks.clear()
        for block_data in data.get("midi_blocks", []):
            block = MidiBlock(0, 0)
            block.from_dict(block_data)
            self.midi_blocks.append(block)
