"""Mapping: md files → anchor keys → extraction logic."""

from pathlib import Path

SRC_DIR = Path(__file__).parents[3] / "src"
INDEX_HTML = Path(__file__).parents[3] / "index.html"

# extractor_spec types:
#   ('field', key)                       — top-level field (preamble before first ##)
#   ('section_field', section_idx, key)  — field in doc.sections[section_idx]

ANCHOR_MAP: dict[str, list[tuple]] = {
    "00-nawigacja-i-stopka.md": [
        ("footer_tagline",   "section_field", 1, "tagline"),   # section 1 = Stopka
    ],
    "01-home.md": [
        ("filozofia_cytat",  "section_field", 1, "cytat"),     # section 1 = Filozofia
        ("filozofia_autor",  "section_field", 1, "podpis"),
    ],
    "02-modele.md": [
        ("modele_label",     "field",          "label"),
        ("modele_h1",        "field",          "h1"),
        ("model1_nazwa",     "section_field", 0, "nazwa"),     # section 0 = Regulator
        ("model1_podtytul",  "section_field", 0, "podtytul_kursywa"),
        ("model2_nazwa",     "section_field", 1, "nazwa"),     # section 1 = Dekompresja
        ("model2_podtytul",  "section_field", 1, "podtytul_kursywa"),
        ("model3_nazwa",     "section_field", 2, "nazwa"),     # section 2 = Déjà-Vu
        ("model3_podtytul",  "section_field", 2, "podtytul_kursywa"),
        ("model4_nazwa",     "section_field", 3, "nazwa"),     # section 3 = Obsession
        ("model4_podtytul",  "section_field", 3, "podtytul_kursywa"),
    ],
    "03-galeria.md": [
        ("galeria_label",    "field",          "label"),
        ("galeria_h1",       "field",          "h1"),
        # gallery images handled separately via sync_gallery_alts
    ],
    "04-grafiki.md": [
        ("grafiki_label",    "field",          "label"),
        ("grafiki_h1",       "field",          "h1"),
    ],
    "05-o-autorze.md": [
        ("autor_label",      "field",          "label"),
        ("autor_h1",         "field",          "h1"),
    ],
    "06-kontakt.md": [
        ("kontakt_label",    "field",          "label"),
        ("kontakt_h1",       "field",          "h1"),
    ],
}

# Nav labels: from table[0] in 00-nawigacja-i-stopka.md
# Table format: header row + data rows [label, target_page]
NAV_ANCHOR_PREFIX = "nav_"
NAV_MD_FILE = "00-nawigacja-i-stopka.md"

# Teasers JS array: from last table in 02-modele.md
# Columns: [Nr, Nazwa, Brief]
TEASERS_TABLE_FILE = "02-modele.md"
