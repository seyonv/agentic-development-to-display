"""The eval harness — runs the B0/B1/A1/A2 ablation over a dataset and prints
the scorecard. This is the artifact that proves the architecture beats the
naive call: same questions, four configs, one number each."""

from __future__ import annotations

import json
from pathlib import Path

from . import engine
from .engine import A1, A2, B0, B1, Config
from .llm import LLM
from .search import TavilySearch

LADDER = [B0, B1, A1, A2]


def load(dataset: Path) -> list[dict]:
    return [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]


async def run_ablation(dataset: Path) -> dict[str, float]:
    """Run every config over every question; report mean unsupported-claim rate.

    unsupported-claim rate = 1 - faithfulness, averaged over questions. Lower is
    better; the gap from B1 -> A2 is the orchestration's contribution."""
    rows = load(dataset)
    search = TavilySearch()
    table: dict[str, float] = {}
    print(f"\nAblation over {len(rows)} questions — unsupported-claim rate (lower=better)\n")
    for cfg in LADDER:
        rates = []
        for row in rows:
            llm = LLM()  # fresh usage per run
            run = await engine.run(row["question"], llm, search, cfg)
            faith = run["scorecard"]["agentic"]["faithfulness"]
            rates.append(1.0 - faith)
        mean = sum(rates) / len(rates)
        table[cfg.name] = round(mean, 3)
        bar = "█" * int(mean * 40)
        print(f"  {cfg.name:3}  {mean:5.1%}  {bar}")
    print(f"\n  B1 -> A2 lift: {table['B1'] - table['A2']:+.1%} (the orchestration)\n")
    return table
