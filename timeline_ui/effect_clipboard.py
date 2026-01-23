# timeline_ui/effect_clipboard.py
# Clipboard storage for copied light effects

from typing import Optional, Dict, List, TYPE_CHECKING
import copy

if TYPE_CHECKING:
    from .light_block_widget import LightBlockWidget

# Module-level clipboard storage
_clipboard_data: Optional[Dict] = None

# Multi-block clipboard storage
_multi_clipboard_data: List[Dict] = []


def copy_effect(light_block) -> None:
    """Copy a LightBlock to the clipboard.

    Creates a deep copy of the block data (as dictionary) so modifications
    to the original don't affect the clipboard.

    Args:
        light_block: LightBlock instance to copy
    """
    global _clipboard_data, _multi_clipboard_data
    _clipboard_data = light_block.to_dict()
    _multi_clipboard_data = []  # Clear multi-clipboard when single copy


def has_clipboard_data() -> bool:
    """Check if there's data in the clipboard (single or multi)."""
    return _clipboard_data is not None or len(_multi_clipboard_data) > 0


def has_multi_clipboard_data() -> bool:
    """Check if there's multi-block data in the clipboard."""
    return len(_multi_clipboard_data) > 0


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
    adjusted_data = _adjust_times(copy.deepcopy(_clipboard_data), time_offset)

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
    global _clipboard_data, _multi_clipboard_data
    _clipboard_data = None
    _multi_clipboard_data = []


def copy_multiple_effects(block_widgets: List['LightBlockWidget']) -> None:
    """Copy multiple LightBlockWidgets to the clipboard.

    Stores blocks with their relative timing information so they can be
    pasted while preserving their relative positions.

    Args:
        block_widgets: List of LightBlockWidget instances to copy
    """
    global _clipboard_data, _multi_clipboard_data

    if not block_widgets:
        return

    # Clear single clipboard
    _clipboard_data = None
    _multi_clipboard_data = []

    # Find the earliest start time to use as reference
    min_start_time = min(w.block.start_time for w in block_widgets)

    # Store each block's data along with its lane identifier and relative offset
    for widget in block_widgets:
        block_data = widget.block.to_dict()

        # Store the relative offset from the earliest block
        relative_offset = widget.block.start_time - min_start_time

        # Get lane name from parent if available
        lane_name = None
        lane_widget = widget.lane_widget
        if lane_widget and hasattr(lane_widget, 'lane') and lane_widget.lane:
            lane_name = lane_widget.lane.name

        entry = {
            'block_data': block_data,
            'relative_offset': relative_offset,
            'lane_name': lane_name,
            'original_start': widget.block.start_time
        }
        _multi_clipboard_data.append(entry)


def paste_multiple_effects(target_time: float, lane_widgets: List) -> List:
    """Paste multiple effects at the target time.

    Pastes all copied blocks, preserving their relative timing.

    Args:
        target_time: Base time to paste at (earliest block will start here)
        lane_widgets: List of LightLaneWidget instances to paste into

    Returns:
        List of (lane_widget, new_block) tuples for successfully pasted blocks
    """
    global _multi_clipboard_data

    if not _multi_clipboard_data:
        return []

    from config.models import LightBlock

    # Build lane lookup by name
    lane_lookup = {}
    for lane_widget in lane_widgets:
        if hasattr(lane_widget, 'lane') and lane_widget.lane.name:
            lane_lookup[lane_widget.lane.name] = lane_widget

    results = []

    for entry in _multi_clipboard_data:
        block_data = copy.deepcopy(entry['block_data'])
        relative_offset = entry['relative_offset']
        lane_name = entry.get('lane_name')

        # Calculate new start time
        new_start_time = target_time + relative_offset

        # Adjust all times in block data
        original_start = block_data.get("start_time", 0.0)
        time_offset = new_start_time - original_start
        adjusted_data = _adjust_times(block_data, time_offset)

        # Create new LightBlock
        new_block = LightBlock.from_dict(adjusted_data)

        # Find target lane
        target_lane = None
        if lane_name and lane_name in lane_lookup:
            target_lane = lane_lookup[lane_name]
        elif lane_widgets:
            # Fall back to first lane if original lane not found
            target_lane = lane_widgets[0]

        if target_lane:
            results.append((target_lane, new_block))

    return results


def get_multi_clipboard_count() -> int:
    """Get number of blocks in multi-clipboard.

    Returns:
        Number of blocks stored in multi-clipboard
    """
    return len(_multi_clipboard_data)
