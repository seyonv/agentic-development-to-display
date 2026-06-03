"""Offline, deterministic tests — the LLM and search are stubbed at the seam,
so CI never makes a network call. This is the AI-native version of unit testing:
mock the model, test the orchestration logic (fan-out, the verification gate,
the generations plateau, the run-dict contract)."""

import asyncio

from verified_loop import engine, render
from verified_loop.engine import A1, A2, B1
from verified_loop.models import Check, Finding, Plan, Report, WorkerResult
from verified_loop.search import FixtureSearch, Source


class StubLLM:
    """Returns canned structured objects; drops claims whose source url ends in
    'bad' so the verification gate has something to do."""

    class _U:
        tokens = 1000
        cost = 0.01

    usage = _U()

    async def structured(self, prompt, schema, system=None, max_tokens=1500):
        if schema is Plan:
            return Plan(sub_questions=["q one", "q two", "q three"])
        if schema is WorkerResult:
            url = "https://src.test/bad" if "two" in prompt else "https://src.test/ok"
            return WorkerResult(findings=[Finding(claim="claim", source="S", url=url)])
        if schema is Check:
            # the verifier sees the source TEXT; the 'bad' source's text is "irrelevant"
            unsupported = "irrelevant" in prompt
            return Check(
                verdict="drop" if unsupported else "keep", note="n", supporting_quote=None
            )
        if schema is Report:
            return Report(markdown="report [1]")
        raise AssertionError(schema)


def _search():
    return FixtureSearch(
        {
            "one": [Source("https://src.test/ok", "ok", "supporting text")],
            "two": [Source("https://src.test/bad", "bad", "irrelevant text")],
            "three": [Source("https://src.test/ok", "ok", "supporting text")],
        }
    )


def test_fan_out_runs_every_subquestion():
    run = asyncio.run(engine.run("why?", StubLLM(), _search(), A2))
    assert len(run["plan"]["sub_questions"]) == 3
    assert len(run["workers"]) == 3
    assert all(w["status"] == "ok" for w in run["workers"])


def test_verifier_gate_drops_unsupported_claims():
    run = asyncio.run(engine.run("why?", StubLLM(), _search(), A1))
    # exactly one sub-question routed to the 'bad' source → one drop
    assert run["verifier"]["drop"] == 1
    assert run["verifier"]["keep"] == 2


def test_generations_loop_records_and_plateaus():
    run = asyncio.run(engine.run("why?", StubLLM(), _search(), A2))
    gens = run["generations"]
    assert 1 <= len(gens) <= A2.max_generations
    # faithfulness = kept/findings = 2/3
    assert abs(gens[-1]["faithfulness"] - round(2 / 3, 2)) < 0.02


def test_baseline_has_no_verifier():
    run = asyncio.run(engine.run("why?", StubLLM(), _search(), B1))
    assert run["verifier"]["drop"] == 0  # gate is ablated off
    assert run["config"]["verifier"] is False


def test_run_dict_renders_to_html():
    run = asyncio.run(engine.run("why?", StubLLM(), _search(), A2))
    html = render(run)
    assert "VERIFIED-LOOP" in html
    assert run["question"] in html
