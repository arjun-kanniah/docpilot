# Retrieval experiments

DocPilot's demo library is five documents, and every model finds the right page for every
question, so it can't show whether retrieval holds up on a real library. These experiments use
public benchmarks of 3,600 to 57,000 documents with human relevance judgments, change one thing
at a time, and keep every result, including the ones that didn't help.

## Setup

**Datasets** (from [BEIR](https://github.com/beir-cellar/beir), test splits; each is tagged
CC BY-SA 4.0 on Hugging Face). They are downloaded at run time and never committed; only the
metrics below are.

| Dataset | Documents | Test queries | What it is |
|---|---|---|---|
| [NFCorpus](https://huggingface.co/datasets/BeIR/nfcorpus) | 3,633 | 323 | Medical articles, questions in plain language |
| [SciFact](https://huggingface.co/datasets/BeIR/scifact) | 5,183 | 300 | Scientific claims against paper abstracts |
| [FiQA-2018](https://huggingface.co/datasets/BeIR/fiqa) | 57,638 | 648 | Personal-finance questions and community answers |

**What runs:** each document is chunked and embedded exactly as an upload is (1,000-character
chunks, 150 overlap, `BAAI/bge-small-en-v1.5`), stored in Postgres + pgvector with the app's
HNSW index, and queried through the app's own search function. Documents are ranked by their
best chunk.

**Metrics:**

- **nDCG@10:** the quality of the top 10, rewarding relevant documents near the top (BEIR's
  headline metric, 0 to 1).
- **Recall@k:** the share of relevant documents found in the top k. Recall@50 is what a reranker
  could work with.
- **MRR@10:** how high the first relevant document lands.
- **Latency:** per query (embedding the question plus the search), on **one CPU core**, like
  the demo's 1-vCPU Cloud Run instance, against a local database. The demo adds the network hop
  to its database.

**Machine:** Intel Core i7-8750H (2018, 6 cores), Postgres 17.11 + pgvector 0.8.7 in Docker.

**Reproduce:** `just bench --dataset nfcorpus --experiment E0` (add `--pipeline` for later
experiments). The first run downloads and indexes the dataset; later runs reuse the index.

**Is a difference real?** `just bench-compare BASELINE.json CANDIDATE.json` compares two runs
query by query: a 95% interval for the change in nDCG@10 (paired bootstrap, 10,000 resamples)
and a p-value (paired randomization test). A change whose interval includes zero is reported
as no difference, however it looks in the table.

## Results

nDCG@10 per pipeline and dataset (higher is better). Each experiment's details are below.

| # | Pipeline | NFCorpus | SciFact | FiQA | p50 latency (FiQA) |
|---|---|---|---|---|---|
| E0 | Vector search (today) | 0.349 | 0.718 | 0.379 | 37 ms |
| E1 | Keyword search (Postgres full-text) | 0.303 | 0.582 | 0.186 | 221 ms |
| E1 | *Reference: BM25 (in memory)* | *0.311* | *0.667* | *0.238* | *1 ms* |
| E2 | Hybrid: vector + Postgres keyword | 0.354 | 0.699 | **0.320** | 252 ms |
| E2 | *Reference: hybrid with BM25* | ***0.363*** | *0.728* | ***0.349*** | *43 ms* |

Bold: a significant difference from vector search (95% interval excludes zero). Italic: bench
only, not available in the app. E0's row is the re-run after the keyword migration, which
rebuilt the vector index (0.350 before on NFCorpus; the rest unchanged).

**So far, vector search alone stays the default.** Hybrid search with Postgres's own ranking
doesn't beat it on any dataset and is 7× slower on the largest. Even with a proper BM25 ranking,
hybrid gains 0.01 to 0.014 on two datasets (significant on one) and loses 0.03 on FiQA.

## E0: baseline, vector search

Today's pipeline, unchanged.

| Dataset | nDCG@10 | Recall@20 | Recall@50 | Recall@100 | MRR@10 | p50 / p95 latency | Index |
|---|---|---|---|---|---|---|---|
| NFCorpus | 0.350 | 0.203 | 0.259 | 0.303 | 0.560 | 49 / 73 ms | 9,231 chunks, 39 MB |
| SciFact | 0.718 | 0.879 | 0.934 | 0.957 | 0.684 | 37 / 69 ms | 12,711 chunks, 54 MB |
| FiQA | 0.379 | 0.506 | 0.598 | 0.669 | 0.461 | 35 / 41 ms | 76,671 chunks, 325 MB |

Raw results, with each query's score for paired comparisons later: [`bench/`](bench/).

- **The harness checks out against the published scores.** The
  [model card](https://huggingface.co/BAAI/bge-small-en-v1.5) lists MTEB nDCG@10 of 0.343 on
  NFCorpus, 0.713 on SciFact and 0.403 on FiQA. DocPilot's pipeline is within 0.01 on the first
  two. It is 0.024 lower on FiQA, the largest corpus. Chunking is an unlikely cause, since
  FiQA's documents are short (1.3 chunks each, against NFCorpus's 2.5, where the scores
  match); the likelier one is the approximate HNSW index, which matters more as the index
  grows. E5 compares it with exact search.
- **Latency doesn't grow with the library:** 57,638 documents answered in 35 ms median, about
  the same as 3,633 and 5,183. (NFCorpus first measured 49 ms; its re-run in E2 gave 29 ms, so
  that was a first-run effect, not the dataset. E5 times the search and the question's
  embedding separately.)
- **NFCorpus recall is low for every method:** its queries have a median of 16 judged
  documents (mean 38), against 1 for SciFact and 2 for FiQA, so even a perfect top 20 can't
  hold them all. Compare pipelines on it, not against
  other datasets.
- **pgvector returns at most `hnsw.ef_search` rows per index scan (40 by default).** The app
  asks for 6 passages, well inside that, but the benchmark asks for 150, so it raises
  `ef_search` to 200. Anyone raising DocPilot's `top_k` past 40 would hit this silently.
- **Indexing speed:** about 11 chunks a second on this CPU, so FiQA took 1 h 51 min. It's a
  one-time cost per dataset. Embedding in batches of 16 instead
  of fastembed's default 256 made it about 65% faster, since each batch is padded to its
  longest text; the app now does the same for uploads.

## E1: keyword search alone

Postgres full-text search: a generated `tsvector` column (English stemming and stop words) with
a GIN index, filled in by the migration from text already stored, so nothing was re-embedded.
A passage matches if it contains **any** of the question's words, ranked by `ts_rank`. Postgres's
own parsers require every word, which finds almost nothing for a question in plain language.

To see what Postgres's ranking costs, the bench also ranks the same chunks with BM25
([bm25s](https://github.com/xhluca/bm25s), k1 = 1.2, b = 0.75, Snowball stemmer), which weighs
each word by how rare it is in the library. `ts_rank` doesn't.

| Dataset | Postgres nDCG@10 | BM25 nDCG@10 | BM25 vs Postgres | BEIR's BM25 | Postgres p50 / p95 |
|---|---|---|---|---|---|
| NFCorpus | 0.303 | 0.311 | +0.008 (−0.007 to +0.021), not significant | 0.325 | 29 / 51 ms |
| SciFact | 0.582 | 0.667 | +0.085 (+0.057 to +0.114) | 0.665 | 58 / 92 ms |
| FiQA | 0.186 | 0.238 | +0.052 (+0.035 to +0.069) | 0.236 | 221 / 367 ms |

BEIR's BM25 numbers are from the [BEIR paper](https://arxiv.org/abs/2104.08663) (Elasticsearch,
whole documents rather than chunks).

- **The BM25 reference checks out:** within 0.003 of BEIR's published BM25 on SciFact and
  FiQA. NFCorpus is 0.014 lower, plausibly because BEIR ranks whole documents and this ranks
  chunks.
- **Keywords alone lose to vector search everywhere**, significantly (−0.05 to −0.19 nDCG@10
  for Postgres, −0.04 to −0.14 for BM25). bge-small is a stronger retriever than BM25 on all
  three datasets.
- **Postgres's ranking gives up 0.05 to 0.085 to BM25** where the gap is measurable. It counts
  how often a word appears but not how rare the word is, so a passage repeating a common word
  can outrank one with the rare word that matters.
- **Any-word matching gets slow as the library grows.** On FiQA, "What is the best way to save
  money for retirement?" matches 32,230 of 76,671 chunks (42%), and Postgres reads and ranks all
  of them to return the top 150: 149 ms in `EXPLAIN ANALYZE`. The GIN index finds the matches
  in 7 ms; fetching the 32,230 rows (88 ms) and ranking them is the cost. The index itself is small
  (20 MB on FiQA).

## E2: hybrid search (Reciprocal Rank Fusion)

Vector search and keyword search each return their top passages, and the two lists are merged
with [Reciprocal Rank Fusion](https://dl.acm.org/doi/10.1145/1571941.1572114): a passage
scores 1 / (60 + rank) in each list it appears in. This needs no score calibration between the
two methods, which is why it's the common default. The bench takes 150 passages from each list;
the app takes 40.

| Dataset | Pipeline | nDCG@10 | vs vector (95% interval) | Better / worse queries | R@50 | p50 / p95 |
|---|---|---|---|---|---|---|
| NFCorpus | Hybrid | 0.354 | +0.005 (−0.009 to +0.019) | 110 / 92 | 0.264 | 49 / 78 ms |
| NFCorpus | Hybrid, BM25 | 0.363 | **+0.014 (+0.001 to +0.026)** | 112 / 85 | 0.269 | 30 / 40 ms |
| SciFact | Hybrid | 0.699 | −0.019 (−0.046 to +0.006) | 49 / 55 | 0.938 | 77 / 113 ms |
| SciFact | Hybrid, BM25 | 0.728 | +0.010 (−0.013 to +0.032) | 51 / 36 | 0.943 | 39 / 51 ms |
| FiQA | Hybrid | 0.320 | **−0.060 (−0.078 to −0.041)** | 126 / 222 | 0.586 | 252 / 397 ms |
| FiQA | Hybrid, BM25 | 0.349 | **−0.030 (−0.046 to −0.014)** | 142 / 192 | 0.610 | 43 / 70 ms |

The latency of "Hybrid, BM25" counts BM25 in memory (about 1 ms), so it is a lower bound, not
what a Postgres BM25 would take.

- **Hybrid with Postgres's ranking isn't worth it here:** no significant gain anywhere, a
  significant loss on FiQA, and 7× the latency on the largest library.
- **With BM25, hybrid helps a little where keywords are competitive** (NFCorpus, SciFact:
  keywords within 0.04 to 0.05 of vector) and **hurts where they aren't** (FiQA: 0.14 behind).
  RRF weighs both lists equally, so a much weaker list pulls good passages down.
- **Recall@50 holds up better than nDCG@10.** On FiQA, hybrid with BM25 finds more of the
  relevant documents in the top 50 than vector alone (0.610 vs 0.598) while ranking the top 10
  worse. A reranker (E3) works from the top 50, so the wider net may pay off there.
- **Why the usual advice doesn't hold:** hybrid search is usually recommended because keyword
  search catches exact terms, names and codes that embeddings miss. These datasets are mostly
  questions in plain language, where a good embedding model already does better. A library of
  part numbers, error codes or legal citations may differ; DocPilot's tests check that keyword
  search finds `SKU-4471`, but no dataset here measures it.
- **The demo library doesn't regress either way:** with hybrid on, the expected page is still
  in the top 6 for all of DocPilot's own eval questions (`just eval-retrieval`), as with vector.

**What ships:** `DOCPILOT_RETRIEVAL=hybrid` is available (with the keyword column and index
from migration 0002) for libraries where exact terms matter, and the default stays `vector`.
Options not tried yet:

- Rank keywords with BM25 inside Postgres, through an extension that provides it, if the
  hosted database offers one.
- Weight the two lists differently (tune on BEIR's dev splits, not these test sets).
- Use keyword search only for queries that look like codes or names.

E3 tests whether a reranker over the top 50 makes this moot.
