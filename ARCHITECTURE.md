# ALI Architecture

## Overview

ALI is a plugin-based command interpreter that translates natural language commands into tool-specific operations through service composition.

## Core Flow

```
User Input → Parse → Route → Resolve → Execute
    ↓          ↓        ↓        ↓         ↓
"WIDTH 012" → Tokens → Plugin → Command → Shell
```

## Component Layers

### 1. CLI Layer (`cli.py`, `executor.py`, `scripts.py`)
- Entry point and argument parsing
- Command execution with dry-run support
- Plugin script delegation

### 2. Core Layer (`core/`)
- **Router**: Verb-driven command parsing
- **Registry**: Service discovery and dependency tracking
- **Resolver**: Service chain building
- **Plugin**: YAML configuration loader

### 3. Plugin Layer (`plugins/*/`)
- YAML-only configuration (no code in plugins)
- Optional scripts for complex operations
- Service declarations (provides/requires)

## Key Concepts

### Service Composition
Plugins declare services they provide and require. The system automatically builds command chains:

```
EDIT @? → micro needs file_selector
        → broot provides file_selector, needs pane
        → tmux provides pane
        → Result: "tmux split | broot | micro"
```

### Pattern Ownership
Plugins own their syntax patterns:
- tmux owns `.` (panes) and `:` (windows)
- broot owns `@` (file selectors)

### Inference Rules
Smart transformations defined in YAML:
- `GO ?` → `GO .?` (visual selector)
- `DELETE .2` → `DELETE PANE .2` (inferred object)

### Script Delegation
Complex operations delegate to scripts:
```yaml
exec: "ali --plugin-script tmux.distribute --dimension {dimension} --panes {panes}"
```

## Design Principles

1. **Plugins are data** - YAML configuration, not code
2. **Services emerge** - No central registry, plugins self-organize
3. **Explicit execution** - Dry-run by default in code
4. **Simple wins** - Scripts for complexity, not YAML gymnastics

## File Structure

```
src/ali/
├── core/
│   ├── plugin.py      # Loads YAML configs
│   ├── registry.py    # Service discovery
│   ├── resolver.py    # Command building
│   └── router.py      # Verb parsing
├── plugins/
│   └── {name}/
│       ├── plugin.yaml
│       └── scripts/   # Optional
└── cli.py            # Entry point
```

## Extension Points

1. **Add a plugin**: Create `plugin.yaml` with vocabulary and commands
2. **Add a service**: Declare in `provides:` section
3. **Add complex logic**: Write a script, reference in `exec:`
4. **Add inference**: Define rules in `inference:` section