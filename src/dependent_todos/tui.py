"""Textual TUI interface for dependent todos."""

import argparse
from datetime import datetime
from textual.app import App, ComposeResult
from typing import cast, Literal, Any
from collections.abc import Callable

from textual.binding import Binding
from textual.containers import Container, Grid
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    SelectionList,
    Static,
    Tabs,
    TextArea,
    Tree,
)
from textual.widgets.selection_list import Selection
from textual.screen import ModalScreen
from textual import events, on

from dependent_todos.config import get_config_path
from dependent_todos.constants import TODOS_CONFIG_NAME

from dependent_todos.models import Task, TaskList, DynamicStatusT
from dependent_todos.storage import load_tasks_from_file, save_tasks_to_file
from dependent_todos.utils import generate_unique_id, truncate
from typing import get_args

TabFilterType = Literal[
    "Doing", "Pending", "Ready TODO", "Done", "Blocked", "Cancelled"
]
TabFilters = get_args(TabFilterType)
SortFieldsT = Literal["created", "started", "completed", "status", "id"]
STATE_COLORS: dict[DynamicStatusT, str] = {
    "pending": "yellow",
    "in-progress": "blue",
    "done": "green",
    "blocked": "red",
    "cancelled": "dim red",
}


class FocusableTabs(Tabs):
    """Tabs widget that can be focused."""

    BINDINGS = Tabs.BINDINGS + [
        Binding("tab", "next_tab", "Next tab", show=False),
    ]

    def __init__(self, *tabs, **kwargs):
        super().__init__(*TabFilters, **kwargs)

    @staticmethod
    def filtered_tasks(tasks: TaskList, filter_state: TabFilterType):
        """This is a nice and type safe way to not use case or if else statements and python
        can also compile it more efficiently since the code paths are better defined"""
        fn_nmap: dict[TabFilterType, Callable[[Task], bool]] = {
            "Pending": lambda t: t.pending,
            "Doing": lambda t: t.doing,
            "Ready TODO": lambda t: t.pending
            and tasks.get_task_state(task) != "blocked",
            "Blocked": lambda t: not t.done and tasks.get_task_state(t) == "blocked",
            "Done": lambda t: t.done,
            "Cancelled": lambda t: t.cancelled,
        }
        for task_id, task in tasks.items():
            if fn_nmap[filter_state](task):
                yield task


def fmt_state(status, text: str | None = None):
    return f"[{STATE_COLORS[status]}]{text or status}[/{STATE_COLORS[status]}]"


def get_status_display(task: Task, tasks: TaskList) -> str:
    """Generate colorized status display with state in brackets if different."""
    state = tasks.get_task_state(task)
    return (
        fmt_state(task.status)
        if task.status == state
        else f"{fmt_state(task.status)} [{fmt_state(state, state)}]"
    )


def _sort_func(by: SortFieldsT = "created") -> Callable[[Task], Any]:
    """Returns a sort function for sorted"""

    def sort(task: Task) -> Any:
        return getattr(task, by, 0)

    return sort


class TaskTable(DataTable):
    """Data table for displaying tasks."""

    DT_FMT = "%Y-%m-%d %H:%M"

    BINDINGS = DataTable.BINDINGS + [
        ("e", "update_task", "Update"),
        ("d", "delete_task", "Delete"),
        ("m", "mark_done", "Mark done"),
        ("c", "cancel_task", "Cancel"),
    ]

    def __init__(self, tasks: TaskList, filter_state: TabFilterType = "all", **kwargs):
        super().__init__(**kwargs)
        self.tasks = tasks
        self.filter_state: TabFilterType = filter_state
        self.can_focus = True
        self.add_columns("ID", "Status", "Created", "Message")
        self._populate_table()

    def action_update_task(self):
        self.app.action_update_task()

    def action_delete_task(self):
        self.app.action_delete_task()

    def action_mark_done(self):
        self.app.action_mark_done()

    def action_cancel_task(self):
        self.app.action_cancel_task()

    def filtered_tasks(self, by: SortFieldsT, reverse: bool = True) -> dict[str, Task]:
        return {
            t.id: t
            for t in sorted(
                FocusableTabs.filtered_tasks(self.tasks, self.filter_state),
                reverse=reverse,
                key=_sort_func(by=by),
            )
        }

    def _populate_table(self):
        """Populate the table with task data."""
        # Clear existing rows
        self.clear()

        if not self.tasks:
            return
        for task_id, task in self.filtered_tasks(by="created").items():
            combined_status = get_status_display(task, self.tasks)

            self.add_row(
                task_id,
                combined_status,
                task.created.strftime(self.DT_FMT),
                truncate(task.message),
            )

    def refresh_data(self, tasks: TaskList):
        """Refresh the table with new task data."""
        self.tasks = tasks
        self._populate_table()


class DependencyTree(Tree):
    """Tree widget for displaying task dependencies."""

    def __init__(self, tasks: TaskList, root_task_id: str | None = None):
        super().__init__("Tasks")
        self.tasks = tasks
        self.root_task_id = root_task_id
        self._build_tree()

    def _build_tree(self):
        """Build the dependency tree."""
        # Clear existing tree
        self.root.remove_children()

        if self.root_task_id and self.root_task_id in self.tasks:
            # Build tree starting from specific task
            self._add_task_node(self.root, self.root_task_id)
        else:
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
        state = self.tasks.get_task_state(task)
        node = parent_node.add(f"{task_id}: {task.message} [{state}]")

        # Add dependency nodes
        for dep_id in task.dependencies:
            self._add_task_node(node, dep_id)

        node.allow_expand = bool(task.dependencies)
        # Expand the node if it has dependencies
        if task.dependencies:
            node.expand()


# TODO: prio low: this class does display two things and has to be refactored. create OrderDetails. Put both into parent container and swap the widget
class TaskDetails(Static):
    """Widget for displaying detailed task information."""

    def __init__(self, task_id: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.task_id = task_id
        self.tasks: TaskList = TaskList()
        self.showing_order = False
        self.order_list: list[str] = []

    def update_task(self, task_id: str, tasks: TaskList):
        """Update the displayed task."""
        self.task_id = task_id
        self.tasks = tasks
        self.showing_order = False
        self.refresh()

    def show_order(self, order_list: list[str]):
        """Show the execution order."""
        self.showing_order = True
        self.order_list = order_list
        self.refresh()

    def render(self):
        """Render the task details."""
        if self.showing_order:
            if self.order_list:
                order_text = "\n".join(
                    f"{i + 1}. {tid}: {self.tasks[tid].message}"
                    for i, tid in enumerate(self.order_list)
                )
                return f"[bold cyan]Execution Order:[/bold cyan]\n{order_text}"
            else:
                return "No active tasks to order"

        if not self.task_id or self.task_id not in self.tasks:
            return "Select a task to view details"

        task = self.tasks[self.task_id]
        state = self.tasks.get_task_state(task)
        details = f"""[bold cyan]ID:[/bold cyan] {task.id}
[bold cyan]Status:[/bold cyan] [{STATE_COLORS[task.status]}]{task.status}[/{STATE_COLORS[task.status]}]
[bold cyan]State:[/bold cyan] [{STATE_COLORS[state]}]{state}[/{STATE_COLORS[state]}]
[bold cyan]Created:[/bold cyan] {task.created}
[bold cyan]Started:[/bold cyan] {task.started or "-"}
[bold cyan]Completed:[/bold cyan] {task.completed or "-"}

{task.message}

[bold green]Dependencies:[/bold green]
"""

        if task.dependencies:
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if dep_task:
                    dep_state = self.tasks.get_task_state(dep_task)
                    details += f"  • {dep_id} [{STATE_COLORS[dep_state]}]{dep_state}[/{STATE_COLORS[dep_state]}]: {dep_task.message}\n"
                else:
                    details += f"  • {dep_id} [not found]\n"
        else:
            details += "  None\n"

        details += "\n[bold red]Blocks:[/bold red]\n"
        dependents = tuple(
            tid for tid, t in self.tasks.items() if self.task_id in t.dependencies
        )
        if dependents:
            for dep_id in dependents:
                dep_task = self.tasks.get(dep_id)
                if dep_task:
                    dep_state = self.tasks.get_task_state(dep_task)
                    details += f"  • {dep_id} [{STATE_COLORS[dep_state]}]{dep_state}[/{STATE_COLORS[dep_state]}]: {dep_task.message}\n"
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
            yield Static(str(self.TITLE), classes="title")
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

    def on_ok_pressed(self) -> None:
        """Override to handle OK button press."""
        pass

    def on_click(self, event: events.Click) -> None:
        """Close modal when clicking outside the dialog."""
        if event.button == 1 and event.control == self:
            self.dismiss()

    @property
    def cycle_selectors(self) -> set[str]:
        return {
            "Button",
            "Input",
            "TextArea",
            "SelectionList",
            "Checkbox",
            "RadioSet",
            "Select",
            "Switch",
            "RadioButton",
        }

    @property
    def cycle_widgets(self):
        """A query to get all widgets we can cycle with keybindings"""
        return self.query(", ".join(self.cycle_selectors))

    def action_next_input(self) -> None:
        """Focus the next input field."""
        focusables = tuple(self.cycle_widgets.nodes)
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

    def action_prev_input(self) -> None:
        """Focus the previous input field."""
        focusables = tuple(self.cycle_widgets.nodes)
        if not focusables:
            return
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

    def _get_dependency_options(self) -> list[Selection[str]]:
        """Get available tasks for dependency selection."""
        app = cast(DependentTodosApp, self.app)
        options = []
        current_deps = app.tasks[self.task_id].dependencies
        for task_id, task in app.tasks.items():
            if task_id == self.task_id:  # Exclude self
                continue
            if (
                task.status == "done" and task_id not in current_deps
            ):  # Exclude done tasks unless they are current dependencies
                continue
            state = app.tasks.get_task_state(task)
            display_text = f"{task_id}: {task.message} [{state}]"
            # Pre-select current dependencies
            selected = task_id in current_deps
            options.append(Selection(display_text, task_id, selected))
        return options

    def _get_depending_on_text(self) -> str:
        """Get text for tasks that depend on this task."""
        app = cast(DependentTodosApp, self.app)
        dependents = [
            tid for tid, t in app.tasks.items() if self.task_id in t.dependencies
        ]
        if not dependents:
            return "None"
        dependent_texts = []
        for dep_id in dependents:
            dep_task = app.tasks[dep_id]
            dep_state = app.tasks.get_task_state(dep_task)
            dependent_texts.append(f"• {dep_id}: {dep_task.message} [{dep_state}]")
        return "\n".join(dependent_texts)

    def get_content(self) -> ComposeResult:
        app = cast(DependentTodosApp, self.app)
        task = app.tasks.get(self.task_id)
        if not task:
            yield Static(f"Error: Task '{self.task_id}' not found", classes="error")
            return
        yield Static(f"Task ID: {self.task_id}", classes="task-id")
        yield TextArea(task.message, classes="task-message")
        yield Static("Depends on:", classes="depends-on-label")
        yield SelectionList[str](
            *self._get_dependency_options(), classes="depends-on-list", id="depends-on"
        )
        yield Static("Depending on:", classes="depending-on-label")
        yield Static(self._get_depending_on_text(), classes="depending-on-list")

    def on_mount(self) -> None:
        self.query_one(".task-message", TextArea).focus()

    def on_ok_pressed(self) -> None:
        message = self.query_one(".task-message", TextArea).text
        if not message.strip():
            self.notify("Task message cannot be empty")
            return

        app = cast(DependentTodosApp, self.app)
        task = app.tasks.get(self.task_id)
        if not task:
            self.notify(f"Error: Task '{self.task_id}' not found")
            self.dismiss()
            return

        # Get selected dependencies
        selection_list = self.query_one("#depends-on", SelectionList)
        selected_deps = list(selection_list.selected)

        # Validate for circular dependencies
        circular_deps = app.tasks.detect_circular_dependencies(
            self.task_id, selected_deps
        )
        if circular_deps:
            self.notify(
                f"Circular dependency detected with: {', '.join(circular_deps)}"
            )
            return

        task.message = message
        task.dependencies = selected_deps
        app._save_and_refresh()
        self.dismiss()


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

    def on_ok_pressed(self) -> None:
        app = cast(DependentTodosApp, self.app)
        if self.task_id in app.tasks:
            del app.tasks[self.task_id]
            app._save_and_refresh()
            app.current_task_id = None
        self.dismiss()


class AddTaskModal(BaseModalScreen):
    """Modal for adding a new task."""

    TITLE = "Add a new task"

    def _get_dependency_options(self) -> list[Selection[str]]:
        """Get available tasks for dependency selection."""
        app = cast(DependentTodosApp, self.app)
        options = []
        for task_id, task in app.tasks.items():
            if task.status == "done":  # Exclude done tasks
                continue
            state = app.tasks.get_task_state(task)
            display_text = f"{task_id}: {task.message} [{state}]"
            options.append(Selection(display_text, task_id))
        return options

    def get_content(self) -> ComposeResult:
        yield Input("", classes="task-id", placeholder="Task ID", disabled=True)
        yield TextArea(placeholder="Task message", classes="task-message")
        yield Static("Depends on:", classes="depends-on-label")
        yield SelectionList[str](
            *self._get_dependency_options(), classes="depends-on-list", id="depends-on"
        )

    def on_mount(self) -> None:
        self.query_one(".task-message", TextArea).focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        message = event.text_area.text
        app = cast(DependentTodosApp, self.app)
        existing_ids = set(app.tasks.keys())
        task_id = generate_unique_id(message, existing_ids)
        inp = self.query_one(".task-id", Input)
        inp.value = task_id

    def on_ok_pressed(self) -> None:
        message = self.query_one(".task-message", TextArea).text

        if not message.strip():
            self.notify("Task message cannot be empty")
            return

        app = cast(DependentTodosApp, self.app)
        existing_ids = set(app.tasks.keys())
        task_id = generate_unique_id(message, existing_ids)

        # Get selected dependencies
        selection_list = self.query_one("#depends-on", SelectionList)
        selected_deps = list(selection_list.selected)

        # Validate for circular dependencies
        circular_deps = app.tasks.detect_circular_dependencies(task_id, selected_deps)
        if circular_deps:
            self.notify(
                f"Circular dependency detected with: {', '.join(circular_deps)}"
            )
            return

        task = Task(
            id=task_id,
            message=message,
            dependencies=selected_deps,
            status="pending",
            started=None,
            completed=None,
        )
        app.tasks[task_id] = task
        app._save_and_refresh()
        self.dismiss()


class Sidebar(Container):
    pass


class DependentTodosApp(App):
    """Main Textual application for dependent todos."""

    BINDINGS = [
        ("a", "add_task", "Add"),
        ("r", "refresh", "Refresh"),
        ("y", "ready_tasks", "Ready"),
        ("o", "show_order", "Ordered"),
        ("t", "toggle_tree", "Toggle tree"),
    ]

    CSS_PATH = "styles.css"

    # TODO: Do the same for the other ids of the main widgets used and use the class variables inside the functions
    SIDEBAR_WIDGET_ID = "sidebar"

    FILTER_EXPLANATIONS = {
        "Doing": "Tasks that have been started",
        "Pending": "All tasks with pending status",
        "Ready TODO": "Pending tasks without start date that are not blocked",
        "Done": "Completed tasks",
        "Blocked": "Tasks that are blocked by dependencies",
        "Cancelled": "Cancelled tasks",
    }

    def __init__(self, config_path: str | None = None):
        super().__init__()
        self.config_path = get_config_path(config_path)
        self.tasks = cast(TaskList, load_tasks_from_file(self.config_path))
        self.current_task_id = None
        self.current_filter: TabFilterType = "Doing"
        self.footer = f"Config: {self.config_path}"

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()

        with Sidebar(id=self.SIDEBAR_WIDGET_ID):
            tree = DependencyTree(self.tasks, root_task_id=self.current_task_id)
            tree.id = "dep-tree"
            yield tree
        with Container(id="main-content"):
            yield FocusableTabs(id="filter-tabs")
            yield TaskTable(
                self.tasks,
                filter_state=self.current_filter,
                id="task-table",
                cursor_type="row",
            )
            yield Static("", id="filter-info")
            yield TaskDetails(id="task-details")
            yield Static(self.footer, id="info-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the UI after mounting."""
        sidebar = self.sidebar
        sidebar.display = False
        self.task_table.focus()

    @property
    def task_table(self) -> TaskTable:
        return self.query_one("#task-table", TaskTable)

    @on(DataTable.RowHighlighted)
    def handle_data_table_row_selected(self, event: DataTable.RowHighlighted) -> None:
        """Handle task selection in the table."""
        table = self.task_table
        row_key = event.row_key
        if row_key is None:
            return
        task_id = table.get_row(row_key)[0]
        self.current_task_id = task_id
        details = self.task_details
        details.update_task(task_id, self.tasks)
        # Refresh tree if visible
        sidebar = self.sidebar
        if sidebar.display:
            tree = self.dep_tree
            tree.root_task_id = self.current_task_id
            tree._build_tree()
            tree.refresh()

    @property
    def dep_tree(self):
        return self.query_one("#dep-tree", DependencyTree)

    @property
    def sidebar(self):
        return self.query_one(Sidebar)

    @property
    def task_details(self):
        return self.query_one("#task-details", TaskDetails)

    @property
    def filter_tabs(self):
        return self.query_one("#filter-tabs", FocusableTabs)

    @on(DependencyTree.NodeSelected)
    def handle_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle task selection in the tree."""
        tree = self.dep_tree
        if event.node == tree.root:
            return
        label = str(event.node.label)
        task_id = label.split(":")[0].strip()
        if task_id in self.tasks:
            self.current_task_id = task_id
            details = self.task_details
            details.update_task(task_id, self.tasks)
            # Rebuild tree centered on selected task
            tree.root_task_id = self.current_task_id
            tree._build_tree()
            tree.refresh()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle filter tab change."""
        self._update_filter_from_tab()

    def action_add_task(self) -> None:
        """Add a new task using modal."""
        self.push_screen(AddTaskModal())

    def action_update_task(self) -> None:
        """Update the selected task using modal."""
        if self.current_task_id:
            self.push_screen(UpdateTaskModal(self.current_task_id))
        else:
            self.notify("No task selected")

    def action_delete_task(self) -> None:
        """Delete the selected task using modal."""
        if self.current_task_id:
            self.push_screen(DeleteTaskModal(self.current_task_id))
        else:
            self.notify("No task selected")

    def action_mark_done(self) -> None:
        """Mark the selected task as done."""
        if self.current_task_id:
            task = self.tasks.get(self.current_task_id)
            if task:
                task.status = "done"
                task.completed = datetime.now()
                self._save_and_refresh()
                self.notify(f"Task '{self.current_task_id}' marked as done")
            else:
                self.notify("Task not found")
        else:
            self.notify("No task selected")

    def action_cancel_task(self) -> None:
        """Cancel or uncancel the selected task."""
        if self.current_task_id:
            task = self.tasks.get(self.current_task_id)
            if task:
                if task.cancelled:
                    task.cancelled = False
                    self.notify(f"Task '{self.current_task_id}' uncancelled")
                else:
                    task.cancelled = True
                    self.notify(f"Task '{self.current_task_id}' cancelled")
                self._save_and_refresh()
            else:
                self.notify("Task not found")
        else:
            self.notify("No task selected")

    def _save_and_refresh(self) -> None:
        """Save tasks to file and refresh the UI."""
        try:
            save_tasks_to_file(self.tasks, self.config_path)
            self.action_refresh()
            # Refresh tree if display
            sidebar = self.sidebar
            if sidebar.display:
                tree = self.dep_tree
                tree.tasks = self.tasks
                tree._build_tree()
                tree.refresh()
        except Exception as e:
            self.notify(f"Error saving tasks: {e}", severity="error")

    def action_refresh(self) -> None:
        """Refresh the task data."""
        try:
            self.tasks = load_tasks_from_file(self.config_path)
            table = self.task_table
            table.refresh_data(self.tasks)
            details = self.task_details
            details.tasks = self.tasks
            details.refresh()
        except Exception as e:
            self.notify(f"Error loading tasks: {e}", severity="error")

    def action_show_ready(self) -> None:
        """Show ready tasks."""
        ready_tasks = self.tasks.get_pending_tasks()
        if ready_tasks:
            task_list = "\n".join(
                f"• {tid}: {self.tasks[tid].message}" for tid in ready_tasks
            )
            self.notify(f"Ready tasks:\n{task_list}")
        else:
            self.notify("No tasks are ready to work on")

    def action_show_order(self) -> None:
        """Show topological execution order."""
        try:
            ordered = self.tasks.topological_sort()
            details = self.task_details
            details.show_order(ordered)
        except Exception as e:
            self.notify(f"Error: {e}")

    def action_toggle_tree(self) -> None:
        """Toggle the dependency tree sidebar."""
        sidebar = self.sidebar
        if not sidebar.display:
            if self.current_task_id:
                # Show sidebar and refresh tree
                sidebar.display = True
                tree = self.dep_tree
                tree.tasks = self.tasks
                tree.root_task_id = self.current_task_id
                tree._build_tree()
                tree.refresh()
                tree.root.expand_all()
            else:
                self.notify("No task selected")
        else:
            # Hide sidebar
            sidebar.display = False
            tree = self.dep_tree
            tree.root.remove_children()
            tree.refresh()

    def _update_filter_from_tab(self) -> None:
        """Update the current filter and table based on active tab."""
        tabs = self.filter_tabs
        if tabs.active_tab is not None:
            self.current_filter: TabFilterType = tabs.active_tab.label.plain
            table = self.task_table
            table.filter_state = self.current_filter
            table._populate_table()
            # Update filter info bar
            info_bar = self.query_one("#filter-info", Static)
            info_bar.update(self.FILTER_EXPLANATIONS.get(self.current_filter, ""))
            # Clear tree if display to avoid showing stale dependencies
            sidebar = self.sidebar
            if sidebar.display:
                tree = self.dep_tree
                tree.refresh(recompose=True)


def run():
    """Run the Textual TUI application."""
    parser = argparse.ArgumentParser(description="Run the Dependent Todos TUI")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (default: %(default)s)",
        default=TODOS_CONFIG_NAME,
    )
    args = parser.parse_args()
    app = DependentTodosApp(config_path=args.config)
    app.run()


if __name__ == "__main__":
    run()
