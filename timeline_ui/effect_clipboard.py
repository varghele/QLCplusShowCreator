# timeline_ui/effect_clipboard.py
# Clipboard storage for copied light effects

from typing import Optional, Dict

# Module-level clipboard storage
_clipboard_data: Optional[Dict] = None


def copy_effect(light_block) -> None:
    """Copy a LightBlock to the clipboard.

    Creates a deep copy of the block data (as dictionary) so modifications
    to the original don't affect the clipboard.

    Args:
        light_block: LightBlock instance to copy
    """
    global _clipboard_data
    _clipboard_data = light_block.to_dict()


def has_clipboard_data() -> bool:
    """Check if there's data in the clipboard."""
    return _clipboard_data is not None


def paste_effect(target_start_time: float):
    """Paste the clipboard data at a new time position.

    Creates a new LightBlock from the clipboard data, adjusting times
    to start at the target position.

    Args:
        target_start_time: Start time for the pasted effect

    Returns:
        New LightBlock instance, or None if clipboard is empty
    """
    global _clipboard_data

    if _clipboard_data is None:
        return None

    from config.models import LightBlock

    # Calculate time offset
    original_start = _clipboard_data.get("start_time", 0.0)
    time_offset = target_start_time - original_start

    # Create a copy of the clipboard data with adjusted times
    adjusted_data = _adjust_times(_clipboard_data.copy(), time_offset)

    # Create new LightBlock from adjusted data
    return LightBlock.from_dict(adjusted_data)


def _adjust_times(data: Dict, offset: float) -> Dict:
    """Adjust all times in the block data by the given offset.

    Args:
        data: Block data dictionary
        offset: Time offset to add

    Returns:
        Adjusted data dictionary
    """
    # Adjust envelope times
    data["start_time"] = data.get("start_time", 0.0) + offset
    data["end_time"] = data.get("end_time", 0.0) + offset

    # Adjust sublane block times
    for key in ["dimmer_blocks", "colour_blocks", "movement_blocks", "special_blocks"]:
        if key in data and data[key]:
            for block in data[key]:
                block["start_time"] = block.get("start_time", 0.0) + offset
                block["end_time"] = block.get("end_time", 0.0) + offset

    return data


def clear_clipboard() -> None:
    """Clear the clipboard."""
    global _clipboard_data
    _clipboard_data = None
