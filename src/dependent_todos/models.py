"""Data models for the dependent todos application."""

import tomllib
from datetime import datetime
from pathlib import Path
from typing import Literal
from graphlib import TopologicalSorter

import tomli_w

from pydantic import BaseModel, Field, RootModel

from dependent_todos.constants import TASK_ID_MAX_LEN, TASK_ID_RE_PATT

StatusT = Literal["pending", "done", "cancelled", "in-progress"]
DynamicStatusT = Literal["pending", "done", "cancelled", "in-progress", "blocked"]


class Task(BaseModel):
    """A task with dependencies and status tracking."""

    id: str = Field(
        ...,
        description="Unique identifier, auto-generated slug from message",
        max_length=TASK_ID_MAX_LEN,
        pattern=TASK_ID_RE_PATT,
    )
    message: str = Field(..., description="Task description")
    status: StatusT = Field("pending", description="Stored status")
    dependencies: list[str] = Field(
        default_factory=list, description="List of task IDs this task depends on"
    )
    created: datetime = Field(
        default_factory=datetime.now, description="When task was created"
    )
    started: datetime | None = Field(None, description="When work began on task")
    completed: datetime | None = Field(None, description="When task was marked done")

    @property
    def cancelled(self) -> bool:
        return self.status == "cancelled"

    @property
    def pending(self) -> bool:
        """Pending v.s. in-progress"""
        return not self.done and not self.cancelled

    @property
    def doing(self) -> bool:
        """Pending v.s. in-progress"""
        return all((bool(self.started), not self.done, not self.cancelled))

    @property
    def done(self) -> bool:
        return bool(self.completed) and not self.cancelled


class TaskList(RootModel):
    """Collection of tasks with dependency management methods."""

    root: dict[str, Task] = Field(default_factory=dict)

    def __getitem__(self, item):
        return self.root[item]

    def __setitem__(self, key, value):
        self.root[key] = value

    def __delitem__(self, key):
        del self.root[key]

    def __len__(self):
        return len(self.root)

    def __contains__(self, item):
        return item in self.root

    def get(self, key, default=None):
        return self.root.get(key, default)

    def items(self):
        return self.root.items()

    def keys(self):
        return self.root.keys()

    def values(self):
        return self.root.values()

    def detect_circular_dependencies(
        self, task_id: str, dependencies: list[str]
    ) -> list[str]:
        """Detect circular dependencies in the dependency graph.

        Args:
            task_id: ID of the task being checked
            dependencies: List of dependency IDs for this task

        Returns:
            List of task IDs that would create a circular dependency, empty if none
        """
        from graphlib import CycleError

        # Build the dependency graph including the new task
        graph = {tid: task.dependencies for tid, task in self.items()}
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

    def topological_sort(self) -> list[str]:
        """Perform topological sort on tasks based on dependencies.

        Only includes tasks that are not done (pending, in-progress, blocked, cancelled).

        Returns:
            List of task IDs in topological order (dependencies first)

        Raises:
            CycleError: If circular dependencies are detected
        """
        active_tasks = {
            tid: task for tid, task in self.items() if task.status != "done"
        }

        if not active_tasks:
            return []

        # Build graph for TopologicalSorter (task -> dependencies)
        graph = {task_id: task.dependencies for task_id, task in active_tasks.items()}

        ts = TopologicalSorter(graph)
        return list(ts.static_order())

    def get_pending_tasks(self) -> list[str]:
        """Get tasks that are ready to work on (all dependencies completed).

        Returns:
            List of task IDs that are ready to work on
        """
        ready = []
        for task_id, task in self.items():
            state = self.get_task_state(task)
            if state == "pending":  # Not blocked, not in progress, not done
                ready.append(task_id)

        # Sort by creation time (oldest first)
        ready.sort(key=lambda tid: self[tid].created)
        return ready

    def get_dependency_tree(
        self, task_id: str, prefix: str = "", is_last: bool = True
    ) -> str:
        """Generate a tree representation of task dependencies.

        Args:
            task_id: Root task ID
            prefix: Current prefix for tree drawing
            is_last: Whether this is the last child

        Returns:
            String representation of the dependency tree
        """
        if task_id not in self:
            return f"{prefix}{'└── ' if is_last else '├── '}{task_id} [not found]\n"

        task = self[task_id]
        state = self.get_task_state(task)

        result = f"{prefix}{'└── ' if is_last else '├── '}{task_id}: {task.message} [{state}]\n"

        deps = task.dependencies
        if not deps:
            return result

        # Sort dependencies for consistent display
        deps = sorted(deps)

        for i, dep_id in enumerate(deps):
            is_last_dep = i == len(deps) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            result += self.get_dependency_tree(dep_id, new_prefix, is_last_dep)

        return result

    @classmethod
    def load_from_file(cls, file_path: Path) -> "TaskList":
        """Load tasks from a TOML file.

        Args:
            file_path: Path to the TOML file

        Returns:
            TaskList of tasks
        """
        if not file_path.exists():
            return cls()
        with open(file_path, "rb") as f:
            data = tomllib.load(f)

        # Use Pydantic's model_validate
        return cls.model_validate(data)

    def save_to_file(self, file_path: Path) -> None:
        tasks_data = self.model_dump(mode="json", exclude_none=True)
        with open(file_path, "wb") as f:
            tomli_w.dump(tasks_data, f)

    def get_task_state(self, task: Task) -> DynamicStatusT:
        """Compute the runtime state from stored fields and dependencies.

        Args:
            task: The task to compute status for

        Returns:
            Computed state: "pending", "in-progress", "done", "blocked", or "cancelled"
        """
        if task.cancelled:
            return "cancelled"

        if task.status == "done" and task.completed is not None:
            return "done"

        if task.status == "pending":
            # Check if any dependencies are not done
            for dep_id in task.dependencies:
                dep_task = self.get(dep_id)
                if dep_task is None or dep_task.status != "done":
                    return "blocked"

            # No blocking dependencies
            if task.started is not None and task.completed is None:
                return "in-progress"
            else:
                return "pending"

        # Fallback (shouldn't reach here with validation)
        return "pending"
