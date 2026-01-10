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
- **Storage**: `.todos.toml` in current directory

### Data Model
```python
Task:
  - id: str (unique identifier)
  - message: str (task description)
  - status: str (pending/done/blocked)
  - dependencies: list[str] (list of task IDs)
  - created: datetime
  - completed: datetime | None
```

---

## Command-Line Interface

### Commands

#### `todos.py add`
Interactive task creation:
1. Prompt for task message
2. Prompt for task ID (suggest auto-generated if empty)
3. Show existing task IDs with fuzzy search
4. Allow selecting multiple dependencies
5. Save to TOML file

**Example flow:**
```
$ python todos.py add
Task message: Implement user authentication
Task ID (leave empty for auto): auth-001
Dependencies (fuzzy search, press Enter when done):
  > [Type to search existing tasks]
  - setup-database (selected)
  - api-framework (selected)
Task added successfully!
```

#### `todos.py list`
Display all tasks with basic info:
```
ID            Status    Message                      Dependencies
auth-001      pending   Implement user auth          setup-database, api-framework
setup-db      done      Setup database               -
api-fw        done      Setup API framework          -
```

#### `todos.py tree [ID]`
Show dependency tree visualization:
- If ID provided: show tree for that specific task
- If no ID: show all tasks as forest

**Example:**
```
$ python todos.py tree auth-001
auth-001: Implement user authentication [pending]
├── setup-database [done]
└── api-framework [done]
    └── install-deps [done]
```

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
- Sets status to 'done'
- Records completion timestamp
- Shows which tasks are now unblocked

#### `todos.py remove <ID>`
Remove a task:
- Warns if other tasks depend on it
- Requires confirmation if dependencies exist
- Removes from TOML file

#### `todos.py show <ID>`
Show detailed task information:
```
ID: auth-001
Message: Implement user authentication
Status: pending
Created: 2026-01-10 14:30:00
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
[tasks.auth-001]
message = "Implement user authentication"
status = "pending"
dependencies = ["setup-database", "api-framework"]
created = "2026-01-10T14:30:00"
started = ""
completed = ""

[tasks.setup-database]
message = "Setup database"
status = "done"
dependencies = []
started = ""
created = "2026-01-10T10:00:00"
completed = "2026-01-10T12:00:00"
```

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

## Open Questions

1. **Storage location**: Should `.todos.toml` be in current directory, or support project-specific locations?
    - should be configurable via env variable. Default to xdg-home. the click tool has the application dir, we can use this

2. **Task ID format**: Auto-generate IDs (UUID, incremental) or always require manual entry?
   - auto-generate, but I want to use a slug value and have a slugify_function, that would be url compatible for example
   - derive the slug from the text, define slug max length
   - slug can be well validated with pydantic

3. **Status values**: Just `pending`/`done`, or add `in-progress`, `blocked`, `cancelled`?
   - blocked as an attribute makes sense, but it is dynamic based on other tasks, so we do not want to store it inside the config
   - I added an attribute `started` to tell when we started the task
   - `cancelled` is also a good state
   - Keep the toml config status separated from the attribute `state`
     - In progress is when the task has a started value but not `completed`
     - blocked is dynamic, etc.
     - only cancelled (should be a boolean) in the task config to write to the toml, but not the other states that are deferred attributes

4. **Dependency strictness**: Should completing a task require all dependencies to be done first?
   - Show some sort of warning and ask for confirmation, but should be possible 

5. **Multi-project support**: Single global file or per-directory files?
   - the env / --cfg flag specifies which toml file should be used
   - The tool is meant to work with like such a config file inside a repo. Otherwise the user should set his global env var to his global task config

6. **Export/Import**: Should we support exporting to other formats (JSON, Markdown)?
    - Yes, I want a markdown report exporter

7. **Task editing**: Should we add an `edit` command to modify existing tasks?
    - not for the cli, can be done in the config itself
    - but for the tui final version

8. **Task priorities**: Add priority levels (high/medium/low)?

---

## Next Steps

1. Review this plan and answer open questions
2. Separate out this plan into multiple markdown file with file naming pattern `01_task1.md`, `02_basic_toml_read_write.md`
3. Implement Phase 1 (core functionality)
4. Iterate based on usage and feedback
