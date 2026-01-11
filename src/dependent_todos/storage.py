"""TOML-based storage for tasks."""

from pathlib import Path


from .models import TaskList


def load_tasks_from_file(file_path: Path) -> TaskList:
    """Load tasks from a TOML file.

    Args:
        file_path: Path to the TOML file

    Returns:
        TaskList of tasks
    """
    return TaskList.load_from_file(file_path)


def save_tasks_to_file(tasklist: TaskList, file_path: Path) -> None:
    """Save tasks to a TOML file.

    Args:
        tasklist: TaskList of tasks to save
        file_path: Path to save the TOML file
    """
    tasklist.save_to_file(file_path)
