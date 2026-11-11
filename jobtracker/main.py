"""Orchestrierung: Quellen abfragen → filtern → Duplikate raus → scoren → Mail → speichern.

    python -m jobtracker --dry-run                 # nur ausgeben, nichts senden/speichern
    python -m jobtracker --dry-run --source bundesagentur --preview data/preview.html
    python -m jobtracker                           # echter Lauf
    python -m jobtracker --scheduled               # für Cron: max. 1 Lauf pro Tag ab 07:00 Berlin
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from . import mailer
from .config import ROOT, Config, load_config
from .filters import JobFilter
from .models import Job, SourceError
from .scoring import Scorer
from .settings import form_url, load_defaults
from .sources import SOURCES, SourceSkipped
from .storage import SeenStore, dedupe

log = logging.getLogger("jobtracker")
BERLIN = ZoneInfo("Europe/Berlin")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="jobtracker", description="Werkstudenten-Job-Tracker")
    p.add_argument("--dry-run", action="store_true", help="nur ausgeben – keine Mail, nichts speichern")
    p.add_argument("--config", type=Path, help="Pfad zur config.yaml")
    p.add_argument("--source", action="append", choices=sorted(SOURCES), help="nur diese Quelle(n) abfragen (auch deaktivierte)")
    p.add_argument("--no-score", action="store_true", help="LLM-Scoring überspringen")
    p.add_argument("--preview", type=Path, help="HTML-Mail zusätzlich in diese Datei schreiben")
    p.add_argument("--scheduled", action="store_true", help="nur ab 07:00 Berlin und max. einmal pro Tag laufen")
    p.add_argument("--days", type=int, help="max_days_old für diesen Lauf überschreiben (z. B. erster Lauf eines neuen Profils)")
    p.add_argument("--no-save", action="store_true", help="Mail senden, aber seen_jobs.json nicht aktualisieren (Testmail)")
    p.add_argument("--include-seen", action="store_true", help="bereits gemailte Stellen nicht ausblenden (zum Testen)")
    p.add_argument("-v", "--verbose", action="store_true", help="Debug-Logging (zeigt u. a. verworfene Stellen)")
    return p.parse_args(argv)


def fetch_all(config: Config, only: list[str] | None) -> tuple[list[Job], list[SourceError], dict[str, int]]:
    jobs: list[Job] = []
    errors: list[SourceError] = []
    counts: dict[str, int] = {}
    for name, cls in SOURCES.items():
        source = cls(config)
        if only is not None and name not in only:
            continue
        if only is None and not source.enabled:
            continue
        started = time.monotonic()
        try:
            found = source.fetch()
        except SourceSkipped as exc:
            log.info("Quelle %s übersprungen: %s", name, exc)
            continue
        except Exception as exc:  # eine kaputte Quelle darf den Lauf nicht abbrechen
            log.exception("Quelle %s fehlgeschlagen", name)
            errors.append(SourceError(source.label, f"{type(exc).__name__}: {exc}"[:300]))
            continue
        errors.extend(getattr(source, "partial_errors", []))  # z. B. einzelne Firmen/Boards der Watchlists
        counts[source.label] = len(found)
        log.info("Quelle %-14s %4d Stellen (%.1fs)", name, len(found), time.monotonic() - started)
        jobs.extend(found)
    return jobs, errors, counts


def should_run_scheduled(store: SeenStore, now: datetime) -> bool:
    if now.hour < 7:
        log.info("Geplanter Lauf: erst ab 07:00 Berlin (jetzt %s) – übersprungen", now.strftime("%H:%M"))
        return False
    if store.last_run == now.date().isoformat():
        log.info("Geplanter Lauf: heute schon gelaufen – übersprungen")
        return False
    return True


def print_jobs(jobs: list[Job]) -> None:
    for job in sorted(jobs, key=lambda j: (j.category or "zz", -(j.score or 0))):
        score = f"{job.score:>2}/10" if job.score is not None else "  –  "
        print(f"[{score}] {job.category or '-':<16} {job.title[:70]:<70} | {job.company[:30]:<30} | {job.location_label[:35]:<35} | {job.source}")
        if job.investors:
            print(f"         💼 Portfolio von {', '.join(job.investors)}")
        if job.reason:
            print(f"         → {job.reason}")
        print(f"         {job.url}")


def onboarding(args: argparse.Namespace) -> int:
    """Noch nichts eingerichtet: Willkommens-Mail mit Link zum Einstellungsformular (max. 1× pro Tag)."""
    storage_cfg = load_defaults().get("storage", {})
    store = SeenStore(ROOT / storage_cfg.get("path", "data/seen_jobs.json"), int(storage_cfg.get("retention_days", 60)))
    now = datetime.now(BERLIN)
    if args.scheduled and not args.dry_run and not should_run_scheduled(store, now):
        return 0
    mail = mailer.render_welcome(form_url(None))
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        args.preview.write_text(mail.html, encoding="utf-8")
    if args.dry_run:
        print(f"\n=== {mail.subject} ===\n\n{mail.text}\n(Dry-Run: keine Mail gesendet)")
        return 0
    mailer.send(mail)
    if not args.no_save:
        store.save(run_at=now)  # merkt sich den Tag, damit die Erinnerung nur 1× täglich kommt
    return 0


def run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if config is None:
        log.info("Noch nicht eingerichtet (keine settings.yaml / config.yaml) – sende Willkommens-Mail")
        return onboarding(args)
    if args.days:
        config.raw.setdefault("search", {})["max_days_old"] = args.days
        for source_cfg in config.sources.values():  # Quellen mit eigenem Zeitfenster (z. B. vc_boards) auch
            if isinstance(source_cfg, dict) and "max_days_old" in source_cfg:
                source_cfg["max_days_old"] = args.days
    storage_cfg = config.storage
    store = SeenStore(ROOT / storage_cfg.get("path", "data/seen_jobs.json"), int(storage_cfg.get("retention_days", 60)))
    now = datetime.now(BERLIN)

    if args.scheduled and not args.dry_run and not should_run_scheduled(store, now):
        return 0

    raw, errors, counts = fetch_all(config, args.source)
    result = JobFilter(config).apply(raw)
    unique = dedupe(result.kept)
    new = unique if args.include_seen else store.filter_new(unique)
    log.info("Gesamt %d → nach Filter %d → ohne Duplikate %d → neu %d", len(raw), len(result.kept), len(unique), len(new))
    if result.rejected:
        log.info("Verworfen: %s", ", ".join(f"{k} ({v})" for k, v in result.rejected.most_common()))

    to_mail = new
    if new and not args.no_score and Scorer.available(config):
        scorer = Scorer(config)
        errors.extend(SourceError("Scoring", m) for m in scorer.score(new))
        to_mail = [j for j in new if scorer.passes(j)]
        log.info("Scoring: %d von %d Stellen ≥ %d Punkte", len(to_mail), len(new), scorer.min_score)
    elif new and not args.no_score:
        log.info("Scoring übersprungen (deaktiviert, ANTHROPIC_API_KEY fehlt oder Profil leer)")

    stats = (f"Quellen: {', '.join(f'{k} {v}' for k, v in counts.items()) or '–'} · "
             f"{len(raw)} gefunden, {len(result.kept)} passend, {len(new)} neu, {len(to_mail)} in dieser Mail")
    mail = mailer.render(to_mail, config, errors, stats=stats, today=now.date())

    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        args.preview.write_text(mail.html, encoding="utf-8")
        log.info("HTML-Vorschau geschrieben: %s", args.preview)

    if args.dry_run:
        print(f"\n=== {mail.subject} ===\n")
        print_jobs(to_mail)
        for e in errors:
            print(f"⚠️  {e.source}: {e.message}")
        print(f"\n{stats}\n(Dry-Run: keine Mail gesendet, nichts gespeichert)")
        return 0

    if to_mail or config.mail.get("send_when_empty", True):
        mailer.send(mail)
    else:
        log.info("Keine neuen Stellen und send_when_empty=false – keine Mail")

    if args.no_save:
        log.info("--no-save: seen_jobs.json bleibt unverändert")
        return 0

    # Auch zu niedrig bewertete Stellen merken, damit sie morgen nicht erneut gescort werden
    store.mark(new, when=now.date())
    removed = store.prune(today=now.date())
    store.save(run_at=now)
    log.info("seen_jobs.json gespeichert (%d URLs, %d Hashes, %d alte Einträge entfernt)",
             len(store.urls), len(store.hashes), removed)
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    for noisy in ("urllib3", "httpx", "anthropic", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    try:
        return run(args)
    except Exception:
        log.exception("Lauf fehlgeschlagen")
        return 1


if __name__ == "__main__":
    sys.exit(main())
