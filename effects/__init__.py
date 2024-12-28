"""
Effects package for light show sequences.
This package contains different effect modules organized by fixture type.
"""

from . import blinders  # Import the blinders module

# List available effect modules
available_effects = ['blinders']

# You could also define some common constants or utility functions used across effects
DEFAULT_FADE_IN = 0
DEFAULT_FADE_OUT = 0
DEFAULT_HOLD = 0

def get_available_effects():
    """Returns list of available effect modules"""
    return available_effects

# As you add more effect modules (like spots.py, bars.py),
# add them to both the imports and available_effects list:
# from . import spots
# from . import bars
# available_effects = ['blinders', 'spots', 'bars']