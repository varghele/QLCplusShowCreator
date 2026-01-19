# Lane Targeting Options

**Problem:** Currently, light lanes can only target a single fixture group. This limits workflows where effects need to target:
1. A single specific fixture within a group
2. Multiple fixture groups at once

This document outlines three potential solutions.

---

## Option 1: Multi-target Lanes (Recommended)

### Concept
A lane can target any combination of groups and/or individual fixtures.

### Data Model Change
```python
# Current
class LightLane:
    fixture_group: str  # "Front Wash"

# New
class LightLane:
    fixture_targets: List[str]  # ["Front Wash", "Back Wash", "Moving Heads:2"]
```

### Target String Format
- `"Group Name"` - targets all fixtures in that group
- `"Group Name:index"` - targets a specific fixture (0-indexed)
- Alternative: use fixture UUIDs for more robust referencing

### UI Changes
- Replace group dropdown with multi-select control
- Options:
  - Tree view with checkboxes (groups expandable to show fixtures)
  - Dual-list picker (available → selected)
  - Tag-style input with autocomplete

### Example Scenarios
- Lane targeting "Front Wash" + "Back Wash" together
- Lane targeting just fixture #3 from "Moving Heads"
- Lane targeting "All PARs" + one specific moving head for a solo effect

### Files to Update
| File | Changes |
|------|---------|
| `config/models.py` | Change `fixture_group: str` to `fixture_targets: List[str]` in LightLane |
| `timeline_ui/light_lane_widget.py` | Replace dropdown with multi-select widget |
| `utils/to_xml/shows_to_xml.py` | Loop over multiple targets when exporting |
| `timeline/light_lane.py` | Update runtime class to handle multiple targets |
| `config/loader.py` (if exists) | Migration logic: convert old `fixture_group` to single-item list |

### Migration Strategy
```python
# When loading old format
if "fixture_group" in lane_data and "fixture_targets" not in lane_data:
    lane_data["fixture_targets"] = [lane_data.pop("fixture_group")]
```

### Pros
- Solves both use cases (single fixture AND multiple groups)
- Flexible targeting syntax
- Relatively clean conceptual model

### Cons
- Requires migration for existing show files
- UI is more complex than current dropdown
- Need to handle capability detection across mixed fixture types

---

## Option 2: Fixture Filtering Within a Group

### Concept
A lane still targets one group, but you can optionally limit it to specific fixtures within that group.

### Data Model Change
```python
# Current
class LightLane:
    fixture_group: str

# New
class LightLane:
    fixture_group: str
    fixture_filter: Optional[List[int]] = None  # None = all, [0, 2] = first and third
```

### UI Changes
- Keep existing group dropdown
- Add secondary control below: fixture checkboxes or multi-select
- Only appears after a group is selected
- Default: all fixtures checked

### Example Scenarios
- Lane targeting just fixture #1 and #3 from "Moving Heads"
- Lane targeting only the center PAR from "Front Wash"

### Limitations
- **Cannot target multiple groups from one lane**
- To affect "Front Wash" + "Back Wash" simultaneously, you need two lanes with identical effect blocks

### Files to Update
| File | Changes |
|------|---------|
| `config/models.py` | Add `fixture_filter: Optional[List[int]] = None` to LightLane |
| `timeline_ui/light_lane_widget.py` | Add fixture filter checkboxes below group dropdown |
| `utils/to_xml/shows_to_xml.py` | Filter `group.fixtures` by indices during export |
| `timeline/light_lane.py` | Apply filter in runtime class |

### Migration Strategy
- None required - new field has default value of `None` (all fixtures)
- Fully backward compatible

### Pros
- Simplest implementation
- Fully backward compatible with existing files
- Minimal UI changes
- Easy to understand

### Cons
- Only solves half the problem (single fixture: ✅, multiple groups: ❌)
- May need duplicate lanes for multi-group effects

---

## Option 3: Virtual/Ad-hoc Groups (Fixture Selections)

### Concept
Create reusable "selections" that group arbitrary fixtures together. Lanes can target either regular groups or these selections.

### Data Model Change
```python
# New class
@dataclass
class FixtureReference:
    group_name: str
    fixture_index: int

@dataclass
class FixtureSelection:
    name: str
    members: List[FixtureReference]
    color: str = "#888888"  # Display color in UI

# In Configuration
class Configuration:
    groups: Dict[str, FixtureGroup]
    selections: Dict[str, FixtureSelection]  # New
    # ...
```

### Lane Reference
```python
class LightLane:
    target_type: Literal["group", "selection"]  # New field
    target_name: str  # References either a group or selection by name
```

### UI Changes
- New "Selections" panel in fixture management (or stage tab)
- Create selection by:
  - Multi-selecting fixtures on stage view
  - Picking from a tree of groups/fixtures
- Lane dropdown shows both groups and selections (possibly grouped)

### Example Scenarios
- Create "Solo Fixtures" selection containing one fixture from each group
- Create "Stage Left" selection with fixtures from multiple groups physically on the left
- Create "Audience Blinders" selection for specific moments
- Reuse the same selection across multiple lanes and shows

### Files to Update
| File | Changes |
|------|---------|
| `config/models.py` | Add `FixtureReference`, `FixtureSelection` classes; update `Configuration` |
| New file: `gui/tabs/selections_tab.py` or add to `stage_tab.py` | UI for managing selections |
| `timeline_ui/light_lane_widget.py` | Dropdown shows groups + selections |
| `utils/to_xml/shows_to_xml.py` | Resolve selections to fixtures during export |
| `timeline/light_lane.py` | Handle both target types |
| Config save/load | Serialize/deserialize selections |

### Migration Strategy
- Existing files continue to work (they only use groups)
- `target_type` defaults to `"group"` for backward compatibility
- `selections` dict defaults to empty

### Pros
- Most powerful and flexible
- Selections are reusable across lanes and shows
- Clean separation of concerns
- Mirrors how some professional lighting software works

### Cons
- Largest implementation effort
- Adds new concept users must learn
- More complex mental model
- Fixture references can become stale if groups are reorganized

---

## Comparison Summary

| Aspect | Option 1: Multi-target | Option 2: Filter | Option 3: Selections |
|--------|:---------------------:|:----------------:|:--------------------:|
| Single fixture from group | ✅ | ✅ | ✅ |
| Multiple groups at once | ✅ | ❌ | ✅ |
| Reusable across lanes | ❌ | ❌ | ✅ |
| UI complexity | Medium | Low | High |
| Implementation effort | Medium | Small | Large |
| Backward compatibility | Migration needed | Full | Migration needed |
| Learning curve | Low | None | Medium |

---

## Recommendation

**Start with Option 1** if you need both features (single fixture + multiple groups). It's a good balance of power and complexity.

**Start with Option 2** if single-fixture targeting is the priority and you can live with duplicate lanes for multi-group effects.

**Consider Option 3** if you find yourself creating the same fixture combinations repeatedly and want to manage them as first-class entities.

---

## Implementation Branch Strategy

```bash
# Create exploration branches from current state
git checkout -b feature/lane-targeting-option1
git checkout -b feature/lane-targeting-option2
git checkout -b feature/lane-targeting-option3

# If an option doesn't work out, return to base
git checkout fix_effect_bugs
git branch -D feature/lane-targeting-optionX
```
