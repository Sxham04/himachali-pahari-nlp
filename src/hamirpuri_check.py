"""Where does Hamirpuri sit? Run the Part B dialect identifier on MA's Hamirpuri sentences.

The classifier (char 1-4-gram TF-IDF + logistic regression, C=10, Bible train books) only knows
Hindi / Mandyali / Bilaspuri / Kangri, so each Hamirpuri sentence is assigned to the closest one.
Control: the Hindi prompts of the same sentences should come out as Hindi.
Only aggregate counts are written (no sentences: family data stays private).

Run: uv run python src/hamirpuri_check.py
Writes to results/hamirpuri_check/: summary.csv, by_batch.csv, shares.png, function_words.csv
"""
from collections import Counter

import matplotlib
import numpy as np
import pandas as pd

from data import LANGS, NAMES, ROOT, clean_text, read_clean, words
from dialect_id import long_form, model

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = ROOT / "results" / "hamirpuri_check"
XLSX = ROOT / "pahari translaton.xlsx"
# function words that separate the varieties: of / and / in / not / we / you / to / from / is
FUNCTION_WORDS = ["दा", "दे", "दी", "रा", "रे", "री", "का", "के", "की", "कने", "होर", "और", "च", "बिच",
                  "मन्झ", "में", "नी", "नहीं", "असां", "अहां", "तुसां", "तुहां", "जो", "को", "ते", "से", "है", "ऐ", "आ"]


def function_word_rates(ham_texts, df: pd.DataFrame) -> pd.DataFrame:
    """Occurrences per 1,000 word tokens, Hamirpuri vs each Bible language."""
    counts = {"Hamirpuri": Counter(w for t in ham_texts for w in words(clean_text(t)))}
    counts |= {NAMES[c]: Counter(w for t in df[c] for w in words(t)) for c in LANGS}
    return pd.DataFrame({k: {w: 1000 * v[w] / sum(v.values()) for w in FUNCTION_WORDS} for k, v in counts.items()}).round(1)


def final_translations(responses: pd.DataFrame) -> pd.DataFrame:
    """One row per num: latest response; text = last non-empty `corrected` for that num, else latest `text`."""
    r = responses.sort_values("timestamp")
    latest = r.groupby("num").tail(1).set_index("num")
    corr = r.dropna(subset=["corrected"]).groupby("num").corrected.last()
    latest["final"] = corr.reindex(latest.index).fillna(latest.text).astype(str).str.strip()
    return latest.reset_index()[["num", "hindi", "final"]]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = read_clean()
    X, y = long_form(df[df.split == "train"])
    clf = model(10).fit(X, y)

    ham = final_translations(pd.read_excel(XLSX, sheet_name="responses"))
    ham = ham[ham.final.map(lambda t: len(words(clean_text(t))) > 0)]
    rows, shares = [], {}
    for name, texts in [("Hamirpuri (MA, proof-read)", ham.final), ("Hindi prompts (control)", ham.hindi)]:
        t = [clean_text(s) for s in texts]
        pred = clf.predict(t)
        prob = clf.predict_proba(t)
        share = pd.Series(pred).value_counts(normalize=True).reindex(LANGS, fill_value=0) * 100
        shares[name] = share
        rows.append({"input": name, "n": len(t),
                     **{f"% {NAMES[c]}": round(share[c], 1) for c in LANGS},
                     **{f"mean p({NAMES[c]})": round(prob[:, list(clf.classes_).index(c)].mean(), 3) for c in LANGS}})
        if name.startswith("Hamirpuri"):
            ham["pred"] = pred
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "summary.csv", index=False)

    ham["batch"] = np.where(ham.num <= 200, "batch 1 (#1-200)", "batch 2 (#201-509)")
    ham["len"] = ham.final.map(lambda t: len(words(clean_text(t))))
    ham["len_bin"] = pd.cut(ham.len, [0, 4, 6, 8, 100], labels=["1-4 words", "5-6", "7-8", "9+"])
    by = pd.concat([
        pd.crosstab(ham.batch, ham.pred, normalize="index"),
        pd.crosstab(ham.len_bin, ham.pred, normalize="index"),
    ]).reindex(columns=LANGS, fill_value=0).mul(100).round(1).rename(columns=NAMES)
    by["n"] = pd.concat([ham.batch.value_counts(), ham.len_bin.value_counts()])
    by.to_csv(OUT / "by_batch.csv")
    function_word_rates(ham.final, df).to_csv(OUT / "function_words.csv", index_label="word")

    fig, ax = plt.subplots(figsize=(6, 3.4))
    names = [NAMES[c] for c in LANGS]
    w = 0.38
    for k, (label, s) in enumerate(shares.items()):
        bars = ax.bar([i + (k - 0.5) * w for i in range(4)], s.values, w, label=label)
        ax.bar_label(bars, fmt="%.0f%%", fontsize=8)
    ax.set_xticks(range(4), names)
    ax.set_ylabel("% of sentences assigned")
    ax.set_ylim(0, 110)
    ax.set_title("Which Bible language does each sentence look like?")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "shares.png", dpi=200)
    plt.close(fig)
    print(summary.to_string(index=False), "\n")
    print(by.to_string())


if __name__ == "__main__":
    toy = pd.DataFrame({"timestamp": [1, 2, 3], "num": [1, 1, 2], "hindi": ["a", "a", "b"],
                        "text": ["old", "new", "x"], "corrected": ["fix", None, None]})
    f = final_translations(toy).set_index("num").final
    assert f[1] == "fix" and f[2] == "x"  # correction on an older row still wins (#45 case)
    main()
