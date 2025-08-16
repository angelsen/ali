# ALI Roadmap

## Current State

✅ **Completed:**
- Vocabulary-driven plugin architecture
- Pure token parser (18 lines)
- Plugin registration system
- Router with context-aware routing
- CLI with --dry-run and --list-verbs
- Full tmux plugin implementation
- Expansion engine (argument transformation)
- Validation system with clear errors

🚧 **In Progress:**
- Interactive UI (tmux-popup)

## Next Steps

### 1. Interactive UI
- [ ] tmux-popup integration
- [ ] Command history
- [ ] Tab completion using vocabulary

### 2. Tmux Integration
- [ ] Keybinding setup script
- [ ] Context passing (ALI_CALLER=tmux-popup)
- [ ] Execute commands (not just dry-run)

### 3. Visual Selection (`?`)
The `?` operator for visual selection - "let me choose visually":

```
GO ?                    # Shows numbered panes, press to select
CREATE PANE FROM ?      # Pick which pane to split
SWAP THIS WITH ?        # Visual swap
DELETE ?                # Pick what to delete
```

Implementation via `tmux display-panes` and prompt capture.

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