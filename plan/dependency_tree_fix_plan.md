# Plan to Fix Dependency Tree Sidebar Issue

## Problem
The dependency tree in the sidebar is not displayed when toggling it on. Only a notification "Dependency tree shown" appears, but the tree itself remains invisible.

## Root Cause Analysis
- The `DependencyTree` widget inherits from Textual's `Tree` widget.
- When toggling the tree on, the code calls `tree._build_tree()` to rebuild the tree structure.
- However, after rebuilding, the widget is not refreshed, so the UI doesn't update to show the new tree content.
- Textual widgets need to call `refresh()` after programmatic changes to update the display.

## Solution
Add `tree.refresh()` calls after `tree._build_tree()` in all places where the tree is rebuilt:

1. In `action_toggle_tree()` method
2. In `_save_and_refresh()` method  
3. In `on_data_table_row_selected()` method

## Implementation Steps
1. Modify `tui.py` to add `tree.refresh()` after each `tree._build_tree()` call
2. Run tests to ensure no regressions
3. Manually verify the fix works by toggling the tree
4. Commit the changes

## Testing
- Run `pytest tests/test_tui.py` to ensure existing functionality still works
- Test the toggle tree functionality manually to confirm the tree now displays

## Files to Modify
- `src/dependent_todos/tui.py`