from dependent_todos.tui import BaseModalScreen


def test_modal_snapshot(snap_compare):
    """Test snapshot of the quit modal."""

    async def run_before(pilot):
        await pilot.app.push_screen(BaseModalScreen())

    assert snap_compare("../src/dependent_todos/tui.py", run_before=run_before)
