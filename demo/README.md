# Demo library and evaluation sets

A small document library for a fictional company, plus question and task sets with reference
answers. Use it to try DocPilot and to measure answer quality. Everything here is invented, so
it is safe to publish and reuse.

## The library

Five documents in three formats, written to make retrieval harder than one clean PDF: newer
documents supersede some of the knowledge base's figures, several passages repeat each other
almost word for word, and some facts exist in only one document.

| File | What it is |
|---|---|
| `library/aurora_knowledge_base.pdf` | 5-page knowledge base for **Aurora Instruments**, a fictional maker of home weather stations: company facts, product specs, cloud plans, warranty and an FAQ (v3.2, 2026). |
| `library/aurora_pricing_update_sep_2026.md` | Pricing update effective 1 September 2026. **Supersedes** the knowledge base's prices and plan limits (Pro $319, Max $529, Plus $59 a year and 4 stations). |
| `library/aurora_for_schools_guide.txt` | Education program terms for 2026-27: the hardware discount now starts at 3 stations (was 5), a 15% tier for 1-2 stations, and a station grant. Replaces earlier terms. |
| `library/skynode_installation_guide.pdf` | 4-page installation guide: siting, the SolarKit (Pro and Max only), the cellular data plan for the Max. Repeats several knowledge-base passages. |
| `library/skynode_firmware_release_notes.md` | Release notes, including 5 GHz Wi-Fi for Lite hardware revision B, which qualifies the knowledge base's 2.4 GHz spec. |

`tools/build_installation_guide.py` rebuilds the installation guide PDF. The live demo indexes
the whole library.

## Evaluation sets

| File | What it is |
|---|---|
| `eval_set.json` | 21 questions with reference answers, the supporting passage, source page, category and difficulty. The source of truth for evaluation. |
| `eval_set.csv` | The same questions as a flat table, for browsing (GitHub renders it). Generated from the JSON. |
| `agent_eval_set.json` | 8 research tasks for Research mode over the knowledge base alone: several facts per task, often from different pages, with conditions and arithmetic; 2 can't be answered. |
| `agent_eval_multi.json` | 10 research tasks over the whole library: answers that combine documents, conflicts where a newer document wins, and 2 the library can't answer. |
| `eval-results/` | Baseline results with per-question grades; `eval-results/agent/` has Research mode's. |
| `sample_questions.md` | A short list of questions that show retrieval, reasoning across pages, and declining to answer. |

## Try it

```bash
just migrate && just dev-api   # terminal 1
just dev-web                   # terminal 2, then open http://localhost:5173
```

Upload the files in `library/` (or just the knowledge base) and ask the questions in
[`sample_questions.md`](sample_questions.md). Each answer should cite the page it came from.

## The evaluation set

```jsonc
{
  "id": "q05",
  "question": "How much does the SkyNode Pro cost?",
  "ground_truth": "The SkyNode Pro costs $299.",
  "reference_context": "Price (USD): SkyNode Lite $149, SkyNode Pro $299, SkyNode Max $499.",
  "source_page": 2,          // null when the answer isn't in the document
  "also_on_pages": [5],      // optional: other pages that state the same evidence
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

Run it with `just eval-retrieval` (free) or `just eval` (answers graded by Claude), and the
research tasks with `just eval-agent`. Baseline
results are in [`eval-results/`](eval-results/).

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
