# Phase 3: UI Implementation Plan
## Sublane Rendering in Timeline

## Current Architecture Understanding

### TimelineWidget (`timeline_ui/timeline_widget.py`)
- Base timeline canvas that draws grid and playhead
- Fixed height (minimum 60px)
- `paintEvent()` draws: song structure backgrounds → grid → playhead
- Provides `time_to_pixel()` and `pixel_to_time()` conversions

### LightLaneWidget (`timeline_ui/light_lane_widget.py`)
- Contains:
  - Controls widget (left, 320px fixed)
  - TimelineWidget (right, scrollable)
- Currently fixed height: min 80px, max 120px
- Contains list of LightBlockWidget instances

### LightBlockWidget (`timeline_ui/light_block_widget.py`)
- Individual effect block visualization
- Positioned absolutely on TimelineWidget
- Handles drag, resize, click to edit

## Required UI Changes

### 1. TimelineWidget Enhancements

**Add sublane awareness:**
- New property: `num_sublanes` (1-4)
- New property: `sublane_height` (default 60px per sublane)
- Calculate total height: `num_sublanes * sublane_height`

**Add sublane separator drawing:**
```python
def draw_sublane_separators(self, painter, width, height):
    """Draw horizontal lines separating sublanes."""
    if self.num_sublanes <= 1:
        return

    separator_pen = QPen(QColor("#666666"), 1)
    painter.setPen(separator_pen)

    for i in range(1, self.num_sublanes):
        y = i * self.sublane_height
        painter.drawLine(0, y, width, y)
```

**Add sublane labels (optional):**
```python
def draw_sublane_labels(self, painter):
    """Draw sublane type labels on the left edge."""
    labels = []
    if self.has_dimmer:
        labels.append("Dimmer")
    if self.has_colour:
        labels.append("Colour")
    if self.has_movement:
        labels.append("Movement")
    if self.has_special:
        labels.append("Special")

    for i, label in enumerate(labels):
        y = i * self.sublane_height + (self.sublane_height / 2)
        painter.drawText(5, y, label)
```

### 2. LightLaneWidget Modifications

**Dynamic height based on capabilities:**
```python
def __init__(self, lane: LightLane, fixture_groups: list, config: Configuration):
    # ...existing code...

    # Detect capabilities for this lane's fixture group
    self.capabilities = self._detect_group_capabilities()

    # Calculate number of sublanes
    self.num_sublanes = self._count_sublanes()

    # Set dynamic height (60px per sublane)
    sublane_height = 60
    total_height = self.num_sublanes * sublane_height
    self.setMinimumHeight(total_height)
    self.setMaximumHeight(total_height)

def _detect_group_capabilities(self):
    """Detect capabilities from fixture group."""
    if self.lane.fixture_group in self.config.groups:
        group = self.config.groups[self.lane.fixture_group]

        # Check if capabilities already cached
        if group.capabilities:
            return group.capabilities

        # Otherwise detect and cache
        from utils.fixture_utils import detect_fixture_group_capabilities
        caps = detect_fixture_group_capabilities(group.fixtures)
        group.capabilities = caps
        return caps

    # Default: all capabilities
    return FixtureGroupCapabilities(True, True, True, True)

def _count_sublanes(self):
    """Count number of active sublanes."""
    count = 0
    if self.capabilities.has_dimmer:
        count += 1
    if self.capabilities.has_colour:
        count += 1
    if self.capabilities.has_movement:
        count += 1
    if self.capabilities.has_special:
        count += 1
    return max(1, count)  # At least 1 sublane
```

**Pass capabilities to TimelineWidget:**
```python
def setup_ui(self):
    # ...existing code...

    self.timeline_widget = TimelineWidget()
    self.timeline_widget.num_sublanes = self.num_sublanes
    self.timeline_widget.sublane_height = 60
    self.timeline_widget.capabilities = self.capabilities  # For label drawing
    self.timeline_widget.setMinimumHeight(self.num_sublanes * 60)
```

### 3. Sublane Index Mapping

Create utility function to map sublane types to row indices:

```python
def get_sublane_index(self, sublane_type: str) -> int:
    """Get the row index (0-based) for a sublane type.

    Args:
        sublane_type: "dimmer", "colour", "movement", or "special"

    Returns:
        Row index, or 0 if not found
    """
    index = 0

    if sublane_type == "dimmer" and self.capabilities.has_dimmer:
        return index
    if self.capabilities.has_dimmer:
        index += 1

    if sublane_type == "colour" and self.capabilities.has_colour:
        return index
    if self.capabilities.has_colour:
        index += 1

    if sublane_type == "movement" and self.capabilities.has_movement:
        return index
    if self.capabilities.has_movement:
        index += 1

    if sublane_type == "special" and self.capabilities.has_special:
        return index

    return 0  # Fallback
```

### 4. LightBlockWidget Modifications

**Add sublane positioning:**
```python
class LightBlockWidget(QLabel):
    def __init__(self, block: LightBlock, timeline_widget, sublane_height=60):
        # ...existing code...

        self.sublane_height = sublane_height
        self.block = block

        # Determine which sublanes this block occupies
        self.active_sublanes = self._get_active_sublanes()

        self.update_position()

    def _get_active_sublanes(self):
        """Determine which sublanes have active blocks."""
        sublanes = []
        if self.block.dimmer_block:
            sublanes.append("dimmer")
        if self.block.colour_block:
            sublanes.append("colour")
        if self.block.movement_block:
            sublanes.append("movement")
        if self.block.special_block:
            sublanes.append("special")
        return sublanes

    def update_position(self):
        """Update widget position and size based on block times and sublanes."""
        x = self.timeline_widget.time_to_pixel(self.block.start_time)
        width = self.timeline_widget.time_to_pixel(self.block.get_duration())

        # Calculate vertical span
        if self.active_sublanes:
            # Find min and max sublane indices
            indices = [self.parent_lane.get_sublane_index(s)
                      for s in self.active_sublanes]
            min_index = min(indices)
            max_index = max(indices)

            y = min_index * self.sublane_height
            height = (max_index - min_index + 1) * self.sublane_height
        else:
            # Default: full lane height
            y = 0
            height = self.timeline_widget.height()

        self.setGeometry(int(x), int(y), int(width), int(height))
```

**Render envelope vs sublane blocks:**
```python
def paintEvent(self, event):
    """Draw the effect block with envelope and sublane blocks."""
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw envelope border (if multi-sublane)
    if len(self.active_sublanes) > 1:
        envelope_pen = QPen(QColor("#4CAF50"), 2)
        painter.setPen(envelope_pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

    # Draw individual sublane blocks
    for sublane_type in self.active_sublanes:
        self._draw_sublane_block(painter, sublane_type)

    # Draw effect name (with asterisk if modified)
    effect_name = self.block.effect_name
    if self.block.modified:
        effect_name += " *"

    painter.setPen(QColor("white"))
    painter.drawText(5, 15, effect_name)

def _draw_sublane_block(self, painter, sublane_type):
    """Draw an individual sublane block."""
    # Get sublane block data
    if sublane_type == "dimmer":
        sublane_block = self.block.dimmer_block
        color = QColor("#FFC107")  # Amber for dimmer
    elif sublane_type == "colour":
        sublane_block = self.block.colour_block
        color = QColor("#9C27B0")  # Purple for colour
    elif sublane_type == "movement":
        sublane_block = self.block.movement_block
        color = QColor("#2196F3")  # Blue for movement
    elif sublane_type == "special":
        sublane_block = self.block.special_block
        color = QColor("#FF5722")  # Orange for special
    else:
        return

    if not sublane_block:
        return

    # Calculate position within this widget
    sublane_index = self.parent_lane.get_sublane_index(sublane_type)
    y_offset = sublane_index * self.sublane_height - self.y()

    # Draw sublane block rectangle
    painter.fillRect(
        0,
        int(y_offset),
        self.width(),
        self.sublane_height,
        color
    )
```

### 5. Visual Design

**Sublane Colors:**
- Dimmer: Amber (#FFC107)
- Colour: Purple (#9C27B0)
- Movement: Blue (#2196F3)
- Special: Orange (#FF5722)

**Effect Envelope:**
- Border: Green (#4CAF50), 2px
- Only shown when effect spans multiple sublanes

**Modified Indicator:**
- Asterisk (*) appended to effect name

## Implementation Order

1. ✅ Update TimelineWidget to support multiple sublanes
   - Add `num_sublanes`, `sublane_height` properties
   - Add `draw_sublane_separators()` method
   - Update `paintEvent()` to call separator drawing

2. ✅ Update LightLaneWidget for dynamic height
   - Add capability detection on init
   - Calculate num_sublanes from capabilities
   - Set dynamic height
   - Pass capabilities to TimelineWidget

3. ✅ Add sublane index mapping
   - Implement `get_sublane_index()` utility

4. ✅ Update LightBlockWidget for sublane rendering
   - Detect active sublanes from block
   - Position based on sublane indices
   - Render envelope + sublane blocks
   - Color coding by sublane type

5. ✅ Test with different fixture types
   - Moving head (4 sublanes)
   - RGBW Par (2 sublanes)
   - Simple dimmer (1 sublane)

## Next Phase Preview

**Phase 4: Interaction** (not started yet)
- Click detection (envelope vs sublane block)
- Drag to create in specific sublane
- Resize sublane blocks independently
- Auto-expand envelope on sublane extension

**Phase 5: Effect Dialogs** (not started yet)
- Full effect creation dialog
- Sublane-specific editing
- Auto-population logic

**Phase 6: DMX Generation** (not started yet)
- Read from sublane blocks
- Gap handling (DMX to 0, movement interpolation)
- Cross-fade for Dimmer/Colour
