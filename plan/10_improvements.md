# Improvements

- change the default location when invoked to use a local config file in the same path, unless the env var is set. 
- tree command: show a line too much between unrelated entries.
- show command: Just show the small table without the task. 
- show command: add flag --details that shows the panels with dependencies. otherwise just the count of task depending on and dependent on.
- done and show and remove commands: if no id is provided, let the user select on with fuzzy search
- Add another command to modify a task: similar to the add menu, but the dependencies can be modified. Check if dependencies have multi select capabilities
- list command. Show the date created in a human friend way as the date

## TUI

- I want the config path be shown in the bottom footer
- For adding a new task, I want a modal to be called and an action added I can select with Ctrl+P (the palette)
- For all other actions, we can use the command palette to generate actions for update, delete of tasks using modals as well.
- The listing of the tasks inside the in the table could be colored the same way
- I want to replace all the buttons with key commands
- When I switch around tasks in the table, I want the area with "Select a task to view details" to be auto-updated.
- Filtering for "ready", "done", "pending": Implement a bar with small colored tabs, which can be switched with tab and shift+tab or numbers (start with 0 for all). when it is switched, updated the list of the todo apps.

## General

- If applicable, refactor constants, such as for colors