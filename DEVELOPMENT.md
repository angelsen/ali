# Development

## Testing Approaches

### CLI Testing (Primary)
Since ALI outputs commands without executing, test directly:

```bash
# Test command resolution
ali "SPLIT right"           # → tmux split-window -h
ali "EDIT test.py left"     # → tmux split-window -h -b 'micro test.py'
ali "WIDTH 012 AS 1/2"      # → python3 /path/to/distribute.py ...

# Verify clean output
ali "SPLIT right" | cat      # Ensure no extra output
ali "SPLIT right" | bash     # Execute if desired
```

### REPL Testing (Debugging)
For low-level debugging without full pipeline:

```python
from pathlib import Path
from src.ali.core import ServiceRegistry, Router

registry = ServiceRegistry()
registry.load_plugins(Path('./src/ali/plugins'))
router = Router(registry)

# Debug internals
result = router.execute("SPLIT right")
print(result)              # See output
print(router.last_state)   # Inspect parsing state
```

### Quick Reload
```python
# After editing plugin.yaml:
registry = ServiceRegistry()
registry.load_plugins(Path('./src/ali/plugins'))
router = Router(registry)
```

### Debug Parsing
```python
# Check parsed state
plugins = registry.get_plugins_for_verb("WIDTH")
if plugins:
    from src.ali.core.resolver import collect_selectors
    state = router._parse("WIDTH", ["012"], plugins[0], collect_selectors(registry))
    print(state)
```

## Scripts

Complex operations use Python scripts:

```bash
# Test script directly
python src/ali/plugins/tmux/scripts/distribute.py --panes 012

# Through ALI
ali "WIDTH 012" | bash
```

## Key Point

ALI outputs commands for piping - test with `ali` directly, use REPL only for debugging internals.