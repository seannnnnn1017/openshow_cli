import json

from openshow import Vault, notebook_to_markdown, read_document


def test_vault_scans_markdown_text_code_and_notebooks(tmp_path):
    (tmp_path / "note.md").write_text("# Note\n", encoding="utf-8")
    (tmp_path / "plain.txt").write_text("plain text\n", encoding="utf-8")
    (tmp_path / "script.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "book.ipynb").write_text(json.dumps({"cells": []}), encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"not a document")

    vault = Vault(tmp_path)

    assert [note.rel for note in vault.notes] == [
        "book.ipynb",
        "note.md",
        "plain.txt",
        "script.py",
    ]


def test_direct_file_target_loads_single_text_file(tmp_path):
    target = tmp_path / "notes.txt"
    target.write_text("hello\n", encoding="utf-8")

    vault = Vault(target)

    assert vault.single_file
    assert vault.display_name == "notes.txt"
    assert [note.rel for note in vault.notes] == ["notes.txt"]
    assert vault.default_note().raw == "hello\n"


def test_read_document_marks_notebooks_view_only(tmp_path):
    target = tmp_path / "book.ipynb"
    target.write_text(json.dumps({"cells": []}), encoding="utf-8")

    raw, body, kind, editable = read_document(target)

    assert raw == body
    assert kind == "notebook"
    assert not editable


def test_notebook_to_markdown_includes_markdown_code_and_output(tmp_path):
    target = tmp_path / "book.ipynb"
    target.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "markdown", "source": ["## Heading\n", "body"]},
                    {
                        "cell_type": "code",
                        "execution_count": 3,
                        "source": ["print('hi')\n"],
                        "outputs": [{"output_type": "stream", "text": "hi\n"}],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    rendered = notebook_to_markdown(target)

    assert "# book.ipynb" in rendered
    assert "## Heading" in rendered
    assert "```python input 3" in rendered
    assert "print('hi')" in rendered
    assert "```text output" in rendered
    assert "hi" in rendered
