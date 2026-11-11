"""Einstellungsformular: Auslesen, Übernehmen, Config bauen, Link erzeugen (ohne Netzwerk)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml

from jobtracker import mailer
from jobtracker.config import load_config
from jobtracker.filters import JobFilter
from jobtracker.settings import (ALL_CATEGORIES, ALL_VCS, FIELDS, FORM_IDS, NO_CITY, SettingsError, apply_changes,
                                 build_raw, catalog, form_url, job_types, parse_issue, save_settings, startup_cities,
                                 vc_names)

ROOT = Path(__file__).resolve().parent.parent

# So schickt GitHub ein ausgefülltes Issue-Formular
ISSUE_BODY = """### Was suchst du?

- [X] Werkstudentenstellen
- [X] Praktika

### Über dich

Master-Student, Praktikum ab März.

### Städte

- [ ] Keine (ganz Deutschland)
- [X] Berlin
- [X] München
- [ ] Hamburg

### Andere Stadt

Freiburg im Breisgau

### Pendelradius

40 km

### Remote-Stellen

unverändert

### Stellen aus ganz Deutschland

Nein

### Bereiche

- [X] Sales / Business Development
- [ ] VC / Startup / Strategy
- [X] Finance / Controlling

### VCs

- [ ] Alle VCs
- [X] HV Capital
- [X] HTGF

### Eigene Stichwörter

_No response_

### Ausschließen

Senior
Teamleitung
"""


def fake_geocoder(place):
    return 47.99, 7.84, place


def test_parse_issue_only_changed_fields():
    changes = parse_issue(ISSUE_BODY)
    assert changes == {
        "job_types": ["werkstudent", "praktikum"],
        "profile": "Master-Student, Praktikum ab März.",
        "cities": ["berlin", "muenchen"],
        "place": "Freiburg im Breisgau",
        "radius_km": 40,
        "other_cities": False,
        "categories": ["sales_bd", "finance"],
        "vcs": ["HV Capital", "HTGF"],
        "exclude_terms": ["Senior", "Teamleitung"],
    }


def test_parse_issue_clear_all_and_unchanged():
    body = (f"### Bereiche\n\n- [X] {ALL_CATEGORIES}\n- [ ] Sales / Business Development\n\n"
            f"### VCs\n\n- [ ] {ALL_VCS}\n- [ ] HTGF\n\n"
            "### Eigene Stichwörter\n\n-\n\n### Andere Stadt\n\n-\n\n"
            "### Städte\n\n- [X] Keine (ganz Deutschland)\n- [ ] Berlin\n")
    assert parse_issue(body) == {"categories": [], "extra_terms": [], "place": "", "cities": []}


def test_apply_changes_geocodes_only_when_needed(settings):
    calls = []

    def geocoder(place):
        calls.append(place)
        return fake_geocoder(place)

    new = apply_changes(settings, {"radius_km": 50}, geocoder=geocoder)
    assert calls == [] and new["lat"] == settings["lat"] and "nearby_places" not in new
    new = apply_changes(settings, {"place": "Freiburg"}, geocoder=geocoder)
    assert calls == ["Freiburg"] and new["lat"] == 47.99


def test_first_setup_needs_only_job_type():
    with pytest.raises(SettingsError, match="Praktika"):
        apply_changes(None, {"place": "Köln"}, geocoder=fake_geocoder)
    new = apply_changes(None, {"job_types": ["praktikum"]}, geocoder=fake_geocoder)
    assert new["place"] == "" and "lat" not in new and new["categories"] == [] and new["vcs"] == []


def test_removing_place_drops_coordinates(settings):
    new = apply_changes(settings, {"place": ""}, geocoder=fake_geocoder)
    assert "lat" not in new and "lon" not in new


def test_startup_cities_without_geocoding():
    calls = []

    def geocoder(place):
        calls.append(place)
        return fake_geocoder(place)

    new = apply_changes(None, {"job_types": ["praktikum"], "cities": ["berlin", "koeln"]}, geocoder=geocoder)
    assert calls == []
    raw = build_raw(new)
    assert [c["name"] for c in raw["location"]["centers"]] == ["Berlin", "Köln"]
    assert {"berlin", "köln", "cologne", "potsdam"} <= set(raw["location"]["nearby_places"])
    new = apply_changes(new, {"place": "Leipzig"}, geocoder=geocoder)
    assert calls == ["Leipzig"] and [c["name"] for c in build_raw(new)["location"]["centers"]] == ["Berlin", "Köln", "Leipzig"]


def test_city_jobs_pass_others_go_to_other_cities(settings, make_job):
    from jobtracker.config import Config, deep_merge
    from jobtracker.settings import load_defaults
    settings.update(cities=["berlin", "muenchen"], place="", nearby_places=[])
    defaults = load_defaults()
    jf = JobFilter(Config(raw=deep_merge(defaults, build_raw(settings, defaults)), settings=settings))
    munich = make_job(location="Munich, Germany", lat=48.14, lon=11.58)
    potsdam = make_job(location="Potsdam, Germany")
    hamburg = make_job(location="Hamburg, Germany", lat=53.55, lon=9.99, elsewhere_ok=True)
    assert jf.check(munich) is None and not munich.elsewhere
    assert jf.check(potsdam) is None and not potsdam.elsewhere
    assert jf.check(hamburg) is None and hamburg.elsewhere


def test_build_raw_job_types_categories_vcs(settings):
    settings.update(job_types=["praktikum"], categories=["marketing_growth", "sales_bd"],
                    extra_terms=["Nachhaltigkeit"], exclude_terms=["Senior"], vcs=["HTGF", "Earlybird"],
                    remote=False, other_cities=False)
    raw = build_raw(settings)
    assert raw["sources"]["vc_boards"]["queries"] == ["praktikum", "praktikant", "internship", "intern"]
    assert [b["name"] for b in raw["sources"]["vc_boards"]["boards"]] == ["HTGF", "Earlybird"]
    assert "praktikum" in raw["filters"]["title_required"] and "werkstudent" not in raw["filters"]["title_required"]
    # Nur Praktika: Vollzeit ist erlaubt, Werkstudenten-Ausschlüsse greifen nicht
    assert "vollzeit" not in raw["filters"]["title_exclude"] and "senior" in raw["filters"]["title_exclude"]
    assert list(raw["categories"]) == ["sales_bd", "marketing_growth", "eigene"]
    assert raw["categories"]["eigene"]["keywords"] == ["nachhaltigkeit"]
    assert raw["filters"]["drop_uncategorized"] is True
    assert raw["location"]["accept_remote"] is False and raw["location"]["nearby_places"][0] == "köln"
    assert raw["sources"]["vc_boards"]["other_cities"] is False
    assert raw["job_search"]["praktikum"]["short"] == "Praktikum"


def test_build_raw_defaults_all_categories_and_vcs(settings):
    settings.update(categories=[], extra_terms=[], vcs=[], place="")
    raw = build_raw(settings)
    assert len(raw["categories"]) == len(catalog()) and raw["filters"]["drop_uncategorized"] is False
    assert len(raw["sources"]["vc_boards"]["boards"]) == len(vc_names())
    assert raw["location"]["centers"] == [] and raw["location"]["nearby_places"] == []
    assert "vollzeit" in raw["filters"]["title_exclude"]  # nur Werkstudent gesucht


def test_remote_can_be_switched_off(config, make_job):
    assert JobFilter(config).check(make_job(location="München", remote=True)) is None
    config.raw["location"]["accept_remote"] = False
    assert JobFilter(config).check(make_job(location="München", remote=True)) is not None


def test_form_url_prefills_text_fields(settings):
    settings["extra_terms"] = ["Nachhaltigkeit", "Einkauf"]
    url = form_url(settings, repo="anna/tracker")
    parts = urlsplit(url)
    assert parts.path == "/anna/tracker/issues/new"
    q = {k: v[0] for k, v in parse_qs(parts.query).items()}
    assert q["template"] == "einstellungen.yml" and q["ort"] == "Köln"
    assert q["stichwoerter"] == "Nachhaltigkeit\nEinkauf"
    assert form_url(None, repo="anna/tracker").count("ort=") == 0


def test_issue_template_matches_parser():
    template = yaml.safe_load((ROOT / ".github/ISSUE_TEMPLATE/einstellungen.yml").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in template["body"] if f["type"] != "markdown"}
    assert {f["attributes"]["label"] for f in fields.values()} == set(FIELDS.values())
    for key, form_id in FORM_IDS.items():
        assert fields[form_id]["attributes"]["label"] == FIELDS[key]

    def options(field_id):
        return [o["label"] for o in fields[field_id]["attributes"]["options"]]

    assert options("art") == [t["label"] for t in job_types().values()]
    assert options("staedte") == [NO_CITY] + [c["label"] for c in startup_cities().values()]
    assert options("bereiche") == [ALL_CATEGORIES] + [c["label"] for c in catalog().values()]
    assert options("vcs") == [ALL_VCS] + vc_names()


def test_load_config_layers(tmp_path, settings, monkeypatch):
    monkeypatch.setattr("jobtracker.config.ROOT", tmp_path)  # keine echte config.yaml im Repo-Ordner
    settings_file = tmp_path / "settings.yaml"
    assert load_config(settings_path=settings_file) is None  # noch nicht eingerichtet
    save_settings(settings, settings_file)
    cfg = load_config(settings_path=settings_file)
    assert cfg.settings["place"] == "Köln" and "sales_bd" in cfg.categories
    assert cfg.sources["vc_boards"]["enabled"] is True and "category_catalog" not in cfg.raw
    override = tmp_path / "config.yaml"
    override.write_text("location:\n  radius_km: 99\nsources:\n  vc_boards:\n    max_days_old: 30\n", encoding="utf-8")
    cfg = load_config(override, settings_path=settings_file)
    assert cfg.location["radius_km"] == 99 and cfg.location["search_places"] == ["Köln"]
    assert cfg.sources["vc_boards"]["max_days_old"] == 30 and cfg.sources["vc_boards"]["queries"] == ["werkstudent", "working student"]


def test_job_mail_has_settings_box_and_type_badge(config, make_job, monkeypatch):
    monkeypatch.setenv("TRACKER_REPO", "anna/tracker")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    mail = mailer.render([make_job(category="sales_bd", job_types=["Praktikum"])], config, errors=[])
    assert "⚙️ Deine Einstellungen" in mail.html and "github.com/anna/tracker/issues/new" in mail.html
    assert "Köln · 30 km" in mail.html and "Einstellungen ändern: https://github.com/anna/tracker" in mail.text
    assert ">Praktikum</span>" in mail.html and "[Praktikum] " in mail.text


def test_welcome_mail():
    mail = mailer.render_welcome("https://github.com/anna/tracker/issues/new?template=einstellungen.yml")
    assert "Jetzt einrichten" in mail.html and "einstellungen.yml" in mail.html
    assert "Willkommen" in mail.subject and "Praktika" in mail.text


def test_vc_names_are_strings():
    assert all(isinstance(n, str) for n in vc_names()) and "2150" in vc_names()


def test_days_overrides_vc_boards_window(config, monkeypatch):
    from jobtracker import main as main_mod
    seen = {}
    monkeypatch.setattr(main_mod, "load_config", lambda path: config)
    monkeypatch.setattr(main_mod, "fetch_all", lambda cfg, only: (seen.setdefault("days", cfg.sources["vc_boards"]["max_days_old"]), [])[1:] + ([], {}))
    main_mod.run(main_mod.parse_args(["--dry-run", "--days", "14", "--no-score"]))
    assert seen["days"] == 14
