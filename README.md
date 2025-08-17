# ALI - Action Language Interpreter

Natural language commands for your terminal tools. Type what you think, ALI figures out the rest.

## Quick Start

```bash
# Install
uv tool install .

# Add to tmux (~/.tmux.conf)
bind-key a command-prompt -p "ALI> " \
  "run-shell 'TMUX_PANE=#{pane_id} ali \"%%\"'"

# Use (press C-b a in tmux)
ALI> GO .2                # Go to pane 2
ALI> SPLIT left           # Split current pane left
ALI> WIDTH 012            # Make panes 0,1,2 equal width
ALI> WIDTH 012 AS 1/2     # Make them half window width
ALI> EDIT file.py         # Open file in editor
ALI> BROWSE               # Open file browser
```

## How It Works

Plugins provide services, ALI chains them together:

```
EDIT @?  →  micro needs file_selector
            →  broot provides that, needs pane
               →  tmux provides that
                  →  Execute: tmux split | broot | micro
```

## Architecture

```
src/ali/
├── core/           # Service discovery & routing
├── plugins/        # Pure YAML + optional scripts
│   ├── tmux/       # Pane/window management
│   ├── micro/      # Text editor
│   └── broot/      # File browser
└── cli.py          # Entry point
```

Plugins are data (YAML), not code. Complex operations use scripts.

## Extending

Add a plugin by creating `plugin.yaml`:

```yaml
name: vim
provides: [text_editor]
requires: [pane]

vocabulary:
  verbs: [EDIT, VIEW]

commands:
  - match: {verb: EDIT, file: present}
    exec: "vim {file}"
```

## Philosophy

- Commands should be what you'd naturally type
- Plugins don't know about each other
- Data-driven > code
- Explicit > magic

MIT License