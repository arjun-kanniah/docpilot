"""Draws docs/retrieval-results.png from the result files in this folder.

    uv run --project backend --with matplotlib python docs/bench/chart.py

Each dot is a pipeline's change in nDCG@10 against vector search with bge-small (the
default), with its 95% interval from the same paired bootstrap as `just bench-compare`.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from docpilot.bench.compare import compare

HERE = Path(__file__).parent
DATASETS = [
    ("nfcorpus", "NFCorpus"),
    ("scifact", "SciFact"),
    ("fiqa", "FiQA (57K docs)"),
]
BASELINE = "E1E2-vector-{}.json"
# (label, time per question on one core, result file pattern), top to bottom
ROWS = [
    ("Hybrid: + Postgres keyword search", "252 ms", "E1E2-hybrid-{}.json"),
    ("Hybrid: + BM25 (reference)", "43 ms", "E1E2-hybrid_bm25-{}.json"),
    ("Reranker: jina-tiny, top 50", "3.1 s", "E3-vector+jina-tiny-50-{}.json"),
    ("Reranker: MiniLM-L6, top 50", "3.8 s", "E3-vector+minilm-l6-50-{}.json"),
    ("Reranker: bge-reranker-base, top 50", "27 s", "E3-vector+bge-base-50-{}.json"),
    ("Embedder: bge-base (local)", "~0.1 s", "E4-vector-bge-base-{}.json"),
    ("Embedder: OpenAI 3-small (hosted)", "0.27 s", "E4-vector-openai-small-{}.json"),
    ("Embedder: OpenAI 3-large (hosted)", "0.28 s", "E4-vector-openai-large-{}.json"),
]
BETTER, WORSE, SAME = "#2a78d6", "#eb6834", "#8a8984"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(name: str) -> dict | None:
    path = HERE / name
    return json.loads(path.read_text()) if path.exists() else None


def main() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, axes = plt.subplots(1, 3, figsize=(13, 5.6), sharey=True, facecolor=SURFACE)
    ys = list(range(len(ROWS)))[::-1]
    for ax, (dataset, title) in zip(axes, DATASETS, strict=True):
        base = load(BASELINE.format(dataset))
        assert base is not None
        ax.set_facecolor(SURFACE)
        ax.axvline(0, color=INK, lw=1)
        for y, (_, _, pattern) in zip(ys, ROWS, strict=True):
            run = load(pattern.format(dataset))
            if run is None:
                ax.text(
                    0.003, y, "not run", va="center", ha="left", color=MUTED, fontsize=9
                )
                continue
            c = compare(base["per_query_ndcg_at_10"], run["per_query_ndcg_at_10"])
            # significant: the interval excludes zero and the randomization test agrees
            significant = c.p_value < 0.05 and (c.low > 0 or c.high < 0)
            color, marker = (
                (SAME, "o")
                if not significant
                else (BETTER, "o")
                if c.difference > 0
                else (WORSE, "v")
            )
            ax.plot([c.low, c.high], [y, y], color=color, lw=2, solid_capstyle="round")
            ax.plot(
                c.difference,
                y,
                marker=marker,
                ms=8,
                color=color,
                markerfacecolor=color if color != SAME else SURFACE,
                markeredgewidth=2,
            )
            right = c.difference >= 0
            ax.text(
                c.high + 0.006 if right else c.low - 0.006,
                y,
                f"{c.difference:+.3f}",
                va="center",
                ha="left" if right else "right",
                color=INK if color != SAME else MUTED,
                fontsize=9,
            )
        score = base["summary"]["ndcg_at_10"]
        ax.set_title(
            f"{title}\nbaseline {score:.3f}", fontsize=11, color=INK, loc="left"
        )
        ax.set_xlim(-0.13, 0.2)
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors=MUTED, length=0)
        for side in ("top", "right", "left", "bottom"):
            ax.spines[side].set_visible(False)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels(
        [f"{label}  ·  {time}" for label, time, _ in ROWS], color=INK
    )
    legend = [
        Line2D([], [], color=BETTER, marker="o", lw=2, label="Significantly better"),
        Line2D([], [], color=WORSE, marker="v", lw=2, label="Significantly worse"),
        Line2D(
            [],
            [],
            color=SAME,
            marker="o",
            markerfacecolor=SURFACE,
            markeredgewidth=2,
            lw=2,
            label="No measurable difference",
        ),
    ]
    fig.supxlabel(
        "Change in nDCG@10 vs vector search with bge-small", color=MUTED, y=0.1
    )
    fig.legend(
        handles=legend,
        loc="lower center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.6, -0.01),
    )
    fig.suptitle(
        "What improved DocPilot's retrieval on BEIR: a better embedder, not add-ons",
        x=0.01,
        ha="left",
        fontsize=14,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.01,
        0.915,
        "Dots: mean change; lines: 95% interval (paired bootstrap). Time: per question, "
        "one CPU core (hosted: network round trip). Baseline (bge-small): 37 ms.",
        ha="left",
        color=MUTED,
        fontsize=9.5,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.92))
    out = HERE.parent / "retrieval-results.png"
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
