from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Note:
    path: Path
    rel: str
    stem_rel: str
    title: str
    raw: str = ""
    body: str = ""
    kind: str = "markdown"
    editable: bool = True


@dataclass
class TreeItem:
    label: str
    path: str
    depth: int
    is_dir: bool
    note: Note | None = None


@dataclass
class RenderLink:
    start: int
    end: int
    text: str
    target: str
    anchor: str | None = None


@dataclass
class RenderLine:
    text: str
    kind: str = "text"
    source_line: int = 0
    heading_level: int = 0
    heading_text: str = ""
    links: list[RenderLink] = field(default_factory=list)
    code_lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Theme:
    name: str
    label: str
    bg_color: int
    bg_rgb: tuple[int, int, int] | None
    pair_colors: dict[int, int]
