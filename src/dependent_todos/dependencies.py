"""Dependency management utilities for tasks."""

from graphlib import TopologicalSorter

from simple_term_menu import TerminalMenu

from .models import Task, TaskList



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
