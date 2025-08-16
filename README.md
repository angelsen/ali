# TAL - Tmux Action Language

A plugin-based command language for tmux and other CLI tools. Write intuitive commands like `CREATE PANE LEFT` instead of memorizing complex tmux syntax.

## Features

- **Simple Commands**: `CREATE PANE LEFT`, `DELETE .1`, `LIST WINDOWS`
- **Plugin Architecture**: Extend TAL with YAML configs - no coding required
- **Smart Expansions**: Automatically transforms commands to correct CLI arguments
- **Validation**: Clear error messages when commands are invalid

## Installation

```bash
uv add pyyaml
uv tool install .
```

## Usage

```bash
# CLI mode
tal "CREATE PANE LEFT"
tal "DELETE .THIS"
tal "SWAP .1 WITH .2"
tal "GO :1"

# List available commands
tal --list-verbs

# Dry run (see what would execute)
tal --dry-run "CREATE WINDOW"
```

## Architecture

TAL uses a vocabulary-driven plugin system where each tool declares what it understands:

```yaml
# plugins/tmux/plugin.yaml
vocabulary:
  verbs: [CREATE, DELETE, GO, SWAP]
  objects: [PANE, WINDOW, SESSION]
  directions: [left, right, up, down]

commands:
  - match: {verb: CREATE, object: PANE}
    exec: "tmux split-window {direction}"
```

Key components:
- **Pure Token Parser**: 18 lines, zero domain knowledge
- **Plugin Registration**: Verbs automatically registered for routing
- **Context Routing**: Correct plugin selected based on environment
- **Vocabulary-Driven**: Plugins declare what they understand

## Current Status

✅ **Working:**
- CLI with full tmux support
- Plugin registration and routing
- Context-aware command execution
- Validation and error messages

🚧 **In Progress:**
- Interactive UI (tmux-popup)
- Additional plugins (vim, i3)

## License

MIT