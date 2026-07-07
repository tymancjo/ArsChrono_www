"""Apply parsed md content to index.html."""

import re
from pathlib import Path


_ANCHOR_RE = re.compile(r"<!-- ac:(\w+) -->(.*?)<!-- /ac:\1 -->", re.DOTALL)

# Anchors to inject on --init-anchors, keyed by (old_text, new_text) replacements.
# Ordered: most specific first to avoid double-replacing.
_INIT_REPLACEMENTS: list[tuple[str, str]] = [
    # --- Nav desktop ---
    (">Modele<", "><!-- ac:nav_modele -->Modele<!-- /ac:nav_modele --><"),
    (">Galeria<", "><!-- ac:nav_galeria -->Galeria<!-- /ac:nav_galeria --><"),
    (">Grafiki<", "><!-- ac:nav_grafiki -->Grafiki<!-- /ac:nav_grafiki --><"),
    (">O Autorze<", "><!-- ac:nav_o_autorze -->O Autorze<!-- /ac:nav_o_autorze --><"),
    # Kontakt appears in CTA buttons too — anchor only the text node pattern in nav buttons
    # We rely on the fact that nav/mobile/footer all share the same text node pattern
    (">Kontakt<", "><!-- ac:nav_kontakt -->Kontakt<!-- /ac:nav_kontakt --><"),
    # --- Footer tagline ---
    (
        ">Polskie rzemiosło zegarmistrzowskie<",
        "><!-- ac:footer_tagline -->Polskie rzemiosło zegarmistrzowskie<!-- /ac:footer_tagline --><",
    ),
    # --- Page labels + h1s ---
    (">Kolekcja<", "><!-- ac:modele_label -->Kolekcja<!-- /ac:modele_label --><"),
    (">Nasze Modele<", "><!-- ac:modele_h1 -->Nasze Modele<!-- /ac:modele_h1 --><"),
    (">Fotografia<", "><!-- ac:galeria_label -->Fotografia<!-- /ac:galeria_label --><"),
    (">Galeria<", "><!-- ac:galeria_h1 -->Galeria<!-- /ac:galeria_h1 --><"),
    (">Rzemiosło<", "><!-- ac:grafiki_label -->Rzemiosło<!-- /ac:grafiki_label --><"),
    (
        ">Grafiki na deklach koperty<",
        "><!-- ac:grafiki_h1 -->Grafiki na deklach koperty<!-- /ac:grafiki_h1 --><",
    ),
    (">Twórca<", "><!-- ac:autor_label -->Twórca<!-- /ac:autor_label --><"),
    (">O Autorze<", "><!-- ac:autor_h1 -->O Autorze<!-- /ac:autor_h1 --><"),
    (">Zamówienia i pytania<", "><!-- ac:kontakt_label -->Zamówienia i pytania<!-- /ac:kontakt_label --><"),
    (">Kontakt<", "><!-- ac:kontakt_h1 -->Kontakt<!-- /ac:kontakt_h1 --><"),
    # --- Home philosophy ---
    (
        '>"Zegarek to nie narzędzie do odmierzania czasu — to przedmiot, który określa naszą osobowość i marzenia."<',
        '><!-- ac:filozofia_cytat -->"Zegarek to nie narzędzie do odmierzania czasu — to przedmiot, który określa naszą osobowość i marzenia."<!-- /ac:filozofia_cytat --><',
    ),
    (
        ">Paweł Jankowski — Twórca Ars Chrono<",
        "><!-- ac:filozofia_autor -->Paweł Jankowski — Twórca Ars Chrono<!-- /ac:filozofia_autor --><",
    ),
    # --- Model names and subtitles ---
    (">Regulator<", "><!-- ac:model1_nazwa -->Regulator<!-- /ac:model1_nazwa --><"),
    (">Czas mierzony precyzją<", "><!-- ac:model1_podtytul -->Czas mierzony precyzją<!-- /ac:model1_podtytul --><"),
    (">Dekompresja<", "><!-- ac:model2_nazwa -->Dekompresja<!-- /ac:model2_nazwa --><"),
    (">Ogień zamknięty w tytanie<", "><!-- ac:model2_podtytul -->Ogień zamknięty w tytanie<!-- /ac:model2_podtytul --><"),
    (">Déjà-Vu<", "><!-- ac:model3_nazwa -->Déjà-Vu<!-- /ac:model3_nazwa --><"),
    (">Perła emalii piecowej<", "><!-- ac:model3_podtytul -->Perła emalii piecowej<!-- /ac:model3_podtytul --><"),
    (">Obsession<", "><!-- ac:model4_nazwa -->Obsession<!-- /ac:model4_nazwa --><"),
    (">Maestria metody treblage<", "><!-- ac:model4_podtytul -->Maestria metody treblage<!-- /ac:model4_podtytul --><"),
]


def init_anchors(html: str) -> tuple[str, int]:
    """Add <!-- ac:KEY --> comment anchors to HTML (one-time operation)."""
    count = 0
    for old, new in _INIT_REPLACEMENTS:
        if old in html and new not in html:
            html = html.replace(old, new)
            count += html.count(new.split("-->")[0] + "-->") - 1  # rough count
            count += 1
    return html, count


def apply_anchors(html: str, updates: dict[str, str]) -> tuple[str, list[str]]:
    """Replace content between <!-- ac:KEY --> markers."""
    applied: list[str] = []

    def replacer(m: re.Match) -> str:
        key = m.group(1)
        if key in updates:
            applied.append(key)
            return f"<!-- ac:{key} -->{updates[key]}<!-- /ac:{key} -->"
        return m.group(0)

    result = _ANCHOR_RE.sub(replacer, html)
    return result, applied


def sync_gallery_alts(html: str, images: list[tuple[str, str]]) -> str:
    """Update alt attrs on gallery images (gallery_pictures/ src) using regex."""
    if not images:
        return html
    # Build src-filename → alt mapping
    path_to_alt: dict[str, str] = {}
    for alt, path in images:
        filename = path.split("/")[-1]
        path_to_alt[filename] = alt

    def _update(m: re.Match) -> str:
        src = m.group(1)
        filename = src.split("/")[-1]
        new_alt = path_to_alt.get(filename, path_to_alt.get(list(path_to_alt)[-1], ""))
        return f'<img src="{src}" alt="{new_alt}"'

    return re.sub(r'<img src="(gallery_pictures/[^"]+)" alt="[^"]*"', _update, html)


_TEASERS_RE = re.compile(r"(teasers\s*=\s*\[)(.*?)(\];)", re.DOTALL)


def sync_teasers(html: str, rows: list[list[str]]) -> str:
    """
    Replace teasers array in <script type="text/x-dc">.
    rows: list of [num, name, brief] from markdown table.
    """
    if not rows:
        return html

    lines = []
    for row in rows:
        if len(row) < 3:
            continue
        num = row[0].strip().zfill(2)
        name = row[1].strip().replace("'", "\\'")
        brief = row[2].strip().replace("'", "\\'")
        lines.append(f"    {{ num: '{num}', name: '{name}',   brief: '{brief}' }},")

    body = "\n".join(lines)

    def replacer(m: re.Match) -> str:
        return f"{m.group(1)}\n{body}\n  {m.group(3)}"

    return _TEASERS_RE.sub(replacer, html)
