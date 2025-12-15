"""
Widget style definitions for various UI components.
"""


class WidgetStyles:
    """Centralized widget style definitions"""

    # Lane widget styles
    LANE_WIDGET = """
        QFrame {
            background-color: #3b444b;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
    """

    LANES_CONTAINER = """
        QScrollArea {
            background-color: #fafafa;
            border: 1px solid #ddd;
        }
        QScrollArea > QWidget > QWidget {
            background-color: #fafafa;
        }
    """

    # MIDI block styles
    MIDI_BLOCK_DEFAULT = """
        QFrame {
            background-color: #4CAF50;
            border: 2px solid #45a049;
            border-radius: 5px;
        }
        QFrame:hover {
            background-color: #5CBF60;
        }
    """

    MIDI_BLOCK_DRAGGING = """
        QFrame {
            background-color: #66BB6A;
            border: 2px solid #4CAF50;
            border-radius: 5px;
            opacity: 0.8;
        }
    """

    # Timeline styles
    TIMELINE_WIDGET = """
        QWidget {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
        }
    """

    # Input field styles
    LINE_EDIT = """
        QLineEdit {
            background-color: white;
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 4px;
            font-size: 12px;
        }
        QLineEdit:focus {
            border: 2px solid #2196F3;
        }
    """

    SPINBOX = """
        QSpinBox {
            background-color: white;
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 4px;
            font-size: 12px;
        }
        QSpinBox:focus {
            border: 2px solid #2196F3;
        }
    """
