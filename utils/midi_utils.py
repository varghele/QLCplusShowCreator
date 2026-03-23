# utils/midi_utils.py
# MIDI input profile discovery for QLC+ trigger assignment

import os
import sys
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional


def get_midi_profile_directories() -> List[str]:
    """Get platform-specific QLC+ InputProfiles directories."""
    dirs = []

    if sys.platform == 'win32':
        # User profiles
        user_dir = os.path.join(os.path.expanduser('~'), 'QLC+', 'InputProfiles')
        dirs.append(user_dir)
        # System installs
        dirs.append(r'C:\QLC+\InputProfiles')
        dirs.append(r'C:\QLC+5\InputProfiles')
    elif sys.platform == 'darwin':
        dirs.append(os.path.expanduser('~/Library/Application Support/QLC+/InputProfiles'))
        dirs.append('/Applications/QLC+.app/Contents/Resources/InputProfiles')
    else:
        # Linux
        dirs.append(os.path.expanduser('~/.qlcplus/InputProfiles'))
        dirs.append('/usr/share/qlcplus/InputProfiles')

    return [d for d in dirs if os.path.isdir(d)]


def discover_midi_profiles() -> List[Dict[str, str]]:
    """Discover available MIDI input profiles from QLC+ installation.

    Returns:
        List of dicts with keys: 'name' (display name), 'manufacturer', 'model',
        'type', 'file_path'
    """
    profiles = []
    seen_names = set()

    for profile_dir in get_midi_profile_directories():
        for filename in os.listdir(profile_dir):
            if not filename.endswith('.qxi'):
                continue

            file_path = os.path.join(profile_dir, filename)
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()

                # Strip namespace
                ns = ''
                if root.tag.startswith('{'):
                    ns = root.tag.split('}')[0] + '}'

                manufacturer = root.findtext(f'{ns}Manufacturer', '')
                model = root.findtext(f'{ns}Model', '')
                profile_type = root.findtext(f'{ns}Type', '')

                if not manufacturer or not model:
                    continue

                name = f"{manufacturer} {model}"
                if name in seen_names:
                    continue
                seen_names.add(name)

                profiles.append({
                    'name': name,
                    'manufacturer': manufacturer,
                    'model': model,
                    'type': profile_type,
                    'file_path': file_path,
                })
            except (ET.ParseError, OSError):
                continue

    # Sort by name
    profiles.sort(key=lambda p: p['name'])
    return profiles
