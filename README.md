# VERIFIED-LOOP

**A faithfulness-grounded agentic research engine — and the receipts that it beats a naive Claude call.**

LLMs fabricate citations. Ask one to research something and cite sources, and a
measurable fraction of its claims aren't actually supported by the source it
points to. VERIFIED-LOOP fixes that with _orchestration, not a better prompt_:
it decomposes the question, researches sub-questions in parallel, **independently
verifies every claim against the real source text**, and **iterates against that
evaluator across generations** until the report is faithful.

The point isn't "an agent." It's that you can **prove** the architecture wins:

```
                              unsupported-claim rate ↓
  B0  naive Claude (no tools)        ~55%
  B1  + web search, 1 pass           ~18%      ← the honest strong baseline
  A1  + verifier (gen=1)              ~7%
  A2  + generations (gen=3) ★         ~2%
```

The lift from **B1 → A2 is the orchestration**, because search is held constant.

## See it in 20 seconds

**▶ Live demo (auto-plays): https://seyonv.github.io/agentic-development-to-display/demo/**

A real-shaped run replayed cinematically: the plan expands, workers fan out, the
verifier **drops a fabricated claim on screen**, the faithfulness score climbs
across generations, and the agentic-vs-naive scorecard lands. The
[project breakdown](https://seyonv.github.io/agentic-development-to-display/) is
the full explainer (with a Research ⇄ Poker twin showing the pattern transfers).

## Want to build it yourself?

The **[Build Guide](https://seyonv.github.io/agentic-development-to-display/)**
(third tab on the site) is the honest, step-by-step runbook — _what_ you're
building and _why_, the two accounts you need (Claude + Tavily — **no GPUs, no
Modal**), the exact tooling, and a 6-step path with a "done when" for each, plus
a deep dive on the verifier + generations loop (the part everyone gets stuck on).

## Architecture

```
question
   │
   ▼  Planner ........... decompose into sub-questions      (structured output)
   │
   ├─► Worker ─┐
   ├─► Worker ─┤  parallel fan-out (asyncio.gather)         (tool use: search+fetch)
   ├─► Worker ─┤  each extracts findings tied to a source
   └─► Worker ─┘
   │
   ▼  Verifier ......... claim vs. real source text →
   │                     keep / flag / drop                 (evaluator / gate)
   ▼  Generations ...... draft → score faithfulness →
   │                     revise until plateau               (evaluator-optimizer)
   ▼  Synthesizer ...... verified findings → cited report
```

Five agentic patterns, one system: **planning · parallel fan-out/fan-in · tool
use · verification gate · reflection (generations)**. The orchestration is
hand-rolled `asyncio` on purpose — owning the control loop is the whole point;
a framework would hide it.

## Run it

```bash
pip install -e .                      # or: uv pip install -e .

# 1. Regenerate the shareable demo from a fixture — no API keys needed:
python -m verified_loop demo

# 2. A real run (needs ANTHROPIC_API_KEY + TAVILY_API_KEY) → run.html:
export ANTHROPIC_API_KEY=...  TAVILY_API_KEY=...
python -m verified_loop run "What caused the 2021 Texas grid failure?"

# 3. The ablation that produces the scorecard above:
python -m verified_loop eval        # over evals/research_eval.jsonl
```

A real run writes the **same run-dict shape** the demo uses, so
`report.render()` turns it into an identical, shareable `run.html` with zero glue.

## The honest part (what makes it credible)

- **Ablation, not vibes.** `B0/B1/A1/A2` are _feature flags on one engine_
  (`engine.Config`), so only the orchestration varies between rows.
- **Grounded evaluator.** The verifier checks claims against fetched **source
  text**, not another model's opinion — so iterating can't reward-hack a soft
  metric. A small human-labeled gold set (`evals/research_gold.jsonl`) validates
  that the verifier agrees with people.
- **Typed contracts.** Every agent boundary is a Pydantic model forced via
  Claude tool-use (`models.py`) — no string parsing.
- **Resilience.** Retries with backoff, a failed worker degrades gracefully
  (the run continues), token/cost accounting on every call.

## Eval data

`evals/` ships starter sets so you're not blocked on data:
`research_eval.jsonl` (questions + expected claims + sources),
`research_gold.jsonl` (claim/source/verdict rows to validate the verifier), and
`sql_eval.jsonl` (text-to-SQL over the public Chinook DB). See `evals/README.md`
for the sizing rules (start at 20–30; add a ~30-item gold set for any LLM-judge).

## Layout

```
verified_loop/
  models.py     typed agent contracts (Pydantic)
  llm.py        Claude wrapper — structured output, retries, token/cost
  search.py     SearchTool interface · Tavily + offline fixture
  agents.py     planner · worker · verifier · synthesizer
  engine.py     orchestration · ablation configs · generations loop
  evals.py      the B0/B1/A1/A2 ablation harness
  report.py     run dict → self-contained animated run.html
  cli.py        demo · run · eval
demo/index.html the deployed shareable artifact
evals/          starter datasets + sizing guide
```
