"""Local web UI for reordering/captioning ArsChrono gallery photos.

Reads/writes src/03-galeria.md (the source of truth). Never touches
index.html - HTML deployment stays a separate manual/Claude step.
"""
import re
from pathlib import Path

from flask import Flask, jsonify, request, render_template, send_from_directory

ROOT = Path(__file__).resolve().parents[2]
GALLERY_DIR = ROOT / "gallery_pictures"
MD_PATH = ROOT / "src" / "03-galeria.md"

IMG_RE = re.compile(r"!\[(.*?)\]\(gallery_pictures/(.*?)\)")
FEATURED_HEADER_RE = re.compile(r"^### Wyróżnione.*$", re.MULTILINE)
GRID_HEADER_RE = re.compile(r"^### Siatka.*$", re.MULTILINE)
TOTAL_COUNT_RE = re.compile(r"Wszystkie \d+ zdjęć")
GRID_COUNT_RE = re.compile(r"pozostałe \d+")

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

app = Flask(__name__)


def default_alt(filename: str) -> str:
    if "Obssesion" in filename:
        return "Ars Chrono, model Obsesja"
    if "Regulator" in filename:
        return "Ars Chrono, model Regulator"
    return "Ars Chrono"


def natural_key(filename: str):
    parts = re.split(r"(\d+)", filename)
    return [int(p) if p.isdigit() else p for p in parts]


def parse_gallery():
    text = MD_PATH.read_text(encoding="utf-8")

    fm = FEATURED_HEADER_RE.search(text)
    gm = GRID_HEADER_RE.search(text)
    if not fm or not gm:
        raise ValueError("src/03-galeria.md: expected section headers not found")

    featured_block = text[fm.end():gm.start()]
    grid_block = text[gm.end():]

    featured = [
        {"file": m.group(2), "alt": m.group(1)}
        for m in IMG_RE.finditer(featured_block)
    ]
    grid = [
        {"file": m.group(2), "alt": m.group(1)}
        for m in IMG_RE.finditer(grid_block)
    ]

    known_files = {item["file"] for item in featured} | {item["file"] for item in grid}
    on_disk = [
        p.name for p in GALLERY_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]
    new_files = sorted((f for f in on_disk if f not in known_files), key=natural_key)
    new = [{"file": f, "alt": default_alt(f)} for f in new_files]

    return {"featured": featured, "grid": grid, "new": new}


def render_gallery(featured, grid):
    """Rewrite src/03-galeria.md, preserving all boilerplate text verbatim
    except the two photo-count numbers and the two image-list blocks."""
    text = MD_PATH.read_text(encoding="utf-8")

    fm = FEATURED_HEADER_RE.search(text)
    gm = GRID_HEADER_RE.search(text)
    if not fm or not gm:
        raise ValueError("src/03-galeria.md: expected section headers not found")

    prefix = text[:fm.end()]
    featured_header = fm.group(0)
    grid_header_original = gm.group(0)

    total = len(featured) + len(grid)
    prefix = TOTAL_COUNT_RE.sub(f"Wszystkie {total} zdjęć", prefix)

    grid_header = GRID_COUNT_RE.sub(f"pozostałe {len(grid)}", grid_header_original)

    featured_lines = "\n".join(
        f"![{item['alt']}](gallery_pictures/{item['file']})" for item in featured
    )
    grid_lines = "\n".join(
        f"![{item['alt']}](gallery_pictures/{item['file']})" for item in grid
    )

    new_text = (
        f"{prefix}\n"
        f"{featured_lines}\n\n"
        f"{grid_header}\n"
        f"{grid_lines}\n"
    )
    MD_PATH.write_text(new_text, encoding="utf-8")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    return jsonify(parse_gallery())


@app.route("/api/save", methods=["POST"])
def api_save():
    body = request.get_json(force=True)
    featured = body.get("featured", [])
    grid = body.get("grid", [])

    if len(featured) != 3:
        return jsonify({"ok": False, "error": "Featured section needs exactly 3 photos"}), 400
    if any(not item.get("file") for item in featured + grid):
        return jsonify({"ok": False, "error": "Every slot needs a photo"}), 400

    render_gallery(featured, grid)
    return jsonify({"ok": True})


@app.route("/pictures/<path:filename>")
def pictures(filename):
    return send_from_directory(GALLERY_DIR, filename)


if __name__ == "__main__":
    app.run(port=5001, debug=True)
