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
            os.makedirs("setup", exist_ok=True)

            tree = ET.parse(workspace_path)
            root = tree.getroot()

            # Extract and write fixtures
            fixtures_data = []
            for fixture in root.findall(".//Fixture"):
                fixtures_data.append({
                    'Universe': fixture.find("Universe").text,
                    'Address': fixture.find("Address").text,
                    'Manufacturer': fixture.find("Manufacturer").text,
                    'Model': fixture.find("Model").text,
                    'Channels': fixture.find("Channels").text,
                    'Mode': fixture.find("Mode").text,
                    'Name': fixture.find("Name").text
                })

            with open("setup/fixtures.csv", 'w', newline='') as csvfile:
                fieldnames = ['Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode', 'Name']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for fixture in fixtures_data:
                    writer.writerow(fixture)

            # Extract and write groups
            groups_data = []
            group_id = 0
            for group in root.findall(".//FixtureGroup"):
                category = group.find("Name").text
                for fixture in group.findall(".//Fixture"):
                    fixture_id = fixture.text
                    # Find corresponding fixture data
                    for fix in root.findall(f".//Fixture[@ID='{fixture_id}']"):
                        groups_data.append({
                            'id': group_id,
                            'category': category,
                            'Universe': fix.find("Universe").text,
                            'Address': fix.find("Address").text,
                            'Manufacturer': fix.find("Manufacturer").text,
                            'Model': fix.find("Model").text,
                            'Channels': fix.find("Channels").text,
                            'Mode': fix.find("Mode").text.split()[0]  # Only take the number
                        })
                group_id += 1

            with open("setup/groups.csv", 'w', newline='') as csvfile:
                fieldnames = ['id', 'category', 'Universe', 'Address', 'Manufacturer', 'Model', 'Channels', 'Mode']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for group in groups_data:
                    writer.writerow(group)

            print("Fixtures and groups data written to setup directory")

        except Exception as e:
            print(f"Error processing workspace file: {e}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
