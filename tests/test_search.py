import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from obsidian_cli import Note, RenderLine, collect_search_hits


def _render(raw: str) -> list[RenderLine]:
    return [RenderLine(line, "text") for line in raw.splitlines()]


def _note(name: str, body: str) -> Note:
    return Note(
        path=Path(f"/fake/{name}.md"),
        rel=f"{name}.md",
        stem_rel=name,
        title=name,
        raw=body,
        body=body,
    )


def test_single_note_hit():
    note = _note("a", "foo\nbar\nbaz")
    hits = collect_search_hits([note], "bar", _render)
    assert hits == [(note, 1)]


def test_cross_file():
    n1 = _note("a", "hello world")
    n2 = _note("b", "hello there")
    hits = collect_search_hits([n1, n2], "hello", _render)
    assert hits[0][0] is n1
    assert hits[1][0] is n2
    assert len(hits) == 2


def test_empty_term_returns_nothing():
    note = _note("a", "hello")
    hits = collect_search_hits([note], "", _render)
    assert hits == []


def test_case_insensitive():
    note = _note("a", "Hello World")
    hits = collect_search_hits([note], "hello", _render)
    assert len(hits) == 1


def test_multiple_hits_same_note():
    note = _note("a", "cat\ndog\ncat")
    hits = collect_search_hits([note], "cat", _render)
    assert len(hits) == 2
    assert hits[0] == (note, 0)
    assert hits[1] == (note, 2)
