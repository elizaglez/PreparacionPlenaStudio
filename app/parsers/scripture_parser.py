from __future__ import annotations

import re

BOOKS = {
    "génesis": "Génesis",
    "éxodo": "Éxodo",
    "levítico": "Levítico",
    "números": "Números",
    "deuteronomio": "Deuteronomio",
    "josué": "Josué",
    "jueces": "Jueces",
    "rut": "Rut",
    "1 samuel": "1 Samuel",
    "2 samuel": "2 Samuel",
    "1 reyes": "1 Reyes",
    "2 reyes": "2 Reyes",
    "1 crónicas": "1 Crónicas",
    "2 crónicas": "2 Crónicas",
    "esdras": "Esdras",
    "nehemías": "Nehemías",
    "ester": "Ester",
    "job": "Job",
    "salmo": "Salmo",
    "salmos": "Salmos",
    "prov.": "Proverbios",
    "proverbios": "Proverbios",
    "ecl.": "Eclesiastés",
    "eclesiastés": "Eclesiastés",
    "isa.": "Isaías",
    "isaías": "Isaías",
    "jer.": "Jeremías",
    "jeremías": "Jeremías",
    "mat.": "Mateo",
    "mateo": "Mateo",
    "mar.": "Marcos",
    "marcos": "Marcos",
    "luc.": "Lucas",
    "lucas": "Lucas",
    "juan": "Juan",
    "hech.": "Hechos",
    "hechos": "Hechos",
    "rom.": "Romanos",
    "romanos": "Romanos",
    "1 cor.": "1 Corintios",
    "2 cor.": "2 Corintios",
    "1 corintios": "1 Corintios",
    "2 corintios": "2 Corintios",
    "gál.": "Gálatas",
    "gálatas": "Gálatas",
    "efes.": "Efesios",
    "efesios": "Efesios",
    "filip.": "Filipenses",
    "filipenses": "Filipenses",
    "col.": "Colosenses",
    "colosenses": "Colosenses",
    "1 tes.": "1 Tesalonicenses",
    "2 tes.": "2 Tesalonicenses",
    "1 tesalonicenses": "1 Tesalonicenses",
    "2 tesalonicenses": "2 Tesalonicenses",
    "1 tim.": "1 Timoteo",
    "2 tim.": "2 Timoteo",
    "1 timoteo": "1 Timoteo",
    "2 timoteo": "2 Timoteo",
    "tito": "Tito",
    "filemón": "Filemón",
    "heb.": "Hebreos",
    "hebreos": "Hebreos",
    "sant.": "Santiago",
    "santiago": "Santiago",
    "1 ped.": "1 Pedro",
    "2 ped.": "2 Pedro",
    "1 pedro": "1 Pedro",
    "2 pedro": "2 Pedro",
    "1 juan": "1 Juan",
    "2 juan": "2 Juan",
    "3 juan": "3 Juan",
    "judas": "Judas",
    "apoc.": "Apocalipsis",
    "apocalipsis": "Apocalipsis",
}

BOOK_PATTERN = "|".join(
    sorted((re.escape(book) for book in BOOKS), key=len, reverse=True)
)

REFERENCE_RE = re.compile(
    rf"\b(?P<book>{BOOK_PATTERN})\s+"
    r"(?P<chapter>\d{1,3}):(?P<verse>\d{1,3})"
    r"(?P<range>(?:[-–]\d{1,3})?(?:,\s*\d{1,3}(?:[-–]\d{1,3})?)*)",
    re.IGNORECASE,
)


def normalize_reference(raw: str) -> str:
    match = REFERENCE_RE.search(raw.strip())
    if not match:
        return raw.strip()

    canonical_book = BOOKS[match.group("book").lower()]
    verse_range = match.group("range").replace("–", "-")
    return (
        f"{canonical_book} {match.group('chapter')}:"
        f"{match.group('verse')}{verse_range}"
    )


def extract_scripture_references(text: str) -> list[str]:
    references: list[str] = []
    for match in REFERENCE_RE.finditer(text):
        normalized = normalize_reference(match.group(0))
        if normalized not in references:
            references.append(normalized)
    return references
