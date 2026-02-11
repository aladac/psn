"""Code chunking for project indexing."""

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
}

CHUNK_WINDOW_SIZE = 50
CHUNK_OVERLAP = 10


@dataclass
class Chunk:
    """A code chunk extracted from a file."""

    chunk_type: str
    name: str | None
    content: str
    start_line: int
    end_line: int


def detect_language(path: Path) -> str | None:
    """Detect language from file extension."""
    return LANGUAGE_EXTENSIONS.get(path.suffix.lower())


def chunk_file(path: Path, language: str | None = None) -> list[Chunk]:
    """Extract semantic chunks from a file.

    Uses tree-sitter if available, otherwise falls back to sliding window.
    """
    if language is None:
        language = detect_language(path)

    content = path.read_text()
    lines = content.splitlines()

    if language and _has_tree_sitter(language):
        try:
            return _tree_sitter_chunks(content, lines, language)
        except Exception as e:
            logger.warning("Tree-sitter failed for %s: %s", path, e)

    return sliding_window_chunks(lines, str(path))


def sliding_window_chunks(
    lines: list[str],
    source_name: str,
    window_size: int = CHUNK_WINDOW_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Create overlapping window chunks from lines."""
    if not lines:
        return []

    chunks = []
    step = max(1, window_size - overlap)
    total_lines = len(lines)

    for start in range(0, total_lines, step):
        end = min(start + window_size, total_lines)
        chunk_lines = lines[start:end]
        content = "\n".join(chunk_lines)

        if content.strip():
            chunks.append(
                Chunk(
                    chunk_type="window",
                    name=f"{source_name}:{start + 1}-{end}",
                    content=content,
                    start_line=start + 1,
                    end_line=end,
                )
            )

        if end >= total_lines:
            break

    return chunks


def _has_tree_sitter(language: str) -> bool:
    """Check if tree-sitter is available for a language."""
    try:
        import tree_sitter  # noqa: F401

        lang_module = f"tree_sitter_{language}"
        __import__(lang_module)
        return True
    except ImportError:
        return False


def _tree_sitter_chunks(content: str, lines: list[str], language: str) -> list[Chunk]:
    """Extract semantic chunks using tree-sitter."""
    import tree_sitter

    lang_module = __import__(f"tree_sitter_{language}")
    ts_language = tree_sitter.Language(lang_module.language())
    parser = tree_sitter.Parser(ts_language)
    tree = parser.parse(content.encode())

    chunks = []
    node_types = _get_chunk_node_types(language)

    def visit(node: tree_sitter.Node) -> None:
        if node.type in node_types:
            name = _extract_name(node, language)
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            chunk_content = "\n".join(lines[start_line - 1 : end_line])

            chunks.append(
                Chunk(
                    chunk_type=node.type,
                    name=name,
                    content=chunk_content,
                    start_line=start_line,
                    end_line=end_line,
                )
            )
        else:
            for child in node.children:
                visit(child)

    visit(tree.root_node)

    if not chunks:
        return sliding_window_chunks(lines, "fallback")

    return chunks


def _get_chunk_node_types(language: str) -> set[str]:
    """Get node types to extract as chunks for a language."""
    types = {
        "python": {"function_definition", "class_definition", "decorated_definition"},
        "ruby": {"method", "class", "module", "singleton_method"},
        "rust": {"function_item", "impl_item", "struct_item", "enum_item", "mod_item"},
        "javascript": {"function_declaration", "class_declaration", "arrow_function"},
        "typescript": {"function_declaration", "class_declaration", "arrow_function"},
    }
    return types.get(language, set())


def _extract_name(node, language: str) -> str | None:
    """Extract the name from a node."""
    name_field = None

    for child in node.children:
        if child.type == "identifier":
            name_field = child
            break
        if child.type == "name":
            name_field = child
            break

    if name_field:
        return name_field.text.decode()

    return None
