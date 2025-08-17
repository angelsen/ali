# Development Guide

## REPL-First Development

ALI is designed for rapid REPL-based development. No compile, no restart, just test.

## Quick Start REPL

```python
# Start Python REPL in project root
from pathlib import Path
from src.ali.core import ServiceRegistry, Router

# Load once
registry = ServiceRegistry()
registry.load_plugins(Path('./src/ali/plugins'))
router = Router(registry)

# Test rapidly
router.execute("WIDTH 012")  # Just returns string, no execution
```

## Development Workflow

### 1. Edit YAML → Test Immediately

```python
# Edit plugin.yaml, then:
reload(registry)  # If you add reload helper
router.execute("NEW_COMMAND")  # See result instantly
```

### 2. Test Without Side Effects

```python
# Router ONLY returns strings, never executes
result = router.execute("DELETE .2")
print(result)  # "tmux kill-pane -t .2" - just a string!
```

### 3. Debug Grammar-Based Parsing

```python
# See what parser understood
plugin = registry.get_plugin_for_verb("WIDTH")
state = router._parse("WIDTH", ["012", "AS", "1/2"], plugin)
print(state)  # {'verb': 'WIDTH', 'panes': '012', 'clause': 'AS', 'fraction': '1/2'}
```

### 4. Test Grammar Definitions

```python
# See plugin grammar
tmux = registry.get_plugin_for_verb("SPLIT")
print(tmux.grammar)
# {'direction': {'values': ['left', 'right', ...], 'transform': 'lower'}, ...}
```

## Useful REPL Helpers

```python
# Add to your REPL session
def test(cmd):
    """Quick test helper"""
    result = router.execute(cmd)
    print(f"{cmd:30} → {result}")

def test_many(*commands):
    """Test multiple commands"""
    for cmd in commands:
        test(cmd)

# Usage
test_many("GO .2", "SPLIT", "WIDTH 012")
```

## Testing Scripts

```python
# Test script resolution without execution
from src.ali.scripts import find_script
find_script("tmux", "distribute")  # Path object if found

# Test with dry-run
import subprocess
subprocess.run(["python", "src/ali/plugins/tmux/scripts/distribute.py", 
                "--dimension", "width", "--panes", "012", "--dry-run"])
```

## Debug Techniques

### See Why Commands Don't Match

```python
# Get plugin and state
plugin = registry.get_plugin_for_verb("WIDTH")
state = {"verb": "WIDTH", "panes": "012"}

# Check each command
for cmd in plugin.commands:
    match = cmd.get("match", {})
    if plugin._matches(state, match):
        print(f"✓ Matches: {match}")
    else:
        print(f"✗ No match: {match}")
```

### Trace Service Resolution

```python
# See service chain
cmd = "EDIT @?"
result = router.execute(cmd)
print(f"Command: {cmd}")
print(f"Resolves to: {result}")
# Shows full chain: tmux split | broot | micro
```

## Pro Tips

1. **Keep REPL open** - Load once, test many times
2. **Test strings, not execution** - Router never runs commands
3. **Use test files** - `python test_service_core.py` for interactive mode
4. **Dry-run for safety** - `--dry-run` shows without doing
5. **Print everything** - States, matches, patterns

## Quick Test File

Save as `quicktest.py`:

```python
#!/usr/bin/env python3
from pathlib import Path
from src.ali.core import ServiceRegistry, Router

registry = ServiceRegistry()
registry.load_plugins(Path('./src/ali/plugins'))
router = Router(registry)

# Your test commands
tests = [
    "GO .2",
    "WIDTH 012",
    "EDIT @?",
]

for cmd in tests:
    print(f"{cmd:20} → {router.execute(cmd)}")
```

Run with: `python quicktest.py`

## The Key Insight

**Resolution is separate from execution.** Test command building all day without opening a single tmux pane!