# ALI - Action Language Interpreter

Your command interpreter that speaks every tool's language. Write intuitive commands like `CREATE PANE LEFT` instead of memorizing complex keybindings.

## Features

- **Simple Commands**: `CREATE PANE LEFT`, `DELETE .1`, `LIST WINDOWS`
- **Plugin Architecture**: Extend ALI with YAML configs - no coding required
- **Smart Expansions**: Automatically transforms commands to correct CLI arguments
- **Validation**: Clear error messages when commands are invalid

## Installation

```bash
uv tool install .
```

### Tmux Integration

Add to your `~/.tmux.conf`:

```bash
# ALI - Action Language Interpreter
# Press C-b a to open ALI command prompt
bind-key a command-prompt -p "ALI> " \
  "run-shell 'TMUX_PANE=#{pane_id} ali \"%%\"'"
```

Then reload tmux config: `tmux source-file ~/.tmux.conf`

## Usage

### CLI Mode
```bash
# Basic commands
ali "CREATE PANE LEFT"
ali "KILL .THIS"            # KILL is alias for DELETE
ali "SWAP .1 WITH .2"
ali "GO :1"                 # Navigate within session
ali "SWITCH practical-dog"  # Switch to different session

# Full tmux target support
ali "GO practical-dog:0.0"  # Go to specific pane in session

# List available commands
ali --list-verbs

# Dry run (see what would execute)
ali --dry-run "CREATE WINDOW"
```

### From Tmux (C-b a)
After setting up tmux integration, press `C-b a` then type:
- `CREATE PANE RIGHT` - Split current pane
- `DELETE .2` - Delete pane 2
- `GO :1` - Go to window 1
- `KILL .THIS` - Kill current pane

## Architecture

ALI uses a vocabulary-driven plugin system where each tool declares what it understands:

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