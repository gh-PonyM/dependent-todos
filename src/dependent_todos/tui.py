"""Textual TUI interface for dependent todos."""

from rich.text import Text
from textual.app import App, ComposeResult
from typing import cast
from textual.containers import Container, Horizontal
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Static,
    Tabs,
    Tree,
)
from textual.screen import ModalScreen

from dependent_todos.config import get_config_path
from dependent_todos.dependencies import get_ready_tasks, topological_sort
from dependent_todos.models import Task
from dependent_todos.storage import load_tasks_from_file


class TaskTable(DataTable):
    """Data table for displaying tasks."""

    def __init__(self, tasks: dict[str, Task], filter_state: str = "all", **kwargs):
        super().__init__(**kwargs)
        self.tasks = tasks
        self.filter_state = filter_state
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

        # Filter tasks
        filtered_tasks = {}
        for task_id, task in self.tasks.items():
            state = task.compute_state(self.tasks)
            if self.filter_state == "all":
                filtered_tasks[task_id] = task
            elif self.filter_state == "ready":
                if state == "pending":
                    filtered_tasks[task_id] = task
            elif self.filter_state == "done":
                if state == "done":
                    filtered_tasks[task_id] = task
            elif self.filter_state == "pending":
                if state in ("pending", "blocked", "in-progress"):
                    filtered_tasks[task_id] = task

        for task_id, task in sorted(filtered_tasks.items()):
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


class AddTaskModal(ModalScreen):
    """Modal for adding a new task."""

    def compose(self) -> ComposeResult:
        yield Static("Add New Task", id="title")
        yield Input(placeholder="Task message", id="task-message")
        yield Button("Add", id="add")
        yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            message = self.query_one("#task-message", Input).value
            if message.strip():
                # For now, add without dependencies
                from dependent_todos.utils import generate_unique_id
                from dependent_todos.storage import save_tasks_to_file

                app = cast(DependentTodosApp, self.app)
                existing_ids = set(app.tasks.keys())
                task_id = generate_unique_id(message, existing_ids)
                task = Task(id=task_id, message=message, dependencies=[], status="pending", cancelled=False, started=None, completed=None)
                app.tasks[task_id] = task
                save_tasks_to_file(app.tasks, app.config_path)
                app.action_refresh()
                self.dismiss()
            else:
                self.notify("Task message cannot be empty")
        elif event.button.id == "cancel":
            self.dismiss()


class UpdateTaskModal(ModalScreen):
    """Modal for updating a task."""

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id

    def compose(self) -> ComposeResult:
        app = cast(DependentTodosApp, self.app)
        task = app.tasks.get(self.task_id)
        if not task:
            self.dismiss()
            return
        yield Static(f"Update Task: {self.task_id}", id="title")
        yield Input(value=task.message, id="task-message")
        yield Button("Update", id="update")
        yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "update":
            message = self.query_one("#task-message", Input).value
            if message.strip():
                app = cast(DependentTodosApp, self.app)
                task = app.tasks.get(self.task_id)
                if task:
                    task.message = message
                    from dependent_todos.storage import save_tasks_to_file
                    save_tasks_to_file(app.tasks, app.config_path)
                    app.action_refresh()
                self.dismiss()
            else:
                self.notify("Task message cannot be empty")
        elif event.button.id == "cancel":
            self.dismiss()


class DeleteTaskModal(ModalScreen):
    """Modal for deleting a task."""

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id

    def compose(self) -> ComposeResult:
        app = cast(DependentTodosApp, self.app)
        task = app.tasks.get(self.task_id)
        message = task.message if task else "Unknown"
        yield Static(f"Delete task '{self.task_id}: {message}'?", id="title")
        yield Button("Delete", id="delete")
        yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete":
            app = cast(DependentTodosApp, self.app)
            if self.task_id in app.tasks:
                del app.tasks[self.task_id]
                from dependent_todos.storage import save_tasks_to_file
                save_tasks_to_file(app.tasks, app.config_path)
                app.action_refresh()
                app.current_task_id = None
            self.dismiss()
        elif event.button.id == "cancel":
            self.dismiss()


class DependentTodosApp(App):
    """Main Textual application for dependent todos."""

    BINDINGS = [
        ("a", "add_task", "Add task"),
        ("r", "refresh", "Refresh"),
        ("y", "ready_tasks", "Show ready"),
        ("o", "topological_order", "Show order"),
        ("u", "update_task", "Update selected task"),
        ("d", "delete_task", "Delete selected task"),
    ]

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

    #footer {
        height: 1;
        border-top: solid $primary;
        padding: 0 1;
    }

    Button {
        margin: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.config_path = get_config_path()
        self.tasks = load_tasks_from_file(self.config_path)
        self.current_task_id = None
        self.current_filter = "all"
        self.footer = f"Config: {self.config_path}"

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()

        with Horizontal():
            with Container(id="sidebar"):
                pass  # Buttons replaced with key bindings

            with Container(id="main-content"):
                yield Tabs("All", "Ready", "Done", "Pending", id="filter-tabs")
                yield TaskTable(self.tasks, filter_state=self.current_filter, id="task-table")
                yield TaskDetails(id="task-details")

        yield Footer()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle task selection in the table."""
        table = self.query_one("#task-table", TaskTable)
        row_key = event.row_key
        if row_key is not None:
            task_id = table.get_row(row_key)[0]
            self.current_task_id = task_id
            details = self.query_one("#task-details", TaskDetails)
            details.update_task(task_id, self.tasks)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle filter tab change."""
        self.current_filter = str(event.tab.label.plain).lower()
        table = self.query_one("#task-table", TaskTable)
        table.filter_state = self.current_filter
        table._populate_table()

    def action_add_task(self):
        """Add a new task using modal."""
        self.push_screen(AddTaskModal())

    def action_update_task(self):
        """Update the selected task using modal."""
        if self.current_task_id:
            self.push_screen(UpdateTaskModal(self.current_task_id))
        else:
            self.notify("No task selected")

    def action_delete_task(self):
        """Delete the selected task using modal."""
        if self.current_task_id:
            self.push_screen(DeleteTaskModal(self.current_task_id))
        else:
            self.notify("No task selected")

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


if __name__ == "__main__":
    run_tui()
