"""Textual TUI interface for dependent todos."""

from datetime import datetime
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
    SelectionList,
    Static,
    Tabs,
    TextArea,
    Tree,
)
from textual.widgets.selection_list import Selection
from textual.screen import ModalScreen
from textual import events

from dependent_todos.config import get_config_path
from dependent_todos.dependencies import detect_circular_dependencies, get_ready_tasks, topological_sort
from dependent_todos.models import STATE_COLORS, Task
from dependent_todos.storage import load_tasks_from_file, save_tasks_to_file
from dependent_todos.utils import generate_unique_id

# UI Constants
MAX_MESSAGE_DISPLAY_LENGTH = 50
MESSAGE_TRUNCATE_LENGTH = 47
TRUNCATION_SUFFIX = "..."

# Tab filter states (must match tab labels in lowercase)
TAB_FILTERS = ("all", "todo", "done", "pending")


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
            elif self.filter_state == "todo":
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
            if len(message) > MAX_MESSAGE_DISPLAY_LENGTH:
                message = message[:MESSAGE_TRUNCATE_LENGTH] + TRUNCATION_SUFFIX

            self.add_row(task_id, state_text.plain, message)

    def refresh_data(self, tasks: dict[str, Task]):
        """Refresh the table with new task data."""
        self.tasks = tasks
        self._populate_table()


class DependencyTree(Tree):
    """Tree widget for displaying task dependencies."""

    def __init__(self, tasks: dict[str, Task], root_task_id: str | None = None):
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
        state = task.compute_state(self.tasks)
        node = parent_node.add(f"{task_id}: {task.message} [{state}]")

        # Add dependency nodes
        for dep_id in task.dependencies:
            self._add_task_node(node, dep_id)

        node.allow_expand = bool(task.dependencies)
        # Expand the node if it has dependencies
        if task.dependencies:
            node.expand()


class TaskDetails(Static):
    """Widget for displaying detailed task information."""

    def __init__(self, task_id: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.task_id = task_id
        self.tasks = {}
        self.showing_order = False
        self.order_list: list[str] = []

    def update_task(self, task_id: str, tasks: dict[str, Task]):
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
        dependents = tuple(
            tid for tid, t in self.tasks.items() if self.task_id in t.dependencies
        )
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
            yield Static(str(self.TITLE), classes="title")
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

    def on_ok_pressed(self) -> None:
        """Override to handle OK button press."""
        pass

    def on_click(self, event: events.Click) -> None:
        """Close modal when clicking outside the dialog."""
        if event.button == 1 and event.control == self:
            self.dismiss()

    def action_next_input(self) -> None:
        """Focus the next input field."""
        focusables = tuple(self.query("Input, TextArea").nodes)
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
        focusables = tuple(self.query("Input, TextArea").nodes)
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

    def _get_dependency_options(self) -> list[Selection[str]]:
        """Get available tasks for dependency selection."""
        app = cast(DependentTodosApp, self.app)
        options = []
        for task_id, task in app.tasks.items():
            if task_id != self.task_id and task.status != "done":  # Exclude self and done tasks
                state = task.compute_state(app.tasks)
                display_text = f"{task_id}: {task.message} [{state}]"
                # Pre-select current dependencies
                selected = task_id in app.tasks[self.task_id].dependencies
                options.append(Selection(display_text, task_id, selected))
        return options

    def _get_depending_on_text(self) -> str:
        """Get text for tasks that depend on this task."""
        app = cast(DependentTodosApp, self.app)
        dependents = [
            tid for tid, t in app.tasks.items()
            if self.task_id in t.dependencies
        ]
        if not dependents:
            return "None"
        dependent_texts = []
        for dep_id in dependents:
            dep_task = app.tasks[dep_id]
            dep_state = dep_task.compute_state(app.tasks)
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
            *self._get_dependency_options(),
            classes="depends-on-list",
            id="depends-on"
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
        circular_deps = detect_circular_dependencies(self.task_id, selected_deps, app.tasks)
        if circular_deps:
            self.notify(f"Circular dependency detected with: {', '.join(circular_deps)}")
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
            if task.status != "done":  # Exclude done tasks
                state = task.compute_state(app.tasks)
                display_text = f"{task_id}: {task.message} [{state}]"
                options.append(Selection(display_text, task_id))
        return options

    def get_content(self) -> ComposeResult:
        yield Input("", classes="task-id", placeholder="Task ID", disabled=True)
        yield TextArea(placeholder="Task message", classes="task-message")
        yield Static("Depends on:", classes="depends-on-label")
        yield SelectionList[str](
            *self._get_dependency_options(),
            classes="depends-on-list",
            id="depends-on"
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
        circular_deps = detect_circular_dependencies(task_id, selected_deps, app.tasks)
        if circular_deps:
            self.notify(f"Circular dependency detected with: {', '.join(circular_deps)}")
            return

        task = Task(
            id=task_id,
            message=message,
            dependencies=selected_deps,
            status="pending",
            cancelled=False,
            started=None,
            completed=None,
        )
        app.tasks[task_id] = task
        app._save_and_refresh()
        self.dismiss()


class DependentTodosApp(App):
    """Main Textual application for dependent todos."""

    BINDINGS = [
        ("a", "add_task", "Add task"),
        ("r", "refresh", "Refresh"),
        ("y", "ready_tasks", "Show ready"),
        ("o", "show_order", "Show order"),
        ("e", "update_task", "Update selected task"),
        ("d", "delete_task", "Delete selected task"),
        ("m", "mark_done", "Mark task done"),
        ("t", "toggle_tree", "Toggle tree"),
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
                tree = DependencyTree(self.tasks, root_task_id=self.current_task_id)
                tree.id = "dep-tree"
                tree.can_focus = False
                yield tree
            with Container(id="main-content"):
                yield FocusableTabs("All", "Todo", "Done", "Pending", id="filter-tabs")
                yield TaskTable(
                    self.tasks, filter_state=self.current_filter, id="task-table"
                )
                yield TaskDetails(id="task-details")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the UI after mounting."""
        sidebar = self.query_one("#sidebar", Container)
        sidebar.visible = False

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle task selection in the table."""
        table = self.query_one("#task-table", TaskTable)
        row_key = event.row_key
        if row_key is not None:
            task_id = table.get_row(row_key)[0]
            self.current_task_id = task_id
            details = self.query_one("#task-details", TaskDetails)
            details.update_task(task_id, self.tasks)
            # Refresh tree if visible
            sidebar = self.query_one("#sidebar", Container)
            if sidebar.visible:
                tree = self.query_one("#dep-tree", DependencyTree)
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

    def _save_and_refresh(self) -> None:
        """Save tasks to file and refresh the UI."""
        try:
            save_tasks_to_file(self.tasks, self.config_path)
            self.action_refresh()
            # Refresh tree if visible
            sidebar = self.query_one("#sidebar", Container)
            if sidebar.visible:
                tree = self.query_one("#dep-tree", DependencyTree)
                tree.tasks = self.tasks
                tree._build_tree()
                tree.refresh()
        except Exception as e:
            self.notify(f"Error saving tasks: {e}", severity="error")

    def action_refresh(self) -> None:
        """Refresh the task data."""
        try:
            self.tasks = load_tasks_from_file(self.config_path)
            table = self.query_one("#task-table", TaskTable)
            table.refresh_data(self.tasks)
            details = self.query_one("#task-details", TaskDetails)
            details.tasks = self.tasks
            details.refresh()
        except Exception as e:
            self.notify(f"Error loading tasks: {e}", severity="error")

    def action_show_ready(self) -> None:
        """Show ready tasks."""
        ready_tasks = get_ready_tasks(self.tasks)
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
            ordered = topological_sort(self.tasks)
            details = self.query_one("#task-details", TaskDetails)
            details.show_order(ordered)
        except ValueError as e:
            self.notify(f"Error: {e}")

    def action_toggle_tree(self) -> None:
        """Toggle the dependency tree sidebar."""
        sidebar = self.query_one("#sidebar", Container)
        if not sidebar.visible:
            if self.current_task_id:
                # Show sidebar and refresh tree
                sidebar.visible = True
                tree = self.query_one("#dep-tree", DependencyTree)
                tree.tasks = self.tasks
                tree.root_task_id = self.current_task_id
                tree._build_tree()
                tree.refresh()
                self.notify("Dependency tree shown")
            else:
                self.notify("No task selected")
        else:
            # Hide sidebar
            sidebar.visible = False
            tree = self.query_one("#dep-tree", DependencyTree)
            tree.root.remove_children()
            tree.refresh()
            self.notify("Dependency tree hidden")

    def action_next_tab(self) -> None:
        """Switch to the next filter tab."""
        tabs = self.query_one("#filter-tabs", FocusableTabs)
        # Cycle through tabs using the tab index
        current_filter = self.current_filter
        if current_filter in TAB_FILTERS:
            current_index = TAB_FILTERS.index(current_filter)
            next_index = (current_index + 1) % len(TAB_FILTERS)
            # Query all tab widgets and get their IDs
            all_tabs = list(tabs.query("Tab"))
            if next_index < len(all_tabs):
                tabs.active = all_tabs[next_index].id or ""
                self._update_filter_from_tab()

    def action_previous_tab(self) -> None:
        """Switch to the previous filter tab."""
        tabs = self.query_one("#filter-tabs", FocusableTabs)
        # Cycle through tabs using the tab index
        current_filter = self.current_filter
        if current_filter in TAB_FILTERS:
            current_index = TAB_FILTERS.index(current_filter)
            prev_index = (current_index - 1) % len(TAB_FILTERS)
            # Query all tab widgets and get their IDs
            all_tabs = list(tabs.query("Tab"))
            if prev_index < len(all_tabs):
                tabs.active = all_tabs[prev_index].id or ""
                self._update_filter_from_tab()

    def action_focus_next(self) -> None:
        """Switch focus to the next widget."""
        focusables = (self.query_one("#filter-tabs"), self.query_one("#task-table"))
        current = self.focused
        if current in focusables:
            index = focusables.index(current)
            next_index = (index + 1) % len(focusables)
            self.set_focus(focusables[next_index])
        else:
            self.set_focus(focusables[0])

    def action_focus_previous(self) -> None:
        """Switch focus to the previous widget."""
        focusables = (self.query_one("#filter-tabs"), self.query_one("#task-table"))
        current = self.focused
        if current in focusables:
            index = focusables.index(current)
            prev_index = (index - 1) % len(focusables)
            self.set_focus(focusables[prev_index])
        else:
            self.set_focus(focusables[-1])

    def _update_filter_from_tab(self) -> None:
        """Update the current filter and table based on active tab."""
        tabs = self.query_one("#filter-tabs", FocusableTabs)
        if tabs.active_tab is not None:
            self.current_filter = str(tabs.active_tab.label.plain).lower()
            table = self.query_one("#task-table", TaskTable)
            table.filter_state = self.current_filter
            table._populate_table()

    def on_key(self, event: events.Key) -> None:
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
                if table.rows:
                    new_row = max(0, table.cursor_row - 1)
                    table.move_cursor(row=new_row)
                    row_keys = list(table.rows.keys())
                    if 0 <= new_row < len(row_keys):
                        row_key = row_keys[new_row]
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
                if table.rows:
                    new_row = min(len(table.rows) - 1, table.cursor_row + 1)
                    table.move_cursor(row=new_row)
                    row_keys = list(table.rows.keys())
                    if 0 <= new_row < len(row_keys):
                        row_key = row_keys[new_row]
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
