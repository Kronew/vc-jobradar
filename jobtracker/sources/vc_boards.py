"""Portfolio-Jobbörsen von VCs über die öffentliche Suche von Getro (ohne Key).

Viele VCs (HV Capital, Earlybird, Cherry, Speedinvest …) betreiben eine Jobseite mit allen
offenen Stellen ihrer Portfolio-Startups. Die Seite fragt selbst diesen Endpunkt ab:
- POST https://api.getro.com/api/v2/collections/{network_id}/search/jobs
  JSON {"hitsPerPage", "page", "filters", "query"} – max. 20 Treffer pro Seite
Die network_id steht im Seitenquelltext der Jobseite (__NEXT_DATA__ → props.pageProps.network.id).
Gesucht wird nur nach Studenten-Begriffen; den Bereich (Sales, VC, Marketing …) prüft der Filter.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from ..models import Job, SourceError
from .base import Source, parse_datetime

log = logging.getLogger(__name__)

API = "https://api.getro.com/api/v2/collections/{id}/search/jobs"
PAGE_SIZE = 20  # mehr liefert Getro nicht, auch wenn man mehr anfragt
DEFAULT_QUERIES = ["werkstudent", "working student"]
POINT = re.compile(r"POINT \((-?[\d.]+) (-?[\d.]+)\)")


class VcBoardsSource(Source):
    name = "vc_boards"
    label = "VC-Portfolio"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.delay = min(self.delay, 0.3)
        self.partial_errors: list[SourceError] = []

    def fetch(self) -> list[Job]:
        days = int(self.cfg.get("max_days_old") or self.max_days_old)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        # Startups stehen oft auf mehreren Boards – das führt dedupe() zusammen ("auch auf: …")
        jobs: list[Job] = []
        for board in self.cfg.get("boards") or []:
            try:
                found = self._board(board, cutoff)
                log.debug("%s (Getro %s): %d Stellen", board.get("name"), board.get("network_id"), len(found))
                jobs.extend(found)
            except Exception as exc:  # ein kaputtes Board darf die anderen nicht abbrechen
                log.warning("VC-Board %s fehlgeschlagen: %s", board.get("name"), exc)
                self.partial_errors.append(SourceError(self.label, f"{board.get('name')}: {exc}"))
        return jobs

    def _board(self, board: dict[str, Any], cutoff: datetime) -> list[Job]:
        jobs: dict[str, Job] = {}
        max_pages = int(self.cfg.get("max_pages", 5))
        for query in self.cfg.get("queries") or DEFAULT_QUERIES:
            for page in range(max_pages):
                data = self.request("POST", API.format(id=board["network_id"]),
                                    json={"hitsPerPage": PAGE_SIZE, "page": page, "filters": "", "query": query},
                                    headers={"Accept": "application/json"}).json()
                results = data.get("results") or {}
                hits = results.get("jobs") or []
                for item in hits:
                    job = self._to_job(item, board)
                    if job.posted_at is None or job.posted_at >= cutoff:
                        jobs.setdefault(job.url, job)
                if (page + 1) * PAGE_SIZE >= int(results.get("count") or 0) or not hits:
                    break
        return list(jobs.values())

    def _to_job(self, item: dict[str, Any], board: dict[str, Any]) -> Job:
        lat = lon = None
        for detail in item.get("location_details") or []:
            if m := POINT.search(str(detail.get("point") or "")):
                lon, lat = float(m.group(1)), float(m.group(2))  # WKT: erst Länge, dann Breite
                break
        work_mode = item.get("work_mode")
        org = item.get("organization") or {}
        return Job(
            id=f"getro:{item.get('id')}",
            title=str(item.get("title") or "").strip(),
            company=str(org.get("name") or ""),
            location=", ".join(item.get("locations") or []),
            remote=True if work_mode == "remote" else None,
            url=str(item.get("url") or ""),
            source=self.label,
            posted_at=parse_datetime(item.get("created_at")),
            lat=lat,
            lon=lon,
            homeoffice_possible=work_mode == "hybrid",
            elsewhere_ok=bool(self.cfg.get("other_cities", False)),
            investors=[board.get("name", "")],
        )
