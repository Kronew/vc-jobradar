"""Parser-Tests der VC-Boards (Getro) mit Beispiel-Payloads (ohne Netzwerk)."""

from __future__ import annotations

from jobtracker.sources.vc_boards import VcBoardsSource


GETRO_ITEM = {
    "id": 4711, "title": "Werkstudent Sales (m/w/d)", "locations": ["Köln, Germany"],
    "location_details": [{"name": "Köln, Germany", "point": "POINT (6.9603 50.9375)"}],
    "work_mode": "hybrid", "created_at": 1793795265, "url": "https://jobs.ashbyhq.com/acme/1",
    "organization": {"name": "Acme"},
}


def test_vc_boards_mapping(config):
    job = VcBoardsSource(config, session=object())._to_job(GETRO_ITEM, {"name": "HV Capital"})  # type: ignore[arg-type]
    assert (job.lat, job.lon) == (50.9375, 6.9603)
    assert job.company == "Acme" and job.source == "VC-Portfolio" and job.investors == ["HV Capital"]
    assert job.remote is None and job.homeoffice_possible
    assert job.posted_at is not None and job.posted_at.year == 2026
    remote = VcBoardsSource(config, session=object())._to_job(  # type: ignore[arg-type]
        {**GETRO_ITEM, "work_mode": "remote", "location_details": []}, {"name": "X"})
    assert remote.remote is True and remote.lat is None


class _FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class _FakeSession:
    """Liefert 25 Treffer auf zwei Seiten; Board 2 schlägt fehl."""

    def __init__(self):
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((url, kwargs["json"]))
        if "/2/" in url:
            raise RuntimeError("kaputt")
        page = kwargs["json"]["page"]
        jobs = [{**GETRO_ITEM, "id": i, "url": f"https://x/{i}", "created_at": None}
                for i in range(page * 20, min(page * 20 + 20, 25))]
        return _FakeResponse({"results": {"count": 25, "jobs": jobs}})


def test_vc_boards_paging_and_errors(config):
    config.raw["sources"]["vc_boards"] = {"queries": ["werkstudent"], "boards": [
        {"name": "Eins", "network_id": 1}, {"name": "Zwei", "network_id": 2}]}
    session = _FakeSession()
    src = VcBoardsSource(config, session=session)  # type: ignore[arg-type]
    src.delay = 0
    jobs = src.fetch()
    assert len(jobs) == 25
    assert [c[1]["page"] for c in session.calls if "/1/" in c[0]] == [0, 1]
    assert len(src.partial_errors) == 1 and "Zwei" in src.partial_errors[0].message
