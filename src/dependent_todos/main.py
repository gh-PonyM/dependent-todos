"""Command-line interface for dependent todos."""

import click
from pathlib import Path
from typing import Dict, Optional

from .config import get_config_path
from .models import Task
from .storage import load_tasks_from_file, save_tasks_to_file
from .utils import generate_unique_id


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    help="Path to todos configuration file",
)
@click.pass_context
def cli(ctx: click.Context, config_path: Optional[str]) -> None:
    """A command-line task management tool with dependency tracking."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = get_config_path(config_path)


@cli.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all tasks with their current state."""
    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    if not tasks:
        click.echo("No tasks found.")
        return

    # Compute states for all tasks
    task_states = {}
    for task_id, task in tasks.items():
        task_states[task_id] = task.compute_state(tasks)

    # Display tasks in a table-like format
    click.echo(f"{'ID':<30} {'State':<12} {'Message'}")
    click.echo("-" * 80)

    for task_id, task in sorted(tasks.items()):
        state = task_states[task_id]
        # Truncate message if too long
        message = task.message
        if len(message) > 35:
            message = message[:32] + "..."

        click.echo(f"{task_id:<30} {state:<12} {message}")


@cli.command()
@click.argument("task_id")
@click.pass_context
def show(ctx: click.Context, task_id: str) -> None:
    """Show detailed information about a specific task."""
    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

    task = tasks.get(task_id)
    if not task:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return

    state = task.compute_state(tasks)

    click.echo(f"ID: {task.id}")
    click.echo(f"Message: {task.message}")
    click.echo(f"State: {state} (computed)")
    click.echo(f"Status: {task.status} (stored)")
    click.echo(f"Created: {task.created}")
    click.echo(f"Started: {task.started or '-'}")
    click.echo(f"Completed: {task.completed or '-'}")
    click.echo(f"Cancelled: {task.cancelled}")
    click.echo(f"Dependencies: {', '.join(task.dependencies) or '-'}")

    # Show tasks that depend on this one
    dependents = [tid for tid, t in tasks.items() if task_id in t.dependencies]
    click.echo(f"Blocks: {', '.join(dependents) or '-'}")


@cli.command()
@click.pass_context
def add(ctx: click.Context) -> None:
    """Add a new task interactively."""
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

    # Create task
    task = Task(id=task_id, message=message)

    # Save
    tasks[task_id] = task
    save_tasks_to_file(tasks, config_path)

    click.echo(f"Task '{task_id}' added successfully!")


@cli.command()
@click.argument("task_id")
@click.pass_context
def done(ctx: click.Context, task_id: str) -> None:
    """Mark a task as completed."""
    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

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
@click.argument("task_id")
@click.pass_context
def remove(ctx: click.Context, task_id: str) -> None:
    """Remove a task."""
    config_path = ctx.obj["config_path"]
    tasks = load_tasks_from_file(config_path)

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


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
