"""Shared location filters for job-board data."""
from __future__ import annotations

import re
import unicodedata


IDF_DEPARTMENT_CODES = {"75", "77", "78", "91", "92", "93", "94", "95"}

IDF_LOCATION_TERMS = (
    "paris",
    "ile de france",
    "ile-de-france",
    "idf",
    "la defense",
    "hauts de seine",
    "hauts-de-seine",
    "seine saint denis",
    "seine-saint-denis",
    "val de marne",
    "val-de-marne",
    "val d oise",
    "val-d-oise",
    "yvelines",
    "essonne",
    "seine et marne",
    "seine-et-marne",
    "boulogne",
    "neuilly",
    "courbevoie",
    "puteaux",
    "nanterre",
    "levallois",
    "issy les moulineaux",
    "issy-les-moulineaux",
    "fontenay sous bois",
    "fontenay-sous-bois",
)


def normalize_location_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def is_ile_de_france_location(value: str | None) -> bool:
    normalized = normalize_location_text(value)
    if not normalized:
        return False
    if any(term in normalized for term in IDF_LOCATION_TERMS):
        return True
    codes = set(re.findall(r"(?<!\d)(?:75|77|78|91|92|93|94|95)(?!\d)", normalized))
    return bool(codes & IDF_DEPARTMENT_CODES)
