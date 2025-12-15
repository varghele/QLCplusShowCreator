# timeline/light_lane.py
# Runtime light lane class for timeline playback

from typing import List, Optional
from config.models import LightBlock


class LightLane:
    """Runtime light lane for timeline editing and playback.

    This class wraps the data model LightLane from config.models
    and provides additional runtime functionality.
    """

    def __init__(self, name: str, fixture_group: str):
        """Create a new light lane.

        Args:
            name: Display name for the lane
            fixture_group: Name of the fixture group this lane controls
        """
        self.name = name
        self.fixture_group = fixture_group
        self.muted = False
        self.solo = False
        self.light_blocks: List[LightBlock] = []

    def add_light_block(self, start_time: float, duration: float,
                        effect_name: str = "", parameters: dict = None) -> LightBlock:
        """Add a new light block to this lane.

        Args:
            start_time: Start time in seconds
            duration: Duration in seconds
            effect_name: Effect name (e.g., "bars.static")
            parameters: Effect parameters dict

        Returns:
            The created LightBlock
        """
        block = LightBlock(
            start_time=start_time,
            duration=duration,
            effect_name=effect_name,
            parameters=parameters or {}
        )
        self.light_blocks.append(block)
        return block

    def remove_light_block(self, block: LightBlock):
        """Remove a light block from this lane.

        Args:
            block: The block to remove
        """
        if block in self.light_blocks:
            self.light_blocks.remove(block)

    def get_block_at_time(self, time: float) -> Optional[LightBlock]:
        """Get the block at a specific time.

        Args:
            time: Time position in seconds

        Returns:
            LightBlock at that time, or None
        """
        for block in self.light_blocks:
            if block.start_time <= time < block.start_time + block.duration:
                return block
        return None

    def get_blocks_in_range(self, start_time: float, end_time: float) -> List[LightBlock]:
        """Get all blocks that overlap with a time range.

        Args:
            start_time: Start of range in seconds
            end_time: End of range in seconds

        Returns:
            List of overlapping blocks
        """
        blocks = []
        for block in self.light_blocks:
            block_end = block.start_time + block.duration
            # Check if block overlaps with range
            if block.start_time < end_time and block_end > start_time:
                blocks.append(block)
        return blocks

    def to_data_model(self):
        """Convert to config.models.LightLane for serialization.

        Returns:
            LightLane data model instance
        """
        from config.models import LightLane as LightLaneModel
        lane_model = LightLaneModel(
            name=self.name,
            fixture_group=self.fixture_group,
            muted=self.muted,
            solo=self.solo,
            light_blocks=self.light_blocks.copy()
        )
        return lane_model

    @classmethod
    def from_data_model(cls, lane_model) -> 'LightLane':
        """Create from config.models.LightLane.

        Args:
            lane_model: LightLane data model instance

        Returns:
            New LightLane instance
        """
        lane = cls(
            name=lane_model.name,
            fixture_group=lane_model.fixture_group
        )
        lane.muted = lane_model.muted
        lane.solo = lane_model.solo
        lane.light_blocks = lane_model.light_blocks.copy()
        return lane
