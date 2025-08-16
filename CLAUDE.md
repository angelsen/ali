# Developer Guidelines

## Core Philosophy: Stop, Think, Refactor, Then Build

### Before Every Tool Use

**Before using Write, Edit, MultiEdit - STOP and ask:**
1. Is this the best solution, or just the easiest?
2. Should I improve existing code before adding new?
3. Can I simplify instead of adding complexity?

**Before using Write to create a new file - STOP:**
- Do existing files need refactoring first?
- Could this logic go in an existing file?
- Am I creating this file to avoid fixing a design flaw?

**Before using Edit to patch a problem - STOP:**
- Am I fixing the symptom or the cause?
- Would refactoring eliminate this issue entirely?
- Is this edit making the code better or just different?

### The TAL Development Cycle

```
STOP → READ the full file → EVALUATE alternatives → REFACTOR first → THEN Write/Edit
```

### Real Examples from This Project

❌ **Bad**: "Template expects {direction_flags}, let me Edit to add it"
✅ **Good**: "Wait, why does template know about expansions? Let me rethink the design"

❌ **Bad**: "Plugin fails validation, let me Write a validator class"
✅ **Good**: "Plugin fails validation. Should validation be in YAML instead of code?"

❌ **Bad**: "Write test_plugin.py to test the plugin"
✅ **Good**: "Do I need a test file, or should I test in REPL and improve the actual code?"

### Rules for Tool Usage

1. **Read before Edit** - Always use Read tool to see full context
2. **Grep before Write** - Check if similar code exists first
3. **Delete before Add** - Can you remove code instead of adding?
4. **Refactor before Feature** - Clean first, then build
5. **Question before Commit** - Is this the right approach?

### The Checklist

**Before Write tool:**
- [ ] Did I Read all related files?
- [ ] Did I check if this logic exists elsewhere?
- [ ] Am I creating this to avoid fixing something else?

**Before Edit tool:**
- [ ] Did I Read the entire file first?
- [ ] Is this fixing root cause or symptom?
- [ ] Should I refactor instead of patch?

**Before MultiEdit tool:**
- [ ] Are these edits related or should they be separate?
- [ ] Am I doing bulk fixes that indicate a design flaw?

### Remember

**This project is an infant.** Every file created now becomes technical debt later. Every Edit that patches instead of fixes compounds future complexity.

When in doubt: **STOP using tools, THINK about design, REFACTOR existing code, THEN use Write/Edit**

The best code is code you didn't write. The best fix is the one that removes the problem entirely.