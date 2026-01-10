"""Textual TUI interface for dependent todos."""

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Static,
    Tree,
)

from dependent_todos.config import get_config_path
from dependent_todos.dependencies import get_ready_tasks, topological_sort
from dependent_todos.models import Task
from dependent_todos.storage import load_tasks_from_file


class TaskTable(DataTable):
    """Data table for displaying tasks."""

    def __init__(self, tasks: dict[str, Task], **kwargs):
        super().__init__(**kwargs)
        self.tasks = tasks
        self.add_columns("ID", "State", "Message")
        self._populate_table()

    def _populate_table(self):
        """Populate the table with task data."""
        # Clear existing rows
        self.clear()

        if not self.tasks:
            return

        # Color mapping for states
        state_colors = {
            "pending": "yellow",
            "in-progress": "blue",
            "done": "green",
            "blocked": "red",
            "cancelled": "dim red",
        }

        for task_id, task in sorted(self.tasks.items()):
            state = task.compute_state(self.tasks)
            state_text = Text(state, style=state_colors.get(state, "white"))

            # Truncate message if too long
            message = task.message
            if len(message) > 50:
                message = message[:47] + "..."

            self.add_row(task_id, state_text.plain, message)

    def refresh_data(self, tasks: dict[str, Task]):
        """Refresh the table with new task data."""
        self.tasks = tasks
        self._populate_table()


class DependencyTree(Tree):
    """Tree widget for displaying task dependencies."""

    def __init__(self, tasks: dict[str, Task]):
        super().__init__("Tasks")
        self.tasks = tasks
        self._build_tree()

    def _build_tree(self):
        """Build the dependency tree."""
        # Group tasks by their root (tasks with no dependencies pointing to them)
        dependents = set()
        for task in self.tasks.values():
            dependents.update(task.dependencies)

        root_tasks = [tid for tid in self.tasks.keys() if tid not in dependents]
        root_tasks.sort()

        if not root_tasks:
            # Handle case where there are cycles - just show all tasks
            root_tasks = sorted(self.tasks.keys())

        for root_id in root_tasks:
            self._add_task_node(self.root, root_id)

    def _add_task_node(self, parent_node, task_id: str):
        """Add a task node to the tree."""
        if task_id not in self.tasks:
            node = parent_node.add(f"{task_id} [not found]")
            node.allow_expand = False
            return

        task = self.tasks[task_id]
        state = task.compute_state(self.tasks)
        node = parent_node.add(f"{task_id}: {task.message} [{state}]")

        # Add dependency nodes
        for dep_id in task.dependencies:
            self._add_task_node(node, dep_id)

        node.allow_expand = bool(task.dependencies)


class TaskDetails(Static):
    """Widget for displaying detailed task information."""

    def __init__(self, task_id: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.task_id = task_id
        self.tasks = {}

    def update_task(self, task_id: str, tasks: dict[str, Task]):
        """Update the displayed task."""
        self.task_id = task_id
        self.tasks = tasks
        self.refresh()

    def render(self):
        """Render the task details."""
        if not self.task_id or self.task_id not in self.tasks:
            return "Select a task to view details"

        task = self.tasks[self.task_id]
        state = task.compute_state(self.tasks)

        # Color mapping for states
        state_colors = {
            "pending": "yellow",
            "in-progress": "blue",
            "done": "green",
            "blocked": "red",
            "cancelled": "dim red",
        }

        details = f"""[bold cyan]ID:[/bold cyan] {task.id}
[bold cyan]Message:[/bold cyan] {task.message}
[bold cyan]State:[/bold cyan] [{state_colors.get(state, "white")}]{state}[/{state_colors.get(state, "white")}]
[bold cyan]Status:[/bold cyan] {task.status}
[bold cyan]Created:[/bold cyan] {task.created}
[bold cyan]Started:[/bold cyan] {task.started or "-"}
[bold cyan]Completed:[/bold cyan] {task.completed or "-"}
[bold cyan]Cancelled:[/bold cyan] {task.cancelled}

[bold green]Dependencies:[/bold green]
"""

        if task.dependencies:
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if dep_task:
                    dep_state = dep_task.compute_state(self.tasks)
                    details += f"  • {dep_id} [{state_colors.get(dep_state, 'white')}]{dep_state}[/{state_colors.get(dep_state, 'white')}]: {dep_task.message}\n"
                else:
                    details += f"  • {dep_id} [not found]\n"
        else:
            details += "  None\n"

        details += "\n[bold red]Blocks:[/bold red]\n"
        dependents = [
            tid for tid, t in self.tasks.items() if self.task_id in t.dependencies
        ]
        if dependents:
            for dep_id in dependents:
                dep_task = self.tasks.get(dep_id)
                if dep_task:
                    dep_state = dep_task.compute_state(self.tasks)
                    details += f"  • {dep_id} [{state_colors.get(dep_state, 'white')}]{dep_state}[/{state_colors.get(dep_state, 'white')}]: {dep_task.message}\n"
        else:
            details += "  None\n"

        return details


class DependentTodosApp(App):
    """Main Textual application for dependent todos."""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 40;
        border-right: solid $primary;
    }

    #main-content {
        layout: vertical;
        width: 1fr;
    }

    #task-table {
        height: 1fr;
    }

    #task-details {
        height: 1fr;
        border-top: solid $primary;
    }

    Button {
        margin: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.config_path = get_config_path()
        self.tasks = load_tasks_from_file(self.config_path)

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()

        with Horizontal():
            with Container(id="sidebar"):
                yield Button("Add Task", id="add-task")
                yield Button("Refresh", id="refresh")
                yield Button("Ready Tasks", id="ready-tasks")
                yield Button("Topological Order", id="topological-order")

            with Container(id="main-content"):
                yield TaskTable(self.tasks, id="task-table")
                yield TaskDetails(id="task-details")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "add-task":
            self.action_add_task()
        elif event.button.id == "refresh":
            self.action_refresh()
        elif event.button.id == "ready-tasks":
            self.action_show_ready()
        elif event.button.id == "topological-order":
            self.action_show_order()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle task selection in the table."""
        table = self.query_one("#task-table", TaskTable)
        row_key = event.row_key
        if row_key is not None:
            task_id = table.get_row(row_key)[0]
            details = self.query_one("#task-details", TaskDetails)
            details.update_task(task_id, self.tasks)

    def action_add_task(self):
        """Add a new task (placeholder - would need input dialogs)."""
        self.notify(
            "Add task functionality not implemented in TUI yet. Use CLI: dependent-todos add"
        )

    def action_refresh(self):
        """Refresh the task data."""
        self.tasks = load_tasks_from_file(self.config_path)
        table = self.query_one("#task-table", TaskTable)
        table.refresh_data(self.tasks)
        details = self.query_one("#task-details", TaskDetails)
        details.tasks = self.tasks
        details.refresh()

    def action_show_ready(self):
        """Show ready tasks."""
        ready_tasks = get_ready_tasks(self.tasks)
        if ready_tasks:
            task_list = "\n".join(
                f"• {tid}: {self.tasks[tid].message}" for tid in ready_tasks
            )
            self.notify(f"Ready tasks:\n{task_list}")
        else:
            self.notify("No tasks are ready to work on")

    def action_show_order(self):
        """Show topological execution order."""
        try:
            ordered = topological_sort(self.tasks)
            if ordered:
                order_list = "\n".join(
                    f"{i + 1}. {tid}: {self.tasks[tid].message}"
                    for i, tid in enumerate(ordered)
                )
                self.notify(f"Execution order:\n{order_list}")
            else:
                self.notify("No active tasks to order")
        except ValueError as e:
            self.notify(f"Error: {e}")


def run_tui():
    """Run the Textual TUI application."""
    app = DependentTodosApp()
    app.run()
