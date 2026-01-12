# dependent_todos

A CLI/TUI tool for dependent todo management.

## Installation

Requires Python >= 3.11.

Install using uv:

    uv tool install git+https://github.com/gh-PonyM/dependent-todos

## Usage

Run the TUI:

    dependent-todos --help

To use a global config not per repo:

    mkdir -p  ~/.config/todos
    echo 'export TODOS_CONFIG=~/.config/todos' >> ~/.bashrc

## Tests

to run the tests:

    uv run pytest