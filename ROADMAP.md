# ALI Roadmap

## Current State

✅ **Completed:**
- Unified rules engine (parsing, inference, validation, expansion)
- Ultra-dumb parser using shlex (37 lines, zero domain knowledge)
- Data-driven token parsing via YAML rules
- Plugin registration system with verb routing
- Router with context-aware plugin selection
- CLI with --dry-run and --list-verbs
- Full tmux plugin implementation
- Smart inference rules (object detection from targets)
- Visual selectors (.?, :?, ?) with context-aware inference
- Command aliases (NEW, KILL, etc.) and shortforms (n, d, g, l, s, r)
- Field transformations and conditional expansions
- Validation system with helpful error messages
- Proper handling of empty targets (no empty -t flags)

🚧 **In Progress:**
- Interactive UI (tmux-popup)

## Next Steps

### 1. Interactive UI
- [ ] tmux-popup integration
- [ ] Command history
- [ ] Tab completion using vocabulary

### 2. Tmux Integration Improvements
- [ ] Keybinding setup script
- [ ] Better context passing (ALI_CALLER=tmux-popup)
- [ ] Direct execution mode (not just dry-run)

### 3. Enhanced Visual Selection
✅ **Already Working:**
```
GO .?                   # Visual pane selector
DELETE .?               # Visual delete pane
GO :?                   # Visual window selector
SWITCH ?                # Visual session selector
SWAP . WITH .?          # Visual swap
```

**Future Enhancements:**
- [ ] Multi-select support for batch operations
- [ ] Visual feedback during selection

### 4. More Plugins
- [ ] Vim plugin (splits, tabs, buffers)
- [ ] i3wm plugin (workspaces, windows)
- [ ] Git plugin (as proof of concept)

### 5. Advanced Features
- [ ] Grammar merging from multiple plugins
- [ ] Command history
- [ ] Persistent configuration
- [ ] Plugin discovery/installation

## Design Principles

1. **Plugins are data** - YAML configs, not code
2. **Commands are intuitive** - If you can think it, you can type it
3. **Errors are helpful** - Tell users what went wrong and how to fix it
4. **Context aware** - Same command works differently in tmux vs vim