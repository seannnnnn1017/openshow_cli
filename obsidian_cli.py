#!/usr/bin/env python3
import argparse
import curses
import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


CTRL_E = 5
CTRL_F = 6
CTRL_G = 7
CTRL_S = 19
CTRL_T = 20
ESC = 27

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)?(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
HR_RE = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")
VAULT_POLL_SECONDS = 1.0


@dataclass
class Note:
    path: Path
    rel: str
    stem_rel: str
    title: str
    raw: str = ""
    body: str = ""


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


THEMES: dict[str, Theme] = {
    "ink": Theme(
        name="ink",
        label="Ink",
        bg_color=17,
        bg_rgb=(90, 102, 149),  # #171a26
        pair_colors={
            1: 67,    # table / meta
            2: 81,    # H1/H2 heading
            3: 114,   # code block
            4: 110,   # blockquote
            5: -1,    # default foreground
            6: 75,    # H3/H4 heading
            7: 111,   # links
        },
    ),
    "graphite": Theme(
        name="graphite",
        label="Graphite",
        bg_color=235,            # xterm-256 #262626, dark graphite gray
        bg_rgb=None,
        pair_colors={
            1: 245,   # muted gray for metadata/table lines
            2: 208,   # orange primary accent
            3: 15,    # white code text
            4: 250,   # light gray quote text
            5: 15,    # white body text
            6: 214,   # warm orange secondary heading
            7: 208,   # orange links/actions
        },
    ),
    "transparent": Theme(
        name="transparent",
        label="Transparent",
        bg_color=-1,             # terminal default background
        bg_rgb=None,
        pair_colors={
            1: 245,   # muted gray for metadata/table lines
            2: 208,   # orange primary accent
            3: 15,    # white code text
            4: 250,   # light gray quote text
            5: 15,    # white body text
            6: 214,   # warm orange secondary heading
            7: 208,   # orange links/actions
        },
    ),
}
THEME_ORDER = list(THEMES)


class Vault:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.notes: list[Note] = []
        self.by_stem: dict[str, Note] = {}
        self.by_rel: dict[str, Note] = {}
        self.reload()

    def signature(self) -> tuple[tuple[str, int, int], ...]:
        items: list[tuple[str, int, int]] = []
        for path in sorted(self.root.rglob("*.md")):
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

        for path in sorted(self.root.rglob("*.md")):
            raw = path.read_text(encoding="utf-8")
            body = strip_frontmatter(raw)
            rel = path.relative_to(self.root).as_posix()
            stem_rel = rel[:-3]
            note = Note(
                path=path,
                rel=rel,
                stem_rel=stem_rel,
                title=extract_title(body, stem_rel),
                raw=raw,
                body=body,
            )
            self.notes.append(note)
            self.by_rel[rel.lower()] = note
            self.by_stem[stem_rel.lower()] = note
            self.by_stem[Path(stem_rel).name.lower()] = note

    def resolve_link(self, target: str | None) -> Note | None:
        if not target:
            return None
        clean = target.strip().removesuffix(".md").lower()
        return self.by_stem.get(clean) or self.by_rel.get(f"{clean}.md")

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


def slugify_heading(text: str) -> str:
    return re.sub(r"\s+", "-", text.strip().lower())


def strip_inline_markup(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"\1", text)
    return text


def display_width(s: str) -> int:
    w = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        w += 2 if eaw in ("W", "F") else 1
    return w


def visual_ljust(s: str, width: int) -> str:
    return s + " " * max(0, width - display_width(s))


def truncate_to_display_width(s: str, max_width: int) -> str:
    total = 0
    for i, ch in enumerate(s):
        w = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if total + w > max_width:
            return s[:i]
        total += w
    return s


def visual_x_to_char_index(line: str, target_vx: int) -> int:
    vx = 0
    for i, ch in enumerate(line):
        w = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if vx + w > target_vx:
            return i
        vx += w
    return len(line)


def offset_links(
    links: list[RenderLink], offset: int
) -> list[RenderLink]:
    return [
        RenderLink(link.start + offset, link.end + offset, link.text, link.target, link.anchor)
        for link in links
    ]


def collect_search_hits(
    notes: list[Note],
    term: str,
    render_fn: Callable[[str], list[RenderLine]],
) -> list[tuple[Note, int]]:
    hits: list[tuple[Note, int]] = []
    lower = term.lower()
    if not lower:
        return hits
    for note in notes:
        rendered = render_fn(note.raw)
        for line_index, line in enumerate(rendered):
            if lower in line.text.lower():
                hits.append((note, line_index))
    return hits


def prompt(stdscr, message: str) -> str:
    height, width = stdscr.getmaxyx()
    curses.echo()
    set_cursor(1)
    stdscr.move(height - 1, 0)
    stdscr.clrtoeol()
    safe_addstr(stdscr, height - 1, 0, message[: width - 1], curses.A_REVERSE)
    stdscr.refresh()
    value = stdscr.getstr(height - 1, min(len(message), width - 2), max(1, width - len(message) - 1))
    curses.noecho()
    set_cursor(0)
    return value.decode("utf-8", errors="ignore").strip()


def safe_addstr(win, y: int, x: int, text: str, attr: int = 0) -> None:
    height, width = win.getmaxyx()
    if y < 0 or y >= height or x >= width:
        return
    try:
        win.addnstr(y, x, text, max(0, width - x - 1), attr)
    except curses.error:
        pass


def set_cursor(visibility: int) -> None:
    try:
        curses.curs_set(visibility)
    except curses.error:
        pass


def copy_to_clipboard(text: str) -> bool:
    import subprocess, shutil
    data = text.encode()
    for cmd in (["clip.exe"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=data, check=True, timeout=3)
                return True
            except Exception:
                pass
    # OSC 52 fallback
    import base64, sys
    b64 = base64.b64encode(data).decode()
    sys.stdout.write(f"\033]52;c;{b64}\007")
    sys.stdout.flush()
    return True


def init_terminal(theme: Theme) -> bool:
    for setup in (
        curses.use_default_colors,
        lambda: curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION),
    ):
        try:
            setup()
        except curses.error:
            pass
    has_256 = False
    try:
        if curses.has_colors():
            curses.start_color()
            has_256 = curses.COLORS >= 256
            if has_256:
                if curses.can_change_color() and theme.bg_rgb:
                    curses.init_color(theme.bg_color, *theme.bg_rgb)
                for pair_id, fg in theme.pair_colors.items():
                    curses.init_pair(pair_id, fg, theme.bg_color)
            else:
                curses.init_pair(1, curses.COLOR_CYAN, -1)
                curses.init_pair(2, curses.COLOR_CYAN, -1)
                curses.init_pair(3, curses.COLOR_GREEN, -1)
                curses.init_pair(4, curses.COLOR_CYAN, -1)
                curses.init_pair(5, curses.COLOR_WHITE, -1)
                curses.init_pair(6, curses.COLOR_CYAN, -1)
                curses.init_pair(7, curses.COLOR_CYAN, -1)
    except curses.error:
        pass
    return has_256


def key_code(key) -> int | None:
    if isinstance(key, str) and len(key) == 1:
        return ord(key)
    if isinstance(key, int):
        return key
    return None


def parent_path(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


class App:
    def __init__(self, stdscr, vault_path: Path, theme_name: str = "transparent"):
        self.stdscr = stdscr
        self.vault = Vault(vault_path)
        self.tree = self.vault.tree_items()
        self.collapsed_dirs: set[str] = set()
        self.current = self.vault.default_note()
        self.mode = "view"
        self.sidebar_visible = True
        self.nav_index = self.index_for_note(self.current)
        self.nav_scroll = 0
        self.view_scroll = 0
        self.status = ""
        self.search_term = ""
        self.search_hits: list[tuple[Note, int]] = []
        self.search_hit_index = -1
        self.toc: list[tuple[int, int, str]] = []
        self.toc_visible = True
        self.toc_index = 0
        self.toc_scroll = 0
        self.page_links: list[Note] = []
        self.page_backlinks: list[Note] = []
        self.page_link_scroll = 0
        self.focus = "nav"
        self.rendered: list[RenderLine] = []
        self.edit_lines: list[str] = []
        self.edit_y = 0
        self.edit_x = 0
        self.edit_scroll = 0
        self.viewer_content_height = 1
        self.has_256_colors = False
        self.theme_name = theme_name
        self.theme_popup_index = THEME_ORDER.index(theme_name)
        self.graph_side = "links"
        self.graph_index = 0
        self.graph_scroll = 0
        self.vault_signature = self.vault.signature()
        self.next_vault_check = 0.0
        self.popup_index = 0
        self.popup_scroll = 0
        self.open_note(self.current)

    def run(self) -> None:
        set_cursor(0)
        curses.raw()  # disable XON/XOFF so Ctrl+S is not intercepted as flow-control
        self.has_256_colors = init_terminal(self.theme)
        self.stdscr.keypad(True)
        while True:
            self.draw()
            key = self.stdscr.get_wch()
            code = key_code(key)
            if code == ord("q") and self.mode == "view":
                break
            if self.mode == "edit":
                self.handle_edit_key(key)
            elif self.mode == "nav_popup":
                self.handle_nav_popup_key(key)
            elif self.mode == "theme_popup":
                self.handle_theme_popup_key(key)
            elif self.mode in ("graph_popup", "graph_full"):
                self.handle_graph_key(key)
            else:
                self.handle_view_key(key)

    @property
    def theme(self) -> Theme:
        return THEMES[self.theme_name]

    def apply_theme(self, theme_name: str) -> None:
        normalized = theme_name.strip().lower()
        if not normalized:
            current_index = THEME_ORDER.index(self.theme_name)
            normalized = THEME_ORDER[(current_index + 1) % len(THEME_ORDER)]
        if normalized not in THEMES:
            choices = ", ".join(THEME_ORDER)
            self.status = f"Unknown theme: {theme_name}. Choices: {choices}"
            return
        self.theme_name = normalized
        self.theme_popup_index = THEME_ORDER.index(normalized)
        self.has_256_colors = init_terminal(self.theme)
        color_note = "256-color" if self.has_256_colors else "basic color fallback"
        self.status = f"Theme: {self.theme.label} ({color_note})"

    def reload_vault(self, status: str, preserve_scroll: bool = True) -> None:
        current_rel = self.current.rel if self.current else ""
        view_scroll = self.view_scroll
        mode = self.mode
        self.vault.reload()
        self.vault_signature = self.vault.signature()
        self.tree = self.vault.tree_items()
        existing_dirs = {item.path for item in self.tree if item.is_dir}
        self.collapsed_dirs.intersection_update(existing_dirs)
        reopened = self.vault.by_rel.get(current_rel.lower()) if current_rel else None
        if not reopened:
            reopened = self.vault.default_note()
        self.open_note(reopened)
        if preserve_scroll and reopened and reopened.rel == current_rel:
            self.view_scroll = min(view_scroll, self.viewer_scroll_limit())
        if mode in ("graph_popup", "graph_full") and self.current:
            self.mode = mode
            self.clamp_graph_selection()
        self.status = status

    def check_vault_updates(self) -> None:
        if self.mode == "edit":
            return
        now = time.monotonic()
        if now < self.next_vault_check:
            return
        self.next_vault_check = now + VAULT_POLL_SECONDS
        signature = self.vault.signature()
        if signature == self.vault_signature:
            return
        self.reload_vault("Vault reloaded after external change")

    def open_note(self, note: Note | None, anchor: str | None = None) -> None:
        if not note:
            self.status = "No markdown notes found"
            return
        self.expand_note_parents(note)
        self.current = note
        note.raw = note.path.read_text(encoding="utf-8")
        note.body = strip_frontmatter(note.raw)
        self.rendered = self.render_markdown(note.raw)
        self.toc = self.extract_toc()
        self.page_links = self.extract_page_links(note)
        self.page_backlinks = self.extract_backlinks(note)
        self.toc_index = 0
        self.toc_scroll = 0
        self.page_link_scroll = 0
        self.view_scroll = 0
        if anchor:
            self.jump_to_anchor(anchor)
        self.nav_index = self.index_for_note(note)
        if not self.search_term:
            self.search_hits = []
            self.search_hit_index = -1
        self.status = f"Opened {note.rel}"

    def extract_page_links(self, note: Note) -> list[Note]:
        links: list[Note] = []
        seen: set[str] = set()
        for match in WIKI_LINK_RE.finditer(note.body):
            target = match.group(1)
            linked = self.vault.resolve_link(target)
            if linked and linked.rel not in seen:
                links.append(linked)
                seen.add(linked.rel)
        return links

    def extract_backlinks(self, note: Note) -> list[Note]:
        backlinks: list[Note] = []
        for candidate in self.vault.notes:
            if candidate.rel == note.rel:
                continue
            for match in WIKI_LINK_RE.finditer(candidate.body):
                linked = self.vault.resolve_link(match.group(1))
                if linked and linked.rel == note.rel:
                    backlinks.append(candidate)
                    break
        return backlinks

    def index_for_note(self, note: Note | None) -> int:
        if not note:
            return 0
        for index, item in enumerate(self.visible_tree()):
            if item.note and item.note.rel == note.rel:
                return index
        return 0

    def expand_note_parents(self, note: Note) -> None:
        parts = note.rel.split("/")[:-1]
        prefix: list[str] = []
        for part in parts:
            prefix.append(part)
            self.collapsed_dirs.discard("/".join(prefix))

    def visible_tree(self) -> list[TreeItem]:
        visible: list[TreeItem] = []
        hidden_depth: int | None = None
        for item in self.tree:
            if hidden_depth is not None:
                if item.depth > hidden_depth:
                    continue
                hidden_depth = None

            visible.append(item)
            if item.is_dir and item.path in self.collapsed_dirs:
                hidden_depth = item.depth
        return visible

    def selected_tree_item(self) -> TreeItem | None:
        visible = self.visible_tree()
        if not visible:
            return None
        self.nav_index = min(self.nav_index, len(visible) - 1)
        return visible[self.nav_index]

    def toggle_folder(self, item: TreeItem) -> None:
        if not item.is_dir:
            return
        if item.path in self.collapsed_dirs:
            self.collapsed_dirs.remove(item.path)
            self.status = f"Expanded {item.path}"
        else:
            self.collapsed_dirs.add(item.path)
            self.status = f"Collapsed {item.path}"

    def is_last_visible_sibling(self, item: TreeItem, visible_tree: list[TreeItem]) -> bool:
        item_parent = parent_path(item.path)
        seen_item = False
        for other in visible_tree:
            if other.path == item.path:
                seen_item = True
                continue
            if seen_item and other.depth == item.depth and parent_path(other.path) == item_parent:
                return False
        return True

    def tree_prefix(self, item: TreeItem, visible_tree: list[TreeItem]) -> str:
        parts = item.path.split("/")
        prefix = ""
        for depth in range(item.depth):
            ancestor_path = "/".join(parts[: depth + 1])
            ancestor = next((candidate for candidate in visible_tree if candidate.path == ancestor_path), None)
            if ancestor and self.is_last_visible_sibling(ancestor, visible_tree):
                prefix += "    "
            else:
                prefix += "│   "
        connector = "└── " if self.is_last_visible_sibling(item, visible_tree) else "├── "
        return prefix + connector

    def nav_popup_layout(self, body_height: int, width: int, item_count: int) -> tuple[int, int, int, int, int]:
        panel_w = min(52, max(30, width - 4))
        inner_w = panel_w - 2
        max_items = max(1, body_height - 8)
        content_h = min(item_count, max_items)
        panel_h = content_h + 6
        panel_x = max(0, (width - panel_w) // 2)
        panel_y = max(0, (body_height - panel_h) // 2)
        return panel_x, panel_y, panel_w, inner_w, content_h

    def theme_popup_layout(self, body_height: int, width: int) -> tuple[int, int, int, int]:
        panel_w = min(52, max(34, width - 4))
        inner_w = panel_w - 2
        panel_h = 7
        panel_x = max(0, (width - panel_w) // 2)
        panel_y = max(0, (body_height - panel_h) // 2)
        return panel_x, panel_y, panel_w, inner_w

    def graph_popup_layout(self, body_height: int, width: int) -> tuple[int, int, int, int]:
        panel_w = min(96, max(48, width - 4))
        inner_w = panel_w - 2
        panel_h = min(16, max(12, body_height - 2))
        panel_x = max(0, (width - panel_w) // 2)
        panel_y = max(0, (body_height - panel_h) // 2)
        return panel_x, panel_y, panel_w, inner_w

    def graph_targets(self) -> list[Note]:
        return self.page_backlinks if self.graph_side == "backlinks" else self.page_links

    def clamp_graph_selection(self) -> None:
        targets = self.graph_targets()
        self.graph_index = min(self.graph_index, max(0, len(targets) - 1))

    def enter_graph(self, mode: str) -> None:
        self.mode = mode
        self.graph_side = "links" if self.page_links else "backlinks"
        self.graph_index = 0
        self.graph_scroll = 0
        self.status = "Graph: Tab side, Enter open, Esc close"

    def graph_children(self, note: Note, side: str) -> list[Note]:
        children = self.extract_backlinks(note) if side == "backlinks" else self.extract_page_links(note)
        out: list[Note] = []
        seen: set[str] = set()
        for child in children:
            if self.current and child.rel == self.current.rel:
                continue
            if child.rel == note.rel or child.rel in seen:
                continue
            seen.add(child.rel)
            out.append(child)
        return out

    def activate_tree_item(self, item: TreeItem) -> None:
        if item.is_dir:
            self.toggle_folder(item)
        elif item.note:
            self.open_note(item.note)

    def open_selected_nav_note(self) -> None:
        visible = self.visible_tree()
        if 0 <= self.nav_index < len(visible) and visible[self.nav_index].note:
            self.open_note(visible[self.nav_index].note)

    def toc_index_for_view(self) -> int:
        if not self.toc:
            return 0
        current = 0
        for index, (line_index, _, _) in enumerate(self.toc):
            if line_index <= self.view_scroll + 1:
                current = index
            else:
                break
        return current

    def update_toc_for_view(self) -> None:
        if not self.toc:
            self.toc_index = 0
            return
        current = self.toc_index_for_view()
        if self.focus != "toc":
            self.toc_index = current

    def jump_to_toc_index(self) -> None:
        if 0 <= self.toc_index < len(self.toc):
            self.view_scroll = max(0, self.toc[self.toc_index][0] - 1)
            self.focus = "viewer"
            self.status = f"TOC: {self.toc[self.toc_index][2]}"

    def viewer_bottom_padding(self) -> int:
        return min(8, max(3, self.viewer_content_height // 3))

    def viewer_scroll_limit(self) -> int:
        return min(
            max(0, len(self.rendered) - 1),
            max(0, len(self.rendered) - self.viewer_content_height + self.viewer_bottom_padding()),
        )

    def viewer_progress_percent(self) -> int:
        if len(self.rendered) <= self.viewer_content_height:
            return 100
        natural_limit = max(1, len(self.rendered) - self.viewer_content_height)
        progress = min(self.view_scroll, natural_limit) / natural_limit
        return min(100, max(0, round(progress * 100)))

    def toc_link_panel_height(self, height: int) -> int:
        link_count = len(self.page_links) + len(self.page_backlinks)
        return min(max(0, height // 3), link_count + 5 if link_count else 2)

    def page_link_entries(self) -> list[tuple[str, Note | None]]:
        entries: list[tuple[str, Note | None]] = []
        if self.page_links:
            entries.append(("links", None))
            entries.extend(("→ " + note.rel, note) for note in self.page_links)
        if self.page_links and self.page_backlinks:
            entries.append(("", None))
        if self.page_backlinks:
            entries.append(("backlinks", None))
            entries.extend(("← " + note.rel, note) for note in self.page_backlinks)
        return entries

    def toc_link_at_panel_row(self, panel_row: int, panel_height: int) -> Note | None:
        visible_rows = max(0, panel_height - 1)
        if visible_rows <= 0 or panel_row <= 0:
            return None
        entries = self.page_link_entries()
        index = self.page_link_scroll + panel_row - 1
        if 0 <= index < len(entries):
            return entries[index][1]
        return None

    def _render_code_block(self, lang: str, lines: list[str], source: int) -> list[RenderLine]:
        n = len(lines)
        ln_w = len(str(max(n, 1)))
        lang_part = f" {lang} ·" if lang else ""
        top = RenderLine(f"─{lang_part} {n} lines ", "code_top", source, code_lines=list(lines))
        out: list[RenderLine] = [top]
        for i, cl in enumerate(lines):
            out.append(RenderLine(f"│ {str(i + 1).rjust(ln_w)} │ {cl}", "code", source + i + 1))
        out.append(RenderLine("", "code_bottom", source + n + 1))
        return out

    def render_markdown(self, raw: str) -> list[RenderLine]:
        result: list[RenderLine] = []
        frontmatter, body = split_frontmatter(raw)
        if frontmatter:
            result.extend(self.render_frontmatter(frontmatter))
            result.append(RenderLine("", "blank"))

        in_code = False
        code_lang = ""
        code_lines: list[str] = []
        code_source = 0
        source_line = 0
        lines = body.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            kind = "text"
            if line.startswith("```"):
                if not in_code:
                    in_code = True
                    code_lang = line.strip("`").strip()
                    code_lines = []
                    code_source = source_line
                else:
                    in_code = False
                    result.extend(self._render_code_block(code_lang, code_lines, code_source))
                index += 1
                source_line += 1
                continue
            elif in_code:
                code_lines.append(line)
                index += 1
                source_line += 1
                continue

            if self.is_table_start(lines, index):
                table_lines = [line, lines[index + 1]]
                index += 2
                source_line += 2
                while index < len(lines) and "|" in lines[index]:
                    table_lines.append(lines[index])
                    index += 1
                    source_line += 1
                result.extend(self.render_table(table_lines))
                continue

            heading = HEADING_RE.match(line)
            if heading:
                level = len(heading.group(1))
                text = strip_inline_markup(heading.group(2))
                result.append(RenderLine(text, "heading", source_line, level, text))
                if level == 1:
                    result.append(RenderLine("━" * 36, "rule", source_line))
            elif HR_RE.match(line):
                result.append(RenderLine("─" * 36, "rule", source_line))
            elif line.lstrip().startswith("> "):
                rendered, links = self.render_links(strip_inline_markup(line.lstrip()[2:]))
                result.append(RenderLine(f"│ {rendered}", "quote", source_line, links=offset_links(links, 2)))
            elif re.match(r"^\s*[-*]\s+", line):
                indent = len(line) - len(line.lstrip())
                content = re.sub(r"^\s*[-*]\s+", "", line)
                rendered, links = self.render_links(strip_inline_markup(content))
                result.append(RenderLine(" " * indent + "• " + rendered, "list", source_line, links=offset_links(links, indent + 2)))
            elif re.match(r"^\s*\d+\.\s+", line):
                indent = len(line) - len(line.lstrip())
                match = re.match(r"^\s*(\d+\.)\s+(.*)", line)
                number = match.group(1) if match else "1."
                content = match.group(2) if match else line.strip()
                rendered, links = self.render_links(strip_inline_markup(content))
                prefix = " " * indent + number + " "
                result.append(RenderLine(prefix + rendered, "list", source_line, links=offset_links(links, len(prefix))))
            else:
                rendered, links = self.render_links(strip_inline_markup(line))
                result.append(RenderLine(rendered, kind, source_line, links=links))
            index += 1
            source_line += 1
        return result

    def render_frontmatter(self, frontmatter: list[tuple[str, str]]) -> list[RenderLine]:
        key_width = min(16, max(len(key) for key, _ in frontmatter))
        rows = [RenderLine("metadata", "meta")]
        for key, value in frontmatter:
            rows.append(RenderLine(f"  {key.ljust(key_width)}  {value}", "meta"))
        return rows

    def is_table_start(self, lines: list[str], index: int) -> bool:
        if index + 1 >= len(lines):
            return False
        return "|" in lines[index] and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]+\|?\s*$", lines[index + 1]) is not None

    def render_table(self, table_lines: list[str]) -> list[RenderLine]:
        rows = [
            [strip_inline_markup(cell.strip()) for cell in line.strip().strip("|").split("|")]
            for line in table_lines
            if not re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]+\|?\s*$", line)
        ]
        if not rows:
            return []
        column_count = max(len(row) for row in rows)
        widths = [
            min(24, max(display_width(row[col]) if col < len(row) else 0 for row in rows))
            for col in range(column_count)
        ]
        top    = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
        mid    = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
        bottom = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"
        result: list[RenderLine] = [RenderLine(top, "table")]
        for row_index, row in enumerate(rows):
            cells = [
                " " + visual_ljust((row[col] if col < len(row) else "")[:widths[col]], widths[col]) + " "
                for col in range(column_count)
            ]
            result.append(RenderLine("│" + "│".join(cells) + "│", "table_header" if row_index == 0 else "table"))
            if row_index == 0 and len(rows) > 1:
                result.append(RenderLine(mid, "table"))
        result.append(RenderLine(bottom, "table"))
        return result

    def render_links(self, line: str) -> tuple[str, list[RenderLink]]:
        parts: list[str] = []
        links: list[RenderLink] = []
        last = 0
        cursor = 0
        for match in WIKI_LINK_RE.finditer(line):
            before = line[last : match.start()]
            parts.append(before)
            cursor += display_width(before)
            target = match.group(1)
            anchor = match.group(2)
            label = match.group(3) or anchor or target or ""
            text = f"[{label}]"
            parts.append(text)
            link_width = display_width(text)
            links.append(RenderLink(cursor, cursor + link_width, text, target or "", anchor))
            cursor += link_width
            last = match.end()
        parts.append(line[last:])
        return "".join(parts), links

    def extract_toc(self) -> list[tuple[int, int, str]]:
        toc: list[tuple[int, int, str]] = []
        for index, line in enumerate(self.rendered):
            if line.kind == "heading":
                toc.append((index, line.heading_level, line.heading_text))
        return toc

    def jump_to_anchor(self, anchor: str) -> None:
        wanted = slugify_heading(anchor)
        for index, line in enumerate(self.rendered):
            if line.kind == "heading" and slugify_heading(line.heading_text) == wanted:
                self.view_scroll = max(0, index - 2)
                return

    def follow_link_on_line(self, row: int, col: int | None = None) -> None:
        if row < 0 or row >= len(self.rendered):
            return
        line = self.rendered[row]
        chosen = None
        if col is not None:
            for link in line.links:
                if link.start <= col < link.end:
                    chosen = (link.target, link.anchor)
                    break
        elif line.links:
            chosen = (line.links[0].target, line.links[0].anchor)

        if not chosen:
            self.status = "No link on this line"
            return
        target, anchor = chosen
        note = self.vault.resolve_link(target)
        if note:
            self.open_note(note, anchor)
        else:
            self.status = f"Unresolved link: {target}"

    def find_next(self) -> None:
        if not self.search_hits:
            self.status = "No search hits"
            return
        self.search_hit_index = (self.search_hit_index + 1) % len(self.search_hits)
        self.focus = "viewer"
        note, line_index = self.search_hits[self.search_hit_index]
        if note is not self.current:
            self.open_note(note)
        self.view_scroll = max(0, line_index - 2)
        self.update_toc_for_view()
        self.status = f"Find: {self.search_term} ({self.search_hit_index + 1}/{len(self.search_hits)})"

    def update_search(self, term: str) -> None:
        self.search_term = term
        self.search_hits = collect_search_hits(self.vault.notes, term, self.render_markdown)
        self.search_hit_index = -1
        self.find_next()

    def find_prev(self) -> None:
        if not self.search_hits:
            self.status = "No search hits"
            return
        self.search_hit_index = (self.search_hit_index - 1) % len(self.search_hits)
        self.focus = "viewer"
        note, line_index = self.search_hits[self.search_hit_index]
        if note is not self.current:
            self.open_note(note)
        self.view_scroll = max(0, line_index - 2)
        self.update_toc_for_view()
        self.status = f"Find: {self.search_term} ({self.search_hit_index + 1}/{len(self.search_hits)})"

    def clear_search(self) -> None:
        self.search_term = ""
        self.search_hits = []
        self.search_hit_index = -1
        self.status = "Search cleared"

    def draw(self) -> None:
        self.check_vault_updates()
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()

        # Auto-hide toc then sidebar as width shrinks
        if width < 100 and self.toc_visible:
            self.toc_visible = False
        if width < 80:
            self.sidebar_visible = False
        # Close popup if terminal expanded back
        if self.mode == "nav_popup" and width >= 80:
            self.mode = "view"

        sidebar_width = min(34, max(22, width // 4)) if self.sidebar_visible else 0
        show_toc = self.toc_visible and self.mode == "view" and width >= 100
        toc_width = min(30, max(20, width // 5)) if show_toc else 0
        body_height = max(1, height - 2)
        viewer_width = max(1, width - sidebar_width - toc_width)

        if self.mode == "nav_popup":
            self.draw_nav_popup(body_height, width)
        else:
            if self.sidebar_visible:
                self.draw_sidebar(0, 0, body_height, sidebar_width)
            if self.mode == "edit":
                self.draw_editor(0, sidebar_width, body_height, width - sidebar_width)
            else:
                self.update_toc_for_view()
                if self.mode == "graph_full":
                    self.draw_graph_full(0, sidebar_width, body_height, viewer_width)
                else:
                    self.draw_viewer(0, sidebar_width, body_height, viewer_width)
                if toc_width:
                    self.draw_toc_sidebar(0, sidebar_width + viewer_width, body_height, toc_width)
                if self.mode == "theme_popup":
                    self.draw_theme_popup(body_height, width)
                elif self.mode == "graph_popup":
                    self.draw_graph_popup(body_height, width)

        self.draw_status(height - 2, width)
        self.draw_help(height - 1, width)
        self.draw_progress(height - 1, width)
        self.stdscr.refresh()

    def draw_sidebar(self, top: int, left: int, height: int, width: int) -> None:
        root_label = f" {self.vault.root.name}/"
        safe_addstr(self.stdscr, top, left, root_label.ljust(width - 1), curses.A_REVERSE)
        visible_tree = self.visible_tree()
        visible_height = max(1, height - 1)
        self.nav_index = min(self.nav_index, max(0, len(visible_tree) - 1))
        self.nav_scroll = min(self.nav_scroll, max(0, len(visible_tree) - visible_height))
        if self.nav_index < self.nav_scroll:
            self.nav_scroll = self.nav_index
        elif self.nav_index >= self.nav_scroll + visible_height:
            self.nav_scroll = self.nav_index - visible_height + 1

        for screen_y, item in enumerate(visible_tree[self.nav_scroll : self.nav_scroll + visible_height], start=top + 1):
            index = self.nav_scroll + screen_y - top - 1
            suffix = "/" if item.is_dir else ""
            hidden_marker = " ..." if item.path in self.collapsed_dirs else ""
            label = self.tree_prefix(item, visible_tree) + item.label + suffix + hidden_marker
            attr = curses.A_NORMAL
            if index == self.nav_index:
                attr = curses.A_BOLD | curses.color_pair(7)
            if item.note and self.current and item.note.rel == self.current.rel:
                attr |= curses.A_BOLD
            safe_addstr(self.stdscr, screen_y, left, label.ljust(width - 1), attr)


    def draw_viewer(self, top: int, left: int, height: int, width: int) -> None:
        viewer_bg = curses.color_pair(5) if self.has_256_colors else curses.A_NORMAL
        if not self.current:
            safe_addstr(self.stdscr, top, left + 1, "No note", viewer_bg)
            return
        # Fill entire viewer area with background color
        blank = " " * max(0, width - 1)
        for y in range(top, top + height):
            safe_addstr(self.stdscr, y, left, blank, viewer_bg)
        title = f" {self.current.rel} "
        safe_addstr(self.stdscr, top, left, title[: max(1, width - 1)].ljust(width - 1), curses.A_REVERSE)
        content_top = top + 1
        content_height = max(1, height - 1)
        self.viewer_content_height = content_height
        self.view_scroll = min(self.view_scroll, self.viewer_scroll_limit())
        current_note_hit_lines = {li for (n, li) in self.search_hits if n is self.current}
        for offset in range(content_height):
            line_index = self.view_scroll + offset
            if line_index >= len(self.rendered):
                break
            line = self.rendered[line_index]
            if line.kind == "code_top":
                bdr = curses.A_DIM | curses.color_pair(1)
                avail = max(2, width - 2)
                label = line.text
                COPY = " [copy]"
                fill = avail - 2 - len(label) - len(COPY)
                if fill >= 0:
                    prefix = "┌" + label + "─" * fill
                    safe_addstr(self.stdscr, content_top + offset, left + 1, prefix, bdr)
                    btn_x = left + 1 + len(prefix)
                    safe_addstr(self.stdscr, content_top + offset, btn_x, COPY,
                                curses.A_BOLD | curses.color_pair(7))
                    safe_addstr(self.stdscr, content_top + offset, btn_x + len(COPY), "┐", bdr)
                else:
                    fill2 = max(0, avail - len("┌" + label) - 1)
                    safe_addstr(self.stdscr, content_top + offset, left + 1,
                                "┌" + label + "─" * fill2 + "┐", bdr)
                continue
            elif line.kind == "code_bottom":
                bdr = curses.A_DIM | curses.color_pair(1)
                avail = max(2, width - 2)
                safe_addstr(self.stdscr, content_top + offset, left + 1,
                            "└" + "─" * max(0, avail - 2) + "┘", bdr)
                continue
            elif line.kind == "code":
                gutter_attr = curses.A_DIM | viewer_bg
                code_attr = curses.color_pair(3)
                if line_index in current_note_hit_lines:
                    code_attr |= curses.A_REVERSE
                text = line.text
                second_bar = text.find("│", 1)
                if second_bar != -1:
                    gutter = text[:second_bar + 1]
                    content = text[second_bar + 1:]
                    gutter_w = display_width(gutter)
                    safe_addstr(self.stdscr, content_top + offset, left + 1, gutter, gutter_attr)
                    safe_addstr(self.stdscr, content_top + offset, left + 1 + gutter_w,
                                truncate_to_display_width(content, max(0, width - 2 - gutter_w)), code_attr)
                else:
                    safe_addstr(self.stdscr, content_top + offset, left + 1,
                                text[:max(1, width - 2)], code_attr)
                continue
            attr = viewer_bg
            if line.kind == "heading":
                level = line.heading_level
                if level <= 2:
                    attr = curses.A_BOLD | curses.color_pair(2)
                    if level == 1:
                        attr |= curses.A_UNDERLINE
                elif level <= 4:
                    attr = curses.A_BOLD | curses.color_pair(6)
                else:
                    attr = curses.A_DIM | curses.color_pair(6)
            elif line.kind == "meta":
                attr = curses.A_DIM | curses.color_pair(1)
            elif line.kind == "table":
                attr = curses.color_pair(1)
            elif line.kind == "table_header":
                attr = curses.A_BOLD | curses.color_pair(2)
            elif line.kind == "quote":
                attr = curses.color_pair(4)
            elif line.kind == "rule":
                attr = curses.A_DIM | viewer_bg
            if line_index in current_note_hit_lines:
                attr |= curses.A_REVERSE
            text = line.text
            safe_addstr(self.stdscr, content_top + offset, left + 1, text[: max(1, width - 2)], attr)
            for link in line.links:
                if link.start < width - 2:
                    safe_addstr(
                        self.stdscr,
                        content_top + offset,
                        left + 1 + link.start,
                        truncate_to_display_width(link.text, max(0, width - 2 - link.start)),
                        curses.A_UNDERLINE | curses.color_pair(7),
                    )

    def draw_editor(self, top: int, left: int, height: int, width: int) -> None:
        title = f" EDIT {self.current.rel if self.current else ''} "
        safe_addstr(self.stdscr, top, left, title[: max(1, width - 1)], curses.A_REVERSE)
        content_top = top + 1
        content_height = max(1, height - 1)
        if self.edit_y < self.edit_scroll:
            self.edit_scroll = self.edit_y
        elif self.edit_y >= self.edit_scroll + content_height:
            self.edit_scroll = self.edit_y - content_height + 1
        avail = max(1, width - 2)
        for offset in range(content_height):
            line_index = self.edit_scroll + offset
            if line_index >= len(self.edit_lines):
                break
            text = truncate_to_display_width(self.edit_lines[line_index], avail)
            safe_addstr(self.stdscr, content_top + offset, left + 1, text)
        set_cursor(0)
        current_line = self.edit_lines[self.edit_y] if self.edit_y < len(self.edit_lines) else ""
        visual_x = display_width(current_line[: self.edit_x])
        cursor_y = content_top + self.edit_y - self.edit_scroll
        cursor_x = left + 1 + min(visual_x, max(0, width - 3))
        if self.edit_x < len(current_line):
            safe_addstr(self.stdscr, cursor_y, cursor_x, current_line[self.edit_x], curses.A_REVERSE)
        else:
            safe_addstr(self.stdscr, cursor_y, cursor_x, "▌", curses.A_BOLD)

    def draw_toc_sidebar(self, top: int, left: int, height: int, width: int) -> None:
        safe_addstr(self.stdscr, top, left, " TOC".ljust(width - 1), curses.A_REVERSE)
        link_panel_height = self.toc_link_panel_height(height)
        toc_height = max(1, height - link_panel_height)

        if not self.toc:
            safe_addstr(self.stdscr, top + 1, left + 2, "No headings")
        else:
            visible_height = max(1, toc_height - 1)
            self.toc_scroll = 0
            if self.toc_index >= visible_height:
                self.toc_scroll = self.toc_index - visible_height + 1

            level_marks = {1: "●", 2: "◇", 3: "·"}
            current_index = self.toc_index_for_view()
            for offset, (_, level, title) in enumerate(self.toc[self.toc_scroll : self.toc_scroll + visible_height]):
                index = self.toc_scroll + offset
                attr = curses.A_NORMAL
                if index == self.toc_index:
                    attr = curses.A_BOLD | curses.color_pair(7)
                if index == current_index:
                    attr |= curses.A_BOLD
                indent = "  " * max(0, level - 1)
                active = "▶ " if index == self.toc_index else "• " if index == current_index else "  "
                lv_mark = level_marks.get(level, "·")
                text = f"{active}{indent}{lv_mark} {title}"
                safe_addstr(self.stdscr, top + 1 + offset, left + 2, text[: max(1, width - 3)], attr)

        self.draw_page_link_panel(top + toc_height, left, link_panel_height, width)

    def draw_page_link_panel(self, top: int, left: int, height: int, width: int) -> None:
        if height <= 0:
            return
        safe_addstr(self.stdscr, top, left + 1, "─" * max(0, width - 2), curses.A_DIM)
        visible_rows = max(0, height - 1)
        if visible_rows <= 0:
            return
        entries = self.page_link_entries()
        if not entries:
            safe_addstr(self.stdscr, top + 1, left + 2, "No links", curses.A_DIM)
            return
        max_scroll = max(0, len(entries) - visible_rows)
        self.page_link_scroll = min(max_scroll, max(0, self.page_link_scroll))
        for offset in range(visible_rows):
            entry_index = self.page_link_scroll + offset
            row = top + 1 + offset
            if entry_index >= len(entries):
                break
            label, note = entries[entry_index]
            if note is None:
                attr = curses.A_BOLD if label else curses.A_DIM
            else:
                attr = curses.A_UNDERLINE | curses.A_DIM
            safe_addstr(self.stdscr, row, left + 2, label[: max(1, width - 3)], attr)
        if max_scroll:
            indicator = f"{self.page_link_scroll + 1}/{max_scroll + 1}"
            safe_addstr(self.stdscr, top, max(left + 1, left + width - len(indicator) - 1), indicator, curses.A_DIM)

    def draw_nav_popup(self, body_height: int, width: int) -> None:
        viewer_bg = curses.color_pair(5) if self.has_256_colors else curses.A_NORMAL

        # Solid background fill
        blank = " " * max(0, width - 1)
        for y in range(body_height):
            safe_addstr(self.stdscr, y, 0, blank, viewer_bg)

        visible_tree = self.visible_tree()
        panel_x, panel_y, _, inner_w, content_h = self.nav_popup_layout(
            body_height, width, len(visible_tree)
        )

        # Clamp and scroll popup_index
        self.popup_index = min(self.popup_index, max(0, len(visible_tree) - 1))
        if self.popup_index < self.popup_scroll:
            self.popup_scroll = self.popup_index
        elif self.popup_index >= self.popup_scroll + content_h:
            self.popup_scroll = self.popup_index - content_h + 1

        # Top border
        safe_addstr(self.stdscr, panel_y, panel_x,
                    "┌" + "─" * inner_w + "┐", viewer_bg)
        # Title row
        vault_name = self.vault.root.name
        title_text = f" 📂 {vault_name}/ "
        safe_addstr(self.stdscr, panel_y + 1, panel_x,
                    "│" + visual_ljust(truncate_to_display_width(title_text, inner_w), inner_w) + "│",
                    curses.A_BOLD | viewer_bg)
        # Title/items separator
        safe_addstr(self.stdscr, panel_y + 2, panel_x,
                    "├" + "─" * inner_w + "┤", viewer_bg)

        # Tree items
        for offset in range(content_h):
            idx = self.popup_scroll + offset
            row_y = panel_y + 3 + offset
            if idx >= len(visible_tree):
                safe_addstr(self.stdscr, row_y, panel_x,
                            "│" + " " * inner_w + "│", viewer_bg)
                continue
            item = visible_tree[idx]
            suffix = "/" if item.is_dir else ""
            hidden_marker = " ..." if item.path in self.collapsed_dirs else ""
            label = " " + self.tree_prefix(item, visible_tree) + item.label + suffix + hidden_marker
            is_selected = idx == self.popup_index
            is_current = bool(item.note and self.current and item.note.rel == self.current.rel)
            if is_selected:
                attr = curses.A_REVERSE
            elif is_current:
                attr = curses.A_BOLD | viewer_bg
            else:
                attr = viewer_bg
            row_text = visual_ljust(truncate_to_display_width(label, inner_w), inner_w)
            safe_addstr(self.stdscr, row_y, panel_x, "│", viewer_bg)
            safe_addstr(self.stdscr, row_y, panel_x + 1, row_text, attr)
            safe_addstr(self.stdscr, row_y, panel_x + 1 + inner_w, "│", viewer_bg)

        # Items/help separator
        sep_y = panel_y + 3 + content_h
        safe_addstr(self.stdscr, sep_y, panel_x,
                    "├" + "─" * inner_w + "┤", viewer_bg)
        # Help row
        help_text = " ↑↓ 移動 · Enter 開啟 · Esc/Tab 關閉 "
        safe_addstr(self.stdscr, sep_y + 1, panel_x,
                    "│" + visual_ljust(truncate_to_display_width(help_text, inner_w), inner_w) + "│",
                    curses.A_DIM | viewer_bg)
        # Bottom border
        safe_addstr(self.stdscr, sep_y + 2, panel_x,
                    "└" + "─" * inner_w + "┘", viewer_bg)

    def draw_theme_popup(self, body_height: int, width: int) -> None:
        viewer_bg = curses.color_pair(5) if self.has_256_colors else curses.A_NORMAL
        panel_x, panel_y, _, inner_w = self.theme_popup_layout(body_height, width)
        border_attr = curses.A_DIM | viewer_bg
        title_attr = curses.A_BOLD | curses.color_pair(2)

        safe_addstr(self.stdscr, panel_y, panel_x, "┌" + "─" * inner_w + "┐", border_attr)
        title = " Theme "
        safe_addstr(
            self.stdscr,
            panel_y + 1,
            panel_x,
            "│" + visual_ljust(truncate_to_display_width(title, inner_w), inner_w) + "│",
            title_attr,
        )
        safe_addstr(self.stdscr, panel_y + 2, panel_x, "├" + "─" * inner_w + "┤", border_attr)

        safe_addstr(self.stdscr, panel_y + 3, panel_x, "│" + " " * inner_w + "│", viewer_bg)

        cursor = 1
        for index, theme_name in enumerate(THEME_ORDER):
            theme = THEMES[theme_name]
            label = f" {theme.label} "
            attr = curses.color_pair(7)
            if index == self.theme_popup_index:
                attr |= curses.A_REVERSE
            if theme_name == self.theme_name:
                attr |= curses.A_BOLD
            safe_addstr(self.stdscr, panel_y + 3, panel_x + 1 + cursor, label, attr)
            cursor += len(label) + 1

        current = f" Current: {self.theme.label} "
        safe_addstr(
            self.stdscr,
            panel_y + 4,
            panel_x,
            "│" + visual_ljust(truncate_to_display_width(current, inner_w), inner_w) + "│",
            viewer_bg,
        )
        help_text = " Tab/←→ switch · Enter apply · Esc close "
        safe_addstr(
            self.stdscr,
            panel_y + 5,
            panel_x,
            "│" + visual_ljust(truncate_to_display_width(help_text, inner_w), inner_w) + "│",
            curses.A_DIM | viewer_bg,
        )
        safe_addstr(self.stdscr, panel_y + 6, panel_x, "└" + "─" * inner_w + "┘", border_attr)

    def graph_line_attr(self, side: str, index: int) -> int:
        if side == self.graph_side and index == self.graph_index:
            return curses.A_BOLD | curses.color_pair(7)
        return curses.color_pair(5) if self.has_256_colors else curses.A_NORMAL

    def draw_graph_popup(self, body_height: int, width: int) -> None:
        viewer_bg = curses.color_pair(5) if self.has_256_colors else curses.A_NORMAL
        panel_x, panel_y, panel_w, inner_w = self.graph_popup_layout(body_height, width)
        panel_h = min(16, max(12, body_height - 2))
        border_attr = curses.A_DIM | viewer_bg
        title_attr = curses.A_BOLD | curses.color_pair(2)
        current = self.current.rel if self.current else "-"

        safe_addstr(self.stdscr, panel_y, panel_x, "┌" + "─" * inner_w + "┐", border_attr)
        title = f" Graph | {current} "
        safe_addstr(
            self.stdscr,
            panel_y + 1,
            panel_x,
            "│" + visual_ljust(truncate_to_display_width(title, inner_w), inner_w) + "│",
            title_attr,
        )
        safe_addstr(self.stdscr, panel_y + 2, panel_x, "├" + "─" * inner_w + "┤", border_attr)
        for y in range(panel_y + 3, panel_y + panel_h - 3):
            safe_addstr(self.stdscr, y, panel_x, "│" + " " * inner_w + "│", viewer_bg)

        content_top = panel_y + 3
        rows = max(1, panel_h - 7)
        left_w = max(16, inner_w // 3 - 2)
        center_w = max(12, inner_w // 3 - 2)
        right_w = max(16, inner_w - left_w - center_w - 7)
        center_x = panel_x + 2 + left_w + 3
        right_x = center_x + center_w + 3
        safe_addstr(self.stdscr, content_top, panel_x + 2, "Backlinks", curses.A_BOLD | curses.color_pair(1))
        safe_addstr(self.stdscr, content_top, center_x, "Current", curses.A_BOLD | curses.color_pair(1))
        safe_addstr(self.stdscr, content_top, right_x, "Links", curses.A_BOLD | curses.color_pair(1))
        safe_addstr(self.stdscr, content_top + 1, panel_x + 2, "─" * min(9, left_w), curses.A_DIM | viewer_bg)
        safe_addstr(self.stdscr, content_top + 1, center_x, "─" * min(7, center_w), curses.A_DIM | viewer_bg)
        safe_addstr(self.stdscr, content_top + 1, right_x, "─" * min(5, right_w), curses.A_DIM | viewer_bg)

        total_rows = max(len(self.page_backlinks), len(self.page_links), 1)
        selected_row = min(self.graph_index, max(0, total_rows - 1))
        max_scroll = max(0, total_rows - rows)
        if total_rows <= rows:
            self.graph_scroll = 0
        elif selected_row < self.graph_scroll:
            self.graph_scroll = selected_row
        elif selected_row >= self.graph_scroll + rows:
            self.graph_scroll = selected_row - rows + 1
        self.graph_scroll = min(max_scroll, max(0, self.graph_scroll))

        backlinks = self.page_backlinks[self.graph_scroll : self.graph_scroll + rows]
        links = self.page_links[self.graph_scroll : self.graph_scroll + rows]
        visible_count = max(len(backlinks), len(links), 1)
        trunk_row = content_top + 2 + visible_count // 2
        current_text = truncate_to_display_width(current, center_w)
        safe_addstr(self.stdscr, trunk_row, center_x, current_text, curses.A_BOLD | curses.color_pair(2))

        for index, note in enumerate(backlinks):
            absolute_index = self.graph_scroll + index
            row_y = content_top + 2 + index
            note_text = truncate_to_display_width(note.rel, max(1, left_w - 4))
            connector = "─" * max(1, left_w - display_width(note_text) - 2)
            joint = "┐" if absolute_index == 0 else "┘" if absolute_index == len(self.page_backlinks) - 1 else "┼"
            if len(self.page_backlinks) == 1:
                joint = "─"
            safe_addstr(self.stdscr, row_y, panel_x + 2, note_text, self.graph_line_attr("backlinks", absolute_index))
            safe_addstr(self.stdscr, row_y, panel_x + 2 + display_width(note_text), connector + joint, border_attr)
            if row_y == trunk_row:
                safe_addstr(self.stdscr, row_y, panel_x + left_w + 1, "─" * max(1, center_x - panel_x - left_w - 1), border_attr)
        if not self.page_backlinks:
            safe_addstr(self.stdscr, trunk_row, panel_x + 2, "No backlinks", curses.A_DIM | viewer_bg)

        link_stem_x = center_x + display_width(current_text)
        if self.page_links:
            safe_addstr(self.stdscr, trunk_row, link_stem_x, "─" * max(1, right_x - link_stem_x), border_attr)
        for index, note in enumerate(links):
            absolute_index = self.graph_scroll + index
            row_y = content_top + 2 + index
            joint = "┬── " if absolute_index == 0 else "└── " if absolute_index == len(self.page_links) - 1 else "├── "
            if len(self.page_links) == 1:
                joint = "── "
            safe_addstr(self.stdscr, row_y, right_x - len(joint), joint, border_attr)
            safe_addstr(
                self.stdscr,
                row_y,
                right_x,
                truncate_to_display_width(note.rel, right_w),
                self.graph_line_attr("links", absolute_index),
            )
        if not self.page_links:
            safe_addstr(self.stdscr, trunk_row, right_x, "No links", curses.A_DIM | viewer_bg)

        sep_y = panel_y + panel_h - 3
        scroll_text = f" · scroll {self.graph_scroll + 1}/{max_scroll + 1}" if max_scroll else ""
        help_text = f" Tab side · ↑↓ select · Enter open · Ctrl+G full · Esc close{scroll_text} "
        safe_addstr(self.stdscr, sep_y, panel_x, "├" + "─" * inner_w + "┤", border_attr)
        safe_addstr(
            self.stdscr,
            sep_y + 1,
            panel_x,
            "│" + visual_ljust(truncate_to_display_width(help_text, inner_w), inner_w) + "│",
            curses.A_DIM | viewer_bg,
        )
        safe_addstr(self.stdscr, sep_y + 2, panel_x, "└" + "─" * inner_w + "┘", border_attr)

    def draw_graph_full(self, top: int, left: int, height: int, width: int) -> None:
        viewer_bg = curses.color_pair(5) if self.has_256_colors else curses.A_NORMAL
        blank = " " * max(0, width - 1)
        for y in range(top, top + height):
            safe_addstr(self.stdscr, y, left, blank, viewer_bg)

        current = self.current.rel if self.current else "-"
        title = f" Graph Tree | {current} | depth 2 "
        safe_addstr(self.stdscr, top, left, title[: max(1, width - 1)].ljust(width - 1), curses.A_REVERSE)
        if height <= 4:
            return

        left2_x = left + 1
        current_x = left + max(22, width // 2 - display_width(current) // 2)
        left1_x = max(left2_x + 12, current_x - 22)
        right1_x = min(left + width - 18, current_x + display_width(current) + 8)
        right2_x = min(left + width - 10, right1_x + 4)
        content_top = top + 2
        content_bottom = top + height - 2
        max1_w = max(1, current_x - left1_x - 6)
        joint1_col = left1_x + max1_w + 2
        joint2_col = left1_x + 3
        max2_w = max(1, joint2_col - left2_x - 1)
        safe_addstr(self.stdscr, content_top, left2_x, "Backlinks", curses.A_BOLD | curses.color_pair(1))
        safe_addstr(self.stdscr, content_top, current_x, "Current", curses.A_BOLD | curses.color_pair(1))
        safe_addstr(self.stdscr, content_top, right1_x, "Links", curses.A_BOLD | curses.color_pair(1))
        safe_addstr(self.stdscr, content_top + 1, left2_x, "─" * 9, curses.A_DIM | viewer_bg)
        safe_addstr(self.stdscr, content_top + 1, current_x, "─" * 7, curses.A_DIM | viewer_bg)
        safe_addstr(self.stdscr, content_top + 1, right1_x, "─" * 5, curses.A_DIM | viewer_bg)

        body_top = content_top + 3
        visible_rows = max(1, content_bottom - body_top)
        backlinks = self.page_backlinks
        links = self.page_links
        groups = max(len(backlinks), len(links), 1)
        center_group = groups // 2
        group_tops: list[int] = []
        first_rows: list[int] = []
        virtual_y = 0
        for index in range(groups):
            left_rows = 1
            if index < len(backlinks):
                left_rows = len(self.graph_children(backlinks[index], "backlinks")[:2]) + 1
            right_rows = 1
            if index < len(links):
                right_rows = len(self.graph_children(links[index], "links")[:2]) + 1
            group_tops.append(virtual_y)
            first_rows.append(virtual_y + (left_rows - 1 if index < len(backlinks) else 0))
            virtual_y += max(2, left_rows, right_rows) + 1
        total_rows = max(1, virtual_y)

        selected_row = first_rows[min(self.graph_index, len(first_rows) - 1)] if first_rows else 0
        max_scroll = max(0, total_rows - visible_rows)
        if total_rows <= visible_rows:
            self.graph_scroll = 0
        elif selected_row < self.graph_scroll:
            self.graph_scroll = selected_row
        elif selected_row >= self.graph_scroll + visible_rows:
            self.graph_scroll = selected_row - visible_rows + 1
        self.graph_scroll = min(max_scroll, max(0, self.graph_scroll))

        def screen_y(vrow: int) -> int:
            return body_top + vrow - self.graph_scroll

        def in_view(vrow: int) -> bool:
            y = screen_y(vrow)
            return body_top <= y < content_bottom

        def draw_v(vrow: int, x: int, text: str, attr: int = 0) -> None:
            if in_view(vrow):
                safe_addstr(self.stdscr, screen_y(vrow), x, text, attr)

        center_joint_end_x: int | None = None

        for index in range(groups):
            group_top = group_tops[index]
            first_row = first_rows[index]
            if index < len(backlinks):
                note = backlinks[index]
                upstream = self.graph_children(note, "backlinks")[:2]
                for child_offset, upstream_note in enumerate(upstream):
                    child_row = group_top + child_offset
                    child_text = truncate_to_display_width(upstream_note.rel, max2_w)
                    u_joint = "┘" if len(upstream) > 1 and child_offset == len(upstream) - 1 else "┐"
                    conn2 = "─" * max(1, joint2_col - left2_x - display_width(child_text)) + u_joint
                    draw_v(child_row, left2_x, child_text, curses.color_pair(5) if self.has_256_colors else curses.A_NORMAL)
                    draw_v(child_row, left2_x + display_width(child_text), conn2, curses.A_DIM | viewer_bg)
                note_text = truncate_to_display_width(note.rel, max1_w)
                joint = "┐" if index == 0 else "┘" if index == len(backlinks) - 1 else "┼"
                if len(backlinks) == 1:
                    joint = "─"
                conn1 = "─" * max(1, joint1_col - left1_x - display_width(note_text)) + joint
                draw_v(first_row, left1_x, note_text, self.graph_line_attr("backlinks", index))
                draw_v(first_row, left1_x + display_width(note_text), conn1, curses.A_DIM | viewer_bg)
                if index == center_group:
                    center_joint_end_x = joint1_col
            elif index == center_group:
                draw_v(first_row, left1_x, "No backlinks", curses.A_DIM | viewer_bg)

            if index == center_group:
                current_row = first_row
                draw_v(current_row, current_x, current, curses.A_BOLD | curses.color_pair(2))
                if backlinks:
                    left_line_start = (center_joint_end_x + 1) if center_joint_end_x is not None else (left1_x + max(1, min(18, current_x - left1_x - 1)))
                    if left_line_start < current_x:
                        draw_v(current_row, left_line_start, "─" * (current_x - left_line_start), curses.A_DIM | viewer_bg)
                if links:
                    right_start = current_x + display_width(current)
                    draw_v(current_row, right_start, "─" * max(1, right1_x - right_start), curses.A_DIM | viewer_bg)

            if index < len(links):
                note = links[index]
                link_row = first_row if index == center_group else group_top
                joint = "┬── " if index == 0 else "└── " if index == len(links) - 1 else "├── "
                if len(links) == 1:
                    joint = "── "
                draw_v(link_row, max(left, right1_x - len(joint)), joint, curses.A_DIM | viewer_bg)
                draw_v(
                    link_row,
                    right1_x,
                    truncate_to_display_width(note.rel, max(1, width - (right1_x - left) - 1)),
                    self.graph_line_attr("links", index),
                )
                downstream = self.graph_children(note, "links")[:2]
                for child_index, child in enumerate(downstream):
                    child_y = link_row + 1 + child_index
                    child_joint = "└── " if child_index == len(downstream) - 1 else "├── "
                    draw_v(child_y, right2_x, child_joint, curses.A_DIM | viewer_bg)
                    draw_v(
                        child_y,
                        right2_x + len(child_joint),
                        truncate_to_display_width(child.rel, max(1, width - (right2_x - left) - len(child_joint) - 1)),
                        viewer_bg,
                    )
            else:
                if index == center_group:
                    draw_v(first_row, right1_x, "No links", curses.A_DIM | viewer_bg)

        scroll_text = f" · scroll {self.graph_scroll + 1}/{max_scroll + 1}" if max_scroll else ""
        help_text = f" g popup · Tab side · ↑↓ select · Enter open · Esc close{scroll_text} "
        safe_addstr(self.stdscr, top + height - 1, left, help_text[: max(1, width - 1)], curses.A_DIM | viewer_bg)

    def draw_status(self, y: int, width: int) -> None:
        mode = self.mode.upper()
        current = self.current.rel if self.current else "-"
        msg = f" {mode} | {current} | {self.theme.label} | {self.status}"
        safe_addstr(self.stdscr, y, 0, msg[: width - 1].ljust(width - 1), curses.A_REVERSE)

    def draw_progress(self, y: int, width: int) -> None:
        text = f" {self.viewer_progress_percent()}% "
        safe_addstr(self.stdscr, y, max(0, width - len(text) - 1), text, curses.A_REVERSE)

    def draw_help(self, y: int, width: int) -> None:
        if width < 80:
            text = " Tab nav-popup | Enter open | g graph | Ctrl+G graph2 | Ctrl+T theme | q quit "
        else:
            text = " Tab sidebar | Enter open/link | g graph | Ctrl+G graph2 | Ctrl+T theme | t TOC | q quit "
        safe_addstr(self.stdscr, y, 0, text[: width - 1])

    def handle_view_key(self, key: int) -> None:
        code = key_code(key)
        if code == curses.KEY_MOUSE:
            self.handle_mouse()
        elif code == 9:
            _, width = self.stdscr.getmaxyx()
            if width < 80:
                self.mode = "nav_popup"
                self.popup_index = self.index_for_note(self.current)
                self.popup_scroll = max(0, self.popup_index - 5)
            else:
                self.sidebar_visible = not self.sidebar_visible
        elif code in (curses.KEY_UP, ord("k")):
            if self.search_hits:
                self.find_prev()
            elif self.focus == "toc" and self.toc_visible:
                self.toc_index = max(0, self.toc_index - 1)
            elif self.sidebar_visible:
                self.nav_index = max(0, self.nav_index - 1)
            else:
                self.scroll_viewer(-1)
        elif code in (curses.KEY_DOWN, ord("j")):
            if self.search_hits:
                self.find_next()
            elif self.focus == "toc" and self.toc_visible:
                self.toc_index = min(max(0, len(self.toc) - 1), self.toc_index + 1)
            elif self.sidebar_visible:
                self.nav_index = min(len(self.visible_tree()) - 1, self.nav_index + 1)
            else:
                self.scroll_viewer(1)
        elif code == curses.KEY_NPAGE:
            self.focus = "viewer"
            self.scroll_viewer(10)
        elif code == curses.KEY_PPAGE:
            self.focus = "viewer"
            self.scroll_viewer(-10)
        elif code in (10, 13):
            if self.focus == "toc" and self.toc_visible:
                self.jump_to_toc_index()
            elif self.sidebar_visible:
                item = self.selected_tree_item()
                if item:
                    self.activate_tree_item(item)
            else:
                self.follow_link_on_line(self.view_scroll)
        elif code == CTRL_E:
            self.start_edit()
        elif code == CTRL_F:
            term = prompt(self.stdscr, "Find: ")
            if term:
                self.update_search(term)
        elif code == CTRL_T:
            self.mode = "theme_popup"
            self.theme_popup_index = THEME_ORDER.index(self.theme_name)
        elif code == CTRL_G:
            self.enter_graph("graph_full")
        elif code == ord("g"):
            self.enter_graph("graph_popup")
        elif code == ESC:
            if self.search_hits:
                self.clear_search()
        elif code == ord("n"):
            self.find_next()
        elif code == ord("t"):
            self.toc_visible = not self.toc_visible
            if self.toc_visible:
                self.update_toc_for_view()
            elif self.focus == "toc":
                self.focus = "nav" if self.sidebar_visible else "viewer"

    def handle_nav_popup_key(self, key) -> None:
        code = key_code(key)
        visible_tree = self.visible_tree()
        if code == curses.KEY_MOUSE:
            self.handle_mouse()
        elif code in (ESC, 9):  # Esc or Tab — close popup
            self.mode = "view"
        elif code in (curses.KEY_UP, ord("k")):
            self.popup_index = max(0, self.popup_index - 1)
        elif code in (curses.KEY_DOWN, ord("j")):
            self.popup_index = min(max(0, len(visible_tree) - 1), self.popup_index + 1)
        elif code in (10, 13):
            if 0 <= self.popup_index < len(visible_tree):
                item = visible_tree[self.popup_index]
                self.activate_tree_item(item)
                if item.note:
                    self.mode = "view"

    def handle_theme_popup_key(self, key) -> None:
        code = key_code(key)
        if code == curses.KEY_MOUSE:
            self.handle_mouse()
        elif code in (ESC, CTRL_T):
            self.mode = "view"
        elif code in (9, curses.KEY_RIGHT, ord("l")):
            self.theme_popup_index = (self.theme_popup_index + 1) % len(THEME_ORDER)
        elif code in (curses.KEY_LEFT, ord("h")):
            self.theme_popup_index = (self.theme_popup_index - 1) % len(THEME_ORDER)
        elif code in (10, 13):
            self.apply_theme(THEME_ORDER[self.theme_popup_index])
            self.mode = "view"

    def handle_graph_key(self, key) -> None:
        code = key_code(key)
        targets = self.graph_targets()
        if code == curses.KEY_MOUSE:
            self.handle_mouse()
        elif code in (ESC, ord("g")):
            self.mode = "view"
        elif code == CTRL_G:
            self.mode = "graph_popup" if self.mode == "graph_full" else "graph_full"
        elif code == 9:
            self.graph_side = "backlinks" if self.graph_side == "links" else "links"
            self.clamp_graph_selection()
        elif code in (curses.KEY_LEFT, ord("h")):
            self.graph_side = "backlinks"
            self.clamp_graph_selection()
        elif code in (curses.KEY_RIGHT, ord("l")):
            self.graph_side = "links"
            self.clamp_graph_selection()
        elif code in (curses.KEY_UP, ord("k")):
            self.graph_index = max(0, self.graph_index - 1)
        elif code in (curses.KEY_DOWN, ord("j")):
            self.graph_index = min(max(0, len(targets) - 1), self.graph_index + 1)
        elif code in (10, 13):
            self.clamp_graph_selection()
            targets = self.graph_targets()
            if 0 <= self.graph_index < len(targets):
                self.open_note(targets[self.graph_index])
                self.mode = "view"

    def handle_nav_popup_mouse(self, x: int, y: int, button: int, body_height: int, width: int) -> bool:
        visible_tree = self.visible_tree()
        if not visible_tree:
            return False

        panel_x, panel_y, panel_w, _, content_h = self.nav_popup_layout(
            body_height, width, len(visible_tree)
        )
        in_panel = panel_x <= x < panel_x + panel_w and panel_y <= y < panel_y + content_h + 6
        if not in_panel:
            return False

        if button & curses.BUTTON4_PRESSED:
            self.popup_index = max(0, self.popup_index - 1)
            return True
        if button & curses.BUTTON5_PRESSED:
            self.popup_index = min(len(visible_tree) - 1, self.popup_index + 1)
            return True

        item_y = y - (panel_y + 3)
        if not (panel_x <= x < panel_x + panel_w and 0 <= item_y < content_h):
            return True

        index = self.popup_scroll + item_y
        if 0 <= index < len(visible_tree):
            self.popup_index = index
            item = visible_tree[index]
            if button & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
                self.activate_tree_item(item)
                if item.note:
                    self.mode = "view"
        return True

    def handle_theme_popup_mouse(self, x: int, y: int, button: int, body_height: int, width: int) -> bool:
        panel_x, panel_y, panel_w, _ = self.theme_popup_layout(body_height, width)
        in_panel = panel_x <= x < panel_x + panel_w and panel_y <= y < panel_y + 7
        if not in_panel:
            self.mode = "view"
            return True

        if button & curses.BUTTON4_PRESSED:
            self.theme_popup_index = (self.theme_popup_index - 1) % len(THEME_ORDER)
            return True
        if button & curses.BUTTON5_PRESSED:
            self.theme_popup_index = (self.theme_popup_index + 1) % len(THEME_ORDER)
            return True
        if not button & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
            return True

        if y == panel_y + 3:
            cursor = panel_x + 2
            for index, theme_name in enumerate(THEME_ORDER):
                label_w = len(f" {THEMES[theme_name].label} ")
                if cursor <= x < cursor + label_w:
                    self.theme_popup_index = index
                    self.apply_theme(theme_name)
                    self.mode = "view"
                    return True
                cursor += label_w + 1
        return True

    def handle_graph_mouse(self, x: int, y: int, button: int, body_height: int, width: int) -> bool:
        targets = self.graph_targets()
        if button & curses.BUTTON4_PRESSED:
            self.graph_index = max(0, self.graph_index - 1)
            return True
        if button & curses.BUTTON5_PRESSED:
            self.graph_index = min(max(0, len(targets) - 1), self.graph_index + 1)
            return True
        if button & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
            if x < width // 2:
                self.graph_side = "backlinks"
            else:
                self.graph_side = "links"
            self.clamp_graph_selection()
            return True
        return True

    def scroll_viewer(self, amount: int) -> None:
        self.view_scroll = min(
            self.viewer_scroll_limit(),
            max(0, self.view_scroll + amount),
        )
        self.update_toc_for_view()

    def handle_mouse(self) -> None:
        try:
            _, x, y, _, button = curses.getmouse()
        except curses.error:
            return
        height, width = self.stdscr.getmaxyx()
        sidebar_width = min(34, max(22, width // 4)) if self.sidebar_visible else 0
        show_toc = self.toc_visible and self.mode == "view" and width >= 80
        toc_width = min(30, max(20, width // 5)) if show_toc else 0
        toc_left = width - toc_width
        body_height = max(1, height - 2)
        if self.mode in ("graph_popup", "graph_full"):
            self.handle_graph_mouse(x, y, button, body_height, width)
            return
        if self.mode == "theme_popup":
            self.handle_theme_popup_mouse(x, y, button, body_height, width)
            return
        if self.mode == "nav_popup":
            if self.handle_nav_popup_mouse(x, y, button, body_height, width):
                return
            if button & curses.BUTTON4_PRESSED:
                self.focus = "viewer"
                self.scroll_viewer(-3)
            elif button & curses.BUTTON5_PRESSED:
                self.focus = "viewer"
                self.scroll_viewer(3)
            return
        if toc_width and x >= toc_left:
            self.focus = "toc"
            link_panel_height = self.toc_link_panel_height(body_height)
            toc_height = max(1, body_height - link_panel_height)
            if y >= toc_height and link_panel_height > 0:
                visible_rows = max(0, link_panel_height - 1)
                max_scroll = max(0, len(self.page_link_entries()) - visible_rows)
                if button & curses.BUTTON4_PRESSED:
                    self.page_link_scroll = max(0, self.page_link_scroll - 1)
                elif button & curses.BUTTON5_PRESSED:
                    self.page_link_scroll = min(max_scroll, self.page_link_scroll + 1)
                elif button & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
                    note = self.toc_link_at_panel_row(y - toc_height, link_panel_height)
                    if note:
                        self.open_note(note)
                        self.focus = "viewer"
                return
            if button & curses.BUTTON4_PRESSED:
                self.toc_index = max(0, self.toc_index - 1)
            elif button & curses.BUTTON5_PRESSED:
                self.toc_index = min(max(0, len(self.toc) - 1), self.toc_index + 1)
            elif button & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED) and 1 <= y < body_height:
                if y < toc_height:
                    index = self.toc_scroll + y - 1
                    if 0 <= index < len(self.toc):
                        self.toc_index = index
                        self.jump_to_toc_index()
            return
        if self.sidebar_visible and x < sidebar_width:
            self.focus = "nav"
            visible_tree = self.visible_tree()
            if button & curses.BUTTON4_PRESSED:
                self.nav_index = max(0, self.nav_index - 1)
                self.open_selected_nav_note()
            elif button & curses.BUTTON5_PRESSED:
                self.nav_index = min(len(visible_tree) - 1, self.nav_index + 1)
                self.open_selected_nav_note()
            elif 1 <= y < body_height:
                index = self.nav_scroll + y - 1
                if 0 <= index < len(visible_tree):
                    self.nav_index = index
                    item = visible_tree[index]
                    if button & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
                        self.activate_tree_item(item)
        elif self.mode == "edit":
            if button & curses.BUTTON4_PRESSED:
                self.edit_y = max(0, self.edit_y - 1)
                self.edit_x = min(self.edit_x, len(self.edit_lines[self.edit_y]))
            elif button & curses.BUTTON5_PRESSED:
                self.edit_y = min(len(self.edit_lines) - 1, self.edit_y + 1)
                self.edit_x = min(self.edit_x, len(self.edit_lines[self.edit_y]))
            elif button & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED) and y > 0:
                line_index = self.edit_scroll + (y - 1)
                line_index = max(0, min(len(self.edit_lines) - 1, line_index))
                self.edit_y = line_index
                target_vx = x - (sidebar_width + 1)
                self.edit_x = visual_x_to_char_index(self.edit_lines[line_index], target_vx)
        else:
            if button & curses.BUTTON4_PRESSED:
                self.focus = "viewer"
                self.scroll_viewer(-3)
            elif button & curses.BUTTON5_PRESSED:
                self.focus = "viewer"
                self.scroll_viewer(3)
            elif button & curses.BUTTON1_CLICKED and y > 0:
                self.focus = "viewer"
                line_index = self.view_scroll + y - 1
                if 0 <= line_index < len(self.rendered):
                    rl = self.rendered[line_index]
                    if rl.kind == "code_top":
                        COPY = " [copy]"
                        viewer_width = width - sidebar_width - toc_width
                        avail = max(2, viewer_width - 2)
                        fill = avail - 2 - len(rl.text) - len(COPY)
                        if fill >= 0:
                            btn_x = sidebar_width + 1 + 1 + len(rl.text) + fill
                            if btn_x <= x < btn_x + len(COPY):
                                copy_to_clipboard("\n".join(rl.code_lines))
                                self.status = "Copied to clipboard"
                                return
                self.follow_link_on_line(line_index, x - sidebar_width - 1)

    def start_edit(self) -> None:
        if not self.current:
            return
        self.mode = "edit"
        self.edit_lines = self.current.raw.splitlines()
        if not self.edit_lines:
            self.edit_lines = [""]
        self.edit_y = min(self.view_scroll, len(self.edit_lines) - 1)
        self.edit_x = 0
        self.edit_scroll = max(0, self.edit_y - 2)
        self.status = "Editing. Ctrl+S saves, Ctrl+E returns to viewer, Esc cancels"

    def save_edit(self) -> None:
        if not self.current:
            return
        text = "\n".join(self.edit_lines) + "\n"
        self.current.path.write_text(text, encoding="utf-8")
        self.mode = "view"
        set_cursor(0)
        self.reload_vault(f"Saved {self.current.rel}", preserve_scroll=False)
        self.status = f"Saved {self.current.rel}"

    def handle_edit_key(self, key: int) -> None:
        code = key_code(key)
        if code == curses.KEY_MOUSE:
            self.handle_mouse()
            return
        if code == CTRL_S:
            self.save_edit()
            return
        if code == CTRL_E:
            self.mode = "view"
            set_cursor(0)
            self.open_note(self.current)
            return
        if code == ESC:
            self.mode = "view"
            set_cursor(0)
            self.status = "Edit canceled"
            return
        if code == curses.KEY_UP:
            self.edit_y = max(0, self.edit_y - 1)
            self.edit_x = min(self.edit_x, len(self.edit_lines[self.edit_y]))
        elif code == curses.KEY_DOWN:
            self.edit_y = min(len(self.edit_lines) - 1, self.edit_y + 1)
            self.edit_x = min(self.edit_x, len(self.edit_lines[self.edit_y]))
        elif code == curses.KEY_LEFT:
            if self.edit_x > 0:
                self.edit_x -= 1
            elif self.edit_y > 0:
                self.edit_y -= 1
                self.edit_x = len(self.edit_lines[self.edit_y])
        elif code == curses.KEY_RIGHT:
            if self.edit_x < len(self.edit_lines[self.edit_y]):
                self.edit_x += 1
            elif self.edit_y < len(self.edit_lines) - 1:
                self.edit_y += 1
                self.edit_x = 0
        elif code in (curses.KEY_BACKSPACE, 127, 8):
            if self.edit_x > 0:
                line = self.edit_lines[self.edit_y]
                self.edit_lines[self.edit_y] = line[: self.edit_x - 1] + line[self.edit_x :]
                self.edit_x -= 1
            elif self.edit_y > 0:
                current = self.edit_lines.pop(self.edit_y)
                self.edit_y -= 1
                self.edit_x = len(self.edit_lines[self.edit_y])
                self.edit_lines[self.edit_y] += current
        elif code in (10, 13):
            line = self.edit_lines[self.edit_y]
            self.edit_lines[self.edit_y] = line[: self.edit_x]
            self.edit_lines.insert(self.edit_y + 1, line[self.edit_x :])
            self.edit_y += 1
            self.edit_x = 0
        elif isinstance(key, str) and key not in ("\n", "\r", "\t"):
            line = self.edit_lines[self.edit_y]
            self.edit_lines[self.edit_y] = line[: self.edit_x] + key + line[self.edit_x :]
            self.edit_x += len(key)
        elif code is not None and 32 <= code <= 126:
            line = self.edit_lines[self.edit_y]
            ch = chr(code)
            self.edit_lines[self.edit_y] = line[: self.edit_x] + ch + line[self.edit_x :]
            self.edit_x += 1


def main() -> None:
    parser = argparse.ArgumentParser(prog="showmd", description="Terminal markdown vault viewer")
    parser.add_argument("vault", nargs="?", default="database", help="Markdown vault directory")
    parser.add_argument(
        "--theme",
        choices=THEME_ORDER,
        default="transparent",
        help="UI theme to use at startup",
    )
    args = parser.parse_args()
    vault = Path(args.vault)
    if not vault.exists() or not vault.is_dir():
        raise SystemExit(f"Vault directory not found: {vault}")
    curses.wrapper(lambda stdscr: App(stdscr, vault, args.theme).run())


if __name__ == "__main__":
    main()
