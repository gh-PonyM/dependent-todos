# Plan: View Dependency Tree as Widget

## Overview
Implement a toggleable sidebar displaying the dependency tree for the currently selected task using Textual's native Tree widget. Users can press 't' to show/hide the sidebar.

## Current State
- `DependencyTree` class exists but builds full tree from root tasks
- Not integrated into the UI
- No toggle mechanism

## Implementation Steps

### 1. Modify DependencyTree Class
- Add optional `root_task_id` parameter to `DependencyTree.__init__`
- If provided, build tree starting from that task's dependencies
- If not provided, fallback to current behavior (all root tasks)

### 2. Add Toggle Binding
- Add `("t", "toggle_tree", "Toggle tree")` to `DependentTodosApp.BINDINGS`
- Implement `action_toggle_tree` method to show/hide sidebar

### 3. Update UI Layout
- Modify `compose` method to include sidebar container:
  ```python
  with Horizontal():
      with Container(id="sidebar", classes="hidden"):  # Initially hidden
          yield DependencyTree(self.tasks, root_task_id=self.current_task_id, id="dep-tree")
      with Container(id="main-content"):
          # existing content
  ```
- Add CSS to hide/show sidebar (e.g., `.hidden { display: none; }`)

### 4. Implement Toggle Logic
- `action_toggle_tree`:
  - If no task selected, notify user or show full tree
  - Toggle sidebar visibility
  - Refresh tree with current task
- Update tree when task selection changes

### 5. Handle Edge Cases
- No task selected: Disable toggle or show full tree
- Task with no dependencies: Show single node
- Cyclic dependencies: Handle gracefully (current code has fallback)

### 6. Update on Changes
- Refresh tree in `_save_and_refresh` and when selection changes
- Ensure tree reflects current task state

## Usage
- Select a task in the table
- Press 't' to open dependency tree sidebar
- Press 't' again to close sidebar
- Tree shows selected task as root with dependencies as children