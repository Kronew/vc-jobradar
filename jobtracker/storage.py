"""Duplikaterkennung über normalisierte URL und Hash aus Firma + Titel."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Job
from .text import normalize_company, normalize_title

log = logging.getLogger(__name__)

TRACKING_PARAMS = {
    "ref", "refid", "trackingid", "trk", "src", "source", "gh_src", "lever-source", "lever-origin",
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id", "fbclid",
    "gclid", "mc_cid", "mc_eid", "campaign", "origin", "from", "jobsearch", "position", "pagenum",
    "exp", "se", "sid",
}


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/") or "/"
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
             if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")]
    return urlunsplit(("https", host, path, urlencode(sorted(query)), ""))


def content_hash(job: Job) -> str:
    key = f"{normalize_company(job.company)}|{normalize_title(job.title)}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _same_company(a: str, b: str) -> bool:
    wa, wb = set(normalize_company(a).split()), set(normalize_company(b).split())
    return bool(wa and wb) and (wa <= wb or wb <= wa)


def dedupe(jobs: list[Job]) -> list[Job]:
    """Entfernt Duplikate innerhalb eines Laufs; merkt sich weitere Quellen in `also_on`."""
    by_key: dict[str, Job] = {}
    by_title: dict[str, list[Job]] = {}
    result: list[Job] = []
    for job in jobs:
        keys = (normalize_url(job.url), content_hash(job))
        existing = next((by_key[k] for k in keys if k in by_key), None)
        title_key = normalize_title(job.title)
        if existing is None:
            existing = next((j for j in by_title.get(title_key, []) if _same_company(j.company, job.company)), None)
        if existing is None:
            result.append(job)
            by_title.setdefault(title_key, []).append(job)
            for k in keys:
                by_key[k] = job
            continue
        # VC-Boards stehen in der eigenen Zeile „Portfolio von …“, nicht zusätzlich unter „auch auf“
        existing.investors += [i for i in job.investors if i not in existing.investors]
        if job.source != existing.source and job.source not in existing.also_on and not job.investors:
            existing.also_on.append(job.source)
        # Längere Beschreibung übernehmen, hilft beim Scoring
        if len(job.description_snippet) > len(existing.description_snippet):
            existing.description_snippet = job.description_snippet
        for k in keys:
            by_key.setdefault(k, existing)
    return result


class SeenStore:
    def __init__(self, path: str | Path, retention_days: int = 60) -> None:
        self.path = Path(path)
        self.retention_days = retention_days
        self.urls: dict[str, str] = {}
        self.hashes: dict[str, str] = {}
        self.last_run: str | None = None
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("seen_jobs.json nicht lesbar (%s) – starte leer", exc)
            return
        self.urls = data.get("urls", {})
        self.hashes = data.get("hashes", {})
        self.last_run = data.get("last_run")

    def is_seen(self, job: Job) -> bool:
        return normalize_url(job.url) in self.urls or content_hash(job) in self.hashes

    def filter_new(self, jobs: list[Job]) -> list[Job]:
        return [j for j in jobs if not self.is_seen(j)]

    def mark(self, jobs: list[Job], when: date | None = None) -> None:
        stamp = (when or date.today()).isoformat()
        for job in jobs:
            self.urls.setdefault(normalize_url(job.url), stamp)
            self.hashes.setdefault(content_hash(job), stamp)

    def prune(self, today: date | None = None) -> int:
        cutoff = ((today or date.today()) - timedelta(days=self.retention_days)).isoformat()
        before = len(self.urls) + len(self.hashes)
        self.urls = {k: v for k, v in self.urls.items() if v >= cutoff}
        self.hashes = {k: v for k, v in self.hashes.items() if v >= cutoff}
        return before - len(self.urls) - len(self.hashes)

    def save(self, run_at: datetime | None = None) -> None:
        self.last_run = (run_at or datetime.now()).date().isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "last_run": self.last_run,
            "urls": dict(sorted(self.urls.items())),
            "hashes": dict(sorted(self.hashes.items())),
        }
        self.path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
