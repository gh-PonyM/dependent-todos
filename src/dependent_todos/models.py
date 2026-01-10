"""Data models for the dependent todos application."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
    """A task with dependencies and status tracking."""

    id: str = Field(
        ..., description="Unique identifier, auto-generated slug from message"
    )
    message: str = Field(..., description="Task description")
    status: str = Field("pending", description="Stored status: 'pending' or 'done'")
    dependencies: list[str] = Field(
        default_factory=list, description="List of task IDs this task depends on"
    )
    created: datetime = Field(
        default_factory=datetime.now, description="When task was created"
    )
    started: datetime | None = Field(None, description="When work began on task")
    completed: datetime | None = Field(None, description="When task was marked done")
    cancelled: bool = Field(False, description="Whether task is cancelled")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is either 'pending' or 'done'."""
        if v not in ("pending", "done"):
            raise ValueError("status must be 'pending' or 'done'")
        return v

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate ID format (slug-like)."""
        import re

        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("ID must be lowercase alphanumeric with hyphens only")
        if len(v) > 50:
            raise ValueError("ID must be 50 characters or less")
        return v

    def compute_state(self, all_tasks: dict[str, "Task"]) -> str:
        """Compute the runtime state from stored fields and dependencies.

        Args:
            all_tasks: Dictionary of all tasks by ID for dependency checking

        Returns:
            Computed state: "pending", "in-progress", "done", "blocked", or "cancelled"
        """
        if self.cancelled:
            return "cancelled"

        if self.status == "done" and self.completed is not None:
            return "done"

        if self.status == "pending":
            # Check if any dependencies are not done
            for dep_id in self.dependencies:
                dep_task = all_tasks.get(dep_id)
                if dep_task is None or dep_task.status != "done":
                    return "blocked"

            # No blocking dependencies
            if self.started is not None and self.completed is None:
                return "in-progress"
            else:
                return "pending"

        # Fallback (shouldn't reach here with validation)
        return "pending"
