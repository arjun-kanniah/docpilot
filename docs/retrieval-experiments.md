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

**Machine:** Intel Core i7-8750H (2018, 6 cores), Postgres 18 + pgvector in Docker.

**Reproduce:** `just bench --dataset nfcorpus --experiment E0` (add `--pipeline` for later
experiments). The first run downloads and indexes the dataset; later runs reuse the index.

## Results

nDCG@10 per pipeline and dataset (higher is better). Each experiment's details are below.

| # | Pipeline | NFCorpus | SciFact | FiQA | p50 latency (NFCorpus) |
|---|---|---|---|---|---|
| E0 | Vector search (today) | 0.350 | 0.718 | 0.379 | 49 ms |

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
- **Latency doesn't grow with the library:** 57,638 documents answered in 35 ms median, no
  slower than 3,633 (49 ms on NFCorpus, whose run was the first of the three; E5 times the
  search and the question's embedding separately).
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
