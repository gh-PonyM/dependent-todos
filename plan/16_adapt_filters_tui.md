# Adapt the filters for tabs and the status filtering

All the types:

```python
StatusT = Literal["pending", "done", "cancelled", "in-progress"]
DynamicStatusT = Literal["pending", "done", "cancelled", "in-progress", "blocked"]
```

Example for the tab filter:

```python
FocusableTabs(
    "All", "Ready", "Todo", "Done", "Pending", id="filter-tabs"
)

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

```
The tabs should reflect the state. We want tabs for (in this order) in the form "Fiter": "Description":

- "Doing": for those tasks with a started date with status, state = in-progress, (for you to know: the state is not used for filtering)
- "Ready TODO": pending tasks without a start date that are not blocked
- "Blocked": All blocked issues, started or pending state, not done yet.
- "Pending": All with pending state (for you to know: the state is not used for filtering)
- "Done": Leave as is

## Additions for the TUI interface

Make these additions when doing the change in the TaskTable:

- In the table, add a header created and format date with time
- Add a slim info bar on the bottom of the table, which shows the filter explanation. Add another element below the table. The bar should show the explanation of the tab filter.
