import json
import mido
from typing import Optional, List
from core.project import Project
from core.lane import MidiLane
from core.midi_block import MidiBlock, MidiMessageType


class FileManager:
    def save_project(self, project: Project, file_path: str):
        """Save project to JSON file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(project.to_dict(), f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to save project: {str(e)}")

    def load_project(self, file_path: str) -> Project:
        """Load project from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            project = Project()
            project.from_dict(data)
            return project
        except Exception as e:
            raise Exception(f"Failed to load project: {str(e)}")

    def load_song_structure(self, file_path: str):
        """Load song structure from file (to be implemented)"""
        pass

    def export_midi_tracks(self, project: Project, base_file_path: str):
        """Export all MIDI lanes to a single MIDI file with multiple tracks"""
        midi_lanes = project.get_midi_lanes()

        if not midi_lanes:
            raise Exception("No MIDI lanes to export")

        # Create a new MIDI file
        mid = mido.MidiFile(ticks_per_beat=480, type=1)

        # Add tempo track
        tempo_track = mido.MidiTrack()
        mid.tracks.append(tempo_track)
        tempo_track.append(mido.MetaMessage('track_name', name='Tempo Track', time=0))
        tempo = mido.bpm2tempo(project.bpm)
        tempo_track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
        tempo_track.append(mido.MetaMessage('end_of_track', time=0))

        # Add each MIDI lane as a track
        for lane in midi_lanes:
            track = mido.MidiTrack()
            mid.tracks.append(track)

            # Add track name
            track.append(mido.MetaMessage('track_name', name=lane.name, time=0))

            # Convert MIDI blocks to MIDI messages
            events = []

            for block in lane.midi_blocks:
                # Convert time in seconds to ticks
                start_ticks = self._seconds_to_ticks(block.start_time, project.bpm, mid.ticks_per_beat)
                end_ticks = self._seconds_to_ticks(block.start_time + block.duration, project.bpm, mid.ticks_per_beat)

                # Create appropriate MIDI message based on message type
                if block.message_type == MidiMessageType.PROGRAM_CHANGE:
                    msg = mido.Message('program_change',
                                       channel=lane.midi_channel - 1,
                                       program=block.value1,
                                       time=0)
                    events.append((start_ticks, msg))

                elif block.message_type == MidiMessageType.CONTROL_CHANGE:
                    msg = mido.Message('control_change',
                                       channel=lane.midi_channel - 1,
                                       control=block.value1,
                                       value=block.value2,
                                       time=0)
                    events.append((start_ticks, msg))

                elif block.message_type == MidiMessageType.NOTE_ON:
                    # Add note on
                    note_on = mido.Message('note_on',
                                           channel=lane.midi_channel - 1,
                                           note=block.value1,
                                           velocity=block.value2,
                                           time=0)
                    events.append((start_ticks, note_on))

                    # Add note off
                    note_off = mido.Message('note_off',
                                            channel=lane.midi_channel - 1,
                                            note=block.value1,
                                            velocity=0,
                                            time=0)
                    events.append((end_ticks, note_off))

                elif block.message_type == MidiMessageType.NOTE_OFF:
                    msg = mido.Message('note_off',
                                       channel=lane.midi_channel - 1,
                                       note=block.value1,
                                       velocity=0,
                                       time=0)
                    events.append((start_ticks, msg))

                elif block.message_type == MidiMessageType.KEMPER_RIG_CHANGE:
                    # Kemper Rig Change: CC47 with bank, then CC50-54 with value 1
                    bank = block.value1  # 0-124
                    slot = block.value2  # 1-5

                    # Add CC47 with bank value
                    cc47 = mido.Message('control_change',
                                        channel=lane.midi_channel - 1,
                                        control=47,
                                        value=bank,
                                        time=0)
                    events.append((start_ticks, cc47))

                    # Add CC50-54 (depending on slot) with value 1
                    cc_number = 49 + slot  # slot 1-5 maps to CC50-54
                    cc_slot = mido.Message('control_change',
                                           channel=lane.midi_channel - 1,
                                           control=cc_number,
                                           value=1,
                                           time=0)
                    events.append((start_ticks, cc_slot))

            # Sort events by time
            events.sort(key=lambda x: x[0])

            # Convert absolute times to delta times and add to track
            previous_time = 0
            for abs_time, msg in events:
                delta_time = abs_time - previous_time
                msg.time = delta_time
                track.append(msg)
                previous_time = abs_time

            # Add end of track
            track.append(mido.MetaMessage('end_of_track', time=0))

        # Save the MIDI file
        mid.save(base_file_path)

        return [base_file_path]

    def import_midi_file(self, file_path: str, bpm: float) -> List[MidiLane]:
        """Import a MIDI file and create MIDI lanes"""
        try:
            mid = mido.MidiFile(file_path)
            lanes = []

            # Process each track
            for i, track in enumerate(mid.tracks):
                # Get track name
                track_name = f"MIDI {i + 1}"
                for msg in track:
                    if msg.type == 'track_name':
                        track_name = msg.name
                        break

                # Create a new MIDI lane
                lane = MidiLane(track_name)

                # Parse MIDI messages and create blocks
                absolute_time = 0
                note_on_events = {}  # Track note_on events to create blocks with duration

                for msg in track:
                    absolute_time += msg.time

                    if msg.type == 'note_on' and msg.velocity > 0:
                        # Store note_on event
                        note_key = (msg.channel, msg.note)
                        time_in_seconds = self._ticks_to_seconds(absolute_time, bpm, mid.ticks_per_beat)
                        note_on_events[note_key] = {
                            'time': time_in_seconds,
                            'velocity': msg.velocity
                        }

                    elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                        # Create block for note
                        note_key = (msg.channel, msg.note)
                        if note_key in note_on_events:
                            note_on = note_on_events[note_key]
                            end_time = self._ticks_to_seconds(absolute_time, bpm, mid.ticks_per_beat)
                            duration = end_time - note_on['time']

                            # Create MIDI block
                            block = lane.add_midi_block(note_on['time'], duration)
                            block.set_note(msg.note, note_on['velocity'], True)
                            block.name = f"Note {self._note_number_to_name(msg.note)}"

                            # Set the channel
                            lane.set_midi_channel(msg.channel + 1)

                            del note_on_events[note_key]

                    elif msg.type == 'program_change':
                        time_in_seconds = self._ticks_to_seconds(absolute_time, bpm, mid.ticks_per_beat)
                        block = lane.add_midi_block(time_in_seconds, 0.1)
                        block.set_program_change(msg.program)
                        block.name = f"PC {msg.program}"
                        lane.set_midi_channel(msg.channel + 1)

                    elif msg.type == 'control_change':
                        time_in_seconds = self._ticks_to_seconds(absolute_time, bpm, mid.ticks_per_beat)
                        block = lane.add_midi_block(time_in_seconds, 0.1)
                        block.set_control_change(msg.control, msg.value)
                        block.name = f"CC {msg.control}"
                        lane.set_midi_channel(msg.channel + 1)

                # Only add lane if it has blocks
                if lane.midi_blocks:
                    lanes.append(lane)

            return lanes

        except Exception as e:
            raise Exception(f"Failed to import MIDI file: {str(e)}")

    def _seconds_to_ticks(self, seconds: float, bpm: float, ticks_per_beat: int) -> int:
        """Convert time in seconds to MIDI ticks"""
        beats = (seconds / 60.0) * bpm
        ticks = int(beats * ticks_per_beat)
        return ticks

    def _ticks_to_seconds(self, ticks: int, bpm: float, ticks_per_beat: int) -> float:
        """Convert MIDI ticks to time in seconds"""
        beats = ticks / ticks_per_beat
        seconds = (beats / bpm) * 60.0
        return seconds

    def _note_number_to_name(self, note_number: int) -> str:
        """Convert MIDI note number to note name"""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note_number // 12) - 1
        note = notes[note_number % 12]
        return f"{note}{octave}"
