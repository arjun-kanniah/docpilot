# Demo corpus and evaluation set

A small knowledge base for a fictional company, plus a question set with reference answers.
Use it to try DocPilot and to measure answer quality. Everything here is invented, so it is
safe to publish and reuse.

| File | What it is |
|---|---|
| `aurora_knowledge_base.pdf` | 5-page knowledge base for **Aurora Instruments**, a fictional maker of home weather stations: company facts, product specs, cloud plans, warranty and an FAQ. |
| `eval_set.json` | 21 questions with reference answers, the supporting passage, source page, category and difficulty. The source of truth for evaluation. |
| `eval_set.csv` | The same questions as a flat table, for browsing (GitHub renders it). Generated from the JSON. |
| `sample_questions.md` | A short list of questions that show retrieval, reasoning across pages, and declining to answer. |

## Try it

```bash
just migrate && just dev-api   # terminal 1
just dev-web                   # terminal 2, then open http://localhost:5173
```

Upload `aurora_knowledge_base.pdf` and ask the questions in
[`sample_questions.md`](sample_questions.md). Each answer should cite the page it came from.

## The evaluation set

```jsonc
{
  "id": "q05",
  "question": "How much does the SkyNode Pro cost?",
  "ground_truth": "The SkyNode Pro costs $299.",
  "reference_context": "Price (USD): SkyNode Lite $149, SkyNode Pro $299, SkyNode Max $499.",
  "source_page": 2,          // null when the answer isn't in the document
  "category": "factual",     // factual | comparative | numeric | procedural | conditional | inference | negative
  "difficulty": "easy",      // easy | medium | hard
  "answerable": true         // false: the right response is to say the document doesn't say
}
```

It covers 19 answerable questions (direct lookups, arithmetic, conditions, facts combined from
two places, and one inference) and 2 negative questions whose answers are not in the document.
The negatives check that DocPilot declines instead of inventing an answer.

What each part measures:

- **Retrieval:** did the top passages include `source_page`? Score by page, not by matching
  `reference_context`, because several contexts are paraphrased rather than quoted.
- **Answer correctness:** does the answer agree with `ground_truth`?
- **Abstention:** for `answerable: false`, does the answer say the information isn't there?

## Limits worth knowing

- **It is small.** The PDF splits into 11 chunks, so the top 6 passages cover over half the
  document. It tests answer quality and abstention well, but not retrieval across a large
  collection.
- **It has tables.** The product and plan tables are extracted by `pypdf` as one cell per line,
  so questions like q06 (sensors in the SkyNode Max) check whether the model can still tell
  which value belongs to which column.

## Content

Aurora Instruments, its founders, products, prices and policies are invented. Any resemblance
to a real company is coincidental. The material may be reproduced, edited and extended freely.
