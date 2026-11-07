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
| E3 | Vector + best small reranker (jina-tiny, top 50) | 0.356 | 0.729 | **0.359** | 3.1 s (1 core) |
| E3 | Vector + bge-reranker-base (top 50) | **0.320** | **0.668** | **0.339** | 27 s (1 core) |
| E4 | Vector, bge-base (local, 768 dims) | **0.376** | 0.741 | not run | 89–125 ms (NFCorpus, SciFact) |
| E4 | Vector, OpenAI text-embedding-3-small (hosted) | **0.381** | 0.725 | **0.428** | 270 ms |
| E4 | Vector, OpenAI text-embedding-3-large, 1536 dims (hosted) | ***0.413*** | ***0.778*** | ***0.523*** | 276 ms |

Bold: a significant difference from vector search (95% interval excludes zero). Italic: bench
only, not available in the app. E0's row is the re-run after the keyword migration, which
rebuilt the vector index (0.350 before on NFCorpus; the rest unchanged).

**The embedding model matters more than anything added around it.** Hybrid search with
Postgres's own ranking doesn't beat bge-small vector search on any dataset and is 7× slower on
the largest. Even with a proper BM25 ranking, hybrid gains 0.01 to 0.014 on two datasets
(significant on one) and loses 0.03 on FiQA. No reranker improved it significantly anywhere,
and on one CPU core each one adds seconds per question. A better embedding model, on the
other hand, gains up to 0.144 on FiQA (OpenAI's text-embedding-3-large, +38%), significantly
on all three datasets, for about USD 1.30 to embed 57,638 documents.

**And one bug found:** a search limited to part of a large library could return few or no
passages, because of how pgvector filters its index. With 1% of FiQA allowed, 69% of questions
got nothing. One database setting fixes it (E5).

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

## E3: rerankers

A cross-encoder reads the question and each passage together and scores the pair, which is
usually more accurate than comparing embeddings made separately, and much slower: one model
pass per passage. Here it reorders vector search's top 50 chunks (`DOCPILOT_RERANKER` in the
app, which reorders the top 20 by default). Five local models, all run through fastembed:

| Reranker | Size | License (model card) | Training data (model card) |
|---|---|---|---|
| [ms-marco-MiniLM-L-6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) | 80 MB | Apache-2.0 | MS MARCO |
| [ms-marco-MiniLM-L-12-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L12-v2) | 120 MB | Apache-2.0 | MS MARCO |
| [jina-reranker-v1-tiny-en](https://huggingface.co/jinaai/jina-reranker-v1-tiny-en) | 130 MB | Apache-2.0 | Not stated (distilled from jina-reranker-v1-base) |
| [bge-reranker-base](https://huggingface.co/BAAI/bge-reranker-base) | 1.0 GB | MIT ("can be used for commercial purposes free of charge") | "multilingual pair data", not listed |
| [bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3), int8 | 570 MB | Apache-2.0 | A multilingual mixture (bge-m3-data, Quora, FEVER); unclear if it covers this model |

[MS MARCO's terms](https://microsoft.github.io/msmarco/) say the dataset is "intended for
non-commercial research purposes only", and the MiniLM models' Apache-2.0 license doesn't
address that. Check both before using these models for a client. jina-reranker-v2 was left out:
its license is non-commercial (CC BY-NC 4.0).

**Speed first**, measured on one core (like the demo's 1-vCPU instance) reranking 50 FiQA
passages (567 characters on average):

| Reranker | 50 passages, 1 core | Memory (process) |
|---|---|---|
| jina-tiny | 3.1 s | 465 MB |
| MiniLM-L6 | 3.8 s | 465 MB |
| MiniLM-L12 | 7.5 s | 502 MB |
| bge-reranker-base | 27 s | 2.0 GB |
| bge-reranker-v2-m3, int8 | 70 s | 2.0 GB |

The int8 model is slower than the full-size bge-reranker-base here, likely because this 2018 CPU
lacks the int8 instructions (VNNI) that make quantized models fast; newer server CPUs may differ.
The quality runs below used all six cores so they finished in hours (the scores don't depend
on it). Even on six cores, the median question took 1.9 s (jina-tiny) to 34 s (v2-m3).

**Quality**, nDCG@10 against vector search alone (95% interval; bold is significant):

| Reranker | NFCorpus | SciFact | FiQA |
|---|---|---|---|
| None (vector search) | 0.349 | 0.718 | 0.379 |
| MiniLM-L6 | 0.358, +0.009 (−0.006 to +0.023) | 0.712, −0.006 (−0.035 to +0.022) | 0.376, −0.003 (−0.019 to +0.012) |
| jina-tiny | 0.356, +0.006 (−0.009 to +0.022) | 0.729, +0.011 (−0.017 to +0.039) | 0.359, **−0.020 (−0.037 to −0.003)** |
| MiniLM-L12 | 0.355, +0.006 (−0.009 to +0.020) | 0.706, −0.012 (−0.040 to +0.016) | 0.372, −0.007 (−0.022 to +0.007) |
| bge-reranker-base | 0.320, **−0.030 (−0.048 to −0.012)** | 0.668, **−0.050 (−0.079 to −0.021)** | 0.339, **−0.041 (−0.057 to −0.024)** |
| bge-reranker-v2-m3, int8 (first 100 queries) | 0.373 vs 0.387, −0.014 (−0.037 to +0.009) | 0.773 vs 0.746, +0.027 (−0.017 to +0.076) | not run (≈ 6 h) |

v2-m3 ran on the first 100 queries of each dataset to keep it to two hours, so it is compared
with vector search on the same 100 queries (whose mean differs from the full set's).

- **No reranker improves on bge-small significantly, on any dataset.** The small ones are
  within ±0.012 on two datasets; the best measured gain is v2-m3's +0.027 on 100 SciFact
  queries, which isn't significant either. Reranking only reorders the top 50, so Recall@50
  can't change, and Recall@20 moved by at most 0.016 (full-set runs).
- **bge-reranker-base makes results significantly worse on all three.** This was checked
  before accepting it: on hand-made examples it scores the relevant passage highest (higher is
  better, as for the others), and its scores don't depend on batching. The model card doesn't
  say what English data it saw; it may simply be weaker on these domains than the embedder it
  is reranking.
- **Why this differs from the usual advice:** rerankers are usually shown fixing a weak first
  stage such as BM25 (FiQA 0.238 here), not a strong 2023 embedding model. Whether bge-small
  saw any of these datasets during training would matter. Its paper and model card describe
  "large-scale pairs data" without listing the sources, so that can't be ruled out. E4
  compares other embedders, which shows whether these datasets leave room above 0.38 on FiQA.
- **A side finding:** the int8 v2-m3 model's scores shift by up to 0.85 depending on what else
  is in the batch (the others don't shift at all), probably because the quantization scale is
  chosen per batch. Its rankings are slightly noisy as a result.

**What ships:** reranking is in DocPilot, off by default (`DOCPILOT_RERANKER` to turn it on).
The demo stays without it. No model gave a measurable gain, and on its single vCPU even the
fastest would add roughly 1.2 to 1.5 s to every question for 20 passages (estimated from the
50-passage times above). A client library unlike these (contracts, part numbers) could still benefit, which
is what an evaluation on the client's own documents decides.

## E4: other embedding models

E3 left a question open: is bge-small simply hard to beat on these datasets, or do they leave
room above it? E4 swaps the embedding model and nothing else (same chunks, same search code,
`--embedder` in the bench), with one larger local model and two hosted ones:

| Model | Runs | Dimensions | License / terms | List price |
|---|---|---|---|---|
| [bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) (today) | Locally, CPU | 384 | MIT | Free |
| [bge-base-en-v1.5](https://huggingface.co/BAAI/bge-base-en-v1.5) | Locally, CPU | 768 | MIT | Free |
| [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small) | OpenAI API | 1,536 | OpenAI API terms | USD 0.02 per million tokens |
| [text-embedding-3-large](https://developers.openai.com/api/docs/models/text-embedding-3-large) | OpenAI API | 1,536 (of 3,072) | OpenAI API terms | USD 0.13 per million tokens |

text-embedding-3-large is asked for 1,536 numbers instead of its full 3,072, because pgvector
can't build an HNSW index on a `vector` column over 2,000 dimensions; OpenAI's API shortens it
without retraining. bge-base ran on NFCorpus and SciFact only: indexing on this CPU took 41 and
59 minutes, so FiQA would take about 5 hours.

**Quality**, nDCG@10 against bge-small (95% interval; bold is significant):

| Model | NFCorpus | SciFact | FiQA |
|---|---|---|---|
| bge-small (today) | 0.349 | 0.718 | 0.379 |
| bge-base | 0.376, **+0.027 (+0.014 to +0.041)** | 0.741, +0.023 (+0.000 to +0.046), p = 0.06 | not run |
| text-embedding-3-small | 0.381, **+0.031 (+0.011 to +0.052)** | 0.725, +0.007 (−0.020 to +0.033) | 0.428, **+0.048 (+0.029 to +0.067)** |
| text-embedding-3-large | 0.413, **+0.064 (+0.044 to +0.085)** | 0.778, **+0.060 (+0.034 to +0.088)** | 0.523, **+0.144 (+0.123 to +0.165)** |

**Cost and speed:**

| Model | Embed all three datasets (13.2M tokens) | FiQA query p50 / p95 | FiQA chunks table |
|---|---|---|---|
| bge-small | Free; FiQA took 1 h 51 min on this CPU | 37 / 41 ms | 325 MB |
| bge-base | Free; ~3.5× slower than bge-small | 89–125 ms (NFCorpus, SciFact) | 88 MB for NFCorpus (39 MB with bge-small) |
| text-embedding-3-small | USD 0.26 (13 min for FiQA) | 270 / 343 ms | 1,326 MB |
| text-embedding-3-large | USD 1.71 (13 min for FiQA) | 276 / 351 ms | 1,326 MB |

Costs are what the API reported in tokens, times the list price; all 2,542 test queries cost
under a cent more. Hosted latency is almost all the network round trip to OpenAI from this
machine (Alberta), and would be similar from the demo's Cloud Run region.

- **The datasets do leave room, and the embedder is where it is.** text-embedding-3-large
  beats bge-small significantly on all three datasets, by +0.06 to +0.144, far more than any
  hybrid or reranker result, and on FiQA, where those lost, it gains 38%. Recall@50
  on FiQA rises from 0.598 to 0.763, so a reranker or an LLM would also get more to work with.
- **Size isn't everything:** text-embedding-3-small, the cheaper hosted model, is no better
  than bge-small on SciFact (+0.007, not significant) and only modestly better on the other
  two. bge-base, free and local, matches it on NFCorpus.
- **What a hosted embedder costs a client** is not mainly the bill: USD 1.30 for 57,638
  documents is trivial. It's that every document and every question goes to the provider, the
  library must be re-embedded to change models, each question waits a network round trip
  (about 250 ms more here), and vectors four times the size take four times the storage.
- **The same caveat applies to every model here:** none of them lists its full training data,
  so none can be shown to have not seen these datasets. The comparison is still fair in the
  sense that matters to a client: these are the scores each model gets on public data it may or
  may not have seen, through the same pipeline.

**What ships:** decided in Phase 5, with the HNSW and filter results from E5. The options are
bge-base (free, local, ~3× slower queries, re-embed the library) or a hosted model as a setting
for clients whose documents may go to the provider. The bench reproduces any row:
`just bench --dataset fiqa --embedder openai-large --experiment E4` (needs `OPENAI_API_KEY`).


## E5: the HNSW index, and searching part of a library

### Exact search vs the index

E0 found DocPilot 0.024 below bge-small's published score on FiQA and suspected the
approximate HNSW index. E5 turns the index off (`--exact`: every chunk compared with the
question) and also tries a wider index search (`--ef-search 400`; the bench's runs use 200).

| Dataset | HNSW (ef_search 200) | Exact | Exact vs HNSW | Exact p50 / p95 | HNSW p50 |
|---|---|---|---|---|---|
| NFCorpus | 0.349 | 0.350 | +0.000 (−0.000 to +0.001) | 48 / 60 ms | 29 ms |
| SciFact | 0.718 | 0.718 | identical on every query | 64 / 96 ms | 37 ms |
| FiQA | 0.379 | 0.385 | +0.005 (+0.001 to +0.011), p = 0.06; better on 5 of 648, worse on none | 161 / 207 ms | 37 ms |

ef_search 400 on FiQA: 0.382 (+0.003, not significant), 38 ms.

- **The index costs almost nothing in quality** at these sizes, and at 57,638 documents it is
  4× faster than comparing every chunk. Exact search changed 5 of 648 FiQA questions.
- **So it doesn't explain E0's FiQA gap:** at most 0.006 of the 0.024. The rest likely comes
  from how documents are scored here (by their best chunk) and other setup differences from
  the published evaluation, not from anything that varies between DocPilot's own runs.

### The filter problem

A chat limited to some documents searches with a `document_id IN (...)` filter, and per-user
access control would work the same way. pgvector's HNSW index finds the 40 nearest chunks
(`hnsw.ef_search`) and only then applies the filter. When the allowed documents are a small
share of the library, few of those 40 pass.

`python -m docpilot.bench.filters` runs every test question against a fixed random subset of
the library (as if that's all a user may read), asks for 6 passages as the app does, and
compares the app's search with the exact answer (index off).

FiQA, 57,638 documents, one core:

| Documents allowed | pgvector defaults (the app before this) | | | With iterative scan (the app now) | | Exact |
|---|---|---|---|---|---|---|
| | Passages returned (of 6) | Questions with none | Recall vs exact | Passages returned | Recall vs exact | p50 |
| All 57,638 | 6.00 | 0% | 0.953 | 6.00 | 0.953 | 147 ms |
| 10% (5,764) | 3.88 | 2% | 0.627 | 6.00 | 0.887 | 85 ms |
| 1% (576) | **0.39** | **69%** | 0.065 | 6.00 | 0.917 | 19 ms |
| 0.1% (58) | 6.00 | 0% | 1.000 | 6.00 | 1.000 | 3 ms |

The iterative scan's p50 is 45 ms at 10% and 19 ms at 1% (3.5 ms unfiltered). NFCorpus and
SciFact show the same pattern at 10% (75 to 79% of questions got fewer than 6 passages, about
3.5 on average, 6 to 7% got none), and the iterative scan fixes them the same way (recall vs
exact 0.86 and 0.93). Results: [`bench/E5-filters-*.json`](bench/).

- **This was a real bug in DocPilot.** With 1% of a 57,638-document library allowed, 69% of
  questions retrieved nothing, and the model would have said the documents don't cover it.
  The five-document demo can't show it, and nothing errors: the search just returns less.
- **It's narrow-but-not-tiny filters that fail.** At 0.1%, Postgres's planner skips the HNSW
  index on its own (comparing the ~80 allowed chunks directly is cheaper) and searches exactly, which
  is correct and fast. Between roughly 1% and 10% it uses the index, and the index runs out.
- **The fix is one setting.** pgvector 0.8 can keep scanning the index until it has enough rows
  (`hnsw.iterative_scan`; `strict_order` keeps them in exact distance order). The app turns it
  on for filtered searches only, per transaction (`SET LOCAL`). It was first a database default
  set by a migration, but Neon doesn't let the app's role set this parameter for a database;
  the deploy's migration step caught that before anything changed. Migration 0003 now only
  checks that the setting exists, so a database with an older pgvector fails the migration
  (which runs before every deploy) rather than the app's searches.
- **Iterative isn't exact:** 0.89 to 0.92 of the exact top 6 on FiQA. For a narrow filter where
  that matters, exact search is cheap (19 ms at 1%); for stricter needs, partial indexes per
  tenant or partitioning are the usual next steps.

**What ships:** the iterative scan for filtered searches (`retrieval.py`), and migration 0003's
pgvector check. DocPilot's chats and Research mode use the document filter
today, and access control would use the same one.
