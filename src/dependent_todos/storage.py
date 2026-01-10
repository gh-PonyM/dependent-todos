"""TOML-based storage for tasks."""

import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from .models import Task


def load_tasks_from_file(file_path: Path) -> dict[str, Task]:
    """Load tasks from a TOML file.

    Args:
        file_path: Path to the TOML file

    Returns:
        Dictionary of tasks keyed by ID
    """
    if not file_path.exists():
        return {}

    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load tasks from {file_path}: {e}")

    tasks = {}
    tasks_data = data.get("tasks", {})

    for task_id, task_dict in tasks_data.items():
        # Convert string timestamps back to datetime objects (empty strings become None)
        task_dict["created"] = _parse_datetime(task_dict.get("created", ""))
        task_dict["started"] = _parse_datetime(task_dict.get("started", ""))
        task_dict["completed"] = _parse_datetime(task_dict.get("completed", ""))

        try:
            task = Task(**task_dict)
            tasks[task_id] = task
        except Exception as e:
            raise RuntimeError(f"Failed to parse task '{task_id}': {e}")

    return tasks


def save_tasks_to_file(tasks: dict[str, Task], file_path: Path) -> None:
    """Save tasks to a TOML file.

    Args:
        tasks: Dictionary of tasks to save
        file_path: Path to save the TOML file
    """
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert tasks to TOML-compatible format
    tasks_data = {}
    for task_id, task in tasks.items():
        task_dict = task.model_dump()

        # Convert datetime objects to ISO strings, None to empty string
        if task_dict["created"]:
            task_dict["created"] = task_dict["created"].isoformat()
        else:
            task_dict["created"] = ""
        if task_dict["started"]:
            task_dict["started"] = task_dict["started"].isoformat()
        else:
            task_dict["started"] = ""
        if task_dict["completed"]:
            task_dict["completed"] = task_dict["completed"].isoformat()
        else:
            task_dict["completed"] = ""

        tasks_data[task_id] = task_dict

    data = {"tasks": tasks_data}

    try:
        with open(file_path, "wb") as f:
            tomli_w.dump(data, f)
    except Exception as e:
        raise RuntimeError(f"Failed to save tasks to {file_path}: {e}")


def _parse_datetime(dt_str: str) -> Any:
    """Parse an ISO datetime string to a datetime object.

    Args:
        dt_str: ISO datetime string

    Returns:
        datetime object or None if empty
    """
    if not dt_str or dt_str == "":
        return None

    from datetime import datetime

    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        # Try parsing without microseconds if it fails
        try:
            return datetime.fromisoformat(dt_str.split(".")[0])
        except ValueError:
            raise ValueError(f"Invalid datetime format: {dt_str}")
