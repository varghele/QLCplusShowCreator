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

    # Read fixtures data
    fixtures_df = pd.read_csv(fixtures_file)

    # Check if groups file exists
    if os.path.exists(groups_file):
        try:
            groups_df = pd.read_csv(groups_file)

            # Create dictionary of existing Universe/Address combinations and their categories
            existing_categories = {
                (row['Universe'], row['Address']): row['category']
                for _, row in groups_df.iterrows()
            }

            # Check for missing fixtures
            existing_fixtures = set(zip(groups_df['Universe'], groups_df['Address']))
            all_fixtures = set(zip(fixtures_df['Universe'], fixtures_df['Address']))
            missing_fixtures = all_fixtures - existing_fixtures

            if missing_fixtures:
                # Create new rows for missing fixtures
                new_rows = []
                for universe, address in missing_fixtures:
                    fixture_data = fixtures_df[
                        (fixtures_df['Universe'] == universe) &
                        (fixtures_df['Address'] == address)
                        ].iloc[0]

                    # Use existing category if fixture was previously categorized
                    category = existing_categories.get((universe, address), 'None')

                    new_row = {
                        'id': len(groups_df) + len(new_rows),
                        'category': category,
                        'Universe': universe,
                        'Address': address,
                        'Manufacturer': fixture_data['Manufacturer'],
                        'Model': fixture_data['Model'],
                        'Channels': fixture_data['Channels'],
                        'Mode': fixture_data['Mode']
                    }
                    new_rows.append(new_row)

                # Append new rows to existing groups
                groups_df = pd.concat([groups_df, pd.DataFrame(new_rows)], ignore_index=True)
                groups_df.to_csv(groups_file, index=False)
                print(f"Updated groups file with {len(new_rows)} new fixtures")
            else:
                print("All fixtures are already in groups file")

        except pd.errors.EmptyDataError:
            # Handle empty file case
            create_new_groups_file(fixtures_df, groups_file, setup_dir)
    else:
        # Create new file case
        create_new_groups_file(fixtures_df, groups_file, setup_dir)


def create_new_groups_file(fixtures_df, groups_file, setup_dir):
    """Helper function to create new groups file"""
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
    print(f"Created new groups file in setup directory")

if __name__ == "__main__":
    # If script is run directly, create groups
    make_channel_groups_from_fixtures()
