import re
import unicodedata

from .models import RenderLink


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


def offset_links(links: list[RenderLink], offset: int) -> list[RenderLink]:
    return [
        RenderLink(link.start + offset, link.end + offset, link.text, link.target, link.anchor)
        for link in links
    ]


def parent_path(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""
