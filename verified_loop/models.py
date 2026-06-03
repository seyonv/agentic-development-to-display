"""Typed contracts for every agent boundary. No string parsing anywhere —
each agent is forced to return one of these via Claude tool-use."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Verdict = Literal["keep", "flag", "drop"]


class Plan(BaseModel):
    """Planner output: the question decomposed into sub-questions."""

    sub_questions: list[str] = Field(min_length=1, max_length=8)


class Finding(BaseModel):
    """A single grounded claim a worker extracted, tied to its source."""

    claim: str
    source: str  # short label, e.g. "FDIC"
    url: str


class WorkerResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)


class Check(BaseModel):
    """Verifier output for one claim, grounded in the fetched source text."""

    verdict: Verdict
    note: str
    supporting_quote: str | None = None


class Report(BaseModel):
    """Synthesizer output: a cited report."""

    markdown: str
    # citations are reconstructed from kept findings by the engine
