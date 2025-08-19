# ALI - Adaptive Language Interface

Action Language Interpreter - compose complex commands from regular phrases.

## Quickstart

```bash
# Install
uv tool install ali  # Recommended
# OR
pip install ali

# Initialize tmux integration
ali --init tmux
# Then reload tmux: tmux source ~/.tmux.conf

# Use
ali GO .2              # → tmux select-pane -t .2
ali SPLIT pop          # → tmux display-popup -w 80% -h 80% -d "$PWD" -E 'bash'
ali EDIT file.txt pop  # → tmux display-popup ... 'micro file.txt'
ali WIDTH 012          # → Distribute panes evenly
ali ECHO ed?           # → Popup editor, pipe output to send-keys
```

Press `C-b a` in tmux to open ALI prompt after initialization.

## Architecture

ALI is a pure command aggregator - it only outputs commands, never executes them.

```
Input → Parser → Router → Resolver → Output
         ↓         ↓         ↓
      Grammar  Commands  Templates
```

### Core Components

- **Parser** - Tokenizes input using plugin grammars
- **Router** - Matches patterns to find commands  
- **Resolver** - Expands templates with conditionals and services
- **Registry** - Manages plugins and their services

### Template Engine

```yaml
# Conditionals
exec: "{?target:tmux select-pane -t {target} && }command"

# Array lookups  
exec: "{direction[left:-h -b,right:-h,up:-v -b,down:-v,pop:display-popup]}"

# Service composition
exec: "{split} 'micro {file}'"  # Uses split service from tmux
```

## Plugin Development

Plugins are YAML-only data files that define grammar, commands, and services.

```yaml
# plugin.yaml
name: example
version: 1.0
description: Example plugin
# Grammar
grammar:
  item: {type: string}
  direction: {values: [left, right, up, down, pop]}
# Commands  
commands:
  - match: {verb: ACTION, item: present}
    exec: "{split} '{item}'"
# Services
services:
  process: "tool --process"
# Selectors
selectors:
  item?:
    type: stream
    exec: "selector"
```

See `src/ali/plugins/llms.txt` for comprehensive plugin patterns.

## Examples

### Navigation
```bash
ali GO .2          # Go to pane 2
ali GO :3          # Go to window 3
ali GO ?           # Visual pane selector
```

### Splits & Layout
```bash
ali SPLIT          # Split right (default)
ali SPLIT left     # Split left
ali SPLIT pop      # Open popup shell
ali WIDTH 012      # Distribute panes evenly
```

### Editing
```bash
ali EDIT file.txt       # Edit in right split
ali EDIT file.txt pop   # Edit in popup
ali VIEW file.txt       # Read-only view
```

### Stream Operations
```bash
ali ECHO ed?       # Edit in popup, pipe to send-keys
ali COPY br?       # Browse in popup, copy to clipboard
```

## Development

```bash
# Install dev version
uv tool install -e .
# OR
uv pip install -e .

# Test commands
python3 -c "from src.ali.core.router import Router; print(Router().route('GO .2'))"

# Run directly
python3 -m src.ali GO .2
```

## License

MIT