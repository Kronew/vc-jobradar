from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from jobtracker.config import Config, deep_merge
from jobtracker.models import Job
from jobtracker.settings import build_raw, load_defaults

ROOT = Path(__file__).resolve().parent.parent

# So würde settings.yaml nach dem Einrichten über das Formular aussehen
TEST_SETTINGS = {
    "job_types": ["werkstudent"],
    "profile": "BWL-Studentin, sucht Werkstudentenjob im Vertrieb.",
    "place": "Köln", "radius_km": 30, "remote": True, "other_cities": True,
    "categories": ["sales_bd", "vc_startup", "marketing_growth"], "vcs": [],
    "extra_terms": [], "exclude_terms": [],
    "lat": 50.9375, "lon": 6.9603,
    "nearby_places": ["bonn", "leverkusen", "bergisch gladbach", "cologne", "siegburg"],
}


@pytest.fixture
def settings() -> dict:
    return {k: (list(v) if isinstance(v, list) else v) for k, v in TEST_SETTINGS.items()}


@pytest.fixture
def config(settings) -> Config:
    defaults = load_defaults()
    raw = deep_merge(defaults, build_raw(settings, defaults))
    raw.pop("category_catalog")
    return Config(raw=raw, settings=settings)


@pytest.fixture
def make_job():
    def _make(**overrides) -> Job:
        defaults = dict(
            id="test:1",
            title="Werkstudent Sales (m/w/d)",
            company="Acme SaaS GmbH",
            location="Köln",
            remote=None,
            url="https://example.com/jobs/1",
            source="Test",
            posted_at=datetime(2026, 10, 27, tzinfo=timezone.utc),
            description_snippet="Unterstütze unser Sales-Team im Outbound.",
        )
        defaults.update(overrides)
        return Job(**defaults)

    return _make
