"""Hilfsfunktionen für Textnormalisierung und Keyword-Matching."""

from __future__ import annotations

import html
import re
import unicodedata
from functools import lru_cache

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(raw: str | None) -> str:
    if not raw:
        return ""
    # Manche APIs liefern doppelt escaptes HTML (&lt;p&gt;)
    text = html.unescape(html.unescape(raw))
    text = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


def snippet(raw: str | None, length: int = 600) -> str:
    text = strip_html(raw)
    return text if len(text) <= length else text[:length].rsplit(" ", 1)[0] + " …"


def fold(text: str) -> str:
    """Kleinbuchstaben, Umlaute vereinheitlicht (ü→ue), Akzente entfernt."""
    text = text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


@lru_cache(maxsize=2048)
def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    # Keyword muss am Wortanfang stehen; ein "$" am Ende erzwingt zusätzlich das Wortende.
    # Beispiel: "vertrieb" trifft "Vertriebsassistenz", "bd$" trifft nur "BD", nicht "BDSG".
    whole_word = keyword.endswith("$")
    kw = fold(keyword.rstrip("$"))
    body = r"\s*".join(re.escape(part) for part in kw.split())
    return re.compile(r"(?<![a-z0-9])" + body + (r"(?![a-z0-9])" if whole_word else ""))


def contains_any(text: str, keywords: list[str]) -> str | None:
    """Gibt das erste passende Keyword zurück (oder None)."""
    folded = fold(text)
    for kw in keywords:
        if _keyword_pattern(kw).search(folded):
            return kw
    return None


_GENDER_RE = re.compile(r"\((?:[mwfdxi]\s*/\s*)+[mwfdxi]\)|\(all genders?\)|\(gn\)|\*in\b|:in\b", re.I)
_COMPANY_SUFFIX_RE = re.compile(
    r"\b(gmbh|mbh|ag|se|kg|kgaa|co|ug|ohg|ev|e\.v|inc|ltd|llc|bv|b\.v|nv|sa|sarl|plc|haftungsbeschraenkt|group|holding)\b"
)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_title(title: str) -> str:
    t = _GENDER_RE.sub(" ", title)
    t = fold(t)
    return _NON_ALNUM_RE.sub(" ", t).strip()


def normalize_company(company: str) -> str:
    c = fold(company)
    c = _NON_ALNUM_RE.sub(" ", c)
    c = _COMPANY_SUFFIX_RE.sub(" ", c)
    return _WS_RE.sub(" ", c).strip()
