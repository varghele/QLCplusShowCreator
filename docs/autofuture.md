# Auto-Generation — Future Improvements

## Investigation / Debugging System

**Priority: HIGH**

The auto-generation algorithm is currently a black box. When it produces unexpected results, there's no way to understand WHY it made specific decisions. We need a decision logging/investigation system.

### Requirements:
- Log every decision the algorithm makes: which rudiments were considered, scores, why one was picked over another
- Log per-section: audio analysis values, target flux, selected rudiments per group, movement strategy, color assignment
- Log per-group: diversity adjustments, complement bonuses, final scores
- Log iterative selection: how many rounds, what changed per round, why it stabilized
- Exportable as a readable report (markdown or HTML) that the user can review alongside the generated show
- Optionally display in the UI (collapsible panel or separate window)

### Possible approaches:
1. **GenerationReport dataclass** returned alongside the lanes, containing all decision data
2. **Structured logging** to a file during generation, parseable after the fact
3. **Interactive inspector** in the UI that lets you click a generated block and see why it was chosen

### When to implement:
After the core algorithm is stable and producing reasonable results. The investigation system helps fine-tune, not build.
