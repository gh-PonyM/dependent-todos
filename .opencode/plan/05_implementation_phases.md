# Dependent Todos Tool - Implementation Phases

## Implementation Phases

### Phase 1: Core Functionality
- [x] Add a test setup (also a single file, using pytest)
- [x] Basic TOML read/write
- [x] Task data model
- [x] `add` command (without fuzzy search)
- [x] `list` command
- [x] `done` command
- [x] `remove` command

### Phase 2: Dependencies
- [x] Dependency tracking in data model
- [x] Circular dependency detection
- [x] `tree` command
- [x] `ready` command
- [x] `order` command (topological sort)

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