"""Part A: how similar are Hindi, Mandyali, Bilaspuri and Kangri?

Run: uv run python src/analysis.py   (after src/data.py)
Writes to results/analysis/: chrf_matrix.csv, chrf_heatmap.png, shared_vocab.csv, typical_words.md
Uses all clean verses (descriptive statistics, no model is trained here).
"""
import math
from collections import Counter
from pathlib import Path

import matplotlib
import pandas as pd
from sacrebleu.metrics import CHRF

from data import LANGS, NAMES, ROOT, read_clean, words

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = ROOT / "results" / "analysis"



def chrf_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Corpus chrF of language a (as hypothesis) against language b (as reference), averaged both ways."""
    chrf = CHRF()
    m = pd.DataFrame(100.0, index=LANGS, columns=LANGS)
    for i, a in enumerate(LANGS):
        for b in LANGS[i + 1:]:
            ab = chrf.corpus_score(df[a].tolist(), [df[b].tolist()]).score
            ba = chrf.corpus_score(df[b].tolist(), [df[a].tolist()]).score
            m.loc[a, b] = m.loc[b, a] = (ab + ba) / 2
    return m.rename(index=NAMES, columns=NAMES)


def heatmap(m: pd.DataFrame, path: Path, title: str, fmt: str = "{:.1f}") -> None:
    fig, ax = plt.subplots(figsize=(5, 4.2))
    im = ax.imshow(m.values, cmap="Blues", vmin=0, vmax=100)
    ax.set_xticks(range(len(m)), m.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(m)), m.index)
    for i in range(len(m)):
        for j in range(len(m)):
            v = m.values[i, j]
            ax.text(j, i, fmt.format(v), ha="center", va="center", color="white" if v > 60 else "black")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def shared_vocab(counts: dict[str, Counter]) -> pd.DataFrame:
    """Row a, column b: % of b's word tokens whose word type also occurs in a."""
    m = pd.DataFrame(100.0, index=LANGS, columns=LANGS)
    for a in LANGS:
        for b in LANGS:
            if a != b:
                m.loc[a, b] = 100 * sum(n for w, n in counts[b].items() if w in counts[a]) / sum(counts[b].values())
    return m.rename(index=NAMES, columns=NAMES)


def log_odds(target: Counter, ref: Counter, prior: Counter, min_count: int = 20) -> pd.DataFrame:
    """Weighted log-odds ratio with an informative Dirichlet prior (Monroe et al. 2008), as z-scores."""
    n_t, n_r, a0 = sum(target.values()), sum(ref.values()), sum(prior.values())
    rows = []
    for w, yt in target.items():
        if yt < min_count:
            continue
        aw, yr = prior[w], ref[w]
        d = math.log((yt + aw) / (n_t + a0 - yt - aw)) - math.log((yr + aw) / (n_r + a0 - yr - aw))
        rows.append((w, yt, yr, d / math.sqrt(1 / (yt + aw) + 1 / (yr + aw))))
    return pd.DataFrame(rows, columns=["word", "count", "count_hin", "z"]).sort_values("z", ascending=False)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = read_clean()

    m = chrf_matrix(df)
    m.round(1).to_csv(OUT / "chrf_matrix.csv")
    heatmap(m, OUT / "chrf_heatmap.png", "chrF between aligned verses")

    counts = {c: Counter(w for t in df[c] for w in words(t)) for c in LANGS}
    v = shared_vocab(counts)
    v.round(1).to_csv(OUT / "shared_vocab.csv")
    heatmap(v, OUT / "shared_vocab_heatmap.png", "% of column's words found in row's vocabulary")

    prior = sum(counts.values(), Counter())
    lines = ["# Typical words vs Hindi", "",
             "Top words by weighted log-odds (Monroe et al. 2008), min count 20, all clean verses.", ""]
    for c in LANGS[1:]:
        top = log_odds(counts[c], counts["hin"], prior).head(20)
        lines += [f"## {NAMES[c]} (`{c}`)", "", "| word | count | count in Hindi | z |", "|---|---|---|---|"]
        lines += [f"| {r.word} | {r.count} | {r.count_hin} | {r.z:.1f} |" for r in top.itertuples()]
        lines.append("")
    (OUT / "typical_words.md").write_text("\n".join(lines), encoding="utf-8")

    vocab = pd.Series({NAMES[c]: len(counts[c]) for c in LANGS}, name="word types")
    vocab.to_csv(OUT / "vocab_size.csv")
    print("chrF (symmetric):\n", m.round(1), "\n\nshared vocab % (row vocab covers column tokens):\n",
          v.round(1), "\n\n", vocab, sep="")


if __name__ == "__main__":
    assert words("हे भाईयो, हऊँ!") == ["हे", "भाईयो", "हऊँ"]
    main()
