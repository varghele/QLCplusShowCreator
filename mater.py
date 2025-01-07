from utils.effects_utils import list_effects_in_directory
import sys
import os
import json
from PyQt6 import QtWidgets
from gui import MainWindow

def main():
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.abspath(__file__))
        effects_dir = os.path.join(project_root, "effects")

        # Create effects directory if it doesn't exist
        os.makedirs(effects_dir, exist_ok=True)

        # Create or update effects dictionary
        print("Checking for new effects")
        effects_dict = list_effects_in_directory(effects_dir)

        # Save effects dictionary
        effects_json_path = os.path.join(effects_dir, "effects.json")
        with open(effects_json_path, 'w') as f:
            json.dump(effects_dict, f, indent=2)

        # Start the application
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())

    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
