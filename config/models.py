# config/models.py

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import yaml
import xml.etree.ElementTree as ET
import os
import sys
import csv
from utils.fixture_utils import determine_fixture_type


@dataclass
class FixtureMode:
    name: str
    channels: int


@dataclass
class Fixture:
    universe: int
    address: int
    manufacturer: str
    model: str
    name: str
    group: str
    direction: str
    current_mode: str
    available_modes: List[FixtureMode]
    type: str = "PAR"  # Default type if none specified
    x: float = 0.0     # X position in meters
    y: float = 0.0     # Y position in meters
    z: float = 0.0     # Z height in meters
    rotation: float = 0.0  # Rotation angle in degrees (0-359)


@dataclass
class Spot:
    name: str
    x: float = 0.0     # X position in meters
    y: float = 0.0     # Y position in meters


@dataclass
class FixtureGroup:
    name: str
    fixtures: List[Fixture]
    color: str = '#808080'  # Default color for the group
    capabilities: Optional['FixtureGroupCapabilities'] = None  # Auto-detected sublane capabilities


@dataclass
class FixtureGroupCapabilities:
    """Capabilities of a fixture group, determining which sublanes to display."""
    has_dimmer: bool = False
    has_colour: bool = False
    has_movement: bool = False
    has_special: bool = False

    def to_dict(self) -> Dict:
        return {
            "has_dimmer": self.has_dimmer,
            "has_colour": self.has_colour,
            "has_movement": self.has_movement,
            "has_special": self.has_special
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'FixtureGroupCapabilities':
        return cls(
            has_dimmer=data.get("has_dimmer", False),
            has_colour=data.get("has_colour", False),
            has_movement=data.get("has_movement", False),
            has_special=data.get("has_special", False)
        )


@dataclass
class DimmerBlock:
    """Dimmer sublane block - controls intensity and shutter effects."""
    start_time: float
    end_time: float
    intensity: float = 255.0  # 0-255
    strobe_speed: float = 0.0  # 0 = no strobe, >0 = strobe speed
    iris: float = 255.0  # 0-255, if applicable
    effect_type: str = "static"  # Effect type: "static", "twinkle", "strobe", etc.
    effect_speed: str = "1"  # Speed multiplier: "1/4", "1/2", "1", "2", "4", etc.

    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "intensity": self.intensity,
            "strobe_speed": self.strobe_speed,
            "iris": self.iris,
            "effect_type": self.effect_type,
            "effect_speed": self.effect_speed
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DimmerBlock':
        return cls(
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", 0.0),
            intensity=data.get("intensity", 255.0),
            strobe_speed=data.get("strobe_speed", 0.0),
            iris=data.get("iris", 255.0),
            effect_type=data.get("effect_type", "static"),
            effect_speed=data.get("effect_speed", "1")
        )


@dataclass
class ColourBlock:
    """Colour sublane block - controls color parameters."""
    start_time: float
    end_time: float
    color_mode: str = "RGB"  # "RGB", "CMY", "HSV", "Wheel"

    # RGB/CMY/RGBW values (0-255)
    red: float = 0.0
    green: float = 0.0
    blue: float = 0.0
    white: float = 0.0
    amber: float = 0.0
    cyan: float = 0.0
    magenta: float = 0.0
    yellow: float = 0.0
    uv: float = 0.0
    lime: float = 0.0

    # HSV values
    hue: float = 0.0  # 0-360
    saturation: float = 0.0  # 0-100
    value: float = 0.0  # 0-100

    # Color wheel
    color_wheel_position: int = 0  # Wheel position

    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "color_mode": self.color_mode,
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
            "white": self.white,
            "amber": self.amber,
            "cyan": self.cyan,
            "magenta": self.magenta,
            "yellow": self.yellow,
            "uv": self.uv,
            "lime": self.lime,
            "hue": self.hue,
            "saturation": self.saturation,
            "value": self.value,
            "color_wheel_position": self.color_wheel_position
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ColourBlock':
        return cls(
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", 0.0),
            color_mode=data.get("color_mode", "RGB"),
            red=data.get("red", 0.0),
            green=data.get("green", 0.0),
            blue=data.get("blue", 0.0),
            white=data.get("white", 0.0),
            amber=data.get("amber", 0.0),
            cyan=data.get("cyan", 0.0),
            magenta=data.get("magenta", 0.0),
            yellow=data.get("yellow", 0.0),
            uv=data.get("uv", 0.0),
            lime=data.get("lime", 0.0),
            hue=data.get("hue", 0.0),
            saturation=data.get("saturation", 0.0),
            value=data.get("value", 0.0),
            color_wheel_position=data.get("color_wheel_position", 0)
        )


@dataclass
class MovementBlock:
    """Movement sublane block - controls pan, tilt, and positioning.

    Supports both static positioning and dynamic shape effects (circle, diamond, etc.).
    When effect_type is 'static', pan/tilt define the exact position.
    When effect_type is a shape, pan/tilt define the center, and the shape is traced
    within the bounds defined by pan_min/pan_max and tilt_min/tilt_max.
    """
    start_time: float
    end_time: float
    pan: float = 127.5  # 0-255 (center position for shapes, or static position)
    tilt: float = 127.5  # 0-255 (center position for shapes, or static position)
    pan_fine: float = 0.0  # Fine adjustment
    tilt_fine: float = 0.0  # Fine adjustment
    speed: float = 255.0  # Movement speed (DMX)
    interpolate_from_previous: bool = True  # Gradual transition from previous block

    # Effect type and speed (similar to DimmerBlock)
    effect_type: str = "static"  # "static", "circle", "diamond", "lissajous", "figure_8", "square", "triangle", "random", "bounce"
    effect_speed: str = "1"  # Speed multiplier: "1/4", "1/2", "1", "2", "4"

    # Boundary limits (hard limits the effect cannot exceed)
    pan_min: float = 0.0  # Minimum pan value (0-255)
    pan_max: float = 255.0  # Maximum pan value (0-255)
    tilt_min: float = 0.0  # Minimum tilt value (0-255)
    tilt_max: float = 255.0  # Maximum tilt value (0-255)

    # Amplitude (size of the effect within the bounds)
    pan_amplitude: float = 50.0  # How far pan moves from center (0-127.5)
    tilt_amplitude: float = 50.0  # How far tilt moves from center (0-127.5)

    # Lissajous-specific parameter
    lissajous_ratio: str = "1:2"  # Frequency ratio for lissajous curves: "1:2", "2:3", "3:4", "3:2", "4:3"

    # Phase offset for multi-fixture effects
    phase_offset_enabled: bool = False  # Enable phase offset between fixtures
    phase_offset_degrees: float = 0.0  # Phase offset in degrees (0-360)

    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "pan": self.pan,
            "tilt": self.tilt,
            "pan_fine": self.pan_fine,
            "tilt_fine": self.tilt_fine,
            "speed": self.speed,
            "interpolate_from_previous": self.interpolate_from_previous,
            "effect_type": self.effect_type,
            "effect_speed": self.effect_speed,
            "pan_min": self.pan_min,
            "pan_max": self.pan_max,
            "tilt_min": self.tilt_min,
            "tilt_max": self.tilt_max,
            "pan_amplitude": self.pan_amplitude,
            "tilt_amplitude": self.tilt_amplitude,
            "lissajous_ratio": self.lissajous_ratio,
            "phase_offset_enabled": self.phase_offset_enabled,
            "phase_offset_degrees": self.phase_offset_degrees
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'MovementBlock':
        return cls(
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", 0.0),
            pan=data.get("pan", 127.5),
            tilt=data.get("tilt", 127.5),
            pan_fine=data.get("pan_fine", 0.0),
            tilt_fine=data.get("tilt_fine", 0.0),
            speed=data.get("speed", 255.0),
            interpolate_from_previous=data.get("interpolate_from_previous", True),
            effect_type=data.get("effect_type", "static"),
            effect_speed=data.get("effect_speed", "1"),
            pan_min=data.get("pan_min", 0.0),
            pan_max=data.get("pan_max", 255.0),
            tilt_min=data.get("tilt_min", 0.0),
            tilt_max=data.get("tilt_max", 255.0),
            pan_amplitude=data.get("pan_amplitude", 50.0),
            tilt_amplitude=data.get("tilt_amplitude", 50.0),
            lissajous_ratio=data.get("lissajous_ratio", "1:2"),
            phase_offset_enabled=data.get("phase_offset_enabled", False),
            phase_offset_degrees=data.get("phase_offset_degrees", 0.0)
        )


@dataclass
class SpecialBlock:
    """Special sublane block - controls gobo, beam, and prism effects."""
    start_time: float
    end_time: float
    gobo_index: int = 0  # Gobo selection
    gobo_rotation: float = 0.0  # Gobo rotation speed/position
    focus: float = 127.5  # Beam focus (0-255)
    zoom: float = 127.5  # Beam zoom (0-255)
    prism_enabled: bool = False  # Prism on/off
    prism_rotation: float = 0.0  # Prism rotation speed

    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "gobo_index": self.gobo_index,
            "gobo_rotation": self.gobo_rotation,
            "focus": self.focus,
            "zoom": self.zoom,
            "prism_enabled": self.prism_enabled,
            "prism_rotation": self.prism_rotation
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SpecialBlock':
        return cls(
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", 0.0),
            gobo_index=data.get("gobo_index", 0),
            gobo_rotation=data.get("gobo_rotation", 0.0),
            focus=data.get("focus", 127.5),
            zoom=data.get("zoom", 127.5),
            prism_enabled=data.get("prism_enabled", False),
            prism_rotation=data.get("prism_rotation", 0.0)
        )


@dataclass
class ShowEffect:
    show_part: str
    fixture_group: str
    effect: str
    speed: str
    color: str
    intensity: int = 200
    spot: str = ""

@dataclass
class ShowPart:
    name: str
    color: str
    signature: str
    bpm: float
    num_bars: int
    transition: str
    # Runtime fields (calculated, not stored)
    start_time: float = 0.0
    duration: float = 0.0


@dataclass
class LightBlock:
    """Represents an effect block (envelope) on a light lane timeline with sublanes.

    The LightBlock acts as an envelope containing sublane blocks.
    Start/end times are automatically adjusted based on sublane block extents.
    """
    start_time: float      # In seconds (envelope start)
    end_time: float        # In seconds (envelope end)
    effect_name: str       # "module.function" e.g., "bars.static"
    modified: bool = False  # True if sublanes modified beyond original effect

    # Sublane blocks - now supports MULTIPLE blocks per sublane type
    dimmer_blocks: List[DimmerBlock] = field(default_factory=list)
    colour_blocks: List[ColourBlock] = field(default_factory=list)
    movement_blocks: List[MovementBlock] = field(default_factory=list)
    special_blocks: List[SpecialBlock] = field(default_factory=list)

    # Legacy support (deprecated, kept for migration)
    duration: Optional[float] = None  # Deprecated: use end_time - start_time
    parameters: Dict[str, any] = field(default_factory=dict)  # Deprecated

    def get_duration(self) -> float:
        """Calculate duration from start and end times."""
        return self.end_time - self.start_time

    def update_envelope_bounds(self):
        """Update envelope start/end times based on sublane block extents."""
        # Collect all sublane blocks from all lists
        all_blocks = (
            self.dimmer_blocks +
            self.colour_blocks +
            self.movement_blocks +
            self.special_blocks
        )

        if all_blocks:
            self.start_time = min(b.start_time for b in all_blocks)
            self.end_time = max(b.end_time for b in all_blocks)

    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "effect_name": self.effect_name,
            "modified": self.modified,
            "dimmer_blocks": [b.to_dict() for b in self.dimmer_blocks],
            "colour_blocks": [b.to_dict() for b in self.colour_blocks],
            "movement_blocks": [b.to_dict() for b in self.movement_blocks],
            "special_blocks": [b.to_dict() for b in self.special_blocks],
            # Legacy fields
            "duration": self.get_duration(),
            "parameters": self.parameters
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'LightBlock':
        # Handle both new format and legacy format
        start_time = data.get("start_time", 0.0)
        end_time = data.get("end_time")

        # Legacy: if no end_time, calculate from duration
        if end_time is None:
            duration = data.get("duration", 4.0)
            end_time = start_time + duration

        block = cls(
            start_time=start_time,
            end_time=end_time,
            effect_name=data.get("effect_name", ""),
            modified=data.get("modified", False),
            duration=data.get("duration"),
            parameters=data.get("parameters", {})
        )

        # Load sublane blocks - handle both new list format and old single-block format
        # New format: dimmer_blocks (list)
        if data.get("dimmer_blocks"):
            block.dimmer_blocks = [DimmerBlock.from_dict(b) for b in data["dimmer_blocks"]]
        # Old format: dimmer_block (single) - migrate to list
        elif data.get("dimmer_block"):
            block.dimmer_blocks = [DimmerBlock.from_dict(data["dimmer_block"])]

        if data.get("colour_blocks"):
            block.colour_blocks = [ColourBlock.from_dict(b) for b in data["colour_blocks"]]
        elif data.get("colour_block"):
            block.colour_blocks = [ColourBlock.from_dict(data["colour_block"])]

        if data.get("movement_blocks"):
            block.movement_blocks = [MovementBlock.from_dict(b) for b in data["movement_blocks"]]
        elif data.get("movement_block"):
            block.movement_blocks = [MovementBlock.from_dict(data["movement_block"])]

        if data.get("special_blocks"):
            block.special_blocks = [SpecialBlock.from_dict(b) for b in data["special_blocks"]]
        elif data.get("special_block"):
            block.special_blocks = [SpecialBlock.from_dict(data["special_block"])]

        return block


@dataclass
class LightLane:
    """Represents a lane controlling a fixture group on the timeline"""
    name: str
    fixture_group: str
    muted: bool = False
    solo: bool = False
    light_blocks: List[LightBlock] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "fixture_group": self.fixture_group,
            "muted": self.muted,
            "solo": self.solo,
            "light_blocks": [block.to_dict() for block in self.light_blocks]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'LightLane':
        lane = cls(
            name=data.get("name", ""),
            fixture_group=data.get("fixture_group", ""),
            muted=data.get("muted", False),
            solo=data.get("solo", False)
        )
        for block_data in data.get("light_blocks", []):
            lane.light_blocks.append(LightBlock.from_dict(block_data))
        return lane


@dataclass
class TimelineData:
    """Timeline-specific data for a show"""
    lanes: List[LightLane] = field(default_factory=list)
    audio_file_path: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "lanes": [lane.to_dict() for lane in self.lanes],
            "audio_file_path": self.audio_file_path
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TimelineData':
        timeline = cls(
            audio_file_path=data.get("audio_file_path")
        )
        for lane_data in data.get("lanes", []):
            timeline.lanes.append(LightLane.from_dict(lane_data))
        return timeline


@dataclass
class Show:
    name: str
    parts: List[ShowPart] = field(default_factory=list)
    effects: List[ShowEffect] = field(default_factory=list)  # Keep for backwards compatibility
    timeline_data: Optional[TimelineData] = None  # NEW: Timeline representation

@dataclass
class Universe:
    id: int
    name: str
    output: Dict[str, any]

    def __post_init__(self):
        if self.name is None:
            self.name = f"Universe {self.id}"

@dataclass
class UniverseOutput:
    plugin: str
    line: str
    parameters: Dict[str, str]



@dataclass
class Configuration:
    fixtures: List[Fixture] = field(default_factory=list)
    groups: Dict[str, FixtureGroup] = field(default_factory=dict)
    shows: Dict[str, Show] = field(default_factory=dict)
    universes: Dict[int, Universe] = field(default_factory=dict)
    spots: Dict[str, Spot] = field(default_factory=dict)
    workspace_path: Optional[str] = None
    shows_directory: Optional[str] = None  # Directory where show CSV files and audio are stored

    @classmethod
    def from_workspace(cls, workspace_path: str) -> 'Configuration':
        """Create Configuration from QLC+ workspace file"""
        fixture_definitions = cls._scan_fixture_definitions()
        fixtures_data = cls._parse_workspace(workspace_path, fixture_definitions)

        config = cls(fixtures=[], groups={}, workspace_path=workspace_path)

        for fixture_data in fixtures_data:
            # Get fixture definition for type info
            fixture_def = fixture_definitions.get(
                (fixture_data['Manufacturer'], fixture_data['Model']))

            # Create FixtureMode objects from the available modes
            modes = []
            if fixture_data['AvailableModes']:
                for mode in fixture_data['AvailableModes']:
                    modes.append(FixtureMode(
                        name=mode['name'],
                        channels=mode['channels']
                    ))

            fixture = Fixture(
                universe=fixture_data['Universe'],
                address=fixture_data['Address'],
                manufacturer=fixture_data['Manufacturer'],
                model=fixture_data['Model'],
                name=fixture_data['Name'],
                group=fixture_data['Group'],
                direction=fixture_data['Direction'],
                current_mode=fixture_data['CurrentMode'],
                available_modes=modes,
                type=fixture_def['type'] if fixture_def else "PAR",  # Default to PAR if no definition found
                x=fixture_data.get('X', 0.0),
                y=fixture_data.get('Y', 0.0),
                z=fixture_data.get('Z', 0.0),
                rotation=fixture_data.get('Rotation', 0.0)
            )
            config.fixtures.append(fixture)

            if fixture.group:
                if fixture.group not in config.groups:
                    config.groups[fixture.group] = FixtureGroup(fixture.group, [])
                config.groups[fixture.group].fixtures.append(fixture)

        return config

    @classmethod
    def import_show_structure(cls, config: 'Configuration', project_root: str) -> 'Configuration':
        """Import show structure from CSV files into existing Configuration"""
        try:
            shows_dir = os.path.join(project_root, "shows")

            # Scan for all show structure files
            for show_dir in os.listdir(shows_dir):
                show_path = os.path.join(shows_dir, show_dir)
                if os.path.isdir(show_path):
                    structure_file = os.path.join(show_path, f"{show_dir}_structure.csv")
                    if os.path.exists(structure_file):
                        # Check if show already exists in configuration
                        if show_dir in config.shows:
                            show = config.shows[show_dir]
                            # Clear existing parts to reload from CSV
                            show.parts.clear()
                        else:
                            # Create new Show object
                            show = Show(name=show_dir)
                            config.shows[show_dir] = show

                        with open(structure_file, 'r') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                # Create ShowPart with all available information
                                show_part = ShowPart(
                                    name=row['showpart'],
                                    color=row['color'],
                                    signature=row['signature'],
                                    bpm=int(row['bpm']),
                                    num_bars=int(row['num_bars']),
                                    transition=row['transition']
                                )
                                # Add part to show
                                show.parts.append(show_part)

                                # Create empty effects for each group, but only if they don't already exist
                                for group_name in config.groups.keys():
                                    # Check if an effect already exists for this show part and group
                                    existing_effect = None
                                    for effect in show.effects:
                                        if (effect.show_part == show_part.name and
                                                effect.fixture_group == group_name):
                                            existing_effect = effect
                                            break

                                    # Only create new effect if none exists or if existing effect is empty
                                    if existing_effect is None:
                                        # No existing effect found, create a new empty one
                                        effect = ShowEffect(
                                            show_part=show_part.name,
                                            fixture_group=group_name,
                                            effect="",
                                            speed="1",
                                            color="",  # Leave color blank for effects
                                            intensity=200  # Default intensity
                                        )
                                        show.effects.append(effect)
                                    elif (existing_effect.effect == "" and
                                          existing_effect.color == "" and
                                          existing_effect.speed == "1" and
                                          existing_effect.intensity == 200):
                                        # Existing effect is empty (default values), keep it as is
                                        pass
                                    else:
                                        # Existing effect has non-empty values, preserve it
                                        print(f"Preserving existing effect for {show_part.name} - {group_name}: "
                                              f"effect='{existing_effect.effect}', color='{existing_effect.color}'")

            return config

        except Exception as e:
            print(f"Error importing show structure: {e}")
            return config


        except Exception as e:
            print(f"Error importing show structure: {e}")
            import traceback
            traceback.print_exc()
            return config

    def save(self, filename: str):
        """Save configuration to YAML file"""
        data = {
            'fixtures': [asdict(f) for f in self.fixtures],
            'groups': {
                name: {
                    'name': group.name,
                    'color': group.color,
                    'fixtures': [asdict(f) for f in group.fixtures]
                }
                for name, group in self.groups.items()
            },
            'universes': {
                str(universe.id): {
                    'name': universe.name,
                    'output': universe.output
                }
                for universe in self.universes.values()
            },
            'shows': {
                show.name: {
                    'parts': [{k: v for k, v in asdict(part).items() if k not in ('start_time', 'duration')} for part in show.parts],
                    'effects': [asdict(effect) for effect in show.effects],
                    'timeline_data': show.timeline_data.to_dict() if show.timeline_data else None
                }
                for show in self.shows.values()
            },
            'spots': {
                name: asdict(spot)
                for name, spot in self.spots.items()
            },
            'workspace_path': self.workspace_path
        }

        with open(filename, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

    @classmethod
    def load(cls, filename: str) -> 'Configuration':
        """Load configuration from YAML file"""
        with open(filename, 'r') as f:
            data = yaml.safe_load(f)

        # Convert dictionary back to Configuration object
        fixtures = []
        for f_data in data.get('fixtures', []):
            if 'available_modes' in f_data:
                modes = []
                for mode_data in f_data['available_modes']:
                    mode = FixtureMode(
                        name=mode_data['name'],
                        channels=mode_data['channels']
                    )
                    modes.append(mode)
                f_data['available_modes'] = modes
            fixtures.append(Fixture(**f_data))

        # Handle groups with colors
        groups = {}
        for name, group_data in data.get('groups', {}).items():
            group_fixtures = []
            for f_data in group_data.get('fixtures', []):
                if 'available_modes' in f_data:
                    modes = []
                    for mode_data in f_data['available_modes']:
                        mode = FixtureMode(
                            name=mode_data['name'],
                            channels=mode_data['channels']
                        )
                        modes.append(mode)
                    f_data['available_modes'] = modes
                group_fixtures.append(Fixture(**f_data))

            groups[name] = FixtureGroup(
                name=name,
                fixtures=group_fixtures,
                color=group_data.get('color', '#808080')  # Add default color if none specified
            )

        # Handle shows
        shows = {}
        if 'shows' in data:
            for show_name, show_data in data['shows'].items():
                # Convert show parts
                parts = []
                for part_data in show_data.get('parts', []):
                    parts.append(ShowPart(
                        name=part_data['name'],
                        color=part_data['color'],
                        signature=part_data['signature'],
                        bpm=part_data['bpm'],
                        num_bars=part_data['num_bars'],
                        transition=part_data['transition']
                    ))

                # Convert show effects
                effects = []
                for effect_data in show_data.get('effects', []):
                    effects.append(ShowEffect(
                        show_part=effect_data['show_part'],
                        fixture_group=effect_data['fixture_group'],
                        effect=effect_data['effect'],
                        speed=effect_data['speed'],
                        color=effect_data['color'],
                        intensity=effect_data['intensity'],
                        spot=effect_data['spot']
                    ))

                # Load timeline data if present
                timeline_data = None
                if show_data.get('timeline_data'):
                    timeline_data = TimelineData.from_dict(show_data['timeline_data'])

                # Create show
                shows[show_name] = Show(
                    name=show_name,
                    parts=parts,
                    effects=effects,
                    timeline_data=timeline_data
                )

        # Handle universes
        universes = {}
        if 'universes' in data:
            for universe_id_str, universe_data in data['universes'].items():
                universe_id = int(universe_id_str)
                universes[universe_id] = Universe(
                    id=universe_id,
                    output=universe_data.get('output', {
                        'plugin': 'E1.31',
                        'line': '0',
                        'parameters': {
                            'ip': f'192.168.1.{universe_id}',
                            'port': '6454',
                            'subnet': '0',
                            'universe': str(universe_id)
                        }
                    }),
                    name=universe_data.get('name', f"Universe {universe_id}")
                )

        # Handle spots
        spots = {}
        if 'spots' in data:
            for spot_name, spot_data in data['spots'].items():
                spots[spot_name] = Spot(**spot_data)

        config = cls(
            fixtures=fixtures,
            groups=groups,
            universes=universes,
            shows=shows,
            spots=spots,
            workspace_path=data.get('workspace_path')
        )

        return config

    @staticmethod
    def _scan_fixture_definitions():
        """Scan QLC+ fixture definitions"""
        # Get QLC+ fixture directories
        qlc_fixture_dirs = []
        if sys.platform.startswith('linux'):
            qlc_fixture_dirs.extend([
                '/usr/share/qlcplus/fixtures',
                os.path.expanduser('~/.qlcplus/fixtures')
            ])
        elif sys.platform == 'win32':
            qlc_fixture_dirs.extend([
                os.path.join(os.path.expanduser('~'), 'QLC+', 'fixtures'),  # User fixtures
                'C:\\QLC+\\Fixtures'  # System-wide fixtures
            ])
        elif sys.platform == 'darwin':
            qlc_fixture_dirs.append(os.path.expanduser('~/Library/Application Support/QLC+/fixtures'))

        # Scan all fixture definitions first
        fixture_definitions = {}
        for dir_path in qlc_fixture_dirs:
            if os.path.exists(dir_path):
                for manufacturer_dir in os.listdir(dir_path):
                    manufacturer_path = os.path.join(dir_path, manufacturer_dir)
                    if os.path.isdir(manufacturer_path):
                        for fixture_file in os.listdir(manufacturer_path):
                            if fixture_file.endswith('.qxf'):
                                fixture_path = os.path.join(manufacturer_path, fixture_file)
                                try:
                                    tree = ET.parse(fixture_path)
                                    root = tree.getroot()
                                    ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

                                    manufacturer = root.find('.//Manufacturer', ns).text
                                    model = root.find('.//Model', ns).text

                                    # Determine fixture type once for all modes
                                    fixture_type = determine_fixture_type(root)

                                    # Get all available modes
                                    modes = []
                                    for mode in root.findall('.//Mode', ns):
                                        mode_name = mode.get('Name')
                                        channels = mode.findall('Channel', ns)
                                        modes.append({
                                            'name': mode_name,
                                            'channels': len(channels),
                                            'type': fixture_type  # Same type for all modes
                                        })

                                    fixture_definitions[(manufacturer, model)] = {
                                        'path': fixture_path,
                                        'modes': modes,
                                        'type': fixture_type  # Store type at fixture level
                                    }
                                except Exception as e:
                                    print(f"Error parsing fixture file {fixture_path}: {e}")
                    elif manufacturer_path.endswith('.qxf'):
                        try:
                            tree = ET.parse(manufacturer_path)
                            root = tree.getroot()
                            ns = {'': 'http://www.qlcplus.org/FixtureDefinition'}

                            manufacturer = root.find('.//Manufacturer', ns).text
                            model = root.find('.//Model', ns).text

                            # Determine fixture type once for all modes
                            fixture_type = determine_fixture_type(root)

                            # Get all available modes
                            modes = []
                            for mode in root.findall('.//Mode', ns):
                                mode_name = mode.get('Name')
                                channels = mode.findall('Channel', ns)
                                modes.append({
                                    'name': mode_name,
                                    'channels': len(channels),
                                    'type': fixture_type  # Same type for all modes
                                })

                            fixture_definitions[(manufacturer, model)] = {
                                'path': manufacturer_path,
                                'modes': modes,
                                'type': fixture_type  # Store type at fixture level
                            }
                        except Exception as e:
                            print(f"Error parsing fixture file {manufacturer_path}: {e}")
        return fixture_definitions

    @staticmethod
    def _parse_workspace(workspace_path: str, fixture_definitions: dict) -> List[Dict]:
        """
        Parse QLC+ workspace file and extract fixture data

        Args:
            workspace_path: Path to QLC+ workspace file
            fixture_definitions: Dictionary of fixture definitions

        Returns:
            List of fixture data dictionaries
        """
        try:
            tree = ET.parse(workspace_path)
            root = tree.getroot()
            ns = {'qlc': 'http://www.qlcplus.org/Workspace'}

            # Extract fixtures with their groups
            fixtures_data = []
            existing_groups = set()

            # First pass - collect all groups
            for group in root.findall(".//qlc:Engine/qlc:ChannelsGroup", ns):
                existing_groups.add(group.get('Name'))

            # Second pass - process fixtures
            for fixture in root.findall(".//qlc:Engine/qlc:Fixture", ns):
                fixture_id = fixture.find("qlc:ID", ns).text
                manufacturer = fixture.find("qlc:Manufacturer", ns).text
                model = fixture.find("qlc:Model", ns).text
                current_mode = fixture.find("qlc:Mode", ns).text

                # Get channel count from workspace (this is the actual count for the current mode)
                channels_elem = fixture.find("qlc:Channels", ns)
                workspace_channels = int(channels_elem.text) if channels_elem is not None else 6

                # Find group for this fixture
                group_name = ""
                for group in root.findall(".//qlc:Engine/qlc:ChannelsGroup", ns):
                    channel_pairs = group.text.split(',')
                    fixture_ids = set(channel_pairs[::2])  # Take every other item (fixture IDs)

                    if fixture_id in fixture_ids:
                        group_name = group.get('Name')
                        break

                # Get fixture definition if available
                fixture_def = fixture_definitions.get((manufacturer, model))

                # Use fixture definition modes if available, otherwise create from workspace data
                if fixture_def and fixture_def['modes']:
                    available_modes = fixture_def['modes']
                else:
                    # Fallback: create a single mode from workspace data
                    available_modes = [{
                        'name': current_mode,
                        'channels': workspace_channels,
                        'type': 'PAR'  # Default type
                    }]

                fixtures_data.append({
                    'Universe': int(fixture.find("qlc:Universe", ns).text) + 1,
                    'Address': int(fixture.find("qlc:Address", ns).text) + 1,
                    'Manufacturer': manufacturer,
                    'Model': model,
                    'Name': fixture.find("qlc:Name", ns).text,
                    'Group': group_name,
                    'Direction': "",
                    'CurrentMode': current_mode,
                    'AvailableModes': available_modes,
                    'WorkspaceChannels': workspace_channels  # Store for validation
                })

            return fixtures_data

        except ET.ParseError as e:
            raise ValueError(f"Invalid workspace file format: {e}")
        except Exception as e:
            raise RuntimeError(f"Error parsing workspace file: {e}")

    def initialize_default_universes(self):
        """Initialize default universes with placeholder values"""
        for i in range(1, 5):  # Create 4 universes
            self.universes[i] = Universe(
                id=i,
                name=f"Universe {i}",
                output={
                    'plugin': 'E1.31',
                    'line': '0',
                    'parameters': {
                        'ip': f'192.168.1.{i}',
                        'port': '6454',
                        'subnet': '0',
                        'universe': str(i)
                    }
                }
            )

    def add_universe(self, universe_id: int, output_type: str, ip: str, port: str, subnet: str, universe: str):
        """Add or update a universe configuration"""
        self.universes[universe_id] = Universe(
            id=universe_id,
            name=f"Universe {universe_id}",
            output={
                'plugin': output_type,
                'line': '0',
                'parameters': {
                    'ip': ip,
                    'port': port,
                    'subnet': subnet,
                    'universe': universe
                }
            }
        )

    def remove_universe(self, universe_id: int):
        """Remove a universe configuration"""
        if universe_id in self.universes:
            del self.universes[universe_id]

