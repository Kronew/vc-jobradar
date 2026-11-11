"""Gemeinsames Datenmodell für alle Jobquellen."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    remote: bool | None
    url: str
    source: str
    posted_at: datetime | None
    description_snippet: str = ""

    # Optionale Zusatzinfos, die nicht jede Quelle liefert
    lat: float | None = None
    lon: float | None = None
    homeoffice_possible: bool = False
    trust_location: bool = False  # z. B. Job-Alerts: Ort wurde schon vom Portal gefiltert
    elsewhere_ok: bool = False    # Quelle will Stellen auch außerhalb des Radius (Abschnitt „Andere Städte“)
    investors: list[str] = field(default_factory=list)  # VCs, auf deren Portfolio-Board die Stelle steht
    job_types: list[str] = field(default_factory=list)  # z. B. ["Praktikum"], vom Filter gesetzt

    # Wird von Filter und Scoring befüllt
    category: str | None = None
    score: int | None = None
    reason: str | None = None
    remote_ok: bool | None = None
    hours_ok: bool | None = None
    also_on: list[str] = field(default_factory=list)
    elsewhere: bool = False  # außerhalb des Radius, aber wegen elsewhere_ok behalten

    @property
    def location_label(self) -> str:
        if self.remote:
            return f"Remote ({self.location})" if self.location and "remote" not in self.location.lower() else (self.location or "Remote")
        if self.homeoffice_possible:
            return f"{self.location} · Homeoffice möglich"
        return self.location or "k. A."


@dataclass
class SourceError:
    source: str
    message: str
