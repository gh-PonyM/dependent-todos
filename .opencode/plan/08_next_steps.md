# Dependent Todos Tool - Next Steps

## Next Steps

1. ✅ Review plan and answer open questions (COMPLETED)
2. ✅ Separate this plan into multiple markdown files with pattern `01_*.md`, `02_*.md`, etc. (COMPLETED)
3. ✅ Implement Phase 1 (core functionality) (COMPLETED)
4. ✅ Implement Phase 2 (dependencies) (COMPLETED)
5. Implement Phase 3 (enhanced UX)
6. Set up comprehensive testing framework (including textual TUI tests)
7. Iterate based on usage and feedback

## Bug Tracking

### TUI Issues

#### ✅ FIXED: Widget initialization missing id parameter
- **File**: `src/dependent_todos/tui.py`
- **Error**: `TaskTable.__init__() got an unexpected keyword argument 'id'`
- **Root Cause**: Custom widget classes (TaskTable, TaskDetails) did not accept **kwargs to pass id and other parameters to parent class
- **Fix**: Added `**kwargs` parameter to `__init__()` methods and passed to `super().__init__()`
- **Lines**: 
  - `TaskTable.__init__()` at line 26
  - `TaskDetails.__init__()` at line 112
- **Status**: Fixed - both classes now accept id parameter

#### Pending Issues
- None currently - waiting for next error report