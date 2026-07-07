"""ArsChrono sync tool — uv run sync [--dry-run] [--init-anchors]"""

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .config import ANCHOR_MAP, INDEX_HTML, NAV_ANCHOR_PREFIX, NAV_MD_FILE, SRC_DIR, TEASERS_TABLE_FILE
from .injector import apply_anchors, init_anchors, sync_gallery_alts, sync_teasers
from .parser import MdDoc, parse

console = Console()


def _resolve(doc: MdDoc, spec: tuple) -> str | None:
    kind = spec[0]
    if kind == "field":
        return doc.fields.get(spec[1])
    elif kind == "section_field":
        idx, field_key = spec[1], spec[2]
        if idx < len(doc.sections):
            return doc.sections[idx].fields.get(field_key)
    return None


def build_updates(docs: dict[str, MdDoc]) -> dict[str, str]:
    updates: dict[str, str] = {}

    for filename, specs in ANCHOR_MAP.items():
        doc = docs.get(filename)
        if not doc:
            console.print(f"[yellow]⚠ missing md file: {filename}[/yellow]")
            continue
        for spec in specs:
            anchor_key = spec[0]
            value = _resolve(doc, spec[1:])
            if value:
                updates[anchor_key] = value
            else:
                console.print(f"[dim]· {filename}: field not found for anchor '{anchor_key}'[/dim]")

    # Nav labels from 00-nawigacja-i-stopka.md table (col 0 = label, col 1 = target)
    nav_doc = docs.get(NAV_MD_FILE)
    if nav_doc and nav_doc.tables:
        nav_table = nav_doc.tables[0]  # first table is the nav table
        for row in nav_table[1:]:  # skip header row
            if len(row) < 2:
                continue
            label = row[0].strip()
            target = row[1].strip()
            anchor_key = f"{NAV_ANCHOR_PREFIX}{_slugify(target)}"
            updates[anchor_key] = label

    return updates


def _slugify(s: str) -> str:
    return s.lower().replace(" ", "_").replace("-", "_")


def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    do_init = "--init-anchors" in args

    console.rule("[bold]ArsChrono Sync[/bold]")

    if not INDEX_HTML.exists():
        console.print(f"[red]✗ index.html not found at {INDEX_HTML}[/red]")
        sys.exit(1)

    html = INDEX_HTML.read_text(encoding="utf-8")

    # Step 1: init anchors if requested
    if do_init:
        console.print("\n[bold]Adding HTML anchors...[/bold]")
        html, added = init_anchors(html)
        console.print(f"  [green]✓ {added} anchor positions processed[/green]")
        if not dry_run:
            INDEX_HTML.write_text(html, encoding="utf-8")
            console.print("  Saved index.html with anchors.")
        else:
            console.print("  [dim](dry-run — not saved)[/dim]")
        return

    # Step 2: load md files
    console.print("\n[bold]Loading src/*.md...[/bold]")
    docs: dict[str, MdDoc] = {}
    for md_path in sorted(SRC_DIR.glob("*.md")):
        doc = parse(md_path)
        docs[md_path.name] = doc
        console.print(f"  [dim]· {md_path.name} — {len(doc.fields)} fields, {len(doc.sections)} sections[/dim]")

    # Step 3: build anchor updates
    console.print("\n[bold]Building updates...[/bold]")
    updates = build_updates(docs)

    # Step 4: apply anchors
    html, applied = apply_anchors(html, updates)

    # Step 5: gallery alts
    gallery_doc = docs.get("03-galeria.md")
    if gallery_doc and gallery_doc.images:
        html = sync_gallery_alts(html, gallery_doc.images)
        console.print(f"  [green]✓ gallery alts: {len(gallery_doc.images)} images[/green]")

    # Step 6: teasers JS array
    teaser_doc = docs.get(TEASERS_TABLE_FILE)
    if teaser_doc and teaser_doc.tables:
        teaser_table = teaser_doc.tables[-1]  # last table = teaser briefs
        data_rows = teaser_table[1:]  # skip header
        if data_rows:
            html = sync_teasers(html, data_rows)
            console.print(f"  [green]✓ modelTeasers: {len(data_rows)} entries[/green]")

    # Step 7: report
    console.print("\n[bold]Results:[/bold]")
    t = Table(show_header=True, header_style="bold")
    t.add_column("Anchor key")
    t.add_column("Value (truncated)")
    for key in sorted(applied):
        val = updates.get(key, "")
        t.add_row(key, val[:60] + ("…" if len(val) > 60 else ""))
    console.print(t)

    skipped = set(updates.keys()) - set(applied)
    if skipped:
        console.print(f"\n[yellow]⚠ {len(skipped)} anchors not found in HTML:[/yellow] {', '.join(sorted(skipped))}")
        console.print("  Run [bold]uv run sync --init-anchors[/bold] first to add them.")

    # Step 8: save
    if dry_run:
        console.print("\n[dim]Dry-run — not saved.[/dim]")
    else:
        INDEX_HTML.write_text(html, encoding="utf-8")
        console.print(f"\n[green]✓ index.html saved — {len(applied)} anchors updated.[/green]")
