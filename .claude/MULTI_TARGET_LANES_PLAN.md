# Multi-target Lanes Implementation Plan

## Summary

Change light lanes from targeting a single fixture group (`fixture_group: str`) to targeting multiple groups and/or individual fixtures (`fixture_targets: List[str]`).

**Target format:**
- `"Front Wash"` - all fixtures in group
- `"Moving Heads:2"` - specific fixture (0-indexed)

---

## Files to Modify

| File | Change |
|------|--------|
| `config/models.py` | Change `fixture_group: str` to `fixture_targets: List[str]` with migration |
| `timeline/light_lane.py` | Mirror data model changes in runtime class |
| `timeline_ui/light_lane_widget.py` | Replace dropdown with target selection dialog |
| `utils/to_xml/shows_to_xml.py` | Resolve multiple targets to fixtures during export |
| **New:** `utils/target_resolver.py` | Target parsing and resolution utilities |
| **New:** `timeline_ui/target_selection_dialog.py` | Tree-based multi-select dialog |

---

## Implementation Steps

### Step 1: Create target resolver utility (`utils/target_resolver.py`)

New file with functions:
- `parse_target(target: str) -> Tuple[str, Optional[int]]` - parse "Group:index" format
- `format_target(group_name, index) -> str` - create target string
- `resolve_target(target, config) -> List[Fixture]` - resolve single target
- `resolve_targets_unique(targets, config) -> List[Fixture]` - resolve all, deduplicate
- `detect_targets_capabilities(targets, config) -> FixtureGroupCapabilities` - union of capabilities
- `validate_targets(targets, config) -> List[str]` - return warnings

### Step 2: Update data model (`config/models.py:958-986`)

```python
@dataclass
class LightLane:
    name: str
    fixture_targets: List[str] = field(default_factory=list)  # Changed from fixture_group
    muted: bool = False
    solo: bool = False
    light_blocks: List[LightBlock] = field(default_factory=list)

    # Backward compatibility property
    @property
    def fixture_group(self) -> str:
        return self.fixture_targets[0] if self.fixture_targets else ""

    @fixture_group.setter
    def fixture_group(self, value: str):
        self.fixture_targets = [value] if value else []
```

Update `to_dict()` to serialize `fixture_targets`.

Update `from_dict()` to:
- Read `fixture_targets` if present
- Migrate old `fixture_group` to single-item list

### Step 3: Update runtime class (`timeline/light_lane.py`)

- Change `__init__` to accept `fixture_targets: List[str]`
- Add same backward compatibility property as data model
- Update `to_data_model()` and `from_data_model()` methods

### Step 4: Create target selection dialog (`timeline_ui/target_selection_dialog.py`)

New `QDialog` with:
- `QTreeWidget` showing groups as parent items, fixtures as children
- Checkboxes for multi-selection
- Parent/child sync (checking group = all fixtures, partial = some fixtures)
- "Select All" / "Clear All" buttons
- Returns list of target strings

### Step 5: Update lane widget UI (`timeline_ui/light_lane_widget.py`)

Replace the group `QComboBox` (lines 165-196) with:
- `QLabel` showing current targets (truncated with "+N more")
- `QPushButton` "..." to open selection dialog

Update `_detect_group_capabilities()` to use `detect_targets_capabilities()`.

Add `on_targets_changed()` handler to update lane and refresh sublanes.

### Step 6: Update export logic (`utils/to_xml/shows_to_xml.py:1121+`)

In `create_tracks_from_timeline()`:
- Get `lane.fixture_targets` (with fallback to old `fixture_group`)
- Call `resolve_targets_unique()` to get combined fixture list
- Use resolved fixtures for Scene creation and effect generation
- Validate targets and log warnings

---

## Migration Strategy

Automatic and backward-compatible:
1. `from_dict()` detects old `fixture_group` field and converts to single-item `fixture_targets`
2. `fixture_group` property provides read/write compatibility for any code not yet updated
3. New files save with `fixture_targets` array format

---

## Edge Cases

| Case | Handling |
|------|----------|
| Empty targets | Show "(none)" in UI; skip lane with warning in export |
| Invalid group/fixture | Log warning, skip that target, continue with valid ones |
| Duplicate fixtures | `resolve_targets_unique()` deduplicates by fixture ID |
| Mixed fixture types | Union of capabilities - show all applicable sublanes |

---

## Verification

1. **Load old show file** - verify `fixture_group` migrates to `fixture_targets`
2. **Create new lane** - verify target selection dialog works
3. **Select multiple groups** - verify capability detection shows correct sublanes
4. **Select individual fixture** - verify "Group:index" format
5. **Export to QLC+** - verify all targeted fixtures appear in XML
6. **Roundtrip** - save and reload, verify targets preserved
