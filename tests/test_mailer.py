from __future__ import annotations

from datetime import date

from jobtracker import mailer
from jobtracker.models import SourceError


def test_render_groups_and_sorting(config, make_job):
    jobs = [
        make_job(id="1", title="Werkstudent Marketing", category="marketing_growth", score=7, url="https://e.com/1"),
        make_job(id="2", title="Werkstudent SDR", category="sales_bd", score=6, reason="Passt gut.", url="https://e.com/2"),
        make_job(id="3", title="Werkstudent Inside Sales", category="sales_bd", score=9, url="https://e.com/3"),
    ]
    mail = mailer.render(jobs, config, errors=[], today=date(2026, 10, 28))

    assert mail.subject == "🎯 VC-Jobradar – 28.10.2026 – 3 neue Stellen"
    # Sales vor Marketing, innerhalb Sales nach Score
    assert mail.html.index("Sales / Business Development") < mail.html.index("Marketing / Growth")
    assert mail.html.index("Werkstudent Inside Sales") < mail.html.index("Werkstudent SDR")
    assert "Jetzt bewerben" in mail.html
    assert 'href="https://e.com/3"' in mail.html
    assert "9/10" in mail.html and "Passt gut." in mail.html
    # Plain-Text-Alternative
    assert "Bewerben: https://e.com/2" in mail.text
    assert "[9/10] Werkstudent Inside Sales" in mail.text


def test_render_escapes_html(config, make_job):
    job = make_job(title="Werkstudent <script>alert(1)</script> Sales", category="sales_bd")
    mail = mailer.render([job], config, errors=[])
    assert "<script>" not in mail.html
    assert "&lt;script&gt;" in mail.html


def test_render_empty_mail(config):
    mail = mailer.render([], config, errors=[], today=date(2026, 10, 28))
    assert "0 neue Stellen" in mail.subject
    assert "Heute keine neuen Treffer" in mail.html
    assert "Heute keine neuen Treffer" in mail.text


def test_render_shows_source_errors(config, make_job):
    mail = mailer.render([make_job(category="sales_bd")], config,
                         errors=[SourceError("Adzuna", "HTTP 503")])
    assert "Adzuna: HTTP 503" in mail.html
    assert "Adzuna: HTTP 503" in mail.text


def test_max_jobs_limit(config, make_job):
    config.raw["mail"]["max_jobs"] = 2
    jobs = [make_job(id=str(i), url=f"https://e.com/{i}", category="sales_bd") for i in range(5)]
    mail = mailer.render(jobs, config, errors=[])
    assert "3 weitere" in mail.html
    assert "5 neue Stellen" in mail.subject


def test_send_requires_env(monkeypatch):
    for name in ("SMTP_USER", "SMTP_APP_PASSWORD", "EMAIL_TO"):
        monkeypatch.delenv(name, raising=False)
    mail = mailer.RenderedMail("s", "<p>x</p>", "x")
    try:
        mailer.send(mail)
    except RuntimeError as exc:
        assert "SMTP_USER" in str(exc)
    else:
        raise AssertionError("RuntimeError erwartet")


def test_subject_singular(config, make_job):
    mail = mailer.render([make_job(category="sales_bd")], config, errors=[], today=date(2026, 10, 31))
    assert mail.subject.endswith("– 1 neue Stelle")


def test_other_cities_last_group(config, make_job):
    jobs = [
        make_job(id="1", title="Werkstudent Sales Berlin", category="sales_bd", score=9, elsewhere=True, url="https://e.com/1"),
        make_job(id="2", title="Werkstudent Marketing Köln", category="marketing_growth", score=6, url="https://e.com/2"),
    ]
    mail = mailer.render(jobs, config, errors=[], today=date(2026, 10, 28))
    assert mail.html.index("Marketing / Growth") < mail.html.index("Andere Städte (1)")
    assert "Sales / Business Development" not in mail.html


def test_investor_badge(config, make_job):
    job = make_job(category="sales_bd", source="VC-Portfolio", investors=["HV Capital", "Earlybird"])
    mail = mailer.render([job], config, errors=[], today=date(2026, 10, 28))
    assert "💼 Portfolio von HV Capital · Earlybird" in mail.html
    assert "Portfolio von HV Capital, Earlybird" in mail.text
