"""Lewisham Council's brand palette adapted for terminal output."""

from rich.theme import Theme

LEWISHAM_DARK_BLUE = "#1E3451"
LEWISHAM_DEEP_BLUE = "#2B4972"
LEWISHAM_TURQUOISE = "#009EB3"
LEWISHAM_COOL_GREY = "#D4DAE2"
LEWISHAM_YELLOW = "#FBDC2B"

LEWISHAM_CONSOLE_THEME = Theme(
    {
        "lewisham.panel": f"{LEWISHAM_COOL_GREY} on {LEWISHAM_DARK_BLUE}",
        "lewisham.border": f"{LEWISHAM_YELLOW} on {LEWISHAM_DARK_BLUE}",
        "lewisham.crown": f"bold {LEWISHAM_YELLOW} on {LEWISHAM_DARK_BLUE}",
        "lewisham.title": f"bold {LEWISHAM_YELLOW} on {LEWISHAM_DARK_BLUE}",
        "lewisham.subtitle": f"{LEWISHAM_COOL_GREY} on {LEWISHAM_DARK_BLUE}",
    }
)
