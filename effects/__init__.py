"""
Effects package for light show sequences.
This package contains different effect modules organized by fixture type.
"""
# List available effect modules
available_effects = ['bars', 'dimmers', 'monocolor', 'moving_heads', 'multicolor']

# You could also define some common constants or utility functions used across effects
DEFAULT_FADE_IN = 0
DEFAULT_FADE_OUT = 0
DEFAULT_HOLD = 0

def get_available_effects():
    """Returns list of available effect modules"""
    return available_effects