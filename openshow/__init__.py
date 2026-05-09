from .documents import Vault, notebook_to_markdown, read_document
from .models import Note, RenderLine
from .search import collect_search_hits


def main() -> None:
    from .cli import main as cli_main

    cli_main()

__all__ = [
    "Note",
    "RenderLine",
    "Vault",
    "collect_search_hits",
    "main",
    "notebook_to_markdown",
    "read_document",
]
