"""
Button style definitions for the MIDI Track Creator application.
All button styles are centralized here for easy maintenance and theming.
"""


class ButtonStyles:
    """Centralized button style definitions"""

    # Base button styles
    BASE_BUTTON = """
        QPushButton {
            background-color: #f0f0f0;
            color: #000000;
            border: 1px solid #adadad;
            border-radius: 0px;
            padding: 5px 10px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #e5f1fb;
            border: 1px solid #0078d7;
        }
        QPushButton:pressed {
            background-color: #cce4f7;
            border: 1px solid #005499;
        }
    """

    # Mute button styles
    MUTE_BUTTON_ACTIVE = """
        QPushButton {
            background-color: #e81123;
            color: white;
            border: 1px solid #c50f1f;
            border-radius: 0px;
            padding: 5px 10px;
            font-weight: bold;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #c50f1f;
        }
        QPushButton:pressed {
            background-color: #a80d1a;
        }
    """

    MUTE_BUTTON_INACTIVE = BASE_BUTTON

    # Solo button styles
    SOLO_BUTTON_ACTIVE = """
        QPushButton {
            background-color: #ffd343;
            color: #000000;
            border: 1px solid #e0b82e;
            border-radius: 0px;
            padding: 5px 10px;
            font-weight: bold;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #ffda5a;
        }
        QPushButton:pressed {
            background-color: #e0b82e;
        }
    """

    SOLO_BUTTON_INACTIVE = BASE_BUTTON

    # Action button styles (Add Block, Load Audio, etc.)
    ACTION_BUTTON = """
        QPushButton {
            background-color: #0078d7;
            color: white;
            border: 1px solid #005499;
            border-radius: 0px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: normal;
        }
        QPushButton:hover {
            background-color: #005a9e;
        }
        QPushButton:pressed {
            background-color: #004275;
        }
    """

    # Remove button styles
    REMOVE_BUTTON = """
        QPushButton {
            background-color: #e81123;
            color: white;
            border: 1px solid #c50f1f;
            border-radius: 0px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #c50f1f;
        }
        QPushButton:pressed {
            background-color: #a80d1a;
        }
    """

    # Transport button styles
    TRANSPORT_BUTTON = """
            QPushButton {
                background-color: #f0f0f0;
                color: #000000;
                border: 1px solid #adadad;
                border-radius: 2px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #e5f1fb;
                border: 1px solid #0078d7;
            }
            QPushButton:pressed {
                background-color: #cce4f7;
                border: 1px solid #005499;
            }
        """

    TRANSPORT_BUTTON_PLAY = """
        QPushButton {
            background-color: #107c10;
            color: white;
            border: 1px solid #0e6b0e;
            border-radius: 2px;
            padding: 8px;
            font-size: 18px;
            font-weight: normal;
            min-width: 50px;
            min-height: 32px;
        }
        QPushButton:hover {
            background-color: #0e6b0e;
            border: 1px solid #0c5a0c;
        }
        QPushButton:pressed {
            background-color: #0c5a0c;
            border: 1px solid #094809;
        }
    """

    TRANSPORT_BUTTON_STOP = """
        QPushButton {
            background-color: #e81123;
            color: white;
            border: 1px solid #c50f1f;
            border-radius: 2px;
            padding: 8px;
            font-size: 18px;
            font-weight: normal;
            min-width: 50px;
            min-height: 32px;
        }
        QPushButton:hover {
            background-color: #c50f1f;
            border: 1px solid #a80d1a;
        }
        QPushButton:pressed {
            background-color: #a80d1a;
            border: 1px solid #8b0a15;
        }
    """

    TRANSPORT_BUTTON_HALT = """
        QPushButton {
            background-color: #5d5d5d;
            color: white;
            border: 1px solid #4a4a4a;
            border-radius: 2px;
            padding: 8px;
            font-size: 18px;
            font-weight: normal;
            min-width: 50px;
            min-height: 32px;
        }
        QPushButton:hover {
            background-color: #6d6d6d;
            border: 1px solid #5d5d5d;
        }
        QPushButton:pressed {
            background-color: #4a4a4a;
            border: 1px solid #373737;
        }
    """

    # Compact Mute button styles (for smaller buttons)
    MUTE_BUTTON_COMPACT_ACTIVE = """
        QPushButton {
            background-color: #e81123;
            color: white;
            border: 1px solid #c50f1f;
            border-radius: 0px;
            padding: 3px;
            font-weight: bold;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #c50f1f;
        }
        QPushButton:pressed {
            background-color: #a80d1a;
        }
    """

    MUTE_BUTTON_COMPACT_INACTIVE = """
        QPushButton {
            background-color: #f0f0f0;
            color: #000000;
            border: 1px solid #adadad;
            border-radius: 0px;
            padding: 3px;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #e5f1fb;
            border: 1px solid #0078d7;
        }
        QPushButton:pressed {
            background-color: #cce4f7;
            border: 1px solid #005499;
        }
    """

    # Compact Solo button styles
    SOLO_BUTTON_COMPACT_ACTIVE = """
        QPushButton {
            background-color: #ffd343;
            color: #000000;
            border: 1px solid #e0b82e;
            border-radius: 0px;
            padding: 3px;
            font-weight: bold;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #ffda5a;
        }
        QPushButton:pressed {
            background-color: #e0b82e;
        }
    """

    SOLO_BUTTON_COMPACT_INACTIVE = MUTE_BUTTON_COMPACT_INACTIVE
