"""Basisklasse und gemeinsamer HTTP-Client für alle Jobquellen."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, ClassVar

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import Config, env
from ..models import Job

log = logging.getLogger(__name__)

USER_AGENT = "vc-jobradar/1.0 (+https://github.com/Kronew/vc-jobradar; private job alert)"


class SourceSkipped(Exception):
    """Quelle bewusst übersprungen (z. B. Key fehlt) – kein Fehler für die Mail."""


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET", "POST"), respect_retry_after_header=True)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = USER_AGENT
    return session


class Source(ABC):
    name: ClassVar[str]
    label: ClassVar[str]
    required_env: ClassVar[tuple[str, ...]] = ()

    def __init__(self, config: Config, session: requests.Session | None = None) -> None:
        self.config = config
        self.cfg: dict[str, Any] = config.sources.get(self.name, {}) or {}
        self.session = session or make_session()
        self.timeout = float(config.http.get("timeout", 20))
        self.delay = float(config.http.get("delay_seconds", 1.0))
        self._last_request = 0.0

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("enabled", False))

    @property
    def terms(self) -> list[str]:
        return list(self.config.search.get("terms", []))

    @property
    def max_days_old(self) -> int:
        return int(self.config.search.get("max_days_old", 2))

    @property
    def search_places(self) -> list[str]:
        """Orte für die Umkreissuche (`search_places` oder einzelnes `search_place`)."""
        loc = self.config.location
        return list(loc.get("search_places") or [loc.get("search_place", "Köln")])

    @property
    def search_radius_km(self) -> int:
        loc = self.config.location
        return int(loc.get("search_radius_km") or loc.get("radius_km", 40))

    def check_env(self) -> None:
        missing = [n for n in self.required_env if not env(n)]
        if missing:
            raise SourceSkipped(f"fehlende Umgebungsvariablen: {', '.join(missing)}")

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        kwargs.setdefault("timeout", self.timeout)
        try:
            resp = self.session.request(method, url, **kwargs)
        finally:
            self._last_request = time.monotonic()
        resp.raise_for_status()
        return resp

    @abstractmethod
    def fetch(self) -> list[Job]:
        ...


def parse_datetime(value: Any) -> datetime | None:
    """Akzeptiert ISO-Strings, Datumsstrings und Unix-Timestamps (s oder ms)."""
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            ts = value / 1000 if value > 1e12 else value
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OSError, OverflowError):
        log.debug("Unbekanntes Datumsformat: %r", value)
        return None
