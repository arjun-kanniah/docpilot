# Research mode evaluation results

Run on 12 October 2026: the 8 tasks in [`agent_eval_set.json`](../../agent_eval_set.json)
through the same agent graph, tools and limits as the app (up to 2 research rounds of 6 tool
calls, 5 passages per search), graded by `claude-opus-5-5` against the reference answers. The
same model ran every agent step.

| Model | Correct (of 6) | Declined correctly (of 2) | Found every evidence page | Cited it | Key figures stated | Rounds / tool calls per task | Agent cost per task | Median time per task |
|---|---|---|---|---|---|---|---|---|
| `claude-haiku-5-5` | 6 | 2 | 100% | 100% | 5 of 5 | 1.4 / 4.6 | ~$0.004 | 18 s |
| `gpt-6-luna` | 6 | 2 | 100% | 100% | 5 of 5 | 1.2 / 4.6 | ~$0.002 | 16 s |
| `gemini-3.5-flash-lite` | 5 | 2 | 100% | 83% | 2 of 5 | 1.0 / 2.6 | free tier | 4 s |

Per-task reports, with the grader's reasons: [Haiku](anthropic-claude-haiku-5-5.md),
[GPT-6 Luna](openai-gpt-6-luna.md), [Gemini Flash-Lite](gemini-gemini-3.5-flash-lite.md).

## What the tasks test

Each task needs several facts combined, which a single retrieval often misses:

- **r02, r03:** pick models and a plan from requirements, then do the arithmetic
  (the school task: $1,393.80 after the education discount).
- **r04:** apply a condition (registered within 30 days, so a 2.5-year-old station is still
  under warranty) and gather four policies.
- **r05:** price a plan over two years. One Plus account covers 3 stations at one price.
- **r07, r08:** the document can't answer these (a CEO, revenue, competitors), so the right
  response is to say so without inventing anything.

Besides the grader's verdict, each run is checked in code: did it retrieve passages from every
page the answer needs, does the answer cite them, and does it state the key figures (commas and
`$` ignored, so `$98.00` counts as `98`).

## What it found

- **Gemini Flash-Lite prices the Plus plan per station** in r05 ("$4.99 per station per month
  × 3 stations"), although the source gives one price per account. Earlier development runs on
  the school task (r02) showed the same mistake, and it led to the analyst checking the notes
  against the sources and the writer keeping prices in the units the source gives. That fixed
  r02 on every model, but Flash-Lite still makes the mistake when writing r05. For Research
  mode, prefer Haiku or Luna.
- **During development these tasks also caught:** GPT-6 Luna writing long keyword-list queries
  that never retrieved the education discount (now short, single-topic queries); the analyst
  sending the researcher to search again for things it had already searched for and not found
  (it now sees the searches already run, and a round that finds no new passages ends the
  research); and Claude rejecting runs that used the whole tool budget (the researcher's
  conversation is now only appended to).

## Checking the grader

- **The reference answers:** 6 of 6 graded correct, and both negatives graded as correctly
  declined.
- **"The documents don't contain this information." for every task:** 0 of 6 correct, and both
  negatives graded as correctly declined.

## Reading these numbers

- **Eight tasks over a 5-page document.** This is a regression check that catches the failure
  modes above, not a benchmark. Answers vary between runs; a single run per model is shown.
- **Costs are estimates** from token counts and list prices. Grading cost about $0.06 per run.
- The grader runs on Opus, a different model family from Luna and Gemini; for the Haiku run it
  grades a smaller Claude model against a written reference.

## Reproduce

```bash
just eval-agent --model claude-haiku-5-5
just eval-agent --provider openai --model gpt-6-luna
just eval-agent --provider gemini --model gemini-3.5-flash-lite --workers 1   # free tier: slow
just eval-agent --answers-from oracle          # check the grader with the reference answers
just eval-agent --only r02,r05                 # selected tasks
```

Rate-limited runs are retried after a minute, which the Gemini free tier needs.
