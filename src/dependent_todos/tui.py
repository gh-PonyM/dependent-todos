"""Textual TUI interface for dependent todos."""

from rich.text import Text
from textual.app import App, ComposeResult
from typing import cast, Literal
from textual.containers import Container, Horizontal, Grid
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Static,
    Tabs,
    TextArea,
    Tree,
)
from textual.screen import ModalScreen
from textual import events

from dependent_todos.config import get_config_path
from dependent_todos.dependencies import get_ready_tasks, topological_sort
from dependent_todos.models import STATE_COLORS, Task
from dependent_todos.storage import load_tasks_from_file, save_tasks_to_file
from dependent_todos.utils import generate_unique_id


class FocusableTabs(Tabs):
    """Tabs widget that can be focused."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_focus = True


class TaskTable(DataTable):
    """Data table for displaying tasks."""

    def __init__(self, tasks: dict[str, Task], filter_state: str = "all", **kwargs):
        super().__init__(**kwargs)
        self.tasks = tasks
        self.filter_state = filter_state
        self.can_focus = True
        self.add_columns("ID", "State", "Message")
        self._populate_table()

    def _populate_table(self):
        """Populate the table with task data."""
        # Clear existing rows
        self.clear()

        if not self.tasks:
            return

        # Use state colors from constants
        state_colors = STATE_COLORS

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

        # Use state colors from constants
        state_colors = STATE_COLORS

        details = f"""[bold cyan]ID:[/bold cyan] {task.id}
[bold cyan]State:[/bold cyan] [{state_colors.get(state, "white")}]{state}[/{state_colors.get(state, "white")}]
[bold cyan]Status:[/bold cyan] {task.status}
[bold cyan]Created:[/bold cyan] {task.created}
[bold cyan]Started:[/bold cyan] {task.started or "-"}
[bold cyan]Completed:[/bold cyan] {task.completed or "-"}
[bold cyan]Cancelled:[/bold cyan] {task.cancelled}

{task.message}

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


class BaseModalScreen(ModalScreen):
    """Base modal screen with extensible content and buttons."""

    TITLE = "Modal title"

    BTN_OKAY_LABEL: str = "Ok"
    BTN_OKAY_VARIANT: Literal["default", "primary", "success", "warning", "error"] = (
        "success"
    )
    BTN_CANCEL_LABEL: str = "Cancel"
    BTN_CANCEL_ID: str = "cancel"
    BTN_CANCEL_VARIANT: Literal["default", "primary", "success", "warning", "error"] = (
        "default"
    )

    BINDINGS = [
        ("escape", "dismiss", "Close modal"),
        ("tab", "next_input", "Next input field"),
        ("shift+tab", "prev_input", "Previous input field"),
    ]

    def compose(self) -> ComposeResult:
        # with Grid(id="modal-dialog"):
        with Grid(classes="modal-dialog"):
            yield Static(self.TITLE, classes="title")
            # TODO: Here I am asking myself if we can check if the elements have a row-span defined.
            # if not we take the height from the title, and the height of the button as rowspan and use 12 (grid row number)
            # set the heights dynamically, is this possible?
            yield from self.get_content()
            yield from self.get_buttons()

    def get_content(self) -> ComposeResult:
        """Override to provide modal content."""
        yield from []

    def get_buttons(self) -> ComposeResult:
        """Provide modal buttons using class variables."""
        yield Button(
            self.BTN_OKAY_LABEL,
            id="ok",
            classes="modal-button",
            variant=self.BTN_OKAY_VARIANT,
        )
        yield Button(
            self.BTN_CANCEL_LABEL,
            id=self.BTN_CANCEL_ID,
            classes="modal-button",
            variant=self.BTN_CANCEL_VARIANT,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.on_ok_pressed()
        elif event.button.id == self.BTN_CANCEL_ID:
            self.dismiss()

    def on_ok_pressed(self):
        """Override to handle OK button press."""
        pass

    def on_click(self, event: events.Click) -> None:
        """Close modal when clicking outside the dialog."""
        if event.button == 1 and event.control == self:
            self.dismiss()

    def action_next_input(self):
        """Focus the next input field."""
        focusables = list(self.query("Input, TextArea").nodes)
        if not focusables:
            self.notify("No inputs to cycle")
            return
        current = self.focused
        if current in focusables:
            index = focusables.index(current)
            next_index = (index + 1) % len(focusables)
        else:
            next_index = 0
        self.set_focus(focusables[next_index])

    def action_prev_input(self):
        """Focus the previous input field."""
        focusables = list(self.query("Input, TextArea").nodes)
        if focusables:
            current = self.focused
            if current in focusables:
                index = focusables.index(current)
                prev_index = (index - 1) % len(focusables)
            else:
                prev_index = -1
            self.set_focus(focusables[prev_index])


class UpdateTaskModal(BaseModalScreen):
    """Modal for updating a task."""

    TITLE = "Update Task"
    BTN_OKAY_LABEL = "Update"
    BTN_OKAY_VARIANT = "primary"

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id

    def get_content(self) -> ComposeResult:
        app = cast(DependentTodosApp, self.app)
        task = app.tasks.get(self.task_id)
        if not task:
            self.dismiss()
            return
        yield Static(f"Task ID: {self.task_id}", classes="task-id")
        yield Input(value=task.message, id="task-message")

    def on_mount(self) -> None:
        self.query_one("#task-message", Input).focus()

    def on_ok_pressed(self):
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


class DeleteTaskModal(BaseModalScreen):
    """Modal for deleting a task."""

    TITLE = "Delete Task"
    BTN_OKAY_LABEL = "Delete"
    BTN_OKAY_VARIANT = "error"

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id

    def get_content(self) -> ComposeResult:
        app = cast(DependentTodosApp, self.app)
        task = app.tasks.get(self.task_id)
        message = task.message if task else "Unknown"
        yield Static(
            f"Are you sure you want to delete task '{self.task_id}: {message}'?",
            classes="confirmation",
        )

    def on_ok_pressed(self):
        app = cast(DependentTodosApp, self.app)
        if self.task_id in app.tasks:
            del app.tasks[self.task_id]
            from dependent_todos.storage import save_tasks_to_file

            save_tasks_to_file(app.tasks, app.config_path)
            app.action_refresh()
            app.current_task_id = None
        self.dismiss()


class AddTaskModal(BaseModalScreen):
    """Modal for adding a new task."""

    TITLE = "Add a new task"

    def get_content(self) -> ComposeResult:
        yield Input("", id="task-id", placeholder="Task ID", disabled=True)
        yield TextArea(placeholder="Task message", id="task-message")

    def on_mount(self) -> None:
        self.query_one("#task-message", TextArea).focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        message = event.text_area.text
        app = cast(DependentTodosApp, self.app)
        existing_ids = set(app.tasks.keys())
        task_id = generate_unique_id(message, existing_ids)
        inp = self.query_one("#task-id", Input)
        inp.value = task_id

    def on_ok_pressed(self):
        message = self.query_one("#task-message", TextArea).text

        if not message.strip():
            self.notify("Task message cannot be empty")
            # For now, add without dependencies
            return

        app = cast(DependentTodosApp, self.app)
        existing_ids = set(app.tasks.keys())
        task_id = generate_unique_id(message, existing_ids)
        task = Task(
            id=task_id,
            message=message,
            dependencies=[],
            status="pending",
            cancelled=False,
            started=None,
            completed=None,
        )
        app.tasks[task_id] = task
        save_tasks_to_file(app.tasks, app.config_path)
        app.action_refresh()
        self.dismiss()


class DependentTodosApp(App):
    """Main Textual application for dependent todos."""

    BINDINGS = [
        ("a", "add_task", "Add task"),
        ("r", "refresh", "Refresh"),
        ("y", "ready_tasks", "Show ready"),
        ("o", "topological_order", "Show order"),
        ("e", "update_task", "Update selected task"),
        ("d", "delete_task", "Delete selected task"),
        ("tab", "next_tab", "Next tab"),
        ("shift+tab", "previous_tab", "Previous tab"),
    ]

    CSS_PATH = "styles.css"

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
                yield FocusableTabs("All", "Ready", "Done", "Pending", id="filter-tabs")
                yield TaskTable(
                    self.tasks, filter_state=self.current_filter, id="task-table"
                )
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
        self._update_filter_from_tab()

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

    def action_next_tab(self):
        """Switch to the next filter tab."""
        tabs = self.query_one("#filter-tabs", FocusableTabs)
        current_tab = tabs.active_tab
        if current_tab is not None:
            current_index = tabs._tabs.index(current_tab)
            next_index = (current_index + 1) % len(tabs._tabs)
            tabs.active = cast(str, tabs._tabs[next_index].id)
            self._update_filter_from_tab()

    def action_previous_tab(self):
        """Switch to the previous filter tab."""
        tabs = self.query_one("#filter-tabs", FocusableTabs)
        current_tab = tabs.active_tab
        if current_tab is not None:
            current_index = tabs._tabs.index(current_tab)
            prev_index = (current_index - 1) % len(tabs._tabs)
            tabs.active = cast(str, tabs._tabs[prev_index].id)
            self._update_filter_from_tab()

    def action_focus_next(self):
        """Switch focus to the next widget."""
        focusables = [self.query_one("#filter-tabs"), self.query_one("#task-table")]
        current = self.focused
        if current in focusables:
            index = focusables.index(current)
            next_index = (index + 1) % len(focusables)
            self.set_focus(focusables[next_index])
        else:
            self.set_focus(focusables[0])

    def action_focus_previous(self):
        """Switch focus to the previous widget."""
        focusables = [self.query_one("#filter-tabs"), self.query_one("#task-table")]
        current = self.focused
        if current in focusables:
            index = focusables.index(current)
            prev_index = (index - 1) % len(focusables)
            self.set_focus(focusables[prev_index])
        else:
            self.set_focus(focusables[-1])

    def _update_filter_from_tab(self):
        """Update the current filter and table based on active tab."""
        tabs = self.query_one("#filter-tabs", FocusableTabs)
        if tabs.active_tab is not None:
            self.current_filter = str(tabs.active_tab.label.plain).lower()
            table = self.query_one("#task-table", TaskTable)
            table.filter_state = self.current_filter
            table._populate_table()

    def on_key(self, event):
        """Handle key presses."""
        if event.key == "tab":
            event.prevent_default()
            self.action_next_tab()
        elif event.key == "shift+tab":
            event.prevent_default()
            self.action_previous_tab()
        elif event.key == "up":
            table = cast(TaskTable, self.query_one("#task-table"))
            if table.has_focus:
                event.prevent_default()
                new_row = max(0, table.cursor_row - 1)
                table.move_cursor(row=new_row)
                row_key = list(table.rows.keys())[new_row]
                task_id = table.get_row(row_key)[0]
                self.current_task_id = task_id
                details = self.query_one("#task-details", TaskDetails)
                details.update_task(task_id, self.tasks)
            else:
                self.action_focus_previous()
                event.prevent_default()
        elif event.key == "down":
            table = cast(TaskTable, self.query_one("#task-table"))
            if table.has_focus:
                event.prevent_default()
                new_row = min(len(table.rows) - 1, table.cursor_row + 1)
                table.move_cursor(row=new_row)
                row_key = list(table.rows.keys())[new_row]
                task_id = table.get_row(row_key)[0]
                self.current_task_id = task_id
                details = self.query_one("#task-details", TaskDetails)
                details.update_task(task_id, self.tasks)
            else:
                self.action_focus_next()
                event.prevent_default()


def run_tui():
    """Run the Textual TUI application."""
    app = DependentTodosApp()
    app.run()


if __name__ == "__main__":
    run_tui()
