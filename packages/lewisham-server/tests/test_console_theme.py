from lewisham_server.console_theme import (
    LEWISHAM_COOL_GREY,
    LEWISHAM_DARK_BLUE,
    LEWISHAM_DEEP_BLUE,
    LEWISHAM_TURQUOISE,
    LEWISHAM_YELLOW,
)


def test_console_palette_matches_lewisham_brand_colours() -> None:
    assert LEWISHAM_DARK_BLUE == "#1E3451"
    assert LEWISHAM_DEEP_BLUE == "#2B4972"
    assert LEWISHAM_TURQUOISE == "#009EB3"
    assert LEWISHAM_COOL_GREY == "#D4DAE2"
    assert LEWISHAM_YELLOW == "#FBDC2B"
