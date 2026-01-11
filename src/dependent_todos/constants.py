TASK_ID_MAX_LEN = 30
TASK_ID_RE_PATT = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"

# Color mapping for task states
STATE_COLORS = {
    "pending": "yellow",
    "in-progress": "blue",
    "done": "green",
    "blocked": "red",
    "cancelled": "dim red",
}
