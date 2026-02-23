#!/usr/bin/env python3
"""
Merge two QLC+ Show Creator configuration files.

Takes shows from both configs and combines them into a new file.
Fixtures, universes, groups, and stage settings are taken from the first (base) file.
Shows are merged from both files, with duplicates renamed.

Usage:
    python merge_configs.py config1.yaml config2.yaml -o merged_config.yaml
"""

import argparse
import sys
from pathlib import Path
import yaml


def load_yaml(path: Path) -> dict:
    """Load a YAML configuration file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(data: dict, path: Path):
    """Save data to a YAML file."""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def merge_shows(base_shows: dict, other_shows: dict) -> tuple[dict, list[str]]:
    """
    Merge shows from two configs.

    Args:
        base_shows: Shows from the base config (kept as-is)
        other_shows: Shows from the other config (renamed if duplicate)

    Returns:
        Tuple of (merged_shows, list of messages about what was done)
    """
    merged = dict(base_shows) if base_shows else {}
    messages = []

    if not other_shows:
        return merged, messages

    for show_name, show_data in other_shows.items():
        if show_name not in merged:
            # No conflict, add directly
            merged[show_name] = show_data
            messages.append(f"  Added show: '{show_name}' from second config")
        else:
            # Conflict - find a unique name
            counter = 2
            new_name = f"{show_name}_v{counter}"
            while new_name in merged:
                counter += 1
                new_name = f"{show_name}_v{counter}"

            # Update the show's internal name field if it exists
            if isinstance(show_data, dict) and 'name' in show_data:
                show_data = dict(show_data)  # Copy to avoid modifying original
                show_data['name'] = new_name

            merged[new_name] = show_data
            messages.append(f"  Added show: '{show_name}' as '{new_name}' (renamed due to conflict)")

    return merged, messages


def merge_configs(base_path: Path, other_path: Path, output_path: Path) -> bool:
    """
    Merge two configuration files.

    Args:
        base_path: Path to base config (fixtures, universes, etc. taken from here)
        other_path: Path to other config (shows merged from here)
        output_path: Path to write merged config

    Returns:
        True if successful, False otherwise
    """
    print(f"Loading base config: {base_path}")
    try:
        base_config = load_yaml(base_path)
    except Exception as e:
        print(f"Error loading base config: {e}")
        return False

    print(f"Loading second config: {other_path}")
    try:
        other_config = load_yaml(other_path)
    except Exception as e:
        print(f"Error loading second config: {e}")
        return False

    # Get shows from both configs
    base_shows = base_config.get('shows', {})
    other_shows = other_config.get('shows', {})

    print(f"\nShows in base config ({base_path.name}):")
    if base_shows:
        for name in base_shows.keys():
            print(f"  - {name}")
    else:
        print("  (none)")

    print(f"\nShows in second config ({other_path.name}):")
    if other_shows:
        for name in other_shows.keys():
            print(f"  - {name}")
    else:
        print("  (none)")

    # Merge shows
    print("\nMerging shows...")
    merged_shows, messages = merge_shows(base_shows, other_shows)

    for msg in messages:
        print(msg)

    if not messages:
        print("  No new shows to add from second config")

    # Create merged config (start with base, update shows)
    merged_config = dict(base_config)
    merged_config['shows'] = merged_shows

    # Save merged config
    print(f"\nSaving merged config to: {output_path}")
    try:
        save_yaml(merged_config, output_path)
    except Exception as e:
        print(f"Error saving merged config: {e}")
        return False

    print(f"\nMerge complete!")
    print(f"  Total shows in merged config: {len(merged_shows)}")
    for name in merged_shows.keys():
        print(f"    - {name}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Merge two QLC+ Show Creator configuration files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Merge two configs, output to new file
    python merge_configs.py config_old.yaml config_new.yaml -o merged.yaml

    # If no output specified, creates 'merged_config.yaml'
    python merge_configs.py config1.yaml config2.yaml

Notes:
    - Fixtures, universes, groups, stage settings are taken from the FIRST config
    - Shows are merged from BOTH configs
    - If a show name exists in both, the second one is renamed (e.g., 'MyShow' -> 'MyShow_v2')
"""
    )

    parser.add_argument('config1', type=Path, help='Base configuration file (fixtures taken from here)')
    parser.add_argument('config2', type=Path, help='Second configuration file (shows merged from here)')
    parser.add_argument('-o', '--output', type=Path, default=Path('merged_config.yaml'),
                        help='Output file path (default: merged_config.yaml)')

    args = parser.parse_args()

    # Validate input files exist
    if not args.config1.exists():
        print(f"Error: Base config file not found: {args.config1}")
        sys.exit(1)

    if not args.config2.exists():
        print(f"Error: Second config file not found: {args.config2}")
        sys.exit(1)

    # Check output doesn't overwrite input
    if args.output.resolve() == args.config1.resolve():
        print("Error: Output file cannot be the same as base config")
        sys.exit(1)
    if args.output.resolve() == args.config2.resolve():
        print("Error: Output file cannot be the same as second config")
        sys.exit(1)

    # Warn if output exists
    if args.output.exists():
        response = input(f"Output file '{args.output}' already exists. Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    # Do the merge
    success = merge_configs(args.config1, args.config2, args.output)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
