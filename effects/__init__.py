"""
Effects package for light show sequences.
This package contains different effect modules organized by fixture type.
"""

#from . import bars  # Import the blinders module
#from . import dimmers
#from . import monocolor


# List available effect modules
available_effects = ['bars', 'dimmers', 'monocolor', 'moving_heads', 'multicolor']

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