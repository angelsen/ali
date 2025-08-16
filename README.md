# ALI - Action Language Interpreter

Your command interpreter that speaks every tool's language. Write intuitive commands like `CREATE PANE LEFT` instead of memorizing complex keybindings.

## Features

- **Natural Commands**: `CREATE PANE LEFT`, `DELETE .1`, `GO :2`
- **Visual Selectors**: `GO .?` shows panes, press number to select
- **Smart Inference**: `GO ?` knows you mean pane, `SWITCH ?` means session
- **Command Aliases**: Use `NEW` or `n` for CREATE, `d` for DELETE
- **Plugin Architecture**: Extend ALI with YAML configs - no coding required
- **Data-Driven**: All parsing rules defined in YAML, zero hardcoded logic
- **Context Aware**: Commands adapt based on environment (tmux, vim, etc.)
- **Helpful Errors**: Clear messages when commands are invalid

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
ali "CREATE PANE LEFT"      # or "NEW PANE LEFT" or "n PANE LEFT"
ali "DELETE .2"             # or "d .2"
ali "GO :1"                 # or "g :1"
ali "SWAP .1 WITH .2"       # Swap specific panes

# Visual selectors
ali "GO .?"                 # Shows pane numbers, press to select
ali "DELETE .?"             # Visual delete
ali "SWAP . WITH .?"        # Swap current with visual selection
ali "SWITCH ?"              # Visual session switcher

# Smart inference
ali "GO ?"                  # Infers pane selector
ali "DELETE ."              # Delete current pane

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

ALI uses a data-driven plugin system where everything is configured in YAML:

```yaml
# plugins/tmux/plugin.yaml
vocabulary:
  verbs: [CREATE, DELETE, GO, SWAP]
  verb_aliases: {NEW: CREATE, n: CREATE, d: DELETE}
  objects: [PANE, WINDOW, SESSION]

parsing:
  token_rules:
    - match: {position: 0, in_set: objects}
      action: set
      field: object

inference:
  rules:
    - when: {verb: GO, target: "^\\?$", object: null}
      set: {object: PANE}
      transform: {target: ".?"}

commands:
  - match: {verb: CREATE, object: PANE}
    exec: "tmux split-window {direction} {target_flag}"
```

Key components:
- **Unified Rules Engine**: Handles parsing, inference, validation, and expansion
- **Ultra-Dumb Parser**: 37 lines using shlex, zero domain knowledge
- **Smart Inference**: Context-aware object detection and transformations
- **Plugin Router**: Fast verb-based routing with context disambiguation
- **Data-Driven**: All logic defined in YAML, no hardcoded rules

## Current Status

✅ **Working:**
- Full tmux plugin with visual selectors
- Smart inference and context-aware parsing
- Command aliases and single-letter shortforms
- Data-driven parsing via YAML rules
- Unified rules engine for all processing
- Proper empty target handling
- Helpful validation and error messages

🚧 **In Progress:**
- Interactive UI (tmux-popup)
- Additional plugins (vim, i3, browser)

## License

MIT