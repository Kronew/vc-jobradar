"""Regelbasierte Vorfilterung: Werkstudent-Pflicht, Ausschlüsse, Ort/Remote, Bereich."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field

from .config import Config
from .geo import matches_nearby_place, within_radius
from .models import Job
from .text import contains_any

log = logging.getLogger(__name__)

REMOTE_KEYWORDS = [
    "remote", "100% homeoffice", "100 % homeoffice", "100% home office", "100 % home office",
    "vollständig remote", "komplett remote", "fully remote", "full remote", "remote first",
    "remote-first", "work from home", "ortsunabhängig", "ortsunabhaengig", "home-office$",
    "homeoffice$", "home office$", "mobiles arbeiten",
]


def detect_remote(*texts: str) -> bool:
    """True, wenn Titel/Ort/Beschreibung klar auf Remote hindeuten."""
    return any(contains_any(t, REMOTE_KEYWORDS) for t in texts if t)


@dataclass
class FilterResult:
    kept: list[Job] = field(default_factory=list)
    rejected: Counter[str] = field(default_factory=Counter)


class JobFilter:
    def __init__(self, config: Config) -> None:
        f = config.filters
        loc = config.location
        self.title_required: list[str] = f.get("title_required", [])
        self.title_exclude: list[str] = f.get("title_exclude", [])
        self.staffing: list[str] = f.get("staffing_agencies", []) if f.get("exclude_staffing_agencies", True) else []
        self.accept_homeoffice_possible: bool = bool(f.get("accept_homeoffice_possible", False))
        self.drop_uncategorized: bool = bool(f.get("drop_uncategorized", True))
        self.centers: list[dict] = loc.get("centers", [])
        self.radius_km: float = float(loc.get("radius_km", 40))
        self.nearby_places: list[str] = loc.get("nearby_places", [])
        self.remote_exclude: list[str] = loc.get("remote_exclude_regions", [])
        self.accept_remote: bool = bool(loc.get("accept_remote", True))
        self.other_cities_countries: list[str] = loc.get("other_cities_countries", ["germany", "deutschland"])
        self.categories = config.categories
        self.job_search: dict[str, dict] = config.raw.get("job_search") or {}
        self.title_only_categories = bool(config.raw.get("title_only_categories", False))

    # --- Einzelregeln -------------------------------------------------------

    def check(self, job: Job) -> str | None:
        """Gibt den Ablehnungsgrund zurück, oder None wenn der Job passt."""
        if self.title_required and not contains_any(job.title, self.title_required):
            return "falsche Stellenart (Titel)"
        job.job_types = [t["short"] for t in self.job_search.values() if contains_any(job.title, t["title_words"])]
        if hit := contains_any(job.title, self.title_exclude):
            return f"Ausschluss: {hit}"
        if self.staffing and contains_any(job.company, self.staffing):
            return "Zeitarbeit"
        if not self.location_ok(job):
            if not (job.elsewhere_ok and contains_any(job.location, self.other_cities_countries)):
                return "Ort außerhalb Radius / nicht remote"
            job.elsewhere = True
        job.category = self.categorize(job)
        if job.category is None and self.drop_uncategorized:
            return "kein passender Bereich"
        return None

    def location_ok(self, job: Job) -> bool:
        if job.trust_location:
            return True
        if not self.centers and not self.nearby_places:  # keine Städte gewählt: ganz Deutschland
            if job.remote is None:
                job.remote = detect_remote(job.title, job.location)
            if job.remote:
                return self.accept_remote and not contains_any(job.location or "", self.remote_exclude)
            return contains_any(job.location or "", self.other_cities_countries)
        if job.lat is not None and job.lon is not None and within_radius(job.lat, job.lon, self.centers, self.radius_km):
            return True
        if job.location and matches_nearby_place(job.location, self.nearby_places):
            return True
        if job.remote is None:
            job.remote = detect_remote(job.title, job.location)
        if job.remote:
            # Keine Remote-Stellen, die auf andere Länder beschränkt sind ("Remote – USA")
            return self.accept_remote and not contains_any(job.location or "", self.remote_exclude)
        return job.homeoffice_possible and self.accept_homeoffice_possible

    def categorize(self, job: Job) -> str | None:
        for key, cat in self.categories.items():
            if contains_any(job.title, cat.get("keywords", [])):
                return key
        if not self.title_only_categories and job.description_snippet:
            for key, cat in self.categories.items():
                if contains_any(job.description_snippet, cat.get("keywords", [])):
                    return key
        return None

    # --- Gesamtlauf ---------------------------------------------------------

    def apply(self, jobs: list[Job]) -> FilterResult:
        result = FilterResult()
        for job in jobs:
            reason = self.check(job)
            if reason is None:
                result.kept.append(job)
            else:
                result.rejected[reason.split(":")[0]] += 1
                log.debug("Verworfen (%s): %s – %s", reason, job.title, job.company)
        return result
