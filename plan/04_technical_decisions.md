# Dependent Todos Tool - Technical Decisions

## Technical Decisions

### Python Version Support

**Option A: Python 3.11+ only (Recommended)**
- Use built-in `tomllib` for reading
- Use `tomli_w` or manual TOML writing for saving
- Simpler, modern approach

**Option B: Python 3.7+ support**
- Conditional import: try `tomllib`, fallback to `tomli`
- Add `tomli` to uv dependencies for older versions
- Broader compatibility

**Recommendation**: Start with Option A (3.11+), add backward compatibility if needed.

**Decision**: Use python 3.11+ since uv can install python's very easily

### Fuzzy Search Implementation

**Option A: Simple substring matching (No dependencies)**
- Filter tasks by substring in ID or message
- Good enough for most use cases
- Zero dependencies

**Option B: Interactive selection with simple-term-menu**
- Add `simple-term-menu` as dependency
- Better UX with arrow key navigation
- Minimal dependency footprint

**Option C: External fzf integration**
- Shell out to `fzf` if available
- Fallback to Option A if not installed
- Best UX but external dependency

**Recommendation**: Option B for balance of UX and simplicity.

### TOML Storage Format

```toml
[tasks.implement-user-authentication]
message = "Implement user authentication"
status = "pending"
dependencies = ["setup-database", "api-framework"]
created = "2026-01-10T14:30:00"
started = ""
completed = ""
cancelled = false

[tasks.setup-database]
message = "Setup database"
status = "done"
dependencies = []
created = "2026-01-10T10:00:00"
started = "2026-01-10T10:30:00"
completed = "2026-01-10T12:00:00"
cancelled = false
```

**Notes:**
- `status`: Only stores "pending" or "done" (minimal state)
- `started`: ISO 8601 timestamp when work began (empty string if not started)
- `completed`: ISO 8601 timestamp when marked done (empty string if not done)
- `cancelled`: Boolean flag for cancelled tasks
- Computed `state` is derived from these fields at runtime:
  - pending: status="pending" AND started="" AND cancelled=false
  - in-progress: status="pending" AND started!="" AND completed="" AND cancelled=false
  - done: status="done" AND completed!="" AND cancelled=false
  - blocked: status="pending" AND any dependency not done AND cancelled=false
  - cancelled: cancelled=true

### Dependency Validation

**Features to implement:**
1. **Circular dependency detection**: Prevent cycles during add/edit
2. **Orphan detection**: Warn about dependencies that don't exist
3. **Completion validation**: Optionally prevent marking done if deps not complete
4. **Cascade operations**: Option to mark all dependencies done when marking task done