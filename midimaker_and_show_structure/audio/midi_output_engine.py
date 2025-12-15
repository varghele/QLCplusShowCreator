"""
MIDI output engine for real-time MIDI playback.
Handles sending MIDI messages to the selected MIDI device during playback.
"""

import rtmidi
from typing import Optional, Set
from core.midi_block import MidiBlock, MidiMessageType


class MidiOutputEngine:
    """Manages real-time MIDI output during playback"""

    def __init__(self):
        self._midi_out = rtmidi.MidiOut()
        self._current_device_index: Optional[int] = None
        self._is_initialized = False

        # Track which blocks have been triggered to avoid retriggering
        self._triggered_blocks: Set[int] = set()

        # Track active notes for proper note off handling
        self._active_notes = {}  # {(channel, note): block_id}

    def initialize(self, device_index: Optional[int] = None) -> bool:
        """Initialize MIDI output with the specified device"""
        try:
            # Close existing port if open
            if self._midi_out.is_port_open():
                self._midi_out.close_port()

            # Get available ports
            available_ports = self._midi_out.get_ports()

            if not available_ports:
                print("No MIDI output devices available")
                self._is_initialized = False
                return False

            # Use first device if no index specified
            if device_index is None:
                device_index = 0

            # Validate device index
            if device_index < 0 or device_index >= len(available_ports):
                print(f"Invalid MIDI device index: {device_index}")
                self._is_initialized = False
                return False

            # Open the MIDI port
            self._midi_out.open_port(device_index)
            self._current_device_index = device_index
            self._is_initialized = True

            print(f"MIDI output initialized: {available_ports[device_index]}")
            return True

        except Exception as e:
            print(f"Error initializing MIDI output: {e}")
            self._is_initialized = False
            return False

    def cleanup(self):
        """Cleanup MIDI resources"""
        try:
            # Send all notes off on all channels before closing
            if self._midi_out.is_port_open():
                for channel in range(16):
                    # All notes off (CC 123)
                    self._midi_out.send_message([0xB0 + channel, 123, 0])
                    # All sound off (CC 120)
                    self._midi_out.send_message([0xB0 + channel, 120, 0])

                self._midi_out.close_port()

            self._active_notes.clear()
            self._triggered_blocks.clear()
            self._is_initialized = False

        except Exception as e:
            print(f"Error cleaning up MIDI output: {e}")

    def is_initialized(self) -> bool:
        """Check if MIDI output is initialized"""
        return self._is_initialized and self._midi_out.is_port_open()

    def send_midi_message(self, message: list):
        """Send a raw MIDI message"""
        if not self.is_initialized():
            return

        try:
            self._midi_out.send_message(message)
        except Exception as e:
            print(f"Error sending MIDI message: {e}")

    def process_block_start(self, block: MidiBlock, channel: int):
        """Process MIDI block at its start time

        Args:
            block: The MIDI block to process
            channel: MIDI channel (0-15, will be adjusted from 1-16)
        """
        if not self.is_initialized():
            return

        block_id = id(block)

        # Skip if already triggered
        if block_id in self._triggered_blocks:
            return

        # Adjust channel to 0-15 range
        midi_channel = max(0, min(15, channel - 1))

        try:
            if block.message_type == MidiMessageType.NOTE_ON:
                # Send note on
                note = block.value1
                velocity = block.value2

                # Note on message: 0x90 + channel
                message = [0x90 + midi_channel, note, velocity]
                self.send_midi_message(message)

                # Track active note
                self._active_notes[(midi_channel, note)] = block_id

            elif block.message_type == MidiMessageType.PROGRAM_CHANGE:
                # Program change message: 0xC0 + channel, program
                program = block.value1
                message = [0xC0 + midi_channel, program]
                self.send_midi_message(message)

            elif block.message_type == MidiMessageType.CONTROL_CHANGE:
                # Control change message: 0xB0 + channel, control, value
                control = block.value1
                value = block.value2
                message = [0xB0 + midi_channel, control, value]
                self.send_midi_message(message)

            elif block.message_type == MidiMessageType.KEMPER_RIG_CHANGE:
                # Kemper Rig Change: CC47 with bank value, then CC50-54 to load slot
                bank = block.value1  # 0-124
                slot = block.value2  # 1-5

                print(f"Kemper Rig Change: Bank={bank}, Slot={slot}, Channel={midi_channel}")

                # Send CC47 with bank value to preselect Performance
                cc47_message = [0xB0 + midi_channel, 47, bank]
                self.send_midi_message(cc47_message)
                print(f"Sent CC47: {cc47_message}")

                # Send CC50-54 (depending on slot) with value 1 to load the slot
                # CC50 = slot 1, CC51 = slot 2, etc.
                cc_number = 49 + slot  # slot 1-5 maps to CC50-54
                cc_slot_message = [0xB0 + midi_channel, cc_number, 1]
                self.send_midi_message(cc_slot_message)
                print(f"Sent CC{cc_number}: {cc_slot_message}")

            elif block.message_type == MidiMessageType.VOICELIVE3_PRESET:
                # Voicelive3 Preset: CC32 for bank select, then PC for patch
                bank = block.value1   # 0-3
                patch = block.value2  # 0-127

                print(f"Voicelive3 Preset: Bank={bank}, Patch={patch}, Channel={midi_channel}")

                # Send CC32 (Bank Select LSB) with bank value
                cc32_message = [0xB0 + midi_channel, 32, bank]
                self.send_midi_message(cc32_message)
                print(f"Sent CC32: {cc32_message}")

                # Send Program Change for patch selection
                pc_message = [0xC0 + midi_channel, patch]
                self.send_midi_message(pc_message)
                print(f"Sent PC: {pc_message}")

            elif block.message_type == MidiMessageType.QUAD_CORTEX_PRESET:
                # Quad Cortex Preset: CC0 for bank, PC for preset, CC43 for scene
                bank = block.value1    # 0-15
                preset = block.value2  # 0-127
                scene = block.value3   # 0-7 (A-H)

                print(f"Quad Cortex Preset: Bank={bank}, Preset={preset}, Scene={scene}, Channel={midi_channel}")

                # Send CC0 (Bank Select MSB) with bank value
                cc0_message = [0xB0 + midi_channel, 0, bank]
                self.send_midi_message(cc0_message)
                print(f"Sent CC0: {cc0_message}")

                # Send Program Change for preset selection
                pc_message = [0xC0 + midi_channel, preset]
                self.send_midi_message(pc_message)
                print(f"Sent PC: {pc_message}")

                # Send CC43 for scene selection (0-7 for scenes A-H)
                cc43_message = [0xB0 + midi_channel, 43, scene]
                self.send_midi_message(cc43_message)
                print(f"Sent CC43: {cc43_message}")

            # Mark as triggered
            self._triggered_blocks.add(block_id)

        except Exception as e:
            print(f"Error processing MIDI block start: {e}")

    def process_block_end(self, block: MidiBlock, channel: int):
        """Process MIDI block at its end time (for note off)

        Args:
            block: The MIDI block to process
            channel: MIDI channel (0-15, will be adjusted from 1-16)
        """
        if not self.is_initialized():
            return

        # Only NOTE_ON blocks need note off
        if block.message_type != MidiMessageType.NOTE_ON:
            return

        # Adjust channel to 0-15 range
        midi_channel = max(0, min(15, channel - 1))

        try:
            note = block.value1

            # Check if this note is still active
            note_key = (midi_channel, note)
            if note_key in self._active_notes:
                # Send note off: 0x80 + channel, note, 0
                message = [0x80 + midi_channel, note, 0]
                self.send_midi_message(message)

                # Remove from active notes
                del self._active_notes[note_key]

        except Exception as e:
            print(f"Error processing MIDI block end: {e}")

    def reset_playback(self):
        """Reset playback state (called when stopping or seeking)"""
        # Send note off for all active notes
        if self.is_initialized():
            for (channel, note), _ in list(self._active_notes.items()):
                message = [0x80 + channel, note, 0]
                self.send_midi_message(message)

        # Clear tracking sets
        self._active_notes.clear()
        self._triggered_blocks.clear()

    def panic(self):
        """Send all notes off and reset all controllers on all channels"""
        if not self.is_initialized():
            return

        try:
            for channel in range(16):
                # All notes off (CC 123)
                self._midi_out.send_message([0xB0 + channel, 123, 0])
                # All sound off (CC 120)
                self._midi_out.send_message([0xB0 + channel, 120, 0])
                # Reset all controllers (CC 121)
                self._midi_out.send_message([0xB0 + channel, 121, 0])

            self._active_notes.clear()

        except Exception as e:
            print(f"Error during MIDI panic: {e}")
