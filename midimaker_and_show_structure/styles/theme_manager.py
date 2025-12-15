"""
Theme management system for the MIDI Track Creator application.
Provides centralized access to all styles and theme switching capabilities.
"""

from .button_styles import ButtonStyles
from .widget_styles import WidgetStyles


class ThemeManager:
    """Manages application themes and provides style access"""

    def __init__(self):
        self.current_theme = "default"
        self.button_styles = ButtonStyles()
        self.widget_styles = WidgetStyles()

    # Button style getters
    def get_mute_button_style(self, active: bool) -> str:
        """Get mute button style based on state"""
        return (self.button_styles.MUTE_BUTTON_ACTIVE if active
                else self.button_styles.MUTE_BUTTON_INACTIVE)

    def get_solo_button_style(self, active: bool) -> str:
        """Get solo button style based on state"""
        return (self.button_styles.SOLO_BUTTON_ACTIVE if active
                else self.button_styles.SOLO_BUTTON_INACTIVE)

    def get_mute_button_compact_style(self, active: bool) -> str:
        """Get compact mute button style based on state"""
        return (self.button_styles.MUTE_BUTTON_COMPACT_ACTIVE if active
                else self.button_styles.MUTE_BUTTON_COMPACT_INACTIVE)

    def get_solo_button_compact_style(self, active: bool) -> str:
        """Get compact solo button style based on state"""
        return (self.button_styles.SOLO_BUTTON_COMPACT_ACTIVE if active
                else self.button_styles.SOLO_BUTTON_COMPACT_INACTIVE)

    def get_action_button_style(self) -> str:
        """Get action button style"""
        return self.button_styles.ACTION_BUTTON

    def get_remove_button_style(self) -> str:
        """Get remove button style"""
        return self.button_styles.REMOVE_BUTTON

    def get_transport_button_style(self, button_type: str = "play") -> str:
        """Get transport button style based on type"""
        if button_type == "stop":
            return self.button_styles.TRANSPORT_BUTTON_STOP
        elif button_type == "halt":
            return self.button_styles.TRANSPORT_BUTTON_HALT
        elif button_type == "play":
            return self.button_styles.TRANSPORT_BUTTON_PLAY
        else:
            self.button_styles.TRANSPORT_BUTTON

    # Widget style getters
    def get_lane_widget_style(self) -> str:
        """Get lane widget style"""
        return self.widget_styles.LANE_WIDGET

    def get_lanes_container_style(self) -> str:
        """Get lanes container style"""
        return self.widget_styles.LANES_CONTAINER

    def get_midi_block_style(self, dragging: bool = False) -> str:
        """Get MIDI block style based on state"""
        return (self.widget_styles.MIDI_BLOCK_DRAGGING if dragging
                else self.widget_styles.MIDI_BLOCK_DEFAULT)

    def get_timeline_style(self) -> str:
        """Get timeline widget style"""
        return self.widget_styles.TIMELINE_WIDGET

    def get_line_edit_style(self) -> str:
        """Get line edit style"""
        return self.widget_styles.LINE_EDIT

    def get_spinbox_style(self) -> str:
        """Get spinbox style"""
        return self.widget_styles.SPINBOX

    # Theme switching (for future use)
    def set_theme(self, theme_name: str):
        """Switch to a different theme"""
        self.current_theme = theme_name
        # Future: Load different style sets based on theme

    def get_current_theme(self) -> str:
        """Get current theme name"""
        return self.current_theme


# Global theme manager instance
theme_manager = ThemeManager()
