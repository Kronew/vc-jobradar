"""HTML-/Text-Mail bauen und über Gmail SMTP versenden."""

from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Config, env
from .models import Job, SourceError
from .settings import form_url, summary

log = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"
APP_NAME = "VC-Jobradar"
OTHER_CATEGORY = ("other", "Sonstige")
ELSEWHERE_GROUP = ("elsewhere", "Andere Städte")


@dataclass
class Group:
    key: str
    label: str
    jobs: list[Job]


@dataclass
class RenderedMail:
    subject: str
    html: str
    text: str


def _score_color(score: int) -> str:
    if score >= 8:
        return "#15803d"
    if score >= 6:
        return "#ca8a04"
    return "#6b7280"


def _sort_key(job: Job) -> tuple:
    # Andere Städte zuletzt, damit sie beim Mail-Limit nicht die passenden Stellen verdrängen
    return (job.elsewhere, -(job.score or 0), -(job.posted_at.timestamp() if job.posted_at else 0))


def group_jobs(jobs: list[Job], categories: dict[str, dict]) -> list[Group]:
    groups = [Group(key, cat.get("label", key), []) for key, cat in categories.items()]
    other = Group(*OTHER_CATEGORY, [])
    elsewhere = Group(*ELSEWHERE_GROUP, [])
    index = {g.key: g for g in groups}
    for job in jobs:
        (elsewhere if job.elsewhere else index.get(job.category or "", other)).jobs.append(job)
    for g in [*groups, other, elsewhere]:
        g.jobs.sort(key=_sort_key)
    return [g for g in [*groups, other, elsewhere] if g.jobs]


def render(jobs: list[Job], config: Config, errors: list[SourceError], stats: str = "",
           today: date | None = None) -> RenderedMail:
    mail_cfg = config.mail
    today = today or date.today()
    max_jobs = int(mail_cfg.get("max_jobs", 60))
    shown = sorted(jobs, key=_sort_key)[:max_jobs]
    truncated = len(jobs) - len(shown)
    groups = group_jobs(shown, config.categories)
    date_str = today.strftime("%d.%m.%Y")
    count = "1 neue Stelle" if len(jobs) == 1 else f"{len(jobs)} neue Stellen"
    subject = mail_cfg.get("subject", f"🎯 {APP_NAME} – {{date}} – {{count}}").format(
        date=date_str, n=len(jobs), count=count)

    jinja = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape(["html", "j2"]))
    html = jinja.get_template("email.html.j2").render(
        app_name=APP_NAME, subject=subject, date=date_str, total=len(jobs), groups=groups, errors=errors,
        truncated=truncated, stats=stats, scored=any(j.score is not None for j in jobs),
        score_color=_score_color, settings_url=form_url(config.settings) if config.settings is not None else None,
        settings_summary=summary(config.settings) if config.settings else [],
    )
    text = _render_text(groups, len(jobs), date_str, errors, truncated)
    if config.settings is not None and (url := form_url(config.settings)):
        text += f"\nEinstellungen ändern: {url}\n"
    return RenderedMail(subject=subject, html=html, text=text)


def render_notice(subject: str, title: str, paragraphs: list[str], settings: dict | None = None,
                  button: tuple[str, str | None] | None = None) -> RenderedMail:
    """Kurze Mail ohne Stellen: Willkommen, Bestätigung, Fehler im Formular."""
    label, url = button if button else ("", None)
    jinja = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape(["html", "j2"]))
    rows = summary(settings) if settings else []
    html = jinja.get_template("notice.html.j2").render(
        app_name=APP_NAME, subject=subject, title=title, paragraphs=paragraphs, settings_summary=rows, button_label=label, button_url=url)
    text = "\n\n".join([title, *paragraphs]) + "\n"
    if rows:
        text += "\n" + "\n".join(f"{k}: {v}" for k, v in rows) + "\n"
    if url:
        text += f"\n{label}: {url}\n"
    return RenderedMail(subject=subject, html=html, text=text)


def render_welcome(repo_settings_url: str | None) -> RenderedMail:
    paragraphs = [
        f"Schön, dass du {APP_NAME} nutzt! Ab jetzt bekommst du jeden Morgen neue Praktika und "
        "Werkstudentenstellen aus den Portfolio-Startups von 25 VCs – HV Capital, HTGF, Earlybird, Cherry und vielen mehr.",
        "Sag mir vorher kurz, was du suchst: Praktikum, Werkstudentenstelle oder beides, in welchen Städten "
        "(Berlin, München, Hamburg, Köln, Frankfurt oder eine andere), welche Bereiche dich interessieren "
        "und ein paar Sätze über dich.",
        "Der Button öffnet ein kurzes Formular in deinem GitHub-Repo (du musst dort eingeloggt sein). "
        "Nach dem Absenden dauert es etwa eine Minute, dann kommt die Bestätigung und direkt danach deine erste Jobmail.",
        "Solange nichts eingerichtet ist, kommt diese Erinnerung einmal am Tag.",
    ]
    if not repo_settings_url:
        paragraphs.append("Hinweis: Ich konnte das GitHub-Repo nicht ermitteln. Setze TRACKER_REPO=besitzer/repo "
                          "oder starte den Tracker über GitHub Actions.")
    return render_notice(f"👋 Willkommen bei {APP_NAME} – kurz einrichten", "Willkommen! 👋",
                         paragraphs, button=("Jetzt einrichten", repo_settings_url))


def _render_text(groups: list[Group], total: int, date_str: str, errors: list[SourceError], truncated: int) -> str:
    lines = [f"{APP_NAME} – {date_str} – {total} neue Stellen", ""]
    if total == 0:
        lines.append("Heute keine neuen Treffer.")
    for g in groups:
        lines += [f"== {g.label} ({len(g.jobs)}) ==", ""]
        for job in g.jobs:
            score = f"[{job.score}/10] " if job.score is not None else ""
            types = f"[{' / '.join(job.job_types)}] " if job.job_types else ""
            lines.append(f"{score}{types}{job.title}")
            lines.append(f"  {job.company} · {job.location_label} · {job.source}"
                         + (f" · {job.posted_at:%d.%m.%Y}" if job.posted_at else ""))
            if job.investors:
                lines.append(f"  Portfolio von {', '.join(job.investors)}")
            if job.reason:
                lines.append(f"  → {job.reason}")
            lines.append(f"  Bewerben: {job.url}")
            lines.append("")
    if truncated:
        lines.append(f"… und {truncated} weitere.")
    if errors:
        lines += ["", "Hinweise:"] + [f"- {e.source}: {e.message}" for e in errors]
    return "\n".join(lines) + "\n"


def send(mail: RenderedMail) -> None:
    user, password, to = env("SMTP_USER"), env("SMTP_APP_PASSWORD"), env("EMAIL_TO")
    missing = [n for n, v in (("SMTP_USER", user), ("SMTP_APP_PASSWORD", password), ("EMAIL_TO", to)) if not v]
    if missing:
        raise RuntimeError(f"Mailversand nicht möglich, fehlende Umgebungsvariablen: {', '.join(missing)}")
    host = env("SMTP_HOST") or "smtp.gmail.com"
    port = int(env("SMTP_PORT") or 465)

    msg = EmailMessage()
    msg["Subject"] = mail.subject
    msg["From"] = f"{APP_NAME} <{user}>"
    msg["To"] = to
    msg.set_content(mail.text)
    msg.add_alternative(mail.html, subtype="html")

    with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(user, password)  # type: ignore[arg-type]
        smtp.send_message(msg, to_addrs=[a.strip() for a in to.split(",")])  # type: ignore[union-attr]
    log.info("Mail an %s gesendet: %s", to, mail.subject)
