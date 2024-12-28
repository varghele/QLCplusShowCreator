import os
import json
import xml.etree.ElementTree as ET
import pandas as pd


def create_tracks(function, base_dir="../"):
    """
    Creates Track elements for a show function
    Parameters:
        function: The Function XML element (show) to add tracks to
    """
    # Get groups from groups.csv
    groups_file = os.path.join(base_dir, 'setup', 'groups.csv')

    if not os.path.exists(groups_file):
        print("Groups file not found in setup directory")
        return

        # Read groups data and get unique categories
    groups_df = pd.read_csv(groups_file)
    categories = groups_df['category'].unique()

    # Create a track for each valid category
    track_id = 0
    for category in categories:
        if pd.isna(category) or category == 'None':
            continue

        track = ET.SubElement(function, "Track")
        track.set("ID", str(track_id))
        track.set("Name", str(category).upper())  # Convert category name to uppercase
        track.set("isMute", "0")
        track_id += 1


def create_shows(root, shows_dir='../shows', base_dir='../'):
    """
    Creates show function elements from show files in the shows folder
    Parameters:
        root: The root XML element to add the show functions to
    """
    show_id = 0  # Initialize show ID counter

    # Get all show folders
    for show_name in os.listdir(shows_dir):
        show_path = os.path.join(shows_dir, show_name)

        if os.path.isdir(show_path):
            # Check if all required files exist
            required_files = [
                f"{show_name}_events",
                f"{show_name}_setup.json",
                f"{show_name}_structure"
            ]

            if all(os.path.exists(os.path.join(show_path, f)) for f in required_files):
                # Create Function element for the show
                function = ET.SubElement(root, "Function")
                function.set("ID", str(show_id))
                function.set("Type", "Show")
                function.set("Name", show_name)

                # Read show setup file for configuration
                setup_file = os.path.join(show_path, f"{show_name}_setup.json")
                try:
                    with open(setup_file, 'r') as f:
                        setup_data = json.load(f)

                    # Create TimeDivision element with data from setup
                    time_division = ET.SubElement(function, "TimeDivision")
                    time_division.set("Type", setup_data.get("TimeType", "Time"))
                    time_division.set("BPM", str(setup_data.get("BPM", 120)))

                    # Create tracks for this show
                    create_tracks(function, base_dir)

                except json.JSONDecodeError:
                    print(f"Error reading setup file for show: {show_name}")
                except Exception as e:
                    print(f"Error processing show {show_name}: {str(e)}")

                show_id += 1  # Increment show ID counter

