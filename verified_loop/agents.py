"""The agent roles. Each is a thin function: a prompt + a typed return.
This is the whole 'agentic' surface — the orchestration in engine.py composes them."""

from __future__ import annotations

from .llm import LLM
from .models import Check, Finding, Plan, Report, WorkerResult
from .search import SearchTool, Source


async def plan(llm: LLM, question: str) -> Plan:
    return await llm.structured(
        f"Decompose this research question into 3–4 focused, non-overlapping "
        f"sub-questions that together answer it:\n\n{question}",
        schema=Plan,
    )


async def work(llm: LLM, search: SearchTool, sub_question: str) -> tuple[WorkerResult, list[Source]]:
    """Search, read, and extract grounded findings for one sub-question."""
    sources = await search.search(sub_question, k=3)
    corpus = "\n\n".join(f"[{s.url}]\n{s.text[:2500]}" for s in sources)
    result = await llm.structured(
        f"Sub-question: {sub_question}\n\nSources:\n{corpus}\n\n"
        "Extract only claims directly supported by the sources above. "
        "Each finding MUST include the source url it came from. "
        "If nothing is supported, return no findings.",
        schema=WorkerResult,
    )
    return result, sources


async def verify(llm: LLM, finding: Finding, source_text: str) -> Check:
    """Adversarially check one claim against the actual source text."""
    return await llm.structured(
        f"Claim: {finding.claim}\n\nSource text:\n{source_text[:4000]}\n\n"
        "Does the source text actually support this claim? "
        "verdict=keep if clearly supported, flag if partially/imprecisely "
        "supported, drop if unsupported or contradicted. "
        "If keep/flag, include the supporting_quote.",
        schema=Check,
        system="You are a skeptical fact-checker. Default to 'drop' when unsure. "
        "Only 'keep' when the source text plainly states the claim.",
    )


async def synthesize(llm: LLM, question: str, findings: list[Finding]) -> Report:
    bullets = "\n".join(f"- {f.claim} [{f.source}]" for f in findings)
    return await llm.structured(
        f"Question: {question}\n\nVerified findings:\n{bullets}\n\n"
        "Write a tight, well-structured report answering the question using "
        "ONLY these findings. Cite each claim inline as [n] matching the order "
        "of findings. Do not introduce any fact not in the findings.",
        schema=Report,
    )
