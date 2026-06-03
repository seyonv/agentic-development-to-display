# Eval data — starter sets

The hardest part of building an agent isn't the agent. It's proving it works.
This folder answers the first question everyone hits: **where does the eval data
come from, and how much do I need?**

## How much

Start with **20–30 examples**. That's enough to see a real gap between two
configs — if a change moves the metric 10–15 points, 25 examples will show it
above the noise. You do _not_ need thousands to start. Grow the set only when:

- two configs score within a few points and you can't tell them apart, or
- you're about to publish a number you want to defend.

If you use an **LLM as the judge**, also label **~30 items by hand** as a "gold
set" and check the judge agrees with you on those. If the judge tracks your
labels, you can trust it on the rest. If it doesn't, fix the rubric before
trusting any automated score. This one step is what separates a real eval from
theater.

## Where to get it

1. **Your own artifacts** — emails, repos, calendar, docs. Free, realistic,
   already labeled by reality.
2. **Public datasets** — HotpotQA / SimpleQA (research), Chinook / Northwind
   (text-to-SQL), SWE-bench-lite (code), RAGTruth (faithfulness).
3. **Synthesize** — inject known bugs into clean code, generate synthetic
   calendars in a loop, or have a strong model draft candidate items that you
   then verify. Synthetic data is great precisely _because you know the answer_.

## The shape of an eval row

Every row is `(input, a checkable signal)`. The signal is the whole game:

| Agent     | input                     | checkable signal                               |
| --------- | ------------------------- | ---------------------------------------------- |
| Research  | a question                | does the cited source contain the claim?       |
| SQL       | an NL question            | do the returned rows equal the gold rows?      |
| Calendar  | a goal + calendars        | zero conflicts and inside the window?          |
| PR review | a diff with a planted bug | was the bug flagged?                           |
| RAG       | a question                | is every sentence backed by a retrieved chunk? |

If you can check it in code (or with a judge validated against a gold set), you
can put a number on it. That number is what turns "I built an agent" into "my
architecture beats the naive call — here's the ablation."

## Files here

- `research_eval.jsonl` — 10 research questions with expected key claims +
  candidate authoritative sources (for the ★ seed agent / the flagship).
- `research_gold.jsonl` — example claim/source/label rows to validate the
  verifier agent against human judgment.
- `sql_eval.jsonl` — text-to-SQL questions over the public **Chinook** SQLite DB
  with reference SQL. Run the reference SQL once to capture each gold result set.

These are starters — extend them to ~25 rows each before you quote a metric.
