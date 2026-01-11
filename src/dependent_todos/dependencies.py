"""Dependency management utilities for tasks."""

from graphlib import TopologicalSorter

from simple_term_menu import TerminalMenu

from .models import Task, TaskList

# All these functions should go onto a class called TaskList.


def detect_circular_dependencies(
    task_id: str, dependencies: list[str], all_tasks: TaskList
) -> list[str]:
    """Detect circular dependencies in the dependency graph.

    Args:
        task_id: ID of the task being checked
        dependencies: List of dependency IDs for this task
        all_tasks: Dictionary of all existing tasks

    Returns:
        List of task IDs that would create a circular dependency, empty if none
    """
    from graphlib import CycleError

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


def topological_sort(tasks: TaskList) -> list[str]:
    """Perform topological sort on tasks based on dependencies.

    Only includes tasks that are not done (pending, in-progress, blocked, cancelled).

    Args:
        tasks: Dictionary of tasks to sort

    Returns:
        List of task IDs in topological order (dependencies first)

    Raises:
        ValueError: If circular dependencies are detected
    """
    from graphlib import CycleError

    active_tasks = {tid: task for tid, task in tasks.items() if task.status != "done"}

    if not active_tasks:
        return []

    # Build graph for TopologicalSorter (task -> dependencies)
    graph = {task_id: task.dependencies for task_id, task in active_tasks.items()}

    ts = TopologicalSorter(graph)
    # TODO: remove custom error, why is this needed? If we have to capture this exception, we can use the cycle error.
    # Also we only catch on exception and multiple, so there is not benefit for the consumer of this function
    try:
        return list(ts.static_order())
    except CycleError as e:
        raise ValueError("Circular dependencies detected in tasks") from e


def get_ready_tasks(tasks: TaskList) -> list[str]:
    """Get tasks that are ready to work on (all dependencies completed).

    Args:
        tasks: Dictionary of all tasks

    Returns:
        List of task IDs that are ready to work on
    """
    ready = []
    for task_id, task in tasks.items():
        state = tasks.get_task_state(task)
        if state == "pending":  # Not blocked, not in progress, not done
            ready.append(task_id)

    # Sort by creation time (oldest first)
    ready.sort(key=lambda tid: tasks[tid].created)
    return ready


def get_dependency_tree(
    task_id: str, tasks: TaskList, prefix: str = "", is_last: bool = True
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
    state = tasks.get_task_state(task)

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
    all_tasks: TaskList, exclude_task_id: str | None = None
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
        state = all_tasks.get_task_state(task)
        option = f"{task_id}: {task.message} [{state}]"
        options.append(option)
        task_ids.append(task_id)

    # Add "None" option to finish selection
    options.append("Done - no more dependencies")
    task_ids.append(None)

    selected_deps = []
    while True:
        print("\nDepends on (use arrow keys and Enter, or type to search):")
        if selected_deps:
            print(f"Already selected: {', '.join(selected_deps)}")

        terminal_menu = TerminalMenu(
            options, title="Available tasks:", show_search_hint=True, multi_select=True
        )
        menu_entry_index = terminal_menu.show()

        if menu_entry_index is None:  # User pressed Ctrl+C or similar
            break

        # Handle the case where menu_entry_index might be a tuple (for multi-select)
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


def select_task_interactive(all_tasks: TaskList) -> str | None:
    """Interactively select a single task using fuzzy search.

    Args:
        all_tasks: Dictionary of all available tasks

    Returns:
        Selected task ID, or None if cancelled
    """
    if not all_tasks:
        return None

    # Create menu options with task ID and message
    options = []
    task_ids = []
    for task_id in sorted(all_tasks.keys()):
        task = all_tasks[task_id]
        state = all_tasks.get_task_state(task)
        option = f"{task_id}: {task.message} [{state}]"
        options.append(option)
        task_ids.append(task_id)

    # Add "Cancel" option
    options.append("Cancel selection")
    task_ids.append(None)

    terminal_menu = TerminalMenu(
        options,
        title="Select a task:",
        show_search_hint=True,
    )
    menu_entry_index = terminal_menu.show()

    if menu_entry_index is None:  # User pressed Ctrl+C or similar
        return None

    selected_index = int(menu_entry_index)
    return task_ids[selected_index]
