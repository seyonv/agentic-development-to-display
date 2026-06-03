"""VERIFIED-LOOP — a faithfulness-grounded agentic research engine.

planner -> parallel workers -> verifier (keep/flag/drop) -> generations loop
-> cited report, plus an ablation harness that proves it beats a naive call.
"""

from .engine import A1, A2, B0, B1, Config, run
from .report import render, write_report

__all__ = ["run", "render", "write_report", "Config", "B0", "B1", "A1", "A2"]
__version__ = "0.1.0"
