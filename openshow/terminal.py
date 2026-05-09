import base64
import curses
import shutil
import subprocess
import sys

from .models import Theme


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
    data = text.encode()
    for cmd in (["clip.exe"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=data, check=True, timeout=3)
                return True
            except Exception:
                pass
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
