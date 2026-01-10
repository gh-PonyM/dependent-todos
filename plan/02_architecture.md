# Dependent Todos Tool - Architecture

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