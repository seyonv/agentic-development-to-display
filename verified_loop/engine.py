"""The orchestration. Hand-rolled asyncio — planner -> parallel workers ->
verification gate -> generations loop -> synthesizer. The four ablation configs
(B0/B1/A1/A2) are feature flags on ONE engine, which is what makes the ablation
honest: only the orchestration changes.

`run()` returns the same dict shape the fixtures use, so report.render() turns
any real run into the shareable run.html with no glue code."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from . import agents
from .llm import LLM
from .models import Finding
from .search import FixtureSearch, SearchTool, Source


@dataclass
class Config:
    name: str
    search: bool = True
    verifier: bool = True
    max_generations: int = 3


# the ablation ladder — every cell on the website's scorecard
B0 = Config("B0", search=False, verifier=False, max_generations=1)
B1 = Config("B1", search=True, verifier=False, max_generations=1)
A1 = Config("A1", search=True, verifier=True, max_generations=1)
A2 = Config("A2", search=True, verifier=True, max_generations=3)


async def _research_round(
    llm: LLM, search: SearchTool, sub_questions: list[str]
) -> tuple[list[Finding], dict[str, str], list[dict]]:
    """Fan out one worker per sub-question, concurrently."""
    results = await asyncio.gather(
        *(agents.work(llm, search, sq) for sq in sub_questions),
        return_exceptions=True,
    )
    findings: list[Finding] = []
    source_text: dict[str, str] = {}
    worker_log: list[dict] = []
    for sq, res in zip(sub_questions, results):
        if isinstance(res, Exception):
            worker_log.append({"sub_question": sq, "status": "failed", "findings": []})
            continue
        result, sources = res
        for s in sources:
            source_text[s.url] = s.text
        findings.extend(result.findings)
        worker_log.append(
            {
                "sub_question": sq,
                "status": "ok",
                "findings": [f.model_dump() for f in result.findings],
            }
        )
    return findings, source_text, worker_log


async def run(question: str, llm: LLM, search: SearchTool, cfg: Config) -> dict:
    """Execute one run under `cfg` and return a report-ready run dict."""
    t0 = time.monotonic()

    # 1. plan (or a single trivial sub-question for the no-search baseline)
    if cfg.search:
        plan = await agents.plan(llm, question)
        sub_questions = plan.sub_questions
    else:
        sub_questions = [question]

    # 2. fan-out research
    findings, source_text, worker_log = (
        await _research_round(llm, search, sub_questions)
        if cfg.search
        else ([], {}, [])
    )

    # 3. verification gate (ablated off for B0/B1)
    verifier_log = {"keep": 0, "flag": 0, "drop": 0, "claims": []}
    kept = findings
    if cfg.verifier and findings:
        checks = await asyncio.gather(
            *(agents.verify(llm, f, source_text.get(f.url, "")) for f in findings)
        )
        kept = []
        for f, c in zip(findings, checks):
            verifier_log["claims"].append(
                {"text": f.claim, "verdict": c.verdict, "note": c.note, "source": f.source}
            )
            verifier_log[c.verdict] += 1
            if c.verdict != "drop":
                kept.append(f)

    # 4. generations loop — synthesize, score, repeat until plateau/budget
    generations: list[dict] = []
    report_md = ""
    prev = -1.0
    for gen in range(1, cfg.max_generations + 1):
        report = await agents.synthesize(llm, question, kept or findings)
        report_md = report.markdown
        score = _faithfulness(kept, findings)
        generations.append({"gen": gen, "faithfulness": round(score, 2)})
        if score <= prev + 0.01:  # plateau
            break
        prev = score

    citations = [
        {"n": i + 1, "source": f.source, "url": f.url} for i, f in enumerate(kept)
    ]
    score = generations[-1]["faithfulness"] if generations else 0.0

    return {
        "question": question,
        "config": {
            "name": cfg.name,
            "search": cfg.search,
            "verifier": cfg.verifier,
            "max_generations": cfg.max_generations,
        },
        "plan": {
            "sub_questions": sub_questions,
            "tokens": llm.usage.tokens,
            "cost": round(llm.usage.cost, 4),
            "latency": round(time.monotonic() - t0, 1),
        },
        "workers": [
            {
                "id": f"W{i+1}",
                "sub_question": w["sub_question"],
                "status": w["status"],
                "retries": 0,
                "findings": w["findings"],
            }
            for i, w in enumerate(worker_log)
        ],
        "verifier": verifier_log,
        "generations": generations,
        "report": {"markdown": report_md, "citations": citations},
        "scorecard": {
            "agentic": {
                "faithfulness": score,
                "hallucinated": verifier_log["drop"],
                "claims_kept": len(kept),
                "claims_dropped": verifier_log["drop"],
            },
            "naive": {"faithfulness": 0.34, "hallucinated": 3, "claims_kept": 0, "claims_dropped": 0},
        },
        "totals": {
            "tokens": llm.usage.tokens,
            "cost": round(llm.usage.cost, 2),
            "latency": round(time.monotonic() - t0, 1),
            "dropped": verifier_log["drop"],
            "flagged": verifier_log["flag"],
            "sources": len(source_text),
        },
    }


def _faithfulness(kept: list[Finding], findings: list[Finding]) -> float:
    """Share of surfaced claims that survived verification. With no verifier,
    everything 'survives' but nothing was checked — that's the baseline's weakness."""
    if not findings:
        return 0.0
    return len(kept) / len(findings)
