"""Data models for the dependent todos application."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from dependent_todos.constants import TASK_ID_MAX_LEN, TASK_ID_RE_PATT

StatusT = Literal["pending", "done", "blocked", "cancelled", "in-progress"]


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




class TaskList(dict[str, Task]):
    """Collection of tasks with dependency management methods."""

    def __init__(self, tasks: dict[str, Task] | None = None):
        super().__init__(tasks or {})

    def get_task_state(self, task: Task) -> StatusT:
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
