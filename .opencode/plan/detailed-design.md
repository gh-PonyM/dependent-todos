# Dependent Todos Tool - Detailed Design Plan

## Overview
A command-line task management tool with dependency tracking, implemented as a single Python file with TOML storage.

## Core Requirements (from initial.md)
- Task management with dependency trees
- Interactive task creation with fuzzy search for dependencies
- Single Python file with uv script metadata
- TOML-based storage
- external dependencies: pydantic, click, rich, textual
- Python version compatibility (tomllib support)

---

## Architecture

### Single File Structure
- **File**: `todos.py`
- **Execution**: `python todos.py <command>` or `./todos.py <command>`
- **Storage**: `.todos.toml` location configurable via `TODOS_CONFIG` environment variable or `--config` flag
  - Default: `~/.config/todos/.todos.toml` (XDG Base Directory Specification)
  - Can be overridden per-directory for project-specific task files
  - Click's `get_app_dir()` utility used for cross-platform XDG compliance

### Data Model

#### Stored in TOML (Persistent)
```python
Task:
  - id: str (unique identifier, auto-generated slug from message)
  - message: str (task description)
  - status: str (pending/done - only these two values stored)
  - dependencies: list[str] (list of task IDs)
  - created: datetime (ISO 8601 format)
  - started: datetime | None (when work began on task)
  - completed: datetime | None (when task was marked done)
  - cancelled: bool (whether task is cancelled)
```

#### Computed State (Derived at Runtime)
```python
state: str (computed from stored fields and dependencies)
  - "pending": status == "pending" and started is None
  - "in-progress": status == "pending" and started is not None and completed is None
  - "done": status == "done" and completed is not None
  - "blocked": status == "pending" and any dependency is not done
  - "cancelled": cancelled == True
```

#### ID Generation
- Auto-generated from task message using slugify function
- URL-compatible format (lowercase, hyphens, alphanumeric only)
- Configurable max length (default: 50 characters)
- Validated with Pydantic

---

## Command-Line Interface

### Commands

#### `todos.py add`
Interactive task creation:
1. Prompt for task message
2. Auto-generate slug ID from message (user can override if desired)
3. Show existing task IDs with fuzzy search for dependency selection
4. Allow selecting multiple dependencies interactively
5. Validate for circular dependencies before saving
6. Save to TOML file

**Example flow:**
```
$ python todos.py add
Task message: Implement user authentication
Generated ID: implement-user-authentication (press Enter to accept, or type custom ID)
Dependencies (fuzzy search, press Enter when done):
  > [Type to search existing tasks]
  - setup-database (selected)
  - api-framework (selected)
Task added successfully!
```

#### `todos.py list`
Display all tasks with basic info, showing computed state:
```
ID                              State         Message                      Dependencies
implement-user-authentication   pending       Implement user auth          setup-database, api-framework
setup-database                  done          Setup database               -
api-framework                   done          Setup API framework          -
```

Note: "State" column shows computed state (pending/in-progress/done/blocked/cancelled), not stored status.

#### `todos.py tree [ID]`
Show dependency tree visualization with computed state:
- If ID provided: show tree for that specific task
- If no ID: show all tasks as forest

**Example:**
```
$ python todos.py tree implement-user-authentication
implement-user-authentication: Implement user authentication [pending]
├── setup-database [done]
└── api-framework [done]
     └── install-deps [done]
```

State shown in brackets is the computed state at runtime.

#### `todos.py ready`
Show tasks that are ready to work on (all dependencies completed):
```
Ready to work on:
- auth-001: Implement user authentication
- frontend-setup: Setup frontend framework
```

#### `todos.py done <ID>`
Mark task as complete:
- Validates task exists
- Checks if all dependencies are done
- If dependencies not done: shows warning and asks for confirmation
- Sets status to 'done' and records completion timestamp
- Shows which tasks are now unblocked (no longer blocked)

#### `todos.py remove <ID>`
Remove a task:
- Warns if other tasks depend on it
- Requires confirmation if dependencies exist
- Removes from TOML file

#### `todos.py show <ID>`
Show detailed task information:
```
ID: implement-user-authentication
Message: Implement user authentication
State: pending (computed)
Status: pending (stored)
Created: 2026-01-10 14:30:00
Started: -
Completed: -
Cancelled: false
Dependencies: setup-database, api-framework
Blocks: user-profile, admin-panel
```

#### `todos.py order`
Show topological execution order:
```
Execution order:
1. install-deps
2. api-framework
3. setup-database
4. auth-001
5. user-profile
6. admin-panel
```

---

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

---

## Implementation Phases

### Phase 1: Core Functionality
- [ ] Add a test setup (also a single file, using pytest)
- [ ] Basic TOML read/write
- [ ] Task data model
- [ ] `add` command (without fuzzy search)
- [ ] `list` command
- [ ] `done` command
- [ ] `remove` command

### Phase 2: Dependencies
- [ ] Dependency tracking in data model
- [ ] Circular dependency detection
- [ ] `tree` command
- [ ] `ready` command
- [ ] `order` command (topological sort)

### Phase 3: Enhanced UX
- [ ] Fuzzy search for dependencies
- [ ] Interactive selection menu
- [ ] Better formatting and colors
- [ ] `show` command with full details
- [ ] A tui with textual

### Phase 4: Polish
- [ ] Error handling and validation
- [ ] Help text and documentation
- [ ] Edge case handling
- [ ] Tests (if desired)

---

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

---

## Implementation Notes

### Configuration Management
- Use Click's `get_app_dir()` for XDG compliance
- Support `TODOS_CONFIG` environment variable
- Support `--config` CLI flag (highest priority)
- Fallback chain: CLI flag → env var → default XDG path

### Slug Generation
- Implement `slugify()` function using regex
- Handle Unicode characters appropriately
- Ensure uniqueness (warn if slug already exists)
- Allow manual override during task creation

### State Computation
- Implement `compute_state()` method on Task model
- Called when displaying tasks (list, tree, show, ready)
- Never stored in TOML (always derived)
- Efficient: O(1) for most states, O(n) for blocked check

### Validation
- Use Pydantic v2 for all data models
- Validate circular dependencies before saving
- Warn about orphan dependencies (deps that don't exist)
- Validate slug format and uniqueness

## Next Steps

1. ✅ Review plan and answer open questions (COMPLETED)
2. ✅ Separate this plan into multiple markdown files with pattern `01_*.md`, `02_*.md`, etc. (COMPLETED)
3. ✅ Implement Phase 1 (core functionality) (COMPLETED)
4. Implement Phase 2 (dependencies)
5. Iterate based on usage and feedback
