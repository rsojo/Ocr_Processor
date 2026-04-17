"""Post-processing utilities for markdown output from OCR / pdf-inspector."""
from __future__ import annotations

import re
from typing import List, Optional

_TABLE_MARKER = "<!-- TABLE -->"
_PAGE_MARKER_RE = re.compile(r"<!-- Page \d+ -->")
_HEADING_RE = re.compile(r"^#{1,6} ")
_LIST_ITEM_RE = re.compile(r"^[-*+] |\d+\. ")

# Lines composed only of visual separators with no meaningful content.
_SEPARATOR_ONLY_RE = re.compile(r"^[-—=_~\s|\\/']{3,}$")

_ALNUM = re.compile(r"[a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ]")

# Slide-decoration annotations appended by pdf-inspector at the end of lines
# e.g. "Gz)", "Cs", "(CD)", "SB", "B"
_TRAILING_DECORATION = re.compile(
    r"\s+(?:[A-Z][a-z]?\)|\([A-Z]{1,3}\)|[A-Z]{1,2})\s*$"
)
# Leading smart-quote or apostrophe before a capital letter
_LEADING_QUOTE = re.compile(r"^['\u2018\u2019]\s*(?=[A-Z])")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_structural_garbage(line: str) -> bool:
    """Return True when a line is pure visual decoration with no real content."""
    stripped = line.strip()
    if not stripped:
        return False
    if _PAGE_MARKER_RE.fullmatch(stripped):
        return False
    if _HEADING_RE.match(stripped) or _LIST_ITEM_RE.match(stripped):
        return False
    if _SEPARATOR_ONLY_RE.fullmatch(stripped):
        return True
    alpha = len(_ALNUM.findall(stripped))
    # Fewer than 25 % alphanumeric characters in a line longer than 4 chars.
    if len(stripped) > 4 and alpha / len(stripped) < 0.25:
        return True
    return False


def _clean_line(line: str) -> str:
    """Strip common inline OCR artefacts from a single line."""
    line = _TRAILING_DECORATION.sub("", line)
    line = _LEADING_QUOTE.sub("", line)
    # Normalise runs of 2+ spaces to a single space.
    line = re.sub(r"  +", " ", line)
    return line.strip()


def _try_markdown_table(rows: List[str]) -> Optional[List[str]]:
    """
    Attempt to build a GFM markdown table from rows with pipe characters.
    Returns None when the data is too ambiguous.
    """
    pipe_rows = [r for r in rows if "|" in r]
    if len(pipe_rows) < 2:
        return None

    parsed: List[List[str]] = []
    for row in pipe_rows:
        cells = [c.strip() for c in row.split("|")]
        cells = [c for c in cells if c]  # drop empty edge cells
        if cells:
            parsed.append(cells)

    if not parsed:
        return None

    max_cols = max(len(r) for r in parsed)
    if max_cols < 2:
        return None

    # Pad every row to the same number of columns.
    normalized = [r + [""] * (max_cols - len(r)) for r in parsed]
    header, *body = normalized

    result = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        result.append("| " + " | ".join(row) + " |")

    return result


def _render_table_block(raw_lines: List[str]) -> List[str]:
    """
    Turn a collected group of table-region lines into readable output.
    Tries markdown table first; falls back to a bullet list.
    """
    clean = [_clean_line(ln) for ln in raw_lines]
    clean = [ln for ln in clean if ln and not _is_structural_garbage(ln)]

    if not clean:
        return []

    md_table = _try_markdown_table(clean)
    if md_table:
        return ["", *md_table, ""]

    # Fall back: render each row as a list item.
    return ["", *[f"- {ln}" for ln in clean], ""]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def clean_markdown(markdown: str) -> str:
    """
    Clean and improve markdown produced by pdf-inspector / OCR engines.

    Actions performed:
    * Removes pure separator / decoration lines (rows of dashes, equals, etc.).
    * Groups ``<!-- TABLE -->`` lines and reconstructs proper GFM tables when
      pipe-delimited columns are detected; falls back to a bullet list otherwise.
    * Strips common OCR artefacts (trailing slide decorations, leading quotes).
    * Collapses three or more consecutive blank lines to two.
    """
    lines = markdown.split("\n")
    output: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # ---- Table block: collect consecutive TABLE-marker lines ----
        if _TABLE_MARKER in line:
            table_lines: List[str] = []
            while i < len(lines) and _TABLE_MARKER in lines[i]:
                content = lines[i].replace(_TABLE_MARKER, "").strip()
                if content:
                    table_lines.append(content)
                i += 1
            output.extend(_render_table_block(table_lines))
            continue

        # ---- Pure structural garbage ----
        if _is_structural_garbage(line):
            i += 1
            continue

        # ---- Regular line ----
        output.append(_clean_line(line) if line.strip() else "")
        i += 1

    # Collapse 3+ consecutive blank lines down to 2.
    result: List[str] = []
    blank_run = 0
    for ln in output:
        if not ln.strip():
            blank_run += 1
            if blank_run <= 2:
                result.append(ln)
        else:
            blank_run = 0
            result.append(ln)

    return "\n".join(result)
