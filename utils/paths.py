"""PyInstaller-aware path utilities."""

import os
import sys


def get_project_root():
    """Return the project root directory.

    When running as a PyInstaller bundle, returns sys._MEIPASS (the temp
    directory where bundled data files are extracted).
    Otherwise, returns the real project root (parent of this file's package).
    """
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
