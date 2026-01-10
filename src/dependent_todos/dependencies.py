"""Dependency management utilities for tasks."""

from simple_term_menu import TerminalMenu

from .models import Task


def detect_circular_dependencies(
    task_id: str, dependencies: list[str], all_tasks: dict[str, Task]
) -> list[str]:
    """Detect circular dependencies in the dependency graph.

    Args:
        task_id: ID of the task being checked
        dependencies: List of dependency IDs for this task
        all_tasks: Dictionary of all existing tasks

    Returns:
        List of task IDs that would create a circular dependency, empty if none
    """
    # Build the dependency graph
    graph = {tid: task.dependencies for tid, task in all_tasks.items()}
    graph[task_id] = dependencies

    # Check for cycles starting from each dependency
    for dep in dependencies:
        if _has_path(dep, task_id, graph):
            return [dep]  # Return the first circular dependency found

    return []


def _has_path(start: str, target: str, graph: dict[str, list[str]]) -> bool:
    """Check if there's a path from start to target in the graph."""
    visited = set()
    stack = [start]

    while stack:
        current = stack.pop()
        if current == target:
            return True

        if current in visited:
            continue

        visited.add(current)

        # Add dependencies to stack
        for dep in graph.get(current, []):
            if dep not in visited:
                stack.append(dep)

    return False


def topological_sort(tasks: dict[str, Task]) -> list[str]:
    """Perform topological sort on tasks based on dependencies.

    Only includes tasks that are not done (pending, in-progress, blocked, cancelled).

    Args:
        tasks: Dictionary of tasks to sort

    Returns:
        List of task IDs in topological order (dependencies first)

    Raises:
        ValueError: If circular dependencies are detected
    """
    # Only consider tasks that are not done
    active_tasks = {tid: task for tid, task in tasks.items() if task.status != "done"}

    if not active_tasks:
        return []

    # Build adjacency list (task -> dependencies)
    graph = {task_id: task.dependencies[:] for task_id, task in active_tasks.items()}

    # Calculate in-degrees (number of incoming edges - how many dependencies each task has)
    in_degree = {
        task_id: len(task.dependencies) for task_id, task in active_tasks.items()
    }

    # Find tasks with no dependencies
    queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
    result = []

    while queue:
        # Sort queue for consistent ordering
        queue.sort()

        current = queue.pop(0)
        result.append(current)

        # Reduce in-degree of tasks that depend on current
        for task_id, deps in graph.items():
            if current in deps:
                in_degree[task_id] -= 1
                if in_degree[task_id] == 0:
                    queue.append(task_id)

    # Check for cycles
    if len(result) != len(active_tasks):
        raise ValueError("Circular dependencies detected in tasks")

    return result


def get_ready_tasks(tasks: dict[str, Task]) -> list[str]:
    """Get tasks that are ready to work on (all dependencies completed).

    Args:
        tasks: Dictionary of all tasks

    Returns:
        List of task IDs that are ready to work on
    """
    ready = []
    for task_id, task in tasks.items():
        state = task.compute_state(tasks)
        if state == "pending":  # Not blocked, not in progress, not done
            ready.append(task_id)

    # Sort by creation time (oldest first)
    ready.sort(key=lambda tid: tasks[tid].created)
    return ready


def get_dependency_tree(
    task_id: str, tasks: dict[str, Task], prefix: str = "", is_last: bool = True
) -> str:
    """Generate a tree representation of task dependencies.

    Args:
        task_id: Root task ID
        tasks: Dictionary of all tasks
        prefix: Current prefix for tree drawing
        is_last: Whether this is the last child

    Returns:
        String representation of the dependency tree
    """
    if task_id not in tasks:
        return f"{prefix}{'└── ' if is_last else '├── '}{task_id} [not found]\n"

    task = tasks[task_id]
    state = task.compute_state(tasks)

    result = (
        f"{prefix}{'└── ' if is_last else '├── '}{task_id}: {task.message} [{state}]\n"
    )

    deps = task.dependencies
    if not deps:
        return result

    # Sort dependencies for consistent display
    deps = sorted(deps)

    for i, dep_id in enumerate(deps):
        is_last_dep = i == len(deps) - 1
        new_prefix = prefix + ("    " if is_last else "│   ")
        result += get_dependency_tree(dep_id, tasks, new_prefix, is_last_dep)

    return result


def select_dependencies_interactive(
    all_tasks: dict[str, Task], exclude_task_id: str | None = None
) -> list[str]:
    """Interactively select dependencies using fuzzy search.

    Args:
        all_tasks: Dictionary of all available tasks
        exclude_task_id: Task ID to exclude from selection (e.g., the task being created)

    Returns:
        List of selected dependency IDs
    """
    # Filter out the task being created and done tasks
    available_tasks = {
        tid: task
        for tid, task in all_tasks.items()
        if tid != exclude_task_id and task.status != "done"
    }

    if not available_tasks:
        return []

    # Create menu options with task ID and message
    options = []
    task_ids = []
    for task_id in sorted(available_tasks.keys()):
        task = available_tasks[task_id]
        state = task.compute_state(all_tasks)
        option = f"{task_id}: {task.message} [{state}]"
        options.append(option)
        task_ids.append(task_id)

    # Add "None" option to finish selection
    options.append("Done - no more dependencies")
    task_ids.append(None)

    selected_deps = []
    while True:
        print("\nSelect dependencies (use arrow keys and Enter, or type to search):")
        if selected_deps:
            print(f"Already selected: {', '.join(selected_deps)}")

        terminal_menu = TerminalMenu(
            options,
            title="Available tasks:",
            show_search_hint=True,
        )
        menu_entry_index = terminal_menu.show()

        if menu_entry_index is None:  # User pressed Ctrl+C or similar
            break

        # Handle the case where menu_entry_index might be a tuple (for multi-select)
        if isinstance(menu_entry_index, tuple):
            menu_entry_index = menu_entry_index[0]

        index = int(menu_entry_index)
        selected_task_id = task_ids[index]

        if selected_task_id is None:  # "Done" option
            break

        if selected_task_id not in selected_deps:
            selected_deps.append(selected_task_id)
            print(f"Added dependency: {selected_task_id}")
        else:
            print(f"Already selected: {selected_task_id}")

        # Remove the selected task from options to prevent re-selection
        # But keep the "Done" option
        options.pop(index)
        task_ids.pop(index)

        if len(options) == 1:  # Only "Done" option left
            break

    return selected_deps
