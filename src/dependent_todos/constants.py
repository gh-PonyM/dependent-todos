TASK_ID_MAX_LEN = 30
TASK_ID_RE_PATT = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
TODOS_CONFIG_ENV_KEY = "TODOS_CONFIG"
TODOS_CONFIG_NAME = "./todos.toml"

# Color mapping for task states
STATE_COLORS = {
    "pending": "yellow",
    "in-progress": "blue",
    "done": "green",
    "blocked": "red",
    "cancelled": "dim red",
}
