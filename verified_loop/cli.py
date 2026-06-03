"""verified-loop CLI.

  python -m verified_loop demo                  # regenerate the shareable demo from the fixture (no keys)
  python -m verified_loop run "<question>"      # real run (needs ANTHROPIC_API_KEY + TAVILY_API_KEY) -> run.html
  python -m verified_loop eval                   # run the B0/B1/A1/A2 ablation over evals/research_eval.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from . import engine, report
from .engine import A2
from .llm import LLM
from .search import TavilySearch

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "svb_run.json"


def cmd_demo(args: argparse.Namespace) -> None:
    run = json.loads(FIXTURE.read_text())
    out = report.write_report(run, args.out)
    print(f"✓ demo written to {out}")


def cmd_run(args: argparse.Namespace) -> None:
    async def _go() -> dict:
        llm = LLM()
        return await engine.run(args.question, llm, TavilySearch(), A2)

    run = asyncio.run(_go())
    out = report.write_report(run, args.out)
    score = run["scorecard"]["agentic"]["faithfulness"]
    print(f"✓ faithfulness {score:.2f} · {run['totals']['dropped']} claims dropped")
    print(f"✓ run.html written to {out}")


def cmd_eval(args: argparse.Namespace) -> None:
    from .evals import run_ablation

    asyncio.run(run_ablation(Path(args.dataset)))


def main() -> None:
    p = argparse.ArgumentParser(prog="verified_loop")
    sub = p.add_subparsers(required=True)

    d = sub.add_parser("demo", help="regenerate the shareable demo (no API keys)")
    d.add_argument("--out", default=str(ROOT / "demo" / "index.html"))
    d.set_defaults(func=cmd_demo)

    r = sub.add_parser("run", help="a real run -> run.html")
    r.add_argument("question")
    r.add_argument("--out", default="run.html")
    r.set_defaults(func=cmd_run)

    e = sub.add_parser("eval", help="run the ablation over an eval set")
    e.add_argument("--dataset", default=str(ROOT / "evals" / "research_eval.jsonl"))
    e.set_defaults(func=cmd_eval)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
