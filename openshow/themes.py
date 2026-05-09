from .models import Theme


THEMES: dict[str, Theme] = {
    "ink": Theme(
        name="ink",
        label="Ink",
        bg_color=17,
        bg_rgb=(90, 102, 149),  # #171a26
        pair_colors={
            1: 67,
            2: 81,
            3: 114,
            4: 110,
            5: -1,
            6: 75,
            7: 111,
        },
    ),
    "graphite": Theme(
        name="graphite",
        label="Graphite",
        bg_color=235,
        bg_rgb=None,
        pair_colors={
            1: 245,
            2: 208,
            3: 15,
            4: 250,
            5: 15,
            6: 214,
            7: 208,
        },
    ),
    "transparent": Theme(
        name="transparent",
        label="Transparent",
        bg_color=-1,
        bg_rgb=None,
        pair_colors={
            1: 245,
            2: 208,
            3: 15,
            4: 250,
            5: 15,
            6: 214,
            7: 208,
        },
    ),
}
THEME_ORDER = list(THEMES)
