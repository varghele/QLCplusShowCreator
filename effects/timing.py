def parse_speed(speed: str) -> float:
    """Parse speed string to multiplier.

    Args:
        speed: Speed string like "1", "2", "1/2", "1/4"

    Returns:
        Speed multiplier as float
    """
    if '/' in speed:
        parts = speed.split('/')
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            return 1.0
    else:
        try:
            return float(speed)
        except ValueError:
            return 1.0


def get_bpm(song_structure, current_time: float) -> float:
    """Get BPM from song structure, defaulting to 120.

    Args:
        song_structure: SongStructure instance or None
        current_time: Current playback time in seconds

    Returns:
        BPM as float
    """
    if song_structure:
        return song_structure.get_bpm_at_time(current_time)
    return 120.0
