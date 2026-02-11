"""Markdown-aware document chunking."""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

MAX_SECTION_LINES = 300
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
CODE_FENCE_PATTERN = re.compile(r"^```")


@dataclass
class DocChunk:
    """A chunk extracted from a markdown document."""

    chunk_type: str  # frontmatter, section, code_block, paragraph
    heading: str | None
    content: str
    start_line: int
    end_line: int
    metadata: dict = field(default_factory=dict)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown content.

    Returns (metadata, remaining_content).
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content

    try:
        metadata = yaml.safe_load(match.group(1)) or {}
        remaining = content[match.end() :]
        return metadata, remaining
    except yaml.YAMLError as e:
        logger.warning("Failed to parse frontmatter: %s", e)
        return {}, content


def chunk_markdown(path: Path) -> list[DocChunk]:
    """Extract semantic chunks from a markdown file."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Failed to read %s: %s", path, e)
        return []

    chunks: list[DocChunk] = []
    lines = content.splitlines()

    # Extract frontmatter
    metadata, remaining = parse_frontmatter(content)
    if metadata:
        fm_lines = content[: len(content) - len(remaining)].count("\n")
        chunks.append(
            DocChunk(
                chunk_type="frontmatter",
                heading=None,
                content=yaml.dump(metadata, default_flow_style=False),
                start_line=1,
                end_line=fm_lines,
                metadata=metadata,
            )
        )
        # Adjust lines to exclude frontmatter
        lines = remaining.splitlines()
        line_offset = fm_lines
    else:
        line_offset = 0

    # Extract sections
    sections = _extract_sections(lines, line_offset)
    chunks.extend(sections)

    return chunks


def _extract_sections(lines: list[str], line_offset: int) -> list[DocChunk]:
    """Extract sections from lines, splitting on H1/H2/H3 headings."""
    if not lines:
        return []

    chunks: list[DocChunk] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    section_start = 0

    def flush_section() -> None:
        nonlocal current_lines, section_start
        if not current_lines:
            return
        content = "\n".join(current_lines).strip()
        if content:
            chunks.append(
                DocChunk(
                    chunk_type="section",
                    heading=current_heading,
                    content=content,
                    start_line=section_start + line_offset + 1,
                    end_line=len(current_lines) + section_start + line_offset,
                    metadata={},
                )
            )
        current_lines = []

    for i, line in enumerate(lines):
        match = HEADING_PATTERN.match(line)
        if match:
            level = len(match.group(1))
            heading_text = match.group(2).strip()

            # Split on H1, H2, or H3 headings (main document structure)
            if level <= 3:
                flush_section()
                current_heading = heading_text
                section_start = i
                current_lines = [line]
            else:
                # H4+ - keep in current section
                current_lines.append(line)
        else:
            current_lines.append(line)

    flush_section()
    return chunks


def extract_code_blocks(content: str) -> list[tuple[int, int, str]]:
    """Extract code block positions from content.

    Returns list of (start_line, end_line, language).
    """
    lines = content.splitlines()
    blocks: list[tuple[int, int, str]] = []
    in_block = False
    block_start = 0
    block_lang = ""

    for i, line in enumerate(lines):
        if CODE_FENCE_PATTERN.match(line):
            if in_block:
                blocks.append((block_start + 1, i + 1, block_lang))
                in_block = False
            else:
                in_block = True
                block_start = i
                block_lang = line[3:].strip()

    return blocks
