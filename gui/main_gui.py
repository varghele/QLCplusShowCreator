import sys
import os
import csv
import xml.etree.ElementTree as ET
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QPushButton, QFileDialog, QTabWidget, QGridLayout,
                            QLabel, QScrollArea)
from PyQt6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lighting Control")
        self.setGeometry(100, 100, 1200, 800)

        # Get the project root directory
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.setup_dir = os.path.join(self.project_root, "setup")

        # Create tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # ---- Fixtures Tab ----
        self.fixtures_tab = QWidget()
        fixtures_layout = QVBoxLayout()

        # Add import workspace button
        import_workspace_button = QPushButton("Import QLC+ Workspace")
        import_workspace_button.clicked.connect(self.import_workspace)
        fixtures_layout.addWidget(import_workspace_button)

        # Add Fixtures section
        fixtures_label = QLabel("Fixtures:")
        fixtures_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        fixtures_layout.addWidget(fixtures_label)

        fixtures_scroll = QScrollArea()
        fixtures_scroll.setWidgetResizable(True)
        self.fixtures_widget = QWidget()
        self.fixtures_grid = QGridLayout()
        self.fixtures_widget.setLayout(self.fixtures_grid)
        fixtures_scroll.setWidget(self.fixtures_widget)
        fixtures_layout.addWidget(fixtures_scroll)

        # Add Channel Groups section
        groups_label = QLabel("Channel Groups:")
        groups_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        fixtures_layout.addWidget(groups_label)

        groups_scroll = QScrollArea()
        groups_scroll.setWidgetResizable(True)
        self.groups_widget = QWidget()
        self.groups_grid = QGridLayout()
        self.groups_widget.setLayout(self.groups_grid)
        groups_scroll.setWidget(self.groups_widget)
        fixtures_layout.addWidget(groups_scroll)

        self.fixtures_tab.setLayout(fixtures_layout)
        self.tabs.addTab(self.fixtures_tab, "Fixtures")

        # ---- Shows Tab ----
        self.shows_tab = QWidget()
        shows_layout = QVBoxLayout()

        # Add import show structure button
        import_show_button = QPushButton("Import Show Structure")
        import_show_button.clicked.connect(self.import_show_structure)
        shows_layout.addWidget(import_show_button)

        # Create scroll area for show structure
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.show_widget = QWidget()
        self.show_grid = QGridLayout()
        self.show_widget.setLayout(self.show_grid)
        scroll.setWidget(self.show_widget)
        shows_layout.addWidget(scroll)

        self.shows_tab.setLayout(shows_layout)
        self.tabs.addTab(self.shows_tab, "Shows")

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
            seen_fixtures = set()

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
                                'Mode': fixture.find("qlc:Mode", ns).text.split()[0]
                            })

            groups_path = os.path.join(self.setup_dir, "groups.csv")
            with open(groups_path, 'w', newline='') as csvfile:
                fieldnames = ['id', 'category', 'Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for group in groups_data:
                    writer.writerow(group)

            # Display fixtures in the fixtures grid
            # Clear existing grid
            for i in reversed(range(self.fixtures_grid.count())):
                widget = self.fixtures_grid.itemAt(i).widget()
                if widget:
                    widget.setParent(None)

            # Add headers
            headers = ['Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode', 'Name']
            for col, header in enumerate(headers):
                label = QLabel(header)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-weight: bold;")
                self.fixtures_grid.addWidget(label, 0, col)

            # Add fixture data
            for row, fixture in enumerate(fixtures_data, 1):
                for col, header in enumerate(headers):
                    label = QLabel(str(fixture[header]))
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.fixtures_grid.addWidget(label, row, col)

            # Display groups in the groups grid
            # Clear existing grid
            for i in reversed(range(self.groups_grid.count())):
                widget = self.groups_grid.itemAt(i).widget()
                if widget:
                    widget.setParent(None)

            # Add headers
            group_headers = ['id', 'category', 'Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode']
            for col, header in enumerate(group_headers):
                label = QLabel(header)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-weight: bold;")
                self.groups_grid.addWidget(label, 0, col)

            # Add group data
            for row, group in enumerate(groups_data, 1):
                for col, header in enumerate(group_headers):
                    # Use the header directly as the key without converting to lowercase
                    label = QLabel(str(group[header]))
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.groups_grid.addWidget(label, row, col)

            print("Workspace data displayed successfully")

        except Exception as e:
            print(f"Error processing workspace file: {e}")
            import traceback
            traceback.print_exc()

    def import_show_structure(self):
        try:
            # Read show parts from structure file
            structure_file = os.path.join(self.project_root, "shows", "show_1", "show_1_structure.csv")
            show_parts = []
            with open(structure_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    show_parts.append(row['name'])

            # Read channel groups from groups.csv
            groups_file = os.path.join(self.setup_dir, "groups.csv")
            channel_groups = set()
            with open(groups_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    channel_groups.add(row['category'])

            # Clear existing grid
            for i in reversed(range(self.show_grid.count())):
                widget = self.show_grid.itemAt(i).widget()
                if widget:
                    widget.setParent(None)

            # Create headers (show parts as columns)
            for col, part in enumerate(show_parts):
                label = QLabel(part)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-weight: bold;")
                self.show_grid.addWidget(label, 0, col)

            # Create rows for each channel group
            for row, group in enumerate(sorted(channel_groups), 1):
                # Add channel group name in first column
                group_label = QLabel(group)
                group_label.setStyleSheet("font-weight: bold;")
                self.show_grid.addWidget(group_label, row, 0)

                # Add empty cells for each show part
                for col in range(1, len(show_parts)):
                    label = QLabel("")
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.show_grid.addWidget(label, row, col)

            # Set column stretch factors
            for col in range(len(show_parts)):
                self.show_grid.setColumnStretch(col, 1)

            print("Show structure imported successfully")

        except Exception as e:
            print(f"Error importing show structure: {e}")
            import traceback
            traceback.print_exc()

    def import_workspace(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select QLC+ Workspace",
            "",
            "QLC+ Workspace Files (*.qxw)"
        )

        if file_path:
            self.extract_from_workspace(file_path)



def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
