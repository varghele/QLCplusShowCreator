import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QFileDialog)
from PyQt6.QtCore import Qt
import xml.etree.ElementTree as ET
import csv


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lighting Control")
        self.setGeometry(100, 100, 800, 600)

        # Get the project root directory
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.setup_dir = os.path.join(self.project_root, "setup")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        import_button = QPushButton("Import QLC+ Workspace")
        import_button.clicked.connect(self.import_workspace)
        layout.addWidget(import_button)

        central_widget.setLayout(layout)

    def import_workspace(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select QLC+ Workspace",
            "",
            "QLC+ Workspace Files (*.qxw)"
        )

        if file_path:
            self.extract_from_workspace(file_path)

    def extract_from_workspace(self, workspace_path):
        try:
            # Ensure setup directory exists
            os.makedirs(self.setup_dir, exist_ok=True)

            tree = ET.parse(workspace_path)
            root = tree.getroot()

            # Define the namespace
            ns = {'qlc': 'http://www.qlcplus.org/Workspace'}

            # Extract and write fixtures
            fixtures_data = []
            for fixture in root.findall(".//qlc:Engine/qlc:Fixture", ns):
                # Add 1 to Universe and Address for 1-based indexing
                universe = int(fixture.find("qlc:Universe", ns).text) + 1
                address = int(fixture.find("qlc:Address", ns).text) + 1

                fixtures_data.append({
                    'Universe': universe,
                    'Address': address,
                    'Manufacturer': fixture.find("qlc:Manufacturer", ns).text,
                    'Model': fixture.find("qlc:Model", ns).text,
                    'Channels': fixture.find("qlc:Channels", ns).text,
                    'Mode': fixture.find("qlc:Mode", ns).text,
                    'Name': fixture.find("qlc:Name", ns).text
                })

            fixtures_path = os.path.join(self.setup_dir, "fixtures.csv")
            with open(fixtures_path, 'w', newline='') as csvfile:
                fieldnames = ['Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode', 'Name']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for fixture in fixtures_data:
                    writer.writerow(fixture)

            # Extract and write groups
            groups_data = []
            seen_fixtures = set()  # Track unique fixtures in groups

            for group in root.findall(".//qlc:Engine/qlc:ChannelsGroup", ns):
                group_id = int(group.get('ID'))
                category = group.get('Name')

                # Get unique fixture IDs from the channels
                fixture_ids = set()
                if group.text:
                    channels = group.text.split(',')
                    fixture_ids = {channels[i] for i in range(0, len(channels), 2)}

                # Process each unique fixture
                for fixture_id in fixture_ids:
                    fixture = root.find(f".//qlc:Engine/qlc:Fixture[qlc:ID='{fixture_id}']", ns)
                    if fixture is not None:
                        # Create unique key for fixture
                        universe = int(fixture.find("qlc:Universe", ns).text) + 1
                        address = int(fixture.find("qlc:Address", ns).text) + 1
                        unique_key = (group_id, universe, address)

                        if unique_key not in seen_fixtures:
                            seen_fixtures.add(unique_key)
                            groups_data.append({
                                'id': group_id,
                                'category': category,
                                'Universe': universe,
                                'Address': address,
                                'Manufacturer': fixture.find("qlc:Manufacturer", ns).text,
                                'Model': fixture.find("qlc:Model", ns).text,
                                'Channels': fixture.find("qlc:Channels", ns).text,
                                'Mode': fixture.find("qlc:Mode", ns).text.split()[0]  # Only take the number
                            })

            groups_path = os.path.join(self.setup_dir, "groups.csv")
            with open(groups_path, 'w', newline='') as csvfile:
                fieldnames = ['id', 'category', 'Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for group in groups_data:
                    writer.writerow(group)

            print(f"Fixtures and groups data written to {self.setup_dir}")

        except Exception as e:
            print(f"Error processing workspace file: {e}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
