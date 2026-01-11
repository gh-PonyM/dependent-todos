# Refactor Plan for Dependent Todos

This plan outlines a series of atomic commits to address TODOs from the last commit (`3a580fde4: chore: add comments code review and some changes`). Each commit targets a specific scope, ensures tests pass with `uv run pytest`, and maintains backward compatibility.

## Context from Last Commit
- **Commit**: `3a580fde4 chore: add comments code review and some changes`
- **Changed Files**: `constants.py`, `dependencies.py`, `main.py`, `models.py`, `storage.py`, `tui.py`, `utils.py`, tests, snapshots
- **Active TODOs**: In `models.py`, `dependencies.py`, `storage.py`, `utils.py`, `tui.py`, `test_tui.py` (excluding design docs under `plan/`).

## 1. Introduce TaskList Root Model and Move Status Logic
- **Scope**: One commit.
- **Changes**:
  - In `models.py`: Add `TaskList` Pydantic model to hold `dict[str, Task]` and own collection methods.
  - Move `Task.compute_state` logic to `TaskList.recompute_status(task: Task) -> StatusT`.
  - Update callers in `dependencies.py`, `main.py`, `tui.py`, tests to use `TaskList`.
- **Rationale**: Addresses `models.py:37` (move to TaskList), `models.py:70` (add TaskList).
- **Verification**: Run `uv run pytest`.

## 2. Move Dependency-Graph Operations onto TaskList
- **Scope**: One commit (after TaskList exists).
- **Changes**:
  - In `dependencies.py`: Convert free functions (`detect_circular_dependencies`, `topological_sort`, etc.) to `TaskList` methods.
  - Simplify cycle error handling: Remove unnecessary `ValueError` wrap or enrich it with cycle details.
  - Update `main.py`, `tui.py`.
- **Rationale**: Addresses `dependencies.py:67` (custom error).
- **Verification**: Run `uv run pytest`.

## 3. Clean Up Storage: Let Pydantic Handle Parsing/Serialization
- **Scope**: One commit.
- **Changes**:
  - In `storage.py`: Replace manual parsing with Pydantic (remove `_parse_datetime`).
  - Use `Task.model_dump(mode="json")` for serialization.
  - Add `TaskList.load/save` or equivalent.
- **Rationale**: Addresses `storage.py:12, 25, 66, 84, 92`.
- **Verification**: Run `uv run pytest`.

## 4. Make utils.generate_unique_id Boundary-Safe and Word-Aware
- **Scope**: One commit.
- **Changes**:
  - In `utils.py`: Implement word-boundary truncation for `generate_unique_id`.
  - Add unit tests for edge cases.
- **Rationale**: Addresses `utils.py:52`.
- **Verification**: Run `uv run pytest`.

## 5. Refine TUI Components and Responsibilities
- **Scope**: One or two commits.
- **5a. TaskDetails Refactor**:
  - Extract `OrderDetails` from `TaskDetails` for execution order display.
  - Update `DependentTodosApp` to switch components.
- **5b. Modal Layout and Sidebar/Tree Lifecycle**:
  - Clarify `BaseModalScreen` grid behavior.
  - Improve tree recomposition on tab switches.
  - Use constants for widget IDs.
- **Rationale**: Addresses `tui.py:162, 272, 559, 770` and test TODOs.
- **Verification**: Run `uv run pytest` (update snapshots/tests as needed).

## 6. Harmonize CLI (main.py) with TaskList/Storage Changes
- **Scope**: One commit (after 1-3).
- **Changes**:
  - Use `TaskList` in `main.py` for loading/saving.
  - Centralize state colors.
- **Rationale**: Align CLI with new domain model.
- **Verification**: Run `uv run pytest`.

## 7. Clean Up Testing TODOs and Consolidate Tests
- **Scope**: Small commits.
- **Changes**:
  - In `test_tui.py`: Use app properties, consolidate overlapping tests.
- **Rationale**: Addresses all test TODOs in `test_tui.py`.
- **Verification**: Run `uv run pytest`.

## 8. (Optional) Align Design Docs with Implementation
- **Scope**: Docs-only commit.
- **Changes**:
  - Update `plan/*.md` to reflect `TaskList`, storage, TUI changes.
- **Rationale**: Resolve design TODOs.

## Execution Notes
- Start with Commit 1 (TaskList).
- After each commit: Run `uv run pytest`, commit if green.
- Request detailed code changes for a specific commit if needed.