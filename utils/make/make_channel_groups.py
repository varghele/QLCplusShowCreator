import os
import pandas as pd
import sys

# Add parent directory to path to allow imports from other project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def make_channel_groups_from_fixtures():
    """
    Creates or updates groups.csv file from fixtures.csv data in setup directory
    """
    # Adjust paths for project structure
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    setup_dir = os.path.join(base_dir, 'setup')
    groups_file = os.path.join(setup_dir, 'groups.csv')
    fixtures_file = os.path.join(setup_dir, 'fixtures.csv')

    # Check if groups file exists and is empty
    file_exists = os.path.exists(groups_file)
    is_empty = True
    if file_exists:
        try:
            df = pd.read_csv(groups_file)
            is_empty = df.empty
        except pd.errors.EmptyDataError:
            is_empty = True

    # Only proceed if file doesn't exist or is empty
    if not file_exists or is_empty:
        # Read fixtures data
        fixtures_df = pd.read_csv(fixtures_file)

        # Create new dataframe with required columns
        groups_data = {
            'id': range(len(fixtures_df)),
            'category': 'None',  # Default category for fixtures
            'Universe': fixtures_df['Universe'],
            'Address': fixtures_df['Address'],
            'Manufacturer': fixtures_df['Manufacturer'],
            'Model': fixtures_df['Model'],
            'Channels': fixtures_df['Channels'],
            'Mode': fixtures_df['Mode']
        }

        groups_df = pd.DataFrame(groups_data)

        # Create setup directory if it doesn't exist
        os.makedirs(setup_dir, exist_ok=True)

        # Save to CSV
        groups_df.to_csv(groups_file, index=False)
        print(f"Created groups file in setup directory")
    else:
        print(f"Groups file already exists and is not empty")

if __name__ == "__main__":
    # If script is run directly, create groups
    make_channel_groups_from_fixtures()
