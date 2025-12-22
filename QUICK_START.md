# Quick Start - Sublane Feature

**Last Updated:** December 22, 2024

## 🚀 What's Working Now

✅ **Multiple blocks per sublane type**
✅ **Drag-to-create** new blocks in sublanes
✅ **Overlap prevention** with visual feedback (RED = invalid)
✅ **Select, resize, move** individual blocks
✅ **Auto-expand** effect envelopes

## 🧪 Try It Out

```bash
# Run visual tests to see it working
python tests/visual/test_sublane_blocks.py
```

**Look for:**
- Block 2: **TWO dimmer blocks** (yellow)
- Block 4: **THREE colour blocks** (red→green→blue)
- Drag in empty areas to create new blocks
- Try overlapping movement blocks → RED preview

## 📁 Where Things Are

```
├── .claude/                      # Development context
│   └── docs/                     # Detailed docs
├── tests/                        # All tests
│   └── visual/                   # Interactive tests
├── config/models.py              # Data structures
├── timeline_ui/                  # UI widgets
│   └── light_block_widget.py     # Main interaction logic
└── SESSION_SUMMARY.md            # Last session details
```

## 📖 Documentation

| File | Purpose | When to Read |
|------|---------|--------------|
| `QUICK_START.md` | This file | Starting point |
| `SESSION_SUMMARY.md` | Last session recap | Continuing work |
| `.claude/docs/SUBLANE_IMPLEMENTATION_COMPLETE.md` | Full details | Deep dive |
| `SUBLANE_FEATURE_PLAN.md` | Original plan + status | Understanding roadmap |

## 🔨 Next Tasks

### Phase 6: Edit Dialogs
Create dialogs to edit sublane block parameters (intensity, colors, pan/tilt, etc.)

### Phase 7: DMX Generation
Update playback engine to read from sublane block lists and generate DMX

### Phase 8: Testing
Integration tests, performance tests, real-world usage

## 💡 Key Concepts

**Effect Envelope:** Container for sublane blocks (dashed border)
**Sublane Block:** Individual block with specific parameters (yellow/green/blue/purple)
**Multiple Blocks:** Can have many blocks of same type in one effect
**Overlap:** Movement/Special can't overlap, Dimmer/Colour can

## ⚡ Quick Commands

```bash
# Run tests
python tests/visual/test_sublane_blocks.py
python tests/visual/test_sublane_ui.py

# Check git status
git status

# Push changes
git push origin refactorplustimeline
```

## 🆘 Troubleshooting

**Q: Can't see multiple blocks**
A: Run test_sublane_blocks.py - Block 2 and Block 4 demonstrate this

**Q: Drag-to-create not working**
A: Make sure you're dragging in an empty area of a sublane row

**Q: RED preview always shows**
A: You're trying to overlap Movement or Special blocks (this is prevented by design)

## 📞 Getting Help

1. Read `SESSION_SUMMARY.md` for context
2. Check `.claude/docs/SUBLANE_IMPLEMENTATION_COMPLETE.md` for details
3. Look at test files to see working examples
4. Review `SUBLANE_FEATURE_PLAN.md` for overall design

---

**Status:** Phase 5 complete, ready for Phase 6
**Commit:** 169fc6b on branch `refactorplustimeline`
