from typing import Dict, Any
from enum import Enum


class MidiMessageType(Enum):
    PROGRAM_CHANGE = "PC"
    CONTROL_CHANGE = "CC"
    NOTE_ON = "NOTE_ON"
    NOTE_OFF = "NOTE_OFF"
    KEMPER_RIG_CHANGE = "KEMPER_RIG"
    VOICELIVE3_PRESET = "VL3_PRESET"
    QUAD_CORTEX_PRESET = "QC_PRESET"


class MidiBlock:
    def __init__(self, start_time: float, duration: float):
        self.start_time = start_time
        self.duration = duration
        self.message_type = MidiMessageType.CONTROL_CHANGE
        self.value1 = 0  # CC number, Program number, or Note number
        self.value2 = 127  # CC value, velocity, etc.
        self.value3 = 0  # Additional value for presets requiring 3 parameters (e.g., QC scene)
        self.name = "MIDI Block"

    def set_program_change(self, program_number: int):
        self.message_type = MidiMessageType.PROGRAM_CHANGE
        self.value1 = program_number
        self.value2 = 0

    def set_control_change(self, cc_number: int, cc_value: int):
        self.message_type = MidiMessageType.CONTROL_CHANGE
        self.value1 = cc_number
        self.value2 = cc_value

    def set_note(self, note_number: int, velocity: int, note_on: bool = True):
        self.message_type = MidiMessageType.NOTE_ON if note_on else MidiMessageType.NOTE_OFF
        self.value1 = note_number
        self.value2 = velocity

    def set_kemper_rig_change(self, bank: int, slot: int):
        """Set Kemper Rig Change

        Args:
            bank: Performance/bank number (0-124)
            slot: Slot number (1-5)
        """
        self.message_type = MidiMessageType.KEMPER_RIG_CHANGE
        self.value1 = max(0, min(124, bank))  # Clamp to 0-124
        self.value2 = max(1, min(5, slot))    # Clamp to 1-5

    def set_voicelive3_preset(self, bank: int, patch: int):
        """Set Voicelive3 Preset Change

        Args:
            bank: Bank number (0-3)
            patch: Patch number within bank (0-127)
        """
        self.message_type = MidiMessageType.VOICELIVE3_PRESET
        self.value1 = max(0, min(3, bank))      # Clamp to 0-3
        self.value2 = max(0, min(127, patch))   # Clamp to 0-127

    def set_quad_cortex_preset(self, bank: int, preset: int, scene: int):
        """Set Quad Cortex Preset Change

        Args:
            bank: Preset Group/Bank number (0-15), sent via CC0
            preset: Preset number (0-127), sent via PC
            scene: Scene number (0-7 for scenes A-H), sent via CC43
        """
        self.message_type = MidiMessageType.QUAD_CORTEX_PRESET
        self.value1 = max(0, min(15, bank))     # Clamp to 0-15
        self.value2 = max(0, min(127, preset))  # Clamp to 0-127
        self.value3 = max(0, min(7, scene))     # Clamp to 0-7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time,
            "duration": self.duration,
            "message_type": self.message_type.value,
            "value1": self.value1,
            "value2": self.value2,
            "value3": self.value3,
            "name": self.name
        }

    def from_dict(self, data: Dict[str, Any]):
        self.start_time = data.get("start_time", 0.0)
        self.duration = data.get("duration", 1.0)
        self.message_type = MidiMessageType(data.get("message_type", "CC"))
        self.value1 = data.get("value1", 0)
        self.value2 = data.get("value2", 127)
        self.value3 = data.get("value3", 0)
        self.name = data.get("name", "MIDI Block")
