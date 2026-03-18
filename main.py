import sys

# Increase recursion limit for loading large YAML configuration files
# PyYAML uses recursive descent parsing which can exceed Python's default limit (1000)
# for deeply nested structures like timeline data with many light blocks
sys.setrecursionlimit(10000)

import os
from PyQt6 import QtWidgets
from PyQt6.QtGui import QIcon
from gui import MainWindow

# Performance profiling - enable with --profile flag
PROFILING_ENABLED = '--profile' in sys.argv
if PROFILING_ENABLED:
    import profile_playback
    profile_playback.install_all_patches()
    profile_playback.enable_profiling()
    print("\n*** PROFILING ENABLED - Press Ctrl+P in console to print report ***\n")

def main():
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.abspath(__file__))

        # Start the application
        app = QtWidgets.QApplication(sys.argv)

        # Set application icon
        icon_path = os.path.join(project_root, "resources", "lightbulb.png")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            app.setWindowIcon(app_icon)

        window = MainWindow()
        window.show()

        # If profiling, set up periodic report printing
        if PROFILING_ENABLED:
            from PyQt6.QtCore import QTimer
            def print_profile_report():
                profile_playback.print_timings(min_total_ms=10.0)
                profile_playback.reset_timings()

            # Print report every 15 seconds
            profile_timer = QTimer()
            profile_timer.timeout.connect(print_profile_report)
            profile_timer.start(15000)
            print("Profiling report will print every 15 seconds during playback")

        sys.exit(app.exec())

    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
