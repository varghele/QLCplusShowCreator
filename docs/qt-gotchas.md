# Qt Gotchas

Three Qt/PyQt6 landmines we discovered the hard way during the UI
modernization rework. Each cost real time to diagnose. Read this before
touching tables with per-row coloring, custom selection rendering, or
cells with embedded editor widgets.

---

## 1. `QTableView::item` QSS rule silently breaks `setBackground`

### Symptom

You set a cell's background with `item.setBackground(color)` (or `setData(Qt.BackgroundRole, brush)`) and **nothing renders**. The cell stays at the table's default color regardless of how vibrant the brush is. No error, no warning. Tints applied via `_update_row_colors`-style iteration appear to do nothing.

### Cause

If the active stylesheet contains *any* rule scoped to `QTableView::item` — even just `padding: 6px 10px; border: none;` — Qt's `QStyleSheetStyle` takes over item rendering and silently ignores the per-item brush. This is documented Qt behavior and applies to `QTreeView::item` and `QListView::item` as well.

### Fix

Don't put a `QTableView::item` block in your stylesheet. Apply the equivalent visuals via the table's properties instead:

- Row height → `table.verticalHeader().setDefaultSectionSize(...)` or `apply_modern_table_style` (see `gui/widgets/modern_table.py`).
- Grid → `table.setShowGrid(False)`.
- Alternating rows → `table.setAlternatingRowColors(True)` and the table-level `alternate-background-color` property in QSS (which is fine — it's on `QTableView`, not `QTableView::item`).

Both `resources/themes/dark.qss` and `light.qss` carry a comment explaining why the `::item` block is intentionally absent. **Don't re-add it.**

### Why not just live with the override?

Because per-row group tints stop working everywhere — Fixtures, Configuration, Structure, anywhere `QTableWidget` is used.

---

## 2. `selection-background-color: rgba(...)` is silently rendered solid

### Symptom

You set `selection-background-color: rgba(33, 150, 243, 70)` in QSS expecting a translucent overlay so per-row tints stay visible when a row is selected. What renders is an opaque solid color that fully covers the underlying tint. The alpha is silently dropped.

Verified by pixel sampling: alpha 70 over a pink (255, 182, 193) cell produced ~(31, 87, 132) — a deep solid blue, not the expected ~(194, 173, 207) translucent blend.

### Cause

Qt's QSS engine accepts `rgba(...)` syntax but throws away the alpha channel before painting selections. The same color used as `background-color` on a regular widget *does* respect alpha; it's specifically the selection-rendering pipeline that ignores it.

### Fix

Two parts, both required:

1. **`GroupRowDelegate`** strips `State_Selected` before calling `super().paint(...)` so Qt doesn't fill the cell with the opaque selection brush — the cell's `BackgroundRole` tint then survives. The delegate paints **no** border itself.
2. **`RowOutlineTableWidget`** draws a single continuous outline around the entire selected row from a transparent overlay widget that sits on top of viewport children. Per-cell border painting can't span widget cells (see gotcha #3) — the overlay sidesteps that entirely.

Apply both to a table with:

```python
from gui.widgets.row_outline_table import RowOutlineTableWidget
from gui.widgets.group_row_delegate import GroupRowDelegate

self.table = RowOutlineTableWidget()
self.table.setItemDelegate(GroupRowDelegate(self.table))
self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
```

### Why not other approaches?

- **`setStyleSheet` with `QTableView::item:selected`** — would work, but adding any `QTableView::item` rule re-triggers gotcha #1.
- **`QPalette.setBrush(Highlight, alpha-color)`** — Qt's palette also treats selection brushes as solid colors; same dead end.
- **Keeping the rgba and accepting the solid fallback** — fully covers the tint, defeating the point.
- **Per-cell border in the delegate** (the previous approach) — invisible on cells with `setCellWidget` (gotcha #3), so the row reads as bordered text cells with gaps.

---

## 3. `setCellWidget` makes the widget replace the cell display

### Symptom

A QTableWidget cell that hosts a widget via `setCellWidget(row, col, widget)` doesn't show the cell's `QTableWidgetItem` background underneath. `item.setBackground(color)` on cells that have a widget set has no visible effect, even though the brush is recorded on the item.

### Cause

`setCellWidget` is documented as replacing the cell's display, not overlaying. Qt's delegate `paint()` is **not called** for cells that host a widget — the widget renders itself inside the cell rect, and that's what you see. Anything that would normally come from the delegate (selection background, item background, alternate-row color) is invisible in widget cells.

### Fix patterns

Pick one based on the use case:

#### Per-widget stylesheet (current Fixtures-tab approach)

For each cell widget, set a stylesheet that includes the per-row tint:

```python
cell_widget.setStyleSheet(
    f"background-color: {color.name()}; color: {fg_hex};"
)
```

This merges with the global theme rule (Qt only overrides the conflicting properties), so border / padding stay theme-styled. The visual reads as "fields colored" rather than "row colored with fields embedded" — acceptable as an interim, but not perfect.

#### Wrap the widget in a styled container

Tried; doesn't work cleanly. `QSpinBox::up-button`, `QSpinBox::down-button`, `QComboBox::drop-down`, and the `QLineEdit` embedded inside an editable `QComboBox` all paint **opaque** sub-control backgrounds by default. Making the wrapper transparent doesn't help — the widget's sub-controls cover the wrapper's tint anyway. Setting all sub-controls transparent in QSS works visually but loses the affordance of "this is a clickable button".

The unused `gui/widgets/tinted_table.py` and `gui/widgets/tinted_rows_table.py` are the experiments that didn't pan out. Don't delete them — they're a reference for the next attempt.

#### Selection outline via a viewport overlay (current approach)

For the *selection* outline specifically — separate from the per-row tint — `gui/widgets/row_outline_table.py::RowOutlineTableWidget` draws the outline from a transparent overlay widget that's a child of the viewport, raised above all cell-widget siblings. The overlay's `paintEvent` looks up `selectionModel().selectedIndexes()`, computes each row's `visualRect` from leftmost to rightmost visible column, and draws a single continuous `drawRect`. Because the overlay paints last (after viewport children), the outline survives across `setCellWidget` cells.

Trade-offs of the overlay:
- `setCellWidget` is overridden to call `_overlay.raise_()` after each insert — new cell widgets become viewport children stacked above existing siblings, so the overlay needs to be re-raised to stay on top.
- `paintEvent` calls `_overlay.update()` so any viewport repaint (selection change, scroll, data change) re-renders the outline correctly.
- The overlay is always sized to the viewport via `resizeEvent`.

#### Replace `setCellWidget` with a `QStyledItemDelegate` (deferred)

The proper Qt-native answer for the *tint* part: the column gets a delegate whose `createEditor` returns the spinbox/combo only when the user starts editing; in display mode, `paint` renders the value as text and the cell's `BackgroundRole` paints normally. With the overlay solution above, this is no longer required for selection rendering — only for getting tints across the full cell rect (currently they read as "fields colored").

The Fixtures tab has 5 widget cells that would each need a delegate (Universe spin, Address spin, Mode combo, Group combo with "Add New…" magic item, Role combo). Significant refactor — not in the current rework's scope.

---

## In-source landmarks

- `gui/widgets/group_row_delegate.py` — strips `State_Selected` so the row tint survives selection
- `gui/widgets/row_outline_table.py` — overlay-based row-selection outline that spans widget cells
- `gui/widgets/modern_table.py` — `apply_modern_table_style` (the right way to set table visuals without `QTableView::item`)
- `resources/themes/{dark,light}.qss` — comments mark where the `::item` rule used to live
- `gui/tabs/fixtures_tab.py::_update_row_colors` — concrete example of per-row tinting that works around all three gotchas at once
