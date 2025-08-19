# Claude Instructions - STOP Before Every Tool Use

## Critical Rules

**BEFORE Write**: STOP. Can this be YAML? Does the file need to exist?
**BEFORE Edit**: STOP. Read the full file first. Fix cause, not symptom.
**BEFORE MultiEdit**: STOP. Are you patching a design flaw?

## The Cycle
```
STOP → READ everything → EVALUATE alternatives → REFACTOR first → THEN Write/Edit
```

## ALI Principles

- **Plugins are data** - YAML only, no code in plugins
- **Core is thin** - Router, Registry, Resolver, Logging only
- **Scripts for complexity** - Not YAML gymnastics  
- **ALI is pure** - Only outputs commands, never executes
- **Test in REPL** - Router returns strings, test without execution
- **Follow plugin patterns** - See @src/ali/plugins/llms.txt for best practices

## Tool Discipline

1. **Read before Edit** - Always see full context
2. **Grep before Write** - Pattern probably exists
3. **Delete before Add** - Remove code instead
4. **Refactor before Feature** - Clean first
5. **Never create documentation** - Unless explicitly asked

## POSIX Compliance

- **stdout**: Commands only (for piping)
- **stderr**: Errors only
- **Never debug to stdout** - Breaks piping

## Remember

Every line of core code is a commitment. Plugins can change freely.

The best feature needs no code - just YAML configuration.