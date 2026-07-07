"""Extract structured content from src/*.md files."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Section:
    heading: str
    fields: dict[str, str]
    images: list[tuple[str, str]]  # (alt, path)


@dataclass
class MdDoc:
    fields: dict[str, str]
    sections: list[Section]
    images: list[tuple[str, str]]
    tables: list[list[list[str]]]  # [table][row][col]


_FIELD_RE = re.compile(
    r"\*\*([^*\n]+?):\*\*\s*\n(.*?)(?=\n\s*\*\*[^*\n]+?:\*\*|\n\s*##|\n\s*---|\Z)",
    re.DOTALL,
)
_IMG_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", re.MULTILINE)
_H2_RE = re.compile(r"^## .+$", re.MULTILINE)


def _extract_fields(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for m in _FIELD_RE.finditer(text):
        key = _norm(m.group(1))
        val = m.group(2).strip()
        lines = [l.strip() for l in val.splitlines() if l.strip()]
        result[key] = " ".join(lines)
    return result


def _extract_images(text: str) -> list[tuple[str, str]]:
    return _IMG_RE.findall(text)


def _parse_table(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|[-| :]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2:
            rows.append(cells)
    return rows


def _extract_tables(text: str) -> list[list[list[str]]]:
    """Extract all markdown tables as list-of-rows."""
    tables = []
    in_table = False
    current: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            if not in_table:
                in_table = True
                current = []
            current.append(stripped)
        else:
            if in_table:
                tables.append(_parse_table("\n".join(current)))
                in_table = False
                current = []
    if in_table and current:
        tables.append(_parse_table("\n".join(current)))
    return tables


def _norm(raw: str) -> str:
    """'Podtytuł (kursywa)' → 'podtytul_kursywa'"""
    s = raw.lower().strip()
    # replace Polish chars
    for src, dst in [("ą","a"),("ć","c"),("ę","e"),("ł","l"),("ń","n"),("ó","o"),("ś","s"),("ź","z"),("ż","z")]:
        s = s.replace(src, dst)
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s


def parse(path: Path) -> MdDoc:
    text = path.read_text(encoding="utf-8")

    # Split into H2 sections
    h2_positions = [m.start() for m in _H2_RE.finditer(text)]
    h2_positions.append(len(text))

    preamble = text[: h2_positions[0]] if h2_positions[0] > 0 else ""
    top_fields = _extract_fields(preamble)
    top_images = _extract_images(preamble)
    top_tables = _extract_tables(preamble)

    sections: list[Section] = []
    for i, pos in enumerate(h2_positions[:-1]):
        chunk_end = h2_positions[i + 1]
        chunk = text[pos:chunk_end]
        heading_line = chunk.splitlines()[0]
        heading = heading_line.lstrip("#").strip()
        body = "\n".join(chunk.splitlines()[1:])
        fields = _extract_fields(body)
        images = _extract_images(body)
        sections.append(Section(heading=heading, fields=fields, images=images))

    # Merge tables from entire doc for convenience
    all_tables = _extract_tables(text)

    return MdDoc(
        fields=top_fields,
        sections=sections,
        images=top_images if top_images else _extract_images(text),
        tables=all_tables,
    )
