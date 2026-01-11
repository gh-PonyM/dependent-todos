"""Command-line interface for dependent todos."""

import click
from datetime import datetime

from .config import get_config_path
from .constants import STATE_COLORS
from .models import Task, TaskList
from .storage import load_tasks_from_file, save_tasks_to_file
from .utils import generate_unique_id


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    envvar="TODOS_CONFIG",
    help="Path to todos configuration file",
)
@click.pass_context
def cli(ctx: click.Context, config_path: str | None) -> None:
    """A command-line task management tool with dependency tracking."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = get_config_path(config_path)


@cli.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all tasks with their current state."""
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    if not tasks:
        click.echo("No tasks found.")
        return

    console = Console()

    # Create a rich table
    table = Table(title="Tasks")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("State", style="magenta")
    table.add_column("Created", style="green")
    table.add_column("Message", style="white")

    # Compute states for all tasks
    task_states = {}
    for task_id, task in tasks.items():
        task_states[task_id] = tasks.get_task_state(task)

    # Use state colors from constants
    state_colors = STATE_COLORS

    def human_friendly_date(dt: datetime) -> str:
        """Return a human-friendly representation of the datetime."""
        now = datetime.now()
        diff = now - dt
        if diff.days == 0:
            if diff.seconds < 3600:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days < 7:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        else:
            return dt.strftime("%Y-%m-%d")

    for task_id, task in sorted(tasks.items()):
        state = task_states[task_id]
        state_text = Text(state, style=state_colors.get(state, "white"))

        created_str = human_friendly_date(task.created)

        # Truncate message if too long
        message = task.message
        if len(message) > 50:
            message = message[:47] + "..."

        table.add_row(task_id, state_text, created_str, message)

    console.print(table)


@cli.command()
@click.argument("task_id", required=False)
@click.pass_context
def tree(ctx: click.Context, task_id: str | None) -> None:
    """Show dependency tree visualization."""

    from rich.console import Console
    from rich.text import Text

    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    if not tasks:
        click.echo("No tasks found.")
        return

    console = Console()

    # Use state colors from constants
    state_colors = STATE_COLORS

    def colorize_tree_output(tree_str: str) -> Text:
        """Colorize the tree output based on task states."""
        lines = tree_str.split("\n")
        colored_lines = []

        for line in lines:
            # Find task ID and state in brackets
            if "[" in line and "]" in line:
                # Extract state from [state]
                start = line.find("[")
                end = line.find("]")
                if start != -1 and end != -1:
                    state = line[start + 1 : end]
                    color = state_colors.get(state, "white")
                    # Color the entire line
                    colored_lines.append(Text(line, style=color))
                else:
                    colored_lines.append(Text(line))
            else:
                colored_lines.append(Text(line))

        # Join with newlines
        result = Text()
        for i, line in enumerate(colored_lines):
            if i > 0:
                result.append("\n")
            result.append(line)
        return result

    if task_id:
        # Show tree for specific task
        if task_id not in tasks:
            click.echo(f"Task '{task_id}' not found.", err=True)
            return
        tree_str = tasks.get_dependency_tree(task_id)
        colored_tree = colorize_tree_output(tree_str)
        console.print(colored_tree)
    else:
        # Show forest of all tasks
        # Group tasks by their root (tasks with no dependencies pointing to them)
        dependents = set()
        for task in tasks.values():
            dependents.update(task.dependencies)

        root_tasks = [tid for tid in tasks.keys() if tid not in dependents]
        root_tasks.sort()  # Consistent ordering

        if not root_tasks:
            # Handle case where there are cycles - just show all tasks
            root_tasks = sorted(tasks.keys())

        for root_id in root_tasks:
            tree_str = tasks.get_dependency_tree(root_id)
            colored_tree = colorize_tree_output(tree_str)
            console.print(colored_tree)


@cli.command()
@click.pass_context
def ready(ctx: click.Context) -> None:
    """Show tasks that are ready to work on (all dependencies completed)."""


    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    ready_tasks = tasks.get_ready_tasks()

    if not ready_tasks:
        click.echo("No tasks are ready to work on.")
        return

    click.echo("Ready to work on:")
    for task_id in ready_tasks:
        task = tasks[task_id]
        click.echo(f"  - {task_id}: {task.message}")


@cli.command()
@click.pass_context
def order(ctx: click.Context) -> None:
    """Show topological execution order."""


    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    if not tasks:
        click.echo("No tasks found.")
        return

    try:
        ordered = tasks.topological_sort()
        click.echo("Execution order:")
        for i, task_id in enumerate(ordered, 1):
            task = tasks[task_id]
            click.echo(f"{i}. {task_id}: {task.message}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("task_id", required=False)
@click.option("--details", is_flag=True, help="Show detailed dependency panels.")
@click.pass_context
def show(ctx: click.Context, task_id: str | None, details: bool) -> None:
    """Show detailed information about a specific task."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table

    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    if not task_id:
        from .dependencies import select_task_interactive

        task_id = select_task_interactive(tasks)
        if not task_id:
            click.echo("No task selected.", err=True)
            return

    task = tasks.get(task_id)
    if not task:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return

    console = Console()

    # Use state colors from constants
    state_colors = STATE_COLORS

    # Main task info panel
    info_table = Table(show_header=False)
    info_table.add_column("Field", style="cyan", width=12)
    info_table.add_column("Value", style="white")

    info_table.add_row("ID", task.id)
    info_table.add_row("Message", task.message)
    info_table.add_row("Status", task.status)
    info_table.add_row("Created", str(task.created))
    info_table.add_row("Started", str(task.started) if task.started else "-")
    info_table.add_row("Completed", str(task.completed) if task.completed else "-")
    info_table.add_row("Cancelled", str(task.cancelled))

    # Add counts if not details
    if not details:
        dep_count = len(task.dependencies)
        dependents = [tid for tid, t in tasks.items() if task_id in t.dependencies]
        block_count = len(dependents)
        info_table.add_row("Blocked By", str(dep_count))
        info_table.add_row("Blocks", str(block_count))

    console.print(Panel(info_table, title=f"Task: {task_id}", border_style="blue"))

    if details:
        # Dependencies section
        if task.dependencies:
            dep_table = Table(show_header=False)
            dep_table.add_column("Dependency ID", style="yellow")
            dep_table.add_column("Message", style="white")

            for dep_id in task.dependencies:
                dep_task = tasks.get(dep_id)
                if dep_task:
                    dep_state = tasks.get_task_state(dep_task)
                    dep_state_text = Text(
                        f"[{dep_state}]", style=state_colors.get(dep_state, "white")
                    )
                    dep_table.add_row(f"{dep_id} {dep_state_text}", dep_task.message)
                else:
                    dep_table.add_row(dep_id, "[not found]")

            console.print(Panel(dep_table, title="Blocked by", border_style="green"))
        else:
            console.print(
                Panel(
                    "No dependencies (not blocked by any task)",
                    title="Dependencies",
                    border_style="green",
                )
            )

        # Tasks that depend on this one
        dependents = [tid for tid, t in tasks.items() if task_id in t.dependencies]
        if dependents:
            block_table = Table(show_header=False)
            block_table.add_column("Task ID", style="red")
            block_table.add_column("Message", style="white")

            for dep_id in dependents:
                dep_task = tasks.get(dep_id)
                if dep_task:
                    dep_state = tasks.get_task_state(dep_task)
                    dep_state_text = Text(
                        f"[{dep_state}]", style=state_colors.get(dep_state, "white")
                    )
                    block_table.add_row(f"{dep_id} {dep_state_text}", dep_task.message)

            console.print(
                Panel(block_table, title="Blocks These Tasks", border_style="red")
            )
        else:
            console.print(
                Panel(
                    "No tasks depend on this one",
                    title="Blocks These Tasks",
                    border_style="red",
                )
            )


@cli.command()
@click.option(
    "--interactive/--no-interactive",
    default=True,
    help="Use interactive dependency selection",
)
@click.pass_context
def add(ctx: click.Context, interactive: bool) -> None:
    """Add a new task interactively."""
    from .dependencies import select_dependencies_interactive

    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    # Get task message
    message = click.prompt("Task message")

    # Generate ID
    existing_ids = set(tasks.keys())
    task_id = generate_unique_id(message, existing_ids)

    # Allow user to override ID
    custom_id = click.prompt(
        f"Generated ID: {task_id} (press Enter to accept, or type custom ID)",
        default="",
    )
    if custom_id:
        # Validate custom ID
        if custom_id in existing_ids:
            click.echo(f"ID '{custom_id}' already exists.", err=True)
            return
        task_id = custom_id

    # Get dependencies
    dependencies = []
    if tasks:
        if interactive:
            # Use interactive fuzzy search
            dependencies = select_dependencies_interactive(
                tasks, exclude_task_id=task_id
            )
        else:
            # Fallback to manual input
            click.echo("Available tasks for dependencies:")
            for tid, task in sorted(tasks.items()):
                click.echo(f"  {tid}: {task.message}")

            dep_input = click.prompt(
                "Dependencies (comma-separated task IDs, or empty for none)", default=""
            )
            if dep_input.strip():
                dep_ids = [d.strip() for d in dep_input.split(",") if d.strip()]

                # Validate dependencies exist
                invalid_deps = [d for d in dep_ids if d not in tasks]
                if invalid_deps:
                    click.echo(
                        f"Invalid dependencies: {', '.join(invalid_deps)}", err=True
                    )
                    return

                dependencies = dep_ids

        # Check for circular dependencies
        if dependencies:
            circular = tasks.detect_circular_dependencies(task_id, dependencies)
            if circular:
                click.echo(
                    f"Circular dependency detected involving: {', '.join(circular)}",
                    err=True,
                )
                return

    # Create task
    task = Task(
        id=task_id,
        message=message,
        dependencies=dependencies,
        status="pending",
        started=None,
        completed=None,
    )

    # Save
    tasks[task_id] = task
    save_tasks_to_file(tasks, config_path)

    click.echo(f"Task '{task_id}' added successfully!")


@cli.command()
@click.argument("task_id", required=False)
@click.option(
    "--interactive/--no-interactive",
    default=True,
    help="Use interactive dependency selection",
)
@click.pass_context
def modify(ctx: click.Context, task_id: str | None, interactive: bool) -> None:
    """Modify an existing task."""
    from .dependencies import select_dependencies_interactive

    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    if not task_id:
        from .dependencies import select_task_interactive

        task_id = select_task_interactive(tasks)
        if not task_id:
            click.echo("No task selected.", err=True)
            return

    task = tasks.get(task_id)
    if not task:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return

    # Get new task message
    message = click.prompt("Task message", default=task.message)

    # Get new dependencies
    click.echo(f"Current dependencies: {', '.join(task.dependencies) or 'none'}")
    dependencies = []
    if tasks:
        if interactive:
            # Use interactive fuzzy search
            dependencies = select_dependencies_interactive(
                tasks, exclude_task_id=task_id
            )
        else:
            # Fallback to manual input
            click.echo("Available tasks for dependencies:")
            for tid, t in sorted(tasks.items()):
                if tid != task_id:
                    click.echo(f"  {tid}: {t.message}")

            dep_input = click.prompt(
                "Dependencies (comma-separated task IDs, or empty for none)", default=""
            )
            if dep_input.strip():
                dep_ids = [d.strip() for d in dep_input.split(",") if d.strip()]

                # Validate dependencies exist
                invalid_deps = [d for d in dep_ids if d not in tasks or d == task_id]
                if invalid_deps:
                    click.echo(
                        f"Invalid dependencies: {', '.join(invalid_deps)}", err=True
                    )
                    return

                dependencies = dep_ids

        # Check for circular dependencies
        if dependencies:
            circular = tasks.detect_circular_dependencies(task_id, dependencies)
            if circular:
                click.echo(
                    f"Circular dependency detected involving: {', '.join(circular)}",
                    err=True,
                )
                return

    # Update task
    task.message = message
    task.dependencies = dependencies

    # Save
    save_tasks_to_file(tasks, config_path)
    click.echo(f"Task '{task_id}' modified successfully!")


@cli.command()
@click.argument("task_id", required=False)
@click.pass_context
def done(ctx: click.Context, task_id: str | None) -> None:
    """Mark a task as completed."""
    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    if not task_id:
        from .dependencies import select_task_interactive

        task_id = select_task_interactive(tasks)
        if not task_id:
            click.echo("No task selected.", err=True)
            return

    task = tasks.get(task_id)
    if not task:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return

    # Check dependencies
    incomplete_deps = []
    for dep_id in task.dependencies:
        dep_task = tasks.get(dep_id)
        if dep_task is None:
            incomplete_deps.append(f"{dep_id} (not found)")
        elif dep_task.status != "done":
            incomplete_deps.append(dep_id)

    if incomplete_deps:
        click.echo("Warning: The following dependencies are not completed:")
        for dep in incomplete_deps:
            click.echo(f"  - {dep}")
        if not click.confirm("Continue anyway?"):
            return

    # Mark as done
    from datetime import datetime

    task.status = "done"
    task.completed = datetime.now()

    save_tasks_to_file(tasks, config_path)
    click.echo(f"Task '{task_id}' marked as done!")

    # Show newly unblocked tasks
    newly_ready = []
    for tid, t in tasks.items():
        if tid != task_id and t.status == "pending":
            # Check if this task was blocked only by the completed task
            was_blocked = any(dep == task_id for dep in t.dependencies)
            if was_blocked:
                # Check if all other deps are done
                other_deps_done = all(
                    tasks.get(dep_id) and tasks[dep_id].status == "done"
                    for dep_id in t.dependencies
                    if dep_id != task_id
                )
                if other_deps_done:
                    newly_ready.append(tid)

    if newly_ready:
        click.echo("Tasks now ready to work on:")
        for tid in newly_ready:
            click.echo(f"  - {tid}: {tasks[tid].message}")


@cli.command()
@click.argument("task_id", required=False)
@click.pass_context
def remove(ctx: click.Context, task_id: str | None) -> None:
    """Remove a task."""
    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    if not task_id:
        from .dependencies import select_task_interactive

        task_id = select_task_interactive(tasks)
        if not task_id:
            click.echo("No task selected.", err=True)
            return

    task = tasks.get(task_id)
    if not task:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return

    # Check if other tasks depend on this one
    dependents = [tid for tid, t in tasks.items() if task_id in t.dependencies]
    if dependents:
        click.echo(f"Warning: The following tasks depend on '{task_id}':")
        for dep in dependents:
            click.echo(f"  - {dep}")
        if not click.confirm("Remove anyway?"):
            return

    # Remove the task
    del tasks[task_id]
    save_tasks_to_file(tasks, config_path)
    click.echo(f"Task '{task_id}' removed!")


@cli.command()
@click.pass_context
def tui(ctx: click.Context) -> None:
    """Launch the Textual TUI interface."""
    from .tui import run_tui

    run_tui()
