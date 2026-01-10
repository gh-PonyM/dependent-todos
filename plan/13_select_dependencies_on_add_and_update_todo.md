# feature: add select fields for update and add todo for dependencies

- as in the cli, we want to define the dependent tasks
- depends on and depending on
- use select field widgets with multi selected (exclude the own id of course)
- write tests for the update and add workflow of the screens

## Analysis

### Current Code Structure
- **AddTaskModal**: Currently has Input (disabled) for task ID and TextArea for message. Creates task with empty dependencies.
- **UpdateTaskModal**: Currently has Static for task ID and TextArea for message. Only updates message, ignores dependencies.
- **Task Model**: Has `dependencies: list[str]` field for task IDs this task depends on.
- **Dependencies Module**: Has `detect_circular_dependencies()` and `select_dependencies_interactive()` for CLI.

### UI Design
- Use Textual `SelectionList` widget for multi-select dependency selection
- **AddTaskModal**:
  - Task ID (auto-generated, disabled Input)
  - Message (TextArea)
  - Depends on (SelectionList multi-select, excludes done tasks)
- **UpdateTaskModal**:
  - Task ID (read-only Static)
  - Message (TextArea)
  - Depends on (SelectionList multi-select, pre-selects current dependencies, excludes done tasks and self)
  - Depending on (read-only list of tasks that depend on this task)

### Implementation Steps

1. **Import SelectionList and Selection** in tui.py
2. **Update AddTaskModal**:
   - Add SelectionList for "Depends on" in get_content()
   - Populate options with available tasks (not done)
   - In on_ok_pressed(), get selected dependencies and validate for circular deps
3. **Update UpdateTaskModal**:
   - Add SelectionList for "Depends on" with current deps pre-selected
   - Add read-only display for "Depending on"
   - In on_ok_pressed(), get selected dependencies and validate
4. **Add Validation**:
   - Use detect_circular_dependencies() before saving
   - Show error notification if circular deps detected
5. **Write Tests**:
   - Test AddTaskModal with dependency selection
   - Test UpdateTaskModal with dependency changes
   - Test circular dependency validation
   - Test pre-selection of current dependencies

## TODO

- [x] write a plan and analyze code
- [x] update this file here with the plan
- [ ] commit this file as the basis for implementation
- [ ] start implementing
