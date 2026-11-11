from __future__ import annotations

from types import SimpleNamespace

import anthropic

from jobtracker.scoring import JobScore, ScoreBatch, Scorer


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


def _response(results):
    return SimpleNamespace(stop_reason="end_turn", parsed_output=ScoreBatch(results=results),
                           usage=SimpleNamespace(input_tokens=100, output_tokens=50))


def _scorer(config, monkeypatch, responses):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    config.raw["scoring"]["batch_size"] = 2
    scorer = Scorer(config)
    fake = FakeMessages(responses)
    scorer.client = SimpleNamespace(messages=fake)  # type: ignore[assignment]
    return scorer, fake


def test_scores_are_applied_in_batches(config, monkeypatch, make_job):
    jobs = [make_job(id=str(i), url=f"https://e.com/{i}") for i in range(3)]
    scorer, fake = _scorer(config, monkeypatch, [
        _response([JobScore(id="0", score=9, reason="Top", remote_ok=True, hours_ok=True),
                   JobScore(id="1", score=3, reason="Nein", remote_ok=False, hours_ok=None)]),
        _response([JobScore(id="0", score=6, reason="Ok", remote_ok=True, hours_ok=None)]),
    ])
    assert scorer.score(jobs) == []
    assert len(fake.calls) == 2
    assert [j.score for j in jobs] == [9, 3, 6]
    assert [scorer.passes(j) for j in jobs] == [True, False, True]
    assert "Acme SaaS GmbH" in fake.calls[0]["messages"][0]["content"]


def test_failed_batch_keeps_jobs_unscored(config, monkeypatch, make_job):
    jobs = [make_job()]
    err = anthropic.APIConnectionError(request=SimpleNamespace())  # type: ignore[arg-type]
    scorer, _ = _scorer(config, monkeypatch, [err])
    errors = scorer.score(jobs)
    assert len(errors) == 1
    assert jobs[0].score is None and scorer.passes(jobs[0])


def test_available_requires_key(config, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not Scorer.available(config)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert Scorer.available(config)
    config.raw["scoring"]["enabled"] = False
    assert not Scorer.available(config)
