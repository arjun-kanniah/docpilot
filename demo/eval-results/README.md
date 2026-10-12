# Evaluation results

Baseline run of the [demo evaluation set](../README.md#the-evaluation-set) on 11 October 2026:
21 questions over the 5-page Aurora Instruments PDF (11 chunks), top 6 passages, answers
graded by `claude-opus-5-5` against the reference answers.

| Answering model | Correct (of 19) | Declined correctly (of 2) | Cites the right page | Median time to full answer | Answer cost per question |
|---|---|---|---|---|---|
| `claude-opus-5-5` | 19 | 2 | 100% | 2.3 s | ~$0.013 |
| `claude-haiku-5-5` | 19 | 2 | 100% | 1.4 s | ~$0.0003 |
| `gemini-3.5-flash-lite` | 19 | 2 | 100% | 0.7 s | free tier |

Retrieval found the expected page in the top 6 for all 19 answerable questions (mean
reciprocal rank 0.97). Full per-question reports, with the grader's reasons:
[Opus](anthropic-claude-opus-5-5.md), [Haiku](anthropic-claude-haiku-5-5.md),
[Gemini](gemini-gemini-3.5-flash-lite.md).

## Checking the grader

Before grading real answers, the grader was run on two fixed answer sets:

- **The reference answers themselves:** graded correct on 21 of 21.
- **"I don't know." for every question:** graded incorrect on all 19 answerable questions and
  correct on the 2 the document can't answer.

## Reading these numbers

- **The set is saturated.** All three models score 100%, so it can't rank them, and it can't
  show whether a retrieval change helps. It is a regression check, not a benchmark: a drop
  means something broke. A harder set (more documents, near-duplicate passages, questions
  that need several sections) is the next step.
- **Opus graded its own answers** in the Opus run. The grading compares facts with a written
  reference answer, which leaves little room for self-preference, but a different grader
  model would remove the doubt.
- **Costs are estimates** from token counts and list prices. Grading cost about $0.10 per run
  on top of the answers.

## Reproduce

```bash
just eval-retrieval                           # free; also runs in CI
just eval --model claude-haiku-5-5            # answers + grading (paid)
just eval --provider gemini --model gemini-3.5-flash-lite --workers 2
just eval --answers-from oracle               # check the grader with the reference answers
```

Each run writes `eval-runs/<time>-<model>/report.md` and `results.jsonl`, which are
git-ignored; the reports here are copies of the baseline runs.
