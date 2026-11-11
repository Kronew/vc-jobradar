"""Persönliche Einstellungen (settings.yaml) und das Einstellungsformular auf GitHub.

Ablauf: Jede Mail enthält einen Link auf ein GitHub-Issue-Formular (vorausgefüllt mit den aktuellen
Werten). Beim Absenden startet `.github/workflows/settings.yml` und ruft auf:

    python -m jobtracker.settings apply --body-env ISSUE_BODY --comment-file … --github-output …

Das liest das Formular aus, ermittelt bei Bedarf die Koordinaten der „anderen Stadt“ (OpenStreetMap),
schreibt settings.yaml und schickt eine Bestätigungsmail. Aus settings.yaml und defaults.yaml
baut `build_raw()` die vollständige Config.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

import yaml

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "settings.yaml"
DEFAULTS_PATH = Path(__file__).resolve().parent / "defaults.yaml"
ISSUE_TEMPLATE = "einstellungen.yml"
ISSUE_LABEL = "einstellungen"
STUDENT_WORDS = re.compile(r"\b(werkstudent(in|\*in|:in)?|working student|studentische[rn]? \w+)\b", re.I)

log = logging.getLogger(__name__)

# Überschriften im Formular (müssen zu .github/ISSUE_TEMPLATE/einstellungen.yml passen – ein Test prüft das)
FIELDS = {
    "job_types": "Was suchst du?",
    "profile": "Über dich",
    "cities": "Städte",
    "place": "Andere Stadt",
    "radius_km": "Pendelradius",
    "remote": "Remote-Stellen",
    "other_cities": "Stellen aus ganz Deutschland",
    "categories": "Bereiche",
    "vcs": "VCs",
    "extra_terms": "Eigene Stichwörter",
    "exclude_terms": "Ausschließen",
}
ALL_CATEGORIES = "Alle Bereiche"
ALL_VCS = "Alle VCs"
NO_CITY = "Keine (ganz Deutschland)"
FORM_IDS = {"profile": "profil", "place": "ort", "extra_terms": "stichwoerter", "exclude_terms": "ausschluesse"}
UNCHANGED = "unverändert"
NO_RESPONSE = "_No response_"
CLEAR = "-"


class SettingsError(Exception):
    """Fehler in den eingegebenen Einstellungen (wird dem Nutzer angezeigt)."""


def load_defaults() -> dict[str, Any]:
    return yaml.safe_load(DEFAULTS_PATH.read_text(encoding="utf-8")) or {}


def catalog() -> dict[str, dict[str, Any]]:
    return load_defaults().get("category_catalog", {})


def job_types() -> dict[str, dict[str, Any]]:
    return load_defaults().get("job_types", {})


def startup_cities() -> dict[str, dict[str, Any]]:
    return load_defaults().get("startup_cities", {})


def vc_names() -> list[str]:
    return [b["name"] for b in load_defaults().get("sources", {}).get("vc_boards", {}).get("boards", [])]


def load_settings(path: Path = SETTINGS_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_settings(settings: dict[str, Any], path: Path = SETTINGS_PATH) -> None:
    header = ("# Deine Einstellungen – am einfachsten über den Link „Einstellungen ändern“ in der Mail pflegen.\n"
              "# Koordinaten einer „anderen Stadt“ werden dabei automatisch ermittelt.\n")
    path.write_text(header + yaml.safe_dump(settings, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")


# --- settings.yaml → Config ---------------------------------------------------


def _keyword(term: str) -> str:
    """'Werkstudent Einkauf' → 'einkauf' (Studenten-Wort steckt schon im Pflicht-Titelfilter)."""
    return re.sub(r"\s+", " ", STUDENT_WORDS.sub(" ", term)).strip(" -–/").lower()


def home_centers(settings: dict[str, Any], defaults: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Mittelpunkte für den Pendelradius: angekreuzte Startup-Städte und die andere Stadt."""
    city_defs = (defaults if defaults is not None else load_defaults()).get("startup_cities", {})
    centers = [{"name": city_defs[c]["label"], "lat": city_defs[c]["lat"], "lon": city_defs[c]["lon"]}
               for c in city_defs if c in (settings.get("cities") or [])]
    if settings.get("place") and settings.get("lat") is not None:
        centers.append({"name": settings["place"], "lat": settings["lat"], "lon": settings["lon"]})
    return centers


def build_raw(settings: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    """Leitet aus den Einstellungen die Config-Abschnitte ab (werden über defaults.yaml gelegt)."""
    defaults = defaults if defaults is not None else load_defaults()
    cat_defs = defaults.get("category_catalog", {})
    type_defs = defaults.get("job_types", {})

    # Stellenart → Getro-Suche, Pflichtwörter im Titel, Ausschlüsse
    types = [t for t in type_defs if t in (settings.get("job_types") or ["werkstudent"])]
    queries = [q for t in types for q in type_defs[t]["queries"]]
    title_required = [w for t in types for w in type_defs[t]["title_words"]]
    excludes = list((defaults.get("filters") or {}).get("title_exclude", []))
    if len(types) == 1:
        excludes += type_defs[types[0]].get("exclusive_excludes", [])
    excludes += [t.lower() for t in settings.get("exclude_terms") or []]

    # Bereiche: ohne Auswahl alle (dann auch nicht zuordenbare Stellen unter „Sonstige“)
    chosen = [c for c in cat_defs if c in (settings.get("categories") or [])]
    extra = [t for t in settings.get("extra_terms") or [] if t]
    all_categories = not chosen and not extra
    categories = {c: {"label": cat_defs[c]["label"], "keywords": cat_defs[c]["keywords"]}
                  for c in (cat_defs if all_categories else chosen)}
    if extra_keywords := [k for k in dict.fromkeys(_keyword(t) for t in extra) if k]:
        categories["eigene"] = {"label": "Eigene Stichwörter", "keywords": extra_keywords}

    # VCs: ohne Auswahl alle
    boards = (defaults.get("sources") or {}).get("vc_boards", {}).get("boards", [])
    if wanted := set(settings.get("vcs") or []):
        boards = [b for b in boards if b["name"] in wanted]

    # Ort: gewählte Startup-Städte + andere Stadt; ohne beides zählt ganz Deutschland
    centers = home_centers(settings, defaults)
    names = [c["name"] for c in centers]
    city_defs = defaults.get("startup_cities", {})
    aliases = [a for c in city_defs if c in (settings.get("cities") or []) for a in city_defs[c].get("aliases", [])]
    location: dict[str, Any] = {
        "search_places": names,
        "radius_km": int(settings.get("radius_km") or 30),
        "centers": centers,
        "nearby_places": list(dict.fromkeys([n.lower() for n in names] + aliases + list(settings.get("nearby_places") or []))) if centers else [],
        "accept_remote": bool(settings.get("remote", True)),
    }
    return {
        "profile": settings.get("profile") or "",
        "job_search": {t: {"label": type_defs[t]["label"], "short": type_defs[t]["short"],
                           "title_words": type_defs[t]["title_words"]} for t in types},
        "location": location,
        "categories": categories,
        "filters": {"title_required": title_required, "title_exclude": excludes,
                    "drop_uncategorized": not all_categories},
        "sources": {"vc_boards": {"queries": list(dict.fromkeys(queries)), "boards": boards,
                                  "other_cities": bool(settings.get("other_cities", True))}},
    }


def summary(settings: dict[str, Any]) -> list[tuple[str, str]]:
    cats, types = catalog(), job_types()
    labels = [cats[c]["label"] for c in settings.get("categories") or [] if c in cats]
    yes_no = lambda v: "ja" if v else "nein"  # noqa: E731
    places = [c["name"] for c in home_centers(settings)]
    vcs = settings.get("vcs") or []
    return [
        ("Suche", ", ".join(types[t]["label"] for t in settings.get("job_types") or [] if t in types) or "–"),
        ("Städte", f"{', '.join(places)} · {settings.get('radius_km', 30)} km" if places else "keine (ganz Deutschland)"),
        ("Remote-Stellen", yes_no(settings.get("remote", True))),
        ("Andere Städte zeigen", yes_no(settings.get("other_cities", True)) if places else "–"),
        ("Bereiche", ", ".join(labels) or "alle"),
        ("VCs", ", ".join(vcs) if vcs else f"alle ({len(vc_names())})"),
        ("Eigene Stichwörter", ", ".join(settings.get("extra_terms") or []) or "–"),
        ("Ausschließen", ", ".join(settings.get("exclude_terms") or []) or "–"),
        ("Profil", "hinterlegt" if settings.get("profile") else "noch leer"),
    ]


# --- Link zum Formular ---------------------------------------------------------


def repo_slug() -> str | None:
    """'besitzer/repo' aus GitHub Actions, TRACKER_REPO oder dem git-Remote."""
    if slug := os.environ.get("GITHUB_REPOSITORY") or os.environ.get("TRACKER_REPO"):
        return slug
    try:
        url = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else None


def form_url(settings: dict[str, Any] | None, repo: str | None = None) -> str | None:
    repo = repo or repo_slug()
    if not repo:
        return None
    settings = settings or {}
    params = {"template": ISSUE_TEMPLATE, "labels": ISSUE_LABEL,
              "title": "Einstellungen ändern" if settings else "Tracker einrichten"}
    if settings.get("profile"):
        params[FORM_IDS["profile"]] = str(settings["profile"])[:3000]  # URL-Länge begrenzen
    if settings.get("place"):
        params[FORM_IDS["place"]] = settings["place"]
    for key in ("extra_terms", "exclude_terms"):
        if settings.get(key):
            params[FORM_IDS[key]] = "\n".join(settings[key])
    return f"https://github.com/{repo}/issues/new?{urlencode(params)}"


# --- Formular auslesen ---------------------------------------------------------


def parse_issue(body: str) -> dict[str, Any]:
    """Issue-Formular (Markdown mit ### Überschriften) → nur die geänderten Felder."""
    sections: dict[str, str] = {}
    current = None
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        if line.startswith("### "):
            current = line[4:].strip()
            sections[current] = ""
        elif current is not None:
            sections[current] += line + "\n"
    by_label = {label: key for key, label in FIELDS.items()}
    changes: dict[str, Any] = {}
    for label, raw in sections.items():
        key = by_label.get(label)
        value = raw.strip()
        if key is None or not value or value == NO_RESPONSE or value == UNCHANGED:
            continue
        if key in ("job_types", "cities", "categories", "vcs"):
            ticked = [m.strip() for m in re.findall(r"- \[[xX]\] (.+)", value)]
            if not ticked:
                continue  # nichts angekreuzt = unverändert
            if key in ("job_types", "cities"):
                defs = job_types() if key == "job_types" else startup_cities()
                label_to_key = {t["label"]: k for k, t in defs.items()}
                changes[key] = [] if NO_CITY in ticked else [label_to_key[m] for m in ticked if m in label_to_key]
            elif key == "categories":
                label_to_key = {c["label"]: k for k, c in catalog().items()}
                changes[key] = [] if ALL_CATEGORIES in ticked else [label_to_key[m] for m in ticked if m in label_to_key]
            else:
                names = vc_names()
                changes[key] = [] if ALL_VCS in ticked else [m for m in ticked if m in names]
        elif key in ("extra_terms", "exclude_terms"):
            changes[key] = [] if value == CLEAR else [t.strip(" -•,") for t in re.split(r"[\n,;]", value) if t.strip(" -•,")]
        elif key == "radius_km":
            changes[key] = int(re.sub(r"\D", "", value))
        elif key in ("remote", "other_cities"):
            changes[key] = value.lower().startswith("ja")
        elif key in ("profile", "place"):
            changes[key] = "" if value == CLEAR else value
        else:
            changes[key] = value
    return changes


# --- Andere Stadt → Koordinaten (OpenStreetMap) ---------------------------------


def _session():
    from .sources.base import make_session  # erst hier: vermeidet Zyklus beim Import
    return make_session()


def geocode(place: str) -> tuple[float, float, str]:
    resp = _session().get("https://nominatim.openstreetmap.org/search", timeout=20, params={
        "q": place, "format": "json", "limit": 1, "countrycodes": "de,at,ch,nl,be,lu,fr,dk,pl,cz"})
    resp.raise_for_status()
    hits = resp.json()
    if not hits:
        raise SettingsError(f"Den Ort „{place}“ habe ich nicht gefunden. Bitte genauer schreiben, z. B. „Köln“ oder „Freiburg im Breisgau“.")
    return float(hits[0]["lat"]), float(hits[0]["lon"]), hits[0].get("display_name", place)


def apply_changes(current: dict[str, Any] | None, changes: dict[str, Any],
                  geocoder: Callable[[str], tuple[float, float, str]] = geocode) -> dict[str, Any]:
    new = {"job_types": [], "profile": "", "cities": [], "place": "", "radius_km": 30, "remote": True,
           "other_cities": True, "categories": [], "vcs": [], "extra_terms": [], "exclude_terms": [], **(current or {})}
    place_changed = "place" in changes and changes["place"] != new.get("place")
    new.update(changes)
    new.pop("nearby_places", None)  # stammt aus älteren Versionen
    if not new["job_types"]:
        raise SettingsError("Bitte ankreuzen, ob du Praktika, Werkstudentenstellen oder beides suchst.")
    if not new["place"]:
        new.pop("lat", None)
        new.pop("lon", None)
    elif place_changed or "lat" not in new:
        new["lat"], new["lon"], _ = geocoder(new["place"])
    order = ["job_types", "profile", "cities", "place", "radius_km", "remote", "other_cities", "categories", "vcs",
             "extra_terms", "exclude_terms", "lat", "lon"]
    return {k: new[k] for k in order if k in new}


# --- CLI für den Settings-Workflow ---------------------------------------------


def _cli_apply(args: argparse.Namespace) -> int:
    from . import mailer

    body = os.environ.get(args.body_env, "")
    current = load_settings()
    first = current is None
    try:
        changes = parse_issue(body)
        settings = apply_changes(current, changes)
    except SettingsError as exc:
        message, ok = str(exc), False
    except Exception as exc:  # z. B. OpenStreetMap nicht erreichbar – dem Nutzer verständlich melden
        log.exception("Einstellungen konnten nicht übernommen werden")
        message, ok = f"Technischer Fehler beim Übernehmen ({type(exc).__name__}). Bitte später nochmal absenden.", False
    else:
        save_settings(settings)
        message, ok = ("Eingerichtet! Deine ersten Stellen kommen gleich in einer eigenen Mail." if first
                       else "Gespeichert. Die nächste tägliche Mail nutzt die neuen Einstellungen."), True
    shown = settings if ok else (current or {})
    if args.comment_file:
        lines = [("✅ " if ok else "⚠️ ") + message, ""] + [f"- **{k}:** {v}" for k, v in summary(shown)]
        Path(args.comment_file).write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as f:
            f.write(f"ok={'true' if ok else 'false'}\nfirst_setup={'true' if ok and first else 'false'}\n")
    if args.mail:
        try:
            mailer.send(mailer.render_notice(
                subject=("✅ Tracker eingerichtet" if first else "✅ Einstellungen gespeichert") if ok else "⚠️ Einstellungen nicht gespeichert",
                title="Alles klar!" if ok else "Da hat etwas nicht gepasst",
                paragraphs=[message] if ok else [message, "Deine bisherigen Einstellungen gelten weiter."],
                settings=shown or None, button=("Einstellungen ändern" if ok else "Nochmal versuchen", form_url(shown or None)),
            ))
        except Exception:
            log.exception("Bestätigungsmail fehlgeschlagen")
    print(message)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="jobtracker.settings")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply", help="Formular aus einem Issue übernehmen")
    a.add_argument("--body-env", default="ISSUE_BODY", help="Umgebungsvariable mit dem Issue-Text")
    a.add_argument("--comment-file", help="Antwort für das Issue hierhin schreiben")
    a.add_argument("--github-output", help="GITHUB_OUTPUT-Datei für ok/first_setup")
    a.add_argument("--mail", action="store_true", help="Bestätigungsmail schicken")
    sub.add_parser("url", help="Link zum Einstellungsformular ausgeben")
    args = p.parse_args(argv)
    if args.cmd == "url":
        print(form_url(load_settings()) or "Kein GitHub-Repo gefunden (TRACKER_REPO=besitzer/repo setzen)")
        return 0
    return _cli_apply(args)


if __name__ == "__main__":
    sys.exit(main())
