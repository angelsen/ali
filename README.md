# ALI - Action Language Interpreter

[![PyPI version](https://badge.fury.io/py/ali-tool.svg)](https://pypi.org/project/ali-tool/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Compose complex tmux commands from regular phrases. Pure command aggregator - outputs commands, never executes them.

## Quickstart

```bash
# Install
uv tool install ali-tool  # Recommended
# OR
pip install ali-tool

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

See the [plugin documentation](https://github.com/angelsen/ali/tree/master/src/ali/plugins) for more patterns.

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
# Clone and install dev version
git clone https://github.com/angelsen/ali.git
cd ali
uv tool install -e .

# Test a command
ali GO .2
```

## License

MIT - see [LICENSE](LICENSE)