"""Standard retrieval metrics, matching BEIR's definitions (pytrec_eval): linear gain for nDCG,
and recall over the documents judged relevant (score > 0)."""

import math
from collections.abc import Mapping, Sequence


def ndcg_at_k(ranked: Sequence[str], judged: Mapping[str, int], k: int) -> float:
    """Normalized discounted cumulative gain of the top k, with gain = relevance score."""
    dcg = sum(judged.get(doc, 0) / math.log2(i + 2) for i, doc in enumerate(ranked[:k]))
    ideal = sorted((score for score in judged.values() if score > 0), reverse=True)[:k]
    idcg = sum(score / math.log2(i + 2) for i, score in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def recall_at_k(ranked: Sequence[str], judged: Mapping[str, int], k: int) -> float:
    """Share of the relevant documents found in the top k."""
    relevant = {doc for doc, score in judged.items() if score > 0}
    if not relevant:
        return 0.0
    return len(relevant.intersection(ranked[:k])) / len(relevant)


def reciprocal_rank(ranked: Sequence[str], judged: Mapping[str, int], k: int = 100) -> float:
    """1 / rank of the first relevant document in the top k, or 0."""
    for i, doc in enumerate(ranked[:k]):
        if judged.get(doc, 0) > 0:
            return 1 / (i + 1)
    return 0.0


def percentile(values: Sequence[float], p: float) -> float:
    """The p-th percentile (0-100) by linear interpolation, as numpy computes it by default."""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * p / 100
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)
