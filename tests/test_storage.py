from __future__ import annotations

import json
from datetime import date

from jobtracker.storage import SeenStore, content_hash, dedupe, normalize_url


def test_normalize_url_strips_tracking():
    a = normalize_url("http://www.Example.com/jobs/1/?utm_source=x&gh_src=abc&id=5#apply")
    b = normalize_url("https://example.com/jobs/1?id=5")
    assert a == b


def test_content_hash_ignores_gender_and_legal_form(make_job):
    a = make_job(title="Werkstudent Sales (m/w/d)", company="Acme GmbH")
    b = make_job(title="Werkstudent  Sales (w/m/d)", company="ACME", url="https://other.de/x")
    assert content_hash(a) == content_hash(b)


def test_dedupe_across_sources(make_job):
    a = make_job(source="Bundesagentur", description_snippet="kurz")
    b = make_job(source="Adzuna", url="https://adzuna.de/123", description_snippet="viel längere Beschreibung")
    c = make_job(title="Werkstudent Marketing", url="https://example.com/jobs/2")
    result = dedupe([a, b, c])
    assert len(result) == 2
    assert result[0].also_on == ["Adzuna"]
    assert result[0].description_snippet == "viel längere Beschreibung"


def test_seen_store_roundtrip(tmp_path, make_job):
    path = tmp_path / "seen.json"
    store = SeenStore(path)
    job = make_job()
    assert store.filter_new([job]) == [job]
    store.mark([job], when=date(2026, 10, 28))
    store.save()

    reloaded = SeenStore(path)
    assert reloaded.is_seen(job)
    # dieselbe Stelle auf anderem Portal → über Hash erkannt
    assert reloaded.is_seen(make_job(url="https://stepstone.de/abc", company="Acme SaaS"))
    assert not reloaded.is_seen(make_job(title="Werkstudent Marketing", url="https://example.com/2"))


def test_prune_old_entries(tmp_path, make_job):
    store = SeenStore(tmp_path / "seen.json", retention_days=60)
    store.mark([make_job()], when=date(2026, 8, 1))
    store.mark([make_job(title="Werkstudent Growth", url="https://example.com/new")], when=date(2026, 10, 20))
    removed = store.prune(today=date(2026, 10, 28))
    assert removed == 2  # URL + Hash des alten Jobs
    assert len(store.urls) == 1 and len(store.hashes) == 1


def test_corrupt_file_starts_empty(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text("{kaputt", encoding="utf-8")
    store = SeenStore(path)
    assert store.urls == {} and store.last_run is None


def test_save_writes_last_run(tmp_path):
    path = tmp_path / "seen.json"
    SeenStore(path).save()
    assert json.loads(path.read_text())["last_run"] == date.today().isoformat()


def test_dedupe_company_name_variants(make_job):
    a = make_job(company="Robert Bosch GmbH", source="Bundesagentur")
    b = make_job(company="Bosch", source="Karriereseite", url="https://jobs.smartrecruiters.com/x/1")
    c = make_job(company="Bosch Rexroth AG", title="Werkstudent Marketing", url="https://e.com/3")
    assert dedupe([a, b, c]) == [a, c]
    assert a.also_on == ["Karriereseite"]


def test_dedupe_merges_vc_investors(make_job):
    a = make_job(id="getro:1", source="VC-Portfolio", investors=["HV Capital"])
    b = make_job(id="getro:2", source="VC-Portfolio", investors=["Earlybird"])
    c = make_job(id="ba:1", source="Bundesagentur für Arbeit")
    [job] = dedupe([a, b, c])
    assert job.investors == ["HV Capital", "Earlybird"]
    assert job.also_on == ["Bundesagentur für Arbeit"]
