# ALI Roadmap - Service-Based Plugin Architecture

## Core Principle
Plugins declare services they provide/require. The system builds command chains.

## Current State (MVP Complete ✅)

### Working Features
- **Plugin-Defined Grammar** - Plugins define complete parsing rules
- **Template Composition** - Two-pass substitution ({split_{direction}})
- **Command Resolution** - Verbs route to plugins, build exec strings
- **Plugin Scripts** - Complex operations via `ali --plugin-script tmux.distribute`
- **Strict Validation** - Leftover token detection, grammar enforcement
- **Inference Rules** - Smart transformations (`GO ?` → `GO .?`)

### Working Commands
```bash
ali "GO .2"              # Navigate to pane
ali "SPLIT left"         # Split pane
ali "WIDTH 012"          # Distribute panes equally
ali "WIDTH 012 AS 1/2"   # Make panes half window width
ali "EDIT @?"            # File selector → editor (chain built)
ali "BROWSE"             # Open file browser
```

## Architecture Achieved

### Grammar-Driven Parsing
```yaml
grammar:
  direction:
    values: [left, right, up, down]
    transform: lower
  fraction:
    pattern: "^\d+/\d+$"
```

### Template Composition
```yaml
# One pattern for all directions:
exec: "{split_{direction}}"
# Resolves: left → {split_left} → "tmux split-window -h -b"
```

### Plugin Scripts
```yaml
# Complex operations delegate to scripts
- match: {verb: WIDTH}
  exec: "ali --plugin-script tmux.distribute --dimension width --panes {panes}"
```

## Next Steps

### Phase 1: Better Service Resolution
- [ ] Actually execute file selector and pass result to editor
- [ ] Handle service responses (not just command strings)
- [ ] Inter-plugin communication beyond command composition

### Phase 2: Multiple Providers
- [ ] Handle multiple plugins providing same service
- [ ] User preference system (EDITOR=vim)
- [ ] Runtime service selection

### Phase 3: Advanced Features
- [ ] Plugin hotloading
- [ ] Service versioning
- [ ] Plugin marketplace/discovery

## Design Decisions

### What We Keep Simple
- **No formal contracts** - Services are just names
- **No complex DI** - Simple provider/require matching
- **Scripts for complexity** - Don't overload YAML

### What We Don't Do
- Not a package manager
- Not a general plugin framework
- Not trying to replace shell

## Success Metrics Achieved ✅
- **Install plugins, they work** - tmux + micro + broot just compose
- **Clean separation** - Plugins don't know each other's implementation
- **Extensible** - Easy to add new plugins following patterns

## Development Philosophy
- Start simple, evolve based on real use
- Data-driven configuration over code
- Explicit over magic