# Dependent Todos Tool - Command-Line Interface

## Command-Line Interface

### Commands

#### `todos.py add`
Interactive task creation:
1. Prompt for task message
2. Auto-generate slug ID from message (user can override if desired)
3. Show existing task IDs with fuzzy search for dependency selection
4. Allow selecting multiple dependencies interactively
5. Validate for circular dependencies before saving
6. Save to TOML file

**Example flow:**
```
$ python todos.py add
Task message: Implement user authentication
Generated ID: implement-user-authentication (press Enter to accept, or type custom ID)
Dependencies (fuzzy search, press Enter when done):
  > [Type to search existing tasks]
  - setup-database (selected)
  - api-framework (selected)
Task added successfully!
```

#### `todos.py list`
Display all tasks with basic info, showing computed state:
```
ID                              State         Message                      Dependencies
implement-user-authentication   pending       Implement user auth          setup-database, api-framework
setup-database                  done          Setup database               -
api-framework                   done          Setup API framework          -
```

Note: "State" column shows computed state (pending/in-progress/done/blocked/cancelled), not stored status.

#### `todos.py tree [ID]`
Show dependency tree visualization with computed state:
- If ID provided: show tree for that specific task
- If no ID: show all tasks as forest

**Example:**
```
$ python todos.py tree implement-user-authentication
implement-user-authentication: Implement user authentication [pending]
├── setup-database [done]
└── api-framework [done]
     └── install-deps [done]
```

State shown in brackets is the computed state at runtime.

#### `todos.py ready`
Show tasks that are ready to work on (all dependencies completed):
```
Ready to work on:
- auth-001: Implement user authentication
- frontend-setup: Setup frontend framework
```

#### `todos.py done <ID>`
Mark task as complete:
- Validates task exists
- Checks if all dependencies are done
- If dependencies not done: shows warning and asks for confirmation
- Sets status to 'done' and records completion timestamp
- Shows which tasks are now unblocked (no longer blocked)

#### `todos.py remove <ID>`
Remove a task:
- Warns if other tasks depend on it
- Requires confirmation if dependencies exist
- Removes from TOML file

#### `todos.py show <ID>`
Show detailed task information:
```
ID: implement-user-authentication
Message: Implement user authentication
State: pending (computed)
Status: pending (stored)
Created: 2026-01-10 14:30:00
Started: -
Completed: -
Cancelled: false
Dependencies: setup-database, api-framework
Blocks: user-profile, admin-panel
```

#### `todos.py order`
Show topological execution order:
```
Execution order:
1. install-deps
2. api-framework
3. setup-database
4. auth-001
5. user-profile
6. admin-panel
```