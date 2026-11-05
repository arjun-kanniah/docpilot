"""Is one run really better than another? A paired comparison of per-query nDCG@10.

    python -m docpilot.bench.compare BASELINE.json CANDIDATE.json [MORE.json ...]

Both runs answer the same queries, so each query's difference is what counts. The 95% interval
comes from resampling queries (paired bootstrap), and the p-value from randomly swapping each
query's two scores (a paired randomization test). A difference whose interval includes zero
is not a finding.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SEED = 2026
ROUNDS = 10_000


@dataclass(frozen=True)
class Comparison:
    queries: int
    baseline: float
    candidate: float
    difference: float
    low: float  # 95% interval for the difference
    high: float
    p_value: float  # two-sided
    better: int  # queries where the candidate scores higher
    worse: int


def compare(baseline: dict[str, float], candidate: dict[str, float]) -> Comparison:
    if baseline.keys() != candidate.keys():
        raise ValueError("The runs answered different queries")
    ids = sorted(baseline)
    a = np.array([baseline[i] for i in ids])
    b = np.array([candidate[i] for i in ids])
    diff = b - a
    rng = np.random.default_rng(SEED)

    resampled = rng.integers(0, len(diff), size=(ROUNDS, len(diff)))
    means = diff[resampled].mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])

    signs = rng.choice([-1.0, 1.0], size=(ROUNDS, len(diff)))
    swapped = np.abs((signs * diff).mean(axis=1))
    p_value = (np.sum(swapped >= abs(diff.mean()) - 1e-12) + 1) / (ROUNDS + 1)

    return Comparison(
        queries=len(diff),
        baseline=float(a.mean()),
        candidate=float(b.mean()),
        difference=float(diff.mean()),
        low=float(low),
        high=float(high),
        p_value=float(p_value),
        better=int(np.sum(diff > 1e-12)),
        worse=int(np.sum(diff < -1e-12)),
    )


def label(run: dict) -> str:
    return f"{run['pipeline']} ({run['experiment']}, {run['dataset']})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m docpilot.bench.compare", description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidates", type=Path, nargs="+")
    args = parser.parse_args(argv)

    base = json.loads(args.baseline.read_text())
    print(f"Baseline: {label(base)}, nDCG@10 {base['summary']['ndcg_at_10']:.3f}")
    for path in args.candidates:
        run = json.loads(path.read_text())
        c = compare(base["per_query_ndcg_at_10"], run["per_query_ndcg_at_10"])
        p = "p < 0.001" if c.p_value < 0.001 else f"p = {c.p_value:.3f}"
        print(
            f"  {label(run)}: {c.candidate:.3f}, {c.difference:+.3f} "
            f"(95% CI {c.low:+.3f} to {c.high:+.3f}, {p}); "
            f"better on {c.better} of {c.queries} queries, worse on {c.worse}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
