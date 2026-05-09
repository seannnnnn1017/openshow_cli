from typing import Callable

from .models import Note, RenderLine


def collect_search_hits(
    notes: list[Note],
    term: str,
    render_fn: Callable[[str], list[RenderLine]],
    render_note_fn: Callable[[Note], list[RenderLine]] | None = None,
) -> list[tuple[Note, int]]:
    hits: list[tuple[Note, int]] = []
    lower = term.lower()
    if not lower:
        return hits
    for note in notes:
        rendered = render_note_fn(note) if render_note_fn else render_fn(note.raw)
        for line_index, line in enumerate(rendered):
            if lower in line.text.lower():
                hits.append((note, line_index))
    return hits
