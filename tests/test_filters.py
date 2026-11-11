from __future__ import annotations

import pytest

from jobtracker.filters import JobFilter, detect_remote


@pytest.fixture
def jf(config):
    return JobFilter(config)


def test_local_sales_job_passes(jf, make_job):
    job = make_job()
    assert jf.check(job) is None
    assert job.category == "sales_bd"


@pytest.mark.parametrize("title", [
    "Werkstudentin Business Development",
    "Working Student Sales Development (f/m/d)",
    "Werkstudierende:r Growth Marketing",
    "Studentische Aushilfe Vertrieb",
])
def test_student_title_variants_pass(jf, make_job, title):
    assert jf.check(make_job(title=title)) is None


@pytest.mark.parametrize("title,reason", [
    ("Sales Manager (m/w/d)", "falsche Stellenart (Titel)"),
    ("Pflichtpraktikum / Werkstudent Marketing", "Ausschluss: pflichtpraktikum"),
    ("Werkstudent Masterarbeit Vertrieb", "Ausschluss: masterarbeit"),
    ("Werkstudent Promoter Sales", "Ausschluss: promoter"),
    ("Werkstudent Sales Vollzeit", "Ausschluss: vollzeit"),
])
def test_exclusions(jf, make_job, title, reason):
    assert jf.check(make_job(title=title)) == reason


def test_staffing_agency_toggle(config, make_job):
    # Bei VC-Startups standardmäßig aus, per config.yaml einschaltbar
    assert JobFilter(config).check(make_job(company="Randstad Deutschland")) is None
    config.raw["filters"].update(exclude_staffing_agencies=True, staffing_agencies=["randstad"])
    assert JobFilter(config).check(make_job(company="Randstad Deutschland GmbH & Co. KG")) == "Zeitarbeit"


def test_far_away_job_rejected(jf, make_job):
    assert jf.check(make_job(location="München")) == "Ort außerhalb Radius / nicht remote"


def test_coordinates_within_radius(jf, make_job):
    # Siegburg per Koordinaten, Ortsname absichtlich unbekannt
    assert jf.check(make_job(location="Irgendwo", lat=50.7998, lon=7.2075)) is None


def test_coordinates_outside_radius(jf, make_job):
    # Aachen: ~65 km von Köln
    assert jf.check(make_job(location="Unbekannt", lat=50.7753, lon=6.0839)) is not None


@pytest.mark.parametrize("location", ["Cologne, Germany", "Bonn", "Leverkusen, Nordrhein-Westfalen", "Bergisch Gladbach"])
def test_nearby_place_names(jf, make_job, location):
    assert jf.check(make_job(location=location)) is None


def test_place_name_needs_whole_word(jf, make_job):
    assert jf.check(make_job(location="Bonnland")) is not None


def test_remote_germany_passes(jf, make_job):
    assert jf.check(make_job(location="Berlin", remote=True)) is None


def test_remote_detected_from_location(jf, make_job):
    job = make_job(location="Remote, Germany")
    assert jf.check(job) is None
    assert job.remote is True


def test_remote_us_rejected(jf, make_job):
    assert jf.check(make_job(location="Remote - United States", remote=True)) is not None


def test_homeoffice_possible_only_with_flag(config, make_job):
    job = make_job(location="Hamburg", homeoffice_possible=True)
    assert JobFilter(config).check(job) is not None
    config.raw["filters"]["accept_homeoffice_possible"] = True
    assert JobFilter(config).check(job) is None


def test_trust_location_skips_geo_check(jf, make_job):
    assert jf.check(make_job(location="München", trust_location=True)) is None


def test_category_priority_and_description_fallback(jf, make_job):
    assert jf.categorize(make_job(title="Werkstudent Venture Capital")) == "vc_startup"
    assert jf.categorize(make_job(title="Working Student Growth Marketing")) == "marketing_growth"
    job = make_job(title="Werkstudent (m/w/d)", description_snippet="Du unterstützt unser Marketing-Team")
    assert jf.categorize(job) == "marketing_growth"


def test_uncategorized_dropped(jf, make_job):
    job = make_job(title="Werkstudent Elektrotechnik", description_snippet="Schaltpläne prüfen")
    assert jf.check(job) == "kein passender Bereich"


def test_short_keywords_need_whole_word(jf, make_job):
    # "bd$" darf nicht in "BDSG" matchen, "account manag" nicht in "Accounting"
    assert jf.categorize(make_job(title="Werkstudent BDSG Datenschutz", description_snippet="")) is None
    assert jf.categorize(make_job(title="Werkstudent Accounting", description_snippet="")) is None


def test_detect_remote():
    assert detect_remote("Werkstudent Sales (100% Remote)")
    assert detect_remote("", "Home-Office")
    assert not detect_remote("Werkstudent Sales", "Köln")


def test_apply_counts_reasons(jf, make_job):
    result = jf.apply([make_job(), make_job(title="Sales Manager"), make_job(location="Hamburg")])
    assert len(result.kept) == 1
    assert sum(result.rejected.values()) == 2


def test_empty_title_required_accepts_any_title(config, make_job):
    config.raw["filters"]["title_required"] = []
    assert JobFilter(config).check(make_job(title="Junior Sales Manager")) is None


def test_profile_config_is_valid():
    # Jede lokale Profil-Config muss ladbar sein und eigene seen_jobs-Datei haben
    from pathlib import Path
    from jobtracker.config import load_config
    root = Path(__file__).resolve().parent.parent
    paths = {load_config(p).storage.get("path") for p in root.glob("config.*.yaml") if p.name != "config.example.yaml"}
    assert "data/seen_jobs.json" not in paths


def test_other_cities_only_when_source_allows(jf, make_job):
    berlin = dict(title="Werkstudent Sales", location="Berlin, Germany", lat=52.52, lon=13.40)
    assert jf.check(make_job(**berlin)) == "Ort außerhalb Radius / nicht remote"
    job = make_job(**berlin, elsewhere_ok=True)
    assert jf.check(job) is None and job.elsewhere
    # Nur Deutschland, nicht z. B. Amsterdam
    assert jf.check(make_job(title="Werkstudent Sales", location="Amsterdam, Netherlands", elsewhere_ok=True)) is not None


def build(settings, **changes):
    from jobtracker.config import Config, deep_merge
    from jobtracker.settings import build_raw, load_defaults
    settings = {**settings, **changes}
    defaults = load_defaults()
    raw = deep_merge(defaults, build_raw(settings, defaults))
    return JobFilter(Config(raw=raw, settings=settings))


@pytest.mark.parametrize("title,types,expected", [
    ("Praktikum Marketing (m/w/d)", ["praktikum"], ["Praktikum"]),
    ("Intern Business Development", ["praktikum"], ["Praktikum"]),
    ("Internal Communications Manager", ["praktikum"], None),
    ("Werkstudent Sales", ["praktikum"], None),
    ("Intern / Working Student Sales", ["werkstudent", "praktikum"], ["Werkstudent", "Praktikum"]),
])
def test_job_types(settings, make_job, title, types, expected):
    job = make_job(title=title)
    reason = build(settings, job_types=types).check(job)
    assert (reason is None) == (expected is not None)
    if expected:
        assert job.job_types == expected


def test_full_time_internship_only_excluded_for_werkstudent(settings, make_job):
    title = "Praktikum Sales (Vollzeit, 6 Monate)"
    assert build(settings, job_types=["praktikum"]).check(make_job(title=title)) is None
    assert build(settings, job_types=["werkstudent", "praktikum"]).check(make_job(title=title)) is None
    assert build(settings, job_types=["werkstudent"]).check(make_job(title="Werkstudent Sales Vollzeit")) is not None


def test_without_place_all_of_germany(settings, make_job):
    jf = build(settings, place="")
    berlin = make_job(location="Berlin, Germany", lat=52.52, lon=13.40)
    assert jf.check(berlin) is None and not berlin.elsewhere
    assert jf.check(make_job(location="Amsterdam, Netherlands")) is not None
