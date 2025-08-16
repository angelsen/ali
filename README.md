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
# CLI mode (coming soon)
tal "CREATE PANE LEFT"
tal "LIST SESSIONS"

# Interactive mode (coming soon)
tal  # Opens popup UI
```

## Architecture

TAL uses a plugin system where each tool (tmux, vim, i3, etc.) is defined as a YAML configuration:

```yaml
# plugins/tmux/plugin.yaml
commands:
  - match: {verb: CREATE, object: PANE}
    exec: "tmux split-window {direction}"

expansions:
  direction:
    mappings:
      left: "-h -b"
      right: "-h"
```

## Current Status

Core plugin system is working. Parser and CLI are in development.

## License

MIT