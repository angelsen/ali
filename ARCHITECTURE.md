# ALI Architecture

Action Language Interpreter - compose complex commands from regular phrases.

## Core Flow

```
Input → Parser → Router → Resolver → Output
```

1. **Parser** tokenizes input using plugin grammars
2. **Router** matches patterns to find commands
3. **Resolver** expands templates with services and state
4. **Output** returns resolved command string

## Components

### Registry (`src/ali/core/registry.py`)
- Loads and indexes plugins from YAML files
- Tracks services and their providers
- Supports multiple plugins per verb

### Router (`src/ali/core/router.py`)
- Parses input into tokens
- Matches against command patterns
- Handles cross-plugin grammar resolution
- Expands selectors (e.g., `ed?` → `micro`)

### Resolver (`src/ali/core/resolver.py`)
- AST-based template parser
- Supports conditionals, array lookups, defaults
- Service composition and resolution
- Single-pass template expansion

### Plugin (`src/ali/core/plugin.py`)
- YAML-only configuration
- Provides grammar, commands, services
- Integration support with `--init`
- Selectors for stream/action operations

## Template Engine

### Conditionals
```yaml
exec: "{?target:tmux select-pane -t {target} && }{command}"
# If target exists: "tmux select-pane -t .2 && command"
# If no target: "command"
```

### Array Lookups
```yaml
exec: "{direction[left:-h -b,right:-h,up:-v -b,down:-v,pop:display-popup]}"
# direction="left" → "-h -b"
# direction="pop" → "display-popup"
```

### Service Composition
```yaml
# tmux plugin provides:
services:
  split: "tmux split-window {direction[...]}"
  
# micro plugin uses:
commands:
  - match: {verb: EDIT}
    exec: "{split} 'micro {file}'"  # Resolves to tmux service
```

### Selectors
```yaml
selectors:
  ed?:
    type: stream
    exec: "micro"
    
# Used as: ali ECHO ed?
# Becomes: tmux display-popup ... 'micro | xargs ...'
```

## Plugin Structure

```yaml
name: plugin_name
version: 1.0
description: Brief description
provides:
  capability:
    type: service
    capabilities: [list]
requires: [other_services]
context:
  requires_env: ENV_VAR
metadata:
  environment:
    requires: [ENV_VARS]
    optional: [OPT_VARS]
grammar:
  field: {type: string, pattern: "regex"}
vocabulary:
  verbs: [VERB1, VERB2]
expectations:
  VERB: [field, "optional?", "default?=value"]
inference:
  - when: {conditions}
    transform: {updates}
commands:
  - match: {pattern}
    exec: "template"
selectors:
  name?:
    type: stream|action
    exec: "command"
services:
  service_name: "template"
  _internal: "template"
integration:
  files:
    - source: "file"
      target: "~/.config/..."
  instructions: |
    Setup steps
```

## Service System

Services are reusable command templates that plugins provide and consume:

1. **Public Services** - Available to all plugins
2. **Internal Services** - Prefixed with `_`, plugin-only
3. **Service Resolution** - Services can reference state and other services
4. **Cross-Plugin Usage** - Plugins use services from other plugins

## Grammar System

Grammar definitions parse and validate input:

1. **Field Types** - string, pattern, values, transform
2. **Cross-Plugin Resolution** - Plugins share grammar
3. **Inference Rules** - Transform parsed values
4. **Expectations** - Define verb requirements

## Best Practices

See `src/ali/plugins/llms.txt` for comprehensive plugin development patterns.