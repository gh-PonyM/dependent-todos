# Dependent Todos Tool - Design Decisions

## Design Decisions (Resolved from Open Questions)

### 1. Storage Location
**Decision**: Configurable via environment variable with XDG Base Directory default
- Environment variable: `TODOS_CONFIG` (path to specific `.todos.toml` file)
- CLI flag: `--config` to override for single command
- Default: `~/.config/todos/.todos.toml` (using Click's `get_app_dir()`)
- Use case: Project-specific files can be stored in repo root, global tasks in home directory
- Implementation: User sets `export TODOS_CONFIG=/path/to/project/.todos.toml` or uses `--config` flag

### 2. Task ID Format
**Decision**: Auto-generated slug from task message
- Slugify function converts message to URL-compatible format
- Format: lowercase, hyphens for spaces, alphanumeric + hyphens only
- Max length: 50 characters (configurable)
- User can override during task creation
- Validation: Pydantic model ensures slug format compliance
- Example: "Implement user authentication" → "implement-user-authentication"

### 3. Status vs State Model
**Decision**: Separate stored status from computed state
- **Stored in TOML** (minimal):
  - `status`: "pending" or "done" only
  - `started`: timestamp when work began (empty if not started)
  - `completed`: timestamp when marked done (empty if not done)
  - `cancelled`: boolean flag
- **Computed at runtime** (derived state):
  - "pending": status="pending" AND not started AND not cancelled
  - "in-progress": status="pending" AND started AND not completed AND not cancelled
  - "done": status="done" AND completed AND not cancelled
  - "blocked": status="pending" AND any dependency not done AND not cancelled
  - "cancelled": cancelled=true
- Rationale: Minimal storage, rich runtime state, no redundancy

### 4. Dependency Strictness
**Decision**: Warn but allow completing tasks with incomplete dependencies
- When marking task done: check if all dependencies are done
- If not: show warning listing incomplete dependencies
- Ask for confirmation: "Continue anyway? (y/n)"
- Allow user to proceed if intentional
- Rationale: Flexibility for real-world scenarios where order might change

### 5. Multi-Project Support
**Decision**: Per-file configuration with environment variable override
- Default: `~/.config/todos/.todos.toml` (global tasks)
- Per-project: Set `TODOS_CONFIG` to project-specific path
- Per-command: Use `--config` flag to override
- Typical workflow:
  - Global tasks: `export TODOS_CONFIG=~/.config/todos/.todos.toml`
  - Project tasks: `export TODOS_CONFIG=./.todos.toml` (in repo root)
- Rationale: Flexible, supports both global and project-scoped workflows

### 6. Export/Import
**Decision**: Implement markdown report exporter in Phase 3
- Command: `todos.py export [--format markdown|json] [--output file.md]`
- Markdown format: Human-readable report with task tree and status
- JSON format: Machine-readable for integration with other tools
- Default: Print to stdout if no output file specified
- Future: Import from markdown/JSON in later phases

### 7. Task Editing
**Decision**: Manual TOML editing for CLI, TUI support in Phase 3
- CLI: Users edit `.todos.toml` directly with text editor
- Rationale: Keeps CLI simple, TOML is human-readable
- TUI (Phase 3): Full `edit` command with interactive interface
- Future: `todos.py edit <ID>` command in TUI version

### 8. Task Priorities
**Decision**: Deferred to Phase 4 (Polish)
- Not included in initial implementation
- Can be added as optional field: `priority: "high" | "medium" | "low"`
- Would affect `ready` command sorting
- Consider for future enhancement based on user feedback