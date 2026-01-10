# Dependent Todos Tool - Implementation Notes

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