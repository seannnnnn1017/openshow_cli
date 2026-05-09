import argparse
import curses
from pathlib import Path

from .app import App
from .themes import THEME_ORDER


def main() -> None:
    parser = argparse.ArgumentParser(prog="openshow", description="Terminal document and Markdown vault viewer")
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="File or directory to open (default: current directory)",
    )
    parser.add_argument(
        "--theme",
        choices=THEME_ORDER,
        default="transparent",
        help="UI theme to use at startup",
    )
    args = parser.parse_args()
    target = Path(args.target)
    if not target.exists():
        raise SystemExit(f"Path not found: {target}")
    if not target.is_file() and not target.is_dir():
        raise SystemExit(f"Path is not a file or directory: {target}")
    curses.wrapper(lambda stdscr: App(stdscr, target, args.theme).run())
