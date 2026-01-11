# Dependent Todos Repository Summary

## Overview
This repository contains a command-line and textual user interface (TUI) tool for managing dependent tasks/todos. It allows users to create tasks with dependencies, track their status, and visualize dependency trees.

## Key Features
- **Task Management**: Add, modify, remove, and mark tasks as done
- **Dependency Tracking**: Tasks can depend on other tasks, with automatic cycle detection
- **Interactive CLI**: Fuzzy search for selecting dependencies and tasks
- **Rich Output**: Colorized console output using Rich library
- **TUI Interface**: Textual-based graphical interface for task management
- **Topological Sorting**: Show execution order based on dependencies
- **State Management**: Tasks have states like pending, in-progress, blocked, done, cancelled
- **TOML Storage**: Persistent storage using TOML format

## Architecture
- **Language**: Python 3.11+
- **CLI Framework**: Click
- **Data Models**: Pydantic v2 for validation and serialization
- **TUI**: Textual library
- **Output**: Rich for console formatting
- **Storage**: TOML files with tomli_w/tomllib
- **Dependencies**: graphlib for topological sorting

## Project Structure
- `src/dependent_todos/`: Main package
  - `main.py`: CLI commands and entry point
  - `models.py`: Pydantic models for Task and TaskList
  - `tui.py`: Textual TUI implementation
  - `storage.py`: File I/O operations
  - `utils.py`: Utility functions
  - `dependencies.py`: Interactive dependency selection
  - `constants.py`: Constants and patterns
- `plan/`: Development planning documents
- `pyproject.toml`: Project configuration with uv
- `README.md`: Basic documentation

## CLI Commands
- `list`: Display all tasks in a table
- `tree`: Show dependency tree visualization
- `ready`: Show tasks ready to work on
- `order`: Display topological execution order
- `show`: Detailed task information
- `add`: Create new tasks with dependencies
- `modify`: Update existing tasks
- `done`: Mark tasks as completed
- `remove`: Delete tasks
- `tui`: Launch the Textual interface

## Development
- Uses `uv` for dependency management and running
- Test suite with pytest
- Type checking with pyright
- Linting with ruff
- CI/CD with GitHub Actions

## Key Design Decisions
- Single binary executable via uv scripts
- TOML for human-readable storage
- Pydantic for data validation
- Topological sorting for dependency resolution
- Interactive fuzzy search for usability

## Development Insights
- **TUI Dependency Selection Consistency**: When implementing dependency selection in the TUI, ensure consistency with CLI behavior by excluding done tasks from selection lists. This prevents users from creating dependencies on completed tasks, which would be illogical.
- **Label Consistency**: Use consistent terminology across the application. For example, use "Depends on" and "Depending on" in TUI modals as preferred labeling convention.
- **Incremental Testing**: When fixing UI issues, update tests and snapshots incrementally to maintain test coverage and catch regressions early.</content>
<parameter name="filePath">AGENTS.md