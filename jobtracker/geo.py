"""Entfernungsberechnung und Ortsabgleich ohne externe Geocoding-API."""

from __future__ import annotations

import math

from .text import contains_any


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def within_radius(lat: float, lon: float, centers: list[dict], radius_km: float) -> bool:
    return any(haversine_km(lat, lon, c["lat"], c["lon"]) <= radius_km for c in centers)


def matches_nearby_place(location: str, places: list[str]) -> str | None:
    # "$" erzwingt Wortende, damit z. B. "Genk" nicht "Genkingen" trifft
    return contains_any(location, [p if p.endswith("$") else p + "$" for p in places])
