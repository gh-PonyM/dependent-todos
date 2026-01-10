### Key Findings from Code Analysis
- **Modal Select Fields Issue**: In `UpdateTaskModal` and `AddTaskModal`, the "depends on" `SelectionList` populates options correctly (excluding self and done tasks), but the "depending on" field is read-only (a `Static` widget showing dependents). The user reports "Depending on is None, no options can be selected" – this likely means the "depends on" list appears empty or incorrect due to task filtering or state computation. The `_get_dependency_options` method filters tasks by status, but if no tasks are available (e.g., all are done or self-referencing), the list will be empty. We need to verify task states and ensure options are populated dynamically.
- **Event Handling Issue**: The app handles table row selection (`on_data_table_row_selected`) and refreshes the tree if visible, but there's no handler for tree node selection (e.g., `Tree.NodeSelected`). When a user selects a task in the tree, it should update `current_task_id`, refresh the details pane, and potentially re-center the tree on that task. Event propagation follows Textual's model (child events bubble to parents), so the app can catch tree events.
- **Tab Switch Issue**: `_update_filter_from_tab` updates the table filter but doesn't clear or reset the dependency tree. On tab switches, the tree should be cleared (e.g., remove children) to avoid showing stale dependencies for the new filter.
- **Testing and Snapshots**: Existing tests cover basic navigation and modal interactions but lack coverage for tree updates, tab switches, and modal snapshots. New tests should verify behavior, and snapshots should capture modal states (e.g., add/update/delete modals with populated fields).

### Proposed Plan
I'll execute this in phases, starting with fixes, then testing. Each phase includes specific changes, rationale, and verification steps. I'll use the `todowrite` tool to track progress.

1. **Fix Modal Select Fields (Priority: High)**  
   - **Objective**: Ensure "depends on" options are correctly populated and visible. Debug why "depending on" appears as "None" (likely due to no dependents or rendering issues).  
   - **Changes**:
     - In `UpdateTaskModal._get_dependency_options`, add logging or assertions to verify task filtering (e.g., ensure non-done tasks exist).
     - In `UpdateTaskModal._get_depending_on_text`, handle cases where no dependents exist more gracefully (currently returns "None" if empty, but confirm it's not a rendering bug).
     - Test with sample tasks to ensure options appear (e.g., add tasks with dependencies in tests).
   - **Rationale**: This directly addresses Issue 1. Modal fields must work before event handling.
   - **Verification**: Run existing tests; manually test modals with tasks having dependencies.

2. **Implement Tree Selection Event Handling (Priority: High)**  
   - **Objective**: Add handler for tree node selection to update the current task and refresh UI components.  
   - **Changes**:
     - Add `on_tree_node_selected` method in `DependentTodosApp` to catch `Tree.NodeSelected` events from `#dep-tree`.
     - In the handler, extract the selected task ID from the node, update `current_task_id`, refresh details pane, and rebuild the tree centered on the selected task.
     - Ensure event bubbling works (tree events reach the app).
   - **Rationale**: Addresses Issue 2. Tree selection should mirror table selection for consistency.
   - **Verification**: Test by selecting tasks in the tree and confirming details update.

3. **Clear Dependency Tree on Tab Switch (Priority: Medium)**  
   - **Objective**: Reset the tree when switching tabs to avoid showing irrelevant dependencies.  
   - **Changes**:
     - Modify `_update_filter_from_tab` to clear the tree (e.g., `tree.root.remove_children()`) if the sidebar is visible.
   - **Rationale**: Addresses Issue 3. Prevents stale UI state.
   - **Verification**: Switch tabs and confirm tree clears.

4. **Write Tests for New Behavior (Priority: High)**  
   - **Objective**: Add tests for tree updates, tab switches, and modal field population.  IMMEDIATELY DO AFTER IMPLEMENTATION
   - **Changes**:
     - In `tests/test_tui.py`, add async tests:
       - Test tree selection updates current task and details.
       - Test tab switch clears tree.
       - Test modal select fields populate with expected options.
     - Use `pilot` to simulate interactions (e.g., press 't' to toggle tree, select nodes).
   - **Rationale**: Ensures fixes work and prevents regressions.
   - **Verification**: Run tests with `pytest`; confirm failures before fixes and passes after.

5. **Add Snapshots for Modals (Priority: Low)**  
   - **Objective**: Capture snapshots of add/update/delete modals with populated fields.  
   - **Changes**:
     - In `tests/test_tui.py`, add snapshot tests using `snap_compare` for each modal (e.g., open modal, populate fields, capture).
     - Use `run_before` to set up tasks and open modals.
   - **Rationale**: Provides visual regression testing for UI.
   - **Verification**: Run snapshot tests and review generated images.

### Execution Order Rationale
- Start with modal fixes (Phase 1) as they're foundational and isolated.
- Then event handling (Phase 2) and tab clearing (Phase 3), as they depend on UI state.
- End with testing (Phases 4-5) to validate everything.
- Total estimated time: 4-6 hours, assuming no major blockers.

### Questions for Clarification
- For Issue 1: Can you provide a specific example of tasks where "depends on" appears empty? Are there tasks with "pending" status that should be options?
- For Issue 2: Should selecting a tree node also update the table selection (e.g., highlight the row)?
- Any preferences on test framework extensions or snapshot tool specifics?

Once you approve this plan, I'll proceed with implementation. If you'd like adjustments, let me know!