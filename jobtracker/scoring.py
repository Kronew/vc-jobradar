"""Optionales Relevanz-Scoring mit der Anthropic API (mehrere Jobs pro Request)."""

from __future__ import annotations

import json
import logging

import anthropic
from pydantic import BaseModel, Field

from .config import Config, env
from .models import Job

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Du bewertest Stellenanzeigen aus Portfolio-Startups von VCs für eine Person, die {suche} sucht.
Bewerte jede Stelle von 1 (passt gar nicht) bis 10 (perfekt) anhand des Profils.
Berücksichtige: Passung des Bereichs zu den Prioritäten, passende Stellenart (Werkstudent: Teilzeit neben
dem Studium; Praktikum: befristet, oft Vollzeit), Ort (remote in Deutschland oder pendelbar),
Startzeitpunkt, Sprachanforderungen. Feste Vollzeitstellen ohne Praktikums- oder Studentencharakter
und reine Callcenter-Jobs bekommen höchstens 3.
`reason`: ein kurzer Satz auf Deutsch, warum die Stelle (nicht) passt.
`remote_ok`: true, wenn die Stelle remote ist oder im Pendelradius liegt.
Stellen mit `andere_stadt: true` liegen bewusst außerhalb des Pendelradius – Ort dort nicht abwerten.
`hours_ok`: true/false, wenn der Umfang erkennbar ist, sonst null.
Gib für jede übergebene id genau ein Ergebnis zurück."""


class ScoringError(Exception):
    pass


class JobScore(BaseModel):
    id: str
    score: int = Field(ge=1, le=10)
    reason: str
    remote_ok: bool
    hours_ok: bool | None


class ScoreBatch(BaseModel):
    results: list[JobScore]


class Scorer:
    def __init__(self, config: Config) -> None:
        cfg = config.scoring
        self.profile = config.profile
        types = [t["label"] for t in (config.raw.get("job_search") or {}).values()] or ["Werkstudentenstellen"]
        self.system_prompt = SYSTEM_PROMPT.format(suche=" oder ".join(types))
        self.model: str = cfg.get("model", "claude-haiku-5-5")
        self.batch_size: int = int(cfg.get("batch_size", 15))
        self.min_score: int = int(cfg.get("min_score", 6))
        self.client = anthropic.Anthropic(max_retries=3)

    @staticmethod
    def available(config: Config) -> bool:
        # Ohne Profil fehlt die Grundlage für die Bewertung
        return (bool(config.scoring.get("enabled", True)) and env("ANTHROPIC_API_KEY") is not None
                and bool(config.profile.strip()))

    def score(self, jobs: list[Job]) -> list[str]:
        """Bewertet die Jobs in-place. Gibt Fehlermeldungen pro fehlgeschlagenem Batch zurück."""
        errors: list[str] = []
        for start in range(0, len(jobs), self.batch_size):
            batch = jobs[start:start + self.batch_size]
            try:
                self._score_batch(batch)
            except (anthropic.APIError, ScoringError, ValueError) as exc:
                log.error("Scoring-Batch %d fehlgeschlagen: %s", start // self.batch_size + 1, exc)
                errors.append(f"Scoring für {len(batch)} Stellen fehlgeschlagen ({type(exc).__name__}) – ungefiltert übernommen")
        return errors

    def _score_batch(self, batch: list[Job]) -> None:
        payload = [
            {
                "id": str(i),
                "titel": job.title,
                "firma": job.company,
                "ort": job.location_label,
                "andere_stadt": job.elsewhere,
                "beschreibung": job.description_snippet[:800],
            }
            for i, job in enumerate(batch)
        ]
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=4000,
            thinking={"type": "disabled"},
            output_config={"effort": "low"},
            system=self.system_prompt,
            messages=[{
                "role": "user",
                "content": f"<profil>\n{self.profile}\n</profil>\n\n<stellen>\n"
                           f"{json.dumps(payload, ensure_ascii=False, indent=1)}\n</stellen>",
            }],
            output_format=ScoreBatch,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            raise ScoringError(f"keine auswertbare Antwort (stop_reason={response.stop_reason})")
        log.info("Scoring: %d Stellen, %d Input-/%d Output-Tokens", len(batch),
                 response.usage.input_tokens, response.usage.output_tokens)
        by_id = {r.id: r for r in response.parsed_output.results}
        for i, job in enumerate(batch):
            if (r := by_id.get(str(i))) is not None:
                job.score, job.reason, job.remote_ok, job.hours_ok = r.score, r.reason, r.remote_ok, r.hours_ok

    def passes(self, job: Job) -> bool:
        # Ungescorte Jobs (z. B. Batch-Fehler) lieber zeigen als verlieren
        return job.score is None or job.score >= self.min_score
