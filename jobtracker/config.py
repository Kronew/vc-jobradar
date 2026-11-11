"""Baut die Config: defaults.yaml ← settings.yaml (Formular) ← config.yaml (optional, für Profis).

Secrets kommen aus Umgebungsvariablen. Ohne settings.yaml und config.yaml ist der Tracker noch
nicht eingerichtet – dann gibt load_config() None zurück und es geht eine Willkommens-Mail raus.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_SECTIONS = ("search", "location", "filters", "categories", "sources")


@dataclass
class Config:
    raw: dict[str, Any]
    path: Path | None = None
    settings: dict[str, Any] | None = None  # Formular-Einstellungen, falls genutzt

    def section(self, name: str) -> dict[str, Any]:
        return self.raw.get(name) or {}

    @property
    def profile(self) -> str:
        return self.raw.get("profile", "")

    @property
    def search(self) -> dict[str, Any]:
        return self.section("search")

    @property
    def location(self) -> dict[str, Any]:
        return self.section("location")

    @property
    def filters(self) -> dict[str, Any]:
        return self.section("filters")

    @property
    def categories(self) -> dict[str, dict[str, Any]]:
        return self.section("categories")

    @property
    def scoring(self) -> dict[str, Any]:
        return self.section("scoring")

    @property
    def storage(self) -> dict[str, Any]:
        return self.section("storage")

    @property
    def mail(self) -> dict[str, Any]:
        return self.section("mail")

    @property
    def http(self) -> dict[str, Any]:
        return self.section("http")

    @property
    def sources(self) -> dict[str, dict[str, Any]]:
        return self.section("sources")


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Abschnitte werden zusammengeführt, Listen und Einzelwerte ersetzt."""
    out = dict(base)
    for key, value in override.items():
        out[key] = deep_merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def load_config(path: str | Path | None = None, settings_path: Path | None = None) -> Config | None:
    from .settings import SETTINGS_PATH, build_raw, load_defaults, load_settings

    defaults = load_defaults()
    settings = load_settings(settings_path or SETTINGS_PATH)
    if path is None and (ROOT / "config.yaml").exists():
        path = ROOT / "config.yaml"
    if settings is None and path is None:
        return None
    raw = deep_merge(defaults, build_raw(settings, defaults)) if settings is not None else defaults
    if path is not None:
        path = Path(path)
        with path.open(encoding="utf-8") as f:
            raw = deep_merge(raw, yaml.safe_load(f) or {})
    raw.pop("category_catalog", None)
    missing = [s for s in REQUIRED_SECTIONS if not raw.get(s)]
    if missing:
        raise ValueError(f"{path or 'settings.yaml'}: fehlende Abschnitte in der Config: {', '.join(missing)}")
    return Config(raw=raw, path=path, settings=settings)


def env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None
