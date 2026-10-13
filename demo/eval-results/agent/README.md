# Research mode evaluation results

Two task sets: [one PDF](#one-document) and [the whole five-document library](#the-whole-library).

## One document

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

### What the tasks test

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

### What it found

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

### Checking the grader

- **The reference answers:** 6 of 6 graded correct, and both negatives graded as correctly
  declined.
- **"The documents don't contain this information." for every task:** 0 of 6 correct, and both
  negatives graded as correctly declined.

## The whole library

Run on 12 October 2026: the 10 tasks in [`agent_eval_multi.json`](../../agent_eval_multi.json)
over all five [library](../../library/) documents (23 chunks), **twice per model**, since
single runs vary. Same graph, limits and grader as above.

| Model | Correct (of 8, run 1 / run 2) | Declined correctly (of 2) | Found every piece of evidence | Rounds / tool calls per task | Agent cost per task | Median time per task |
|---|---|---|---|---|---|---|
| `claude-haiku-5-5` | 8 / 8 | 2 / 2 | 100% | 1.2 / 3.6 | ~$0.004 | 18 s |
| `gpt-6-luna` | 6 / 8 | 2 / 2 | 100% | 1.1 / 3.8 | ~$0.002 | 12 s |
| `gemini-3.5-flash-lite` | 8 / 8 | 2 / 2 | 100% | 1.0 / 2.3 | free tier | 5 s |

Reports: Haiku [1](multi/anthropic-claude-haiku-5-5-1.md), [2](multi/anthropic-claude-haiku-5-5-2.md);
GPT-6 Luna [1](multi/openai-gpt-6-luna-1.md), [2](multi/openai-gpt-6-luna-2.md);
Gemini [1](multi/gemini-gemini-3.5-flash-lite-1.md), [2](multi/gemini-gemini-3.5-flash-lite-2.md).

### What the tasks test

- **Conflicts (m01, m05, m07):** a pricing update and a schools guide supersede the knowledge
  base's prices and discount rules; release notes qualify its Wi-Fi spec. The right answer uses
  the newer document and says what changed.
- **Combining documents (m02, m03):** the school task at current prices ($1,477.80) and an
  off-grid vineyard ($756 over two years) need three or four documents each.
- **Conditions and near-duplicates (m04, m06, m08):** the SolarKit fits Pro and Max only;
  grant and discount tiers; cellular pricing after the first year. Several passages repeat
  knowledge-base text almost word for word.
- **Negatives (m09, m10):** a euro price that isn't given and a product that doesn't exist.

### What it found

- **Conflicts were the main failure.** Before the prompts said how to handle documents that
  disagree, 6 runs (two per model) scored 56 of 60, and all four misses mixed old and new
  versions: an old Plus price ($49) in a cost total, a pre-September scenario that misapplied
  the old discount rule, and the 40% hardware tier described as withdrawn rather than moved
  to 3 stations. Adding one rule to the Ask, researcher and writer prompts (use the newest
  applicable figure, cite it, mention the older one only to say it changed) gave **58 of
  60**, with one conflict slip left: GPT-6 Luna once priced the Max at the old $499. The
  original 21-question Ask set still scored 19/19 and 2/2 on Haiku after the change.
- **The other remaining miss is fair:** Luna answered m04 correctly ("no") but didn't say the
  SolarKit fits the Pro and Max, which a helpful answer would.
- **Two references were too strict at first.** m05 required the firmware version and m06 the
  plan discount, neither of which the task asked about; both models' answers were otherwise
  complete. Both references were narrowed before the runs above.

### Checking the grader

On this set too, the reference answers were graded 8 of 8 correct and a blanket "the documents
don't contain this information" 0 of 8, with both negatives graded as correctly declined.

## Reading these numbers

- **Small sets.** 8 tasks over one PDF and 10 over five documents catch the failure modes
  above; they are regression checks, not benchmarks. Answers vary between runs: the
  one-document results are single runs, the library results two runs each. The one-document
  runs predate the rule for documents that disagree, which that set doesn't exercise.
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
just eval-agent --set multi --model claude-haiku-5-5   # the whole library
```

Rate-limited runs are retried after a minute, which the Gemini free tier needs.
