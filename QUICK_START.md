# Quick Start - Sublane Feature

**Last Updated:** December 23, 2024

## 🚀 What's Working Now

✅ **Multiple blocks per sublane type**
✅ **Drag-to-create** new blocks in sublanes
✅ **Overlap prevention** with visual feedback (RED = invalid)
✅ **Select, resize, move** individual blocks
✅ **Auto-expand** effect envelopes
✅ **Sublane labels** on timeline rows and blocks
✅ **Dimmer effects** (static, twinkle, strobe, etc.)
✅ **Grid visualization** showing beat divisions
✅ **Speed control** with Ctrl+mousewheel
✅ **Intensity handle** with visual dragging
✅ **Export to QLC+** sequences

## 🆕 New in This Session

### Sublane Labels
- **Row labels** on the left side of each sublane (Dimmer, Colour, Movement, Special)
- **Block labels** showing effect type and intensity (e.g., "Dimmer: Twinkle (255)")

### Dimmer Effects
- **Effect selection**: Choose from static, twinkle, strobe, ping_pong_smooth, waterfall
- **Speed control**: Set effect speed (1/4, 1/2, 1, 2, 4)
- **Export**: Each dimmer block generates its own QLC+ sequence

### Interactive Controls
- **Grid visualization**: Black dotted lines showing beat divisions
- **Ctrl+mousewheel**: Adjust effect speed (select block first)
- **Intensity handle**: Drag white horizontal line to adjust intensity

## 🧪 Try It Out

```bash
# Run the application
python main.py
```

**Test the new features:**
1. Create a light block on the timeline
2. Drag in the dimmer sublane to create a dimmer block
3. Double-click to open editor → select "twinkle" effect
4. Click block to select → Ctrl+scroll to change speed
5. Hover over white line in block → drag vertically to adjust intensity
6. Observe grid lines showing beat divisions

## 📁 Where Things Are

```
├── .claude/                      # Development context
│   └── docs/                     # Detailed docs
├── tests/                        # All tests
│   └── visual/                   # Interactive tests
├── config/models.py              # Data structures (DimmerBlock)
├── timeline_ui/                  # UI widgets
│   ├── light_block_widget.py     # Main interaction logic
│   ├── dimmer_block_dialog.py    # Dimmer effect editor
│   └── timeline_widget.py        # Sublane row labels
├── utils/to_xml/
│   └── shows_to_xml.py           # Export to QLC+
└── effects/
    └── dimmers.py                # Dimmer effect functions
```

## 📖 Documentation

| File | Purpose | When to Read |
|------|---------|--------------|
| `QUICK_START.md` | This file | Starting point |
| `SESSION_SUMMARY.md` | Last session recap | Continuing work |
| `.claude/docs/SUBLANE_IMPLEMENTATION_COMPLETE.md` | Full details | Deep dive |
| `SUBLANE_FEATURE_PLAN.md` | Original plan + status | Understanding roadmap |

## 🔨 Current Tasks

### Phase 6.5: Dimmer Effects Integration ✅
- [x] Add effect_type and effect_speed to DimmerBlock model
- [x] Update dimmer block dialog with effect selection
- [x] Add sublane labels to timeline
- [x] Add grid visualization to dimmer blocks
- [x] Implement Ctrl+mousewheel speed adjustment
- [x] Add intensity handle with dragging
- [x] Export dimmer blocks to QLC+ sequences

### Phase 6.6: RGB Control for No-Dimmer Fixtures ✅
- [x] Automatic RGB control mode for fixtures without dimmer capability
- [x] Dimmer sublane controls RGB intensity (scales RGB values)
- [x] Fix RGB channel detection (IntensityRed/Green/Blue presets)
- [x] Fix dimmer effect functions to generate steps for RGB fixtures
- [x] Support multi-segment RGB fixtures (e.g., 10-pixel LED bars)
- [x] Export RGB sequences with dimmer effects applied

### Phase 7: Full Effect Integration (Next)
- [ ] Add colour effects (RGB, rainbow, fade, etc.)
- [ ] Add movement effects (pan/tilt, positions, etc.)
- [ ] Add special effects (gobo, prism, beam, etc.)
- [ ] Test export with multiple effect types

### Phase 8: Testing & Refinement
- [ ] Integration tests
- [ ] Performance tests
- [ ] Real-world usage testing

## 💡 Key Concepts

**Effect Envelope:** Container for sublane blocks (dashed border)
**Sublane Block:** Individual block with specific parameters (yellow/green/blue/purple)
**Effect Type:** The lighting effect to apply (static, twinkle, strobe, etc.)
**Effect Speed:** How fast the effect runs (1/4, 1/2, 1, 2, 4 = beats per step)
**Grid Lines:** Visual beat divisions showing where effect steps occur
**Intensity Handle:** White horizontal line to adjust brightness
**RGB Control Mode:** For fixtures without dimmer, dimmer blocks control RGB intensity (orange color)

## 🎮 Controls

### Block Creation
- **Drag in sublane** to create new block
- **Double-click block** to edit parameters

### Block Selection
- **Click block** to select
- **Click elsewhere** to deselect

### Movement
- **Horizontal drag** on block body = move in time
- **Edge drag** = resize (adds/removes beats)

### Intensity
- **Drag white line** vertically = adjust intensity
- **Top** = 255 (full brightness)
- **Bottom** = 0 (off)
- **Label shows** current value while dragging

### Speed
- **Select block** first
- **Ctrl+Scroll Up** = increase speed (faster effect)
- **Ctrl+Scroll Down** = decrease speed (slower effect)
- **Grid updates** automatically

### Zoom
- **Shift+Scroll** = zoom timeline (existing feature)

## ⚡ Quick Commands

```bash
# Run application
python main.py

# Run tests
python tests/visual/test_sublane_blocks.py
python tests/visual/test_sublane_ui.py

# Check git status
git status

# Commit changes
git add .
git commit -m "Add dimmer effects integration with grid visualization"

# Push changes
git push origin refactorplustimeline
```

## 🆘 Troubleshooting

**Q: Can't see sublane labels**
A: Make sure you have at least one light block on the timeline

**Q: Grid lines not visible**
A: Grid lines are black dotted lines - they show up best on yellow dimmer blocks

**Q: Ctrl+scroll not working**
A: Make sure you've clicked on a dimmer block to select it first

**Q: Intensity handle not dragging**
A: Hover over the white horizontal line until cursor changes to ↕, then drag

**Q: Can't see multiple blocks**
A: Run test_sublane_blocks.py - Block 2 and Block 4 demonstrate this

**Q: RED preview always shows**
A: You're trying to overlap Movement or Special blocks (prevented by design)

## 📞 Getting Help

1. Read `SESSION_SUMMARY.md` for detailed feature documentation
2. Check `.claude/docs/SUBLANE_IMPLEMENTATION_COMPLETE.md` for implementation details
3. Look at test files to see working examples
4. Review `SUBLANE_FEATURE_PLAN.md` for overall design

---

**Status:** Phase 6.6 complete (RGB control for no-dimmer fixtures), ready for Phase 7
**Branch:** `refactorplustimeline`
**Last Commit:** RGB control integration for multi-segment fixtures without dimmer
