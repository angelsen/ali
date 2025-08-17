# Developer Guidelines

## Core Philosophy: Stop, Think, Refactor, Then Build

### Before Every Tool Use

**Before using Write, Edit, MultiEdit - STOP and ask:**
1. Is this the best solution, or just the easiest?
2. Should I improve existing code before adding new?
3. Can I simplify instead of adding complexity?

**Before using Write to create a new file - STOP:**
- Do existing files need refactoring first?
- Could this logic go in an existing module?
- Am I creating this file to avoid fixing a design flaw?

**Before using Edit to patch a problem - STOP:**
- Am I fixing the symptom or the cause?
- Would refactoring eliminate this issue entirely?
- Is this edit making the code better or just different?

### The ALI Development Cycle

```
STOP → READ the full file → EVALUATE alternatives → REFACTOR first → THEN Write/Edit
```

### Real Examples from ALI

❌ **Bad**: "ServiceResolver needs complex logic, let me add more methods"
✅ **Good**: "Wait, do we even need ServiceResolver? Just use functions in resolver.py"

❌ **Bad**: "Script fails, let me add error handling everywhere"
✅ **Good**: "Scripts should be simple. Move complexity to plugins or core"

❌ **Bad**: "Router needs to know about targets, directions, objects"
✅ **Good**: "Plugins define their grammar. Router just applies it"

### ALI-Specific Principles

1. **Plugins are data, not code** - If you're writing plugin code, stop and use YAML
2. **Grammar is declarative** - Plugins define parsing rules, not procedural code
3. **Template composition** - Use {split_{direction}} not 6 separate patterns
4. **Scripts for complexity** - Complex logic goes in scripts, not YAML gymnastics
5. **Test in REPL first** - Router returns strings. Test without execution

### Rules for Tool Usage

1. **Read before Edit** - Always use Read tool to see full context
2. **Grep before Write** - Check if similar patterns exist first
3. **Delete before Add** - Can you remove code instead of adding?
4. **Refactor before Feature** - Clean first, then build
5. **Test before Commit** - Does it work in REPL?

### The Checklist

**Before Write tool:**
- [ ] Did I Read all related files?
- [ ] Did I check if this pattern exists in other plugins?
- [ ] Could this be data (YAML) instead of code?

**Before Edit tool:**
- [ ] Did I Read the entire file first?
- [ ] Is this fixing root cause or symptom?
- [ ] Would moving this to a plugin/script be cleaner?

**Before MultiEdit tool:**
- [ ] Are these edits related or should they be separate?
- [ ] Am I doing bulk fixes that indicate a design flaw?

### ALI Architecture Reminders

**Core is thin** - Router, Registry, Resolver. That's it.
**Plugins are dumb** - Just YAML configuration files.
**Scripts are simple** - One job, clear arguments, no magic.

### Remember

**Every line of core code is a commitment.** Plugins can change freely, but core changes affect everything.

When in doubt: **STOP using tools, TEST in REPL, REFACTOR to plugins/scripts, THEN use Write/Edit**

The best feature is one that needs no code - just YAML configuration.