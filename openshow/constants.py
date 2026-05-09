import re


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

MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd"}
TEXT_EXTENSIONS = {".txt", ".text", ".log", ".csv", ".tsv", ".json", ".yaml", ".yml", ".toml", ".xml"}
CODE_EXTENSIONS = {
    ".bash", ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html",
    ".java", ".js", ".jsx", ".kt", ".lua", ".php", ".pl", ".py", ".r", ".rb",
    ".rs", ".scala", ".scss", ".sh", ".sql", ".swift", ".tsx", ".ts", ".vue",
}
NOTEBOOK_EXTENSIONS = {".ipynb"}
SUPPORTED_FILE_EXTENSIONS = MARKDOWN_EXTENSIONS | TEXT_EXTENSIONS | CODE_EXTENSIONS | NOTEBOOK_EXTENSIONS
