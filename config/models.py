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
    bpm: int
    num_bars: int
    transition: str

@dataclass
class Show:
    name: str
    parts: List[ShowPart] = field(default_factory=list)
    effects: List[ShowEffect] = field(default_factory=list)

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

    @classmethod
    def from_workspace(cls, workspace_path: str) -> 'Configuration':
        """Create Configuration from QLC+ workspace file"""
        fixture_definitions = cls._scan_fixture_definitions()
        fixtures_data = cls._parse_workspace(workspace_path, fixture_definitions)

        config = cls(fixtures=[], groups={}, workspace_path=workspace_path)

        for fixture_data in fixtures_data:
            # Get fixture definition and current mode
            fixture_def = fixture_definitions.get(
                (fixture_data['Manufacturer'], fixture_data['Model']))

            # Create FixtureMode objects without the 'type' field
            modes = []
            if fixture_data['AvailableModes']:
                for mode in fixture_data['AvailableModes']:
                    modes.append(FixtureMode(
                        name=mode['name'],
                        channels=mode['channels']
                    ))

        for fixture_data in fixtures_data:
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
                x = fixture_data.get('X', 0.0),
                y = fixture_data.get('Y', 0.0),
                z = fixture_data.get('Z', 0.0),
                rotation = fixture_data.get('Rotation', 0.0)
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
                        # Create new Show object
                        show = Show(name=show_dir)

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

                                # Create empty effects for each group
                                for group_name in config.groups.keys():
                                    effect = ShowEffect(
                                        show_part=show_part.name,
                                        fixture_group=group_name,
                                        effect="",
                                        speed="1",
                                        color="",  # Leave color blank for effects
                                        intensity=200 # Default intensity
                                    )
                                    show.effects.append(effect)

                        # Add show to configuration
                        config.shows[show_dir] = show

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
                    'parts': [asdict(part) for part in show.parts],
                    'effects': [asdict(effect) for effect in show.effects]
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
                        intensity=effect_data['intensity']
                    ))

                # Create show
                shows[show_name] = Show(
                    name=show_name,
                    parts=parts,
                    effects=effects
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

                fixtures_data.append({
                    'Universe': int(fixture.find("qlc:Universe", ns).text) + 1,
                    'Address': int(fixture.find("qlc:Address", ns).text) + 1,
                    'Manufacturer': manufacturer,
                    'Model': model,
                    'Name': fixture.find("qlc:Name", ns).text,
                    'Group': group_name,
                    'Direction': "",
                    'CurrentMode': fixture.find("qlc:Mode", ns).text,
                    'AvailableModes': fixture_def['modes'] if fixture_def else None
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

