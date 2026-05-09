import json
from pathlib import Path

from .constants import CODE_EXTENSIONS, HEADING_RE, NOTEBOOK_EXTENSIONS, SUPPORTED_FILE_EXTENSIONS, TEXT_EXTENSIONS
from .models import Note, TreeItem


class Vault:
    def __init__(self, source: Path):
        self.source = source.resolve()
        self.single_file = self.source.is_file()
        self.root = self.source.parent if self.single_file else self.source
        self.display_name = self.source.name if self.single_file else f"{self.source.name}/"
        self.notes: list[Note] = []
        self.by_stem: dict[str, Note] = {}
        self.by_rel: dict[str, Note] = {}
        self.reload()

    def iter_document_paths(self) -> list[Path]:
        if self.single_file:
            return [self.source]
        return [
            path
            for path in sorted(self.root.rglob("*"))
            if path.is_file() and is_supported_document(path)
        ]

    def signature(self) -> tuple[tuple[str, int, int], ...]:
        items: list[tuple[str, int, int]] = []
        for path in self.iter_document_paths():
            try:
                stat = path.stat()
            except OSError:
                continue
            rel = path.relative_to(self.root).as_posix()
            items.append((rel, stat.st_mtime_ns, stat.st_size))
        return tuple(items)

    def reload(self) -> None:
        self.notes.clear()
        self.by_stem.clear()
        self.by_rel.clear()

        for path in self.iter_document_paths():
            raw, body, kind, editable = read_document(path)
            rel = path.relative_to(self.root).as_posix()
            stem_rel = Path(rel).with_suffix("").as_posix()
            note = Note(
                path=path,
                rel=rel,
                stem_rel=stem_rel,
                title=extract_title(body, stem_rel),
                raw=raw,
                body=body,
                kind=kind,
                editable=editable,
            )
            self.notes.append(note)
            self.by_rel[rel.lower()] = note
            self.by_stem[stem_rel.lower()] = note
            self.by_stem[Path(stem_rel).name.lower()] = note

    def resolve_link(self, target: str | None) -> Note | None:
        if not target:
            return None
        clean = target.strip().replace("\\", "/").lower()
        stem = Path(clean).with_suffix("").as_posix() if Path(clean).suffix else clean
        return (
            self.by_rel.get(clean)
            or self.by_stem.get(stem)
            or self.by_stem.get(Path(stem).name)
            or self.by_rel.get(f"{stem}.md")
        )

    def default_note(self) -> Note | None:
        return self.resolve_link("index") or (self.notes[0] if self.notes else None)

    def tree_items(self) -> list[TreeItem]:
        items: list[TreeItem] = []
        dirs_seen: set[str] = set()
        for note in self.notes:
            parts = note.rel.split("/")
            prefix = []
            for depth, part in enumerate(parts[:-1]):
                prefix.append(part)
                key = "/".join(prefix)
                if key not in dirs_seen:
                    dirs_seen.add(key)
                    items.append(TreeItem(part, key, depth, True))
            items.append(TreeItem(parts[-1], note.rel, len(parts) - 1, False, note))
        return items


def is_supported_document(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_FILE_EXTENSIONS


def read_text_document(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def source_lines(source) -> list[str]:
    if isinstance(source, list):
        return [str(part) for part in source]
    if isinstance(source, str):
        return source.splitlines(keepends=True)
    return []


def notebook_outputs_text(outputs: list[dict]) -> list[str]:
    lines: list[str] = []
    for output in outputs:
        output_type = output.get("output_type", "output")
        if output_type == "stream":
            text = output.get("text", "")
        elif output_type in ("execute_result", "display_data"):
            data = output.get("data", {})
            text = data.get("text/plain", "")
        elif output_type == "error":
            traceback = output.get("traceback")
            text = traceback if traceback else [output.get("ename", "Error"), output.get("evalue", "")]
        else:
            text = ""
        rendered = "".join(source_lines(text)).strip("\n")
        if rendered:
            lines.extend(rendered.splitlines())
    return lines


def notebook_to_markdown(path: Path) -> str:
    try:
        data = json.loads(read_text_document(path))
    except (OSError, json.JSONDecodeError) as exc:
        return f"# {path.name}\n\nCould not parse notebook: {exc}\n"

    chunks: list[str] = [f"# {path.name}"]
    for index, cell in enumerate(data.get("cells", []), start=1):
        cell_type = cell.get("cell_type", "cell")
        lines = source_lines(cell.get("source", []))
        source = "".join(lines).rstrip("\n")
        if cell_type == "markdown":
            if source:
                chunks.append(source)
        elif cell_type == "code":
            execution_count = cell.get("execution_count")
            label = f"python input {execution_count}" if execution_count is not None else "python input"
            chunks.append(f"```{label}\n{source}\n```")
            outputs = notebook_outputs_text(cell.get("outputs", []))
            if outputs:
                chunks.append("```text output\n" + "\n".join(outputs) + "\n```")
        else:
            if source:
                chunks.append(f"```text {cell_type} {index}\n{source}\n```")
    return "\n\n".join(chunks).rstrip() + "\n"


def read_document(path: Path) -> tuple[str, str, str, bool]:
    suffix = path.suffix.lower()
    if suffix in NOTEBOOK_EXTENSIONS:
        raw = notebook_to_markdown(path)
        return raw, raw, "notebook", False
    raw = read_text_document(path)
    if suffix in CODE_EXTENSIONS:
        return raw, raw, "code", True
    if suffix in TEXT_EXTENSIONS:
        return raw, raw, "text", True
    return raw, strip_frontmatter(raw), "markdown", True


def strip_frontmatter(raw: str) -> str:
    if raw.startswith("---\n"):
        end = raw.find("\n---", 4)
        if end != -1:
            after = raw.find("\n", end + 4)
            return raw[after + 1 :] if after != -1 else ""
    return raw


def split_frontmatter(raw: str) -> tuple[list[tuple[str, str]], str]:
    if not raw.startswith("---\n"):
        return [], raw
    end = raw.find("\n---", 4)
    if end == -1:
        return [], raw

    frontmatter: list[tuple[str, str]] = []
    for line in raw[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter.append((key.strip(), value.strip()))

    after = raw.find("\n", end + 4)
    body = raw[after + 1 :] if after != -1 else ""
    return frontmatter, body


def extract_title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        match = HEADING_RE.match(line)
        if match:
            return match.group(2)
    return fallback
