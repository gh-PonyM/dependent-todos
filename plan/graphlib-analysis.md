# GraphLib Analysis - Potential Optimization for Dependency Management

## User's Question
Review the code in `detailed-design.md` and `src/dependent_todos/dependencies.py` - there is a Python builtin from graphlib that could be relevant.

## My Thoughts

### Current Implementation
The `dependencies.py` file currently implements dependency management with custom algorithms:

1. **Circular Dependency Detection** (`detect_circular_dependencies`, `_has_path`):
   - Custom depth-first search implementation
   - Lines 8-53 in dependencies.py
   - Manually tracks visited nodes and uses a stack

2. **Topological Sort** (`topological_sort`):
   - Custom Kahn's algorithm implementation
   - Lines 56-106 in dependencies.py
   - Manually calculates in-degrees and processes queue

### Python's `graphlib.TopologicalSorter` (Python 3.9+)

Python's standard library includes `graphlib.TopologicalSorter` since Python 3.9, which provides:

- **Topological sorting** with built-in cycle detection
- **Automatic circular dependency detection** (raises `CycleError`)
- **Parallel execution support** (can identify tasks that can run concurrently)
- **Well-tested, optimized implementation**

### Advantages of Using `graphlib.TopologicalSorter`

1. **Less Code to Maintain**: Replace ~50 lines of custom algorithm code with stdlib
2. **Better Tested**: Standard library implementation is battle-tested
3. **Cycle Detection Built-in**: Automatically detects circular dependencies
4. **Performance**: Optimized C implementation in CPython
5. **Future Features**: Could leverage parallel execution capabilities for identifying tasks that can be worked on simultaneously

### Compatibility Considerations

**Current Design Decision** (from detailed-design.md:178):
- "Use python 3.11+ since uv can install python's very easily"

**GraphLib Availability**:
- `graphlib` introduced in Python 3.9
- Project targets Python 3.11+
- ✅ **Fully compatible** - no issues

### Proposed Changes

#### Replace `topological_sort()` function:
```python
from graphlib import TopologicalSorter

def topological_sort(tasks: dict[str, Task]) -> list[str]:
    """Perform topological sort on tasks based on dependencies."""
    active_tasks = {tid: task for tid, task in tasks.items() if task.status != "done"}
    
    if not active_tasks:
        return []
    
    # Build graph for TopologicalSorter (task -> dependencies)
    graph = {task_id: task.dependencies for task_id, task in active_tasks.items()}
    
    ts = TopologicalSorter(graph)
    try:
        return list(ts.static_order())
    except CycleError as e:
        raise ValueError("Circular dependencies detected in tasks") from e
```

#### Simplify `detect_circular_dependencies()`:
```python
def detect_circular_dependencies(
    task_id: str, dependencies: list[str], all_tasks: dict[str, Task]
) -> list[str]:
    """Detect circular dependencies in the dependency graph."""
    from graphlib import TopologicalSorter, CycleError
    
    # Build the dependency graph including the new task
    graph = {tid: task.dependencies for tid, task in all_tasks.items()}
    graph[task_id] = dependencies
    
    ts = TopologicalSorter(graph)
    try:
        # Attempt to prepare the graph (this checks for cycles)
        ts.prepare()
        return []  # No cycles detected
    except CycleError:
        # Could parse the error message to identify specific cycle
        # For now, return the dependencies that caused the issue
        return dependencies
```

### Trade-offs

**Pros**:
- Significantly less code to maintain
- Standard library = no external dependency
- Better performance
- More reliable (extensively tested)
- Could enable future features (parallel task identification)

**Cons**:
- Less control over error messages (CycleError is generic)
- Current implementation returns specific task causing cycle; graphlib is less specific
- Minor behavior differences in edge cases

### Recommendation

**YES - Adopt `graphlib.TopologicalSorter`**

**Rationale**:
1. Project already targets Python 3.11+ (graphlib available since 3.9)
2. Reduces maintenance burden significantly
3. More reliable and performant
4. Aligns with Python best practices (use stdlib when available)
5. The trade-off of less specific error messages is acceptable for the benefits gained

**Implementation Priority**: 
- Should be done in **Phase 2** (Dependencies) as a refactor
- Or as a quick win before Phase 2 completion
- Low risk, high value change

### Additional Opportunities

Once using `graphlib`, could add a new command:

```bash
todos.py parallel
```

This could show which tasks can be worked on in parallel (no dependency relationship between them), leveraging `TopologicalSorter.get_ready()` for incremental processing.

## Next Steps (If User Approves)

1. Refactor `topological_sort()` to use `graphlib.TopologicalSorter`
2. Simplify `detect_circular_dependencies()` to use graphlib
3. Update tests to verify behavior matches
4. Consider removing `_has_path()` helper if no longer needed
5. Update documentation to mention graphlib usage
