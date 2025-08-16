# TAL Roadmap

## Current State

✅ **Completed:**
- Plugin architecture (YAML-based)
- Expansion engine (argument transformation)
- Validation system
- Tmux plugin working in REPL

🚧 **In Progress:**
- Grammar parser (Lark)
- CLI entry point
- Interactive UI (tmux-popup)

## Next Steps

### 1. Parser & CLI
- [ ] Basic Lark grammar for commands
- [ ] CLI entry point that uses plugins
- [ ] Execute actual tmux commands (not just generate)

### 2. Context & Routing
- [ ] Detect tmux/vim/desktop context
- [ ] Route commands to correct plugin
- [ ] Pass context from tmux keybinding

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