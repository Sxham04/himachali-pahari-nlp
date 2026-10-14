"""Part B: dialect identifier (Hindi / Mandyali / Bilaspuri / Kangri).

Char 1-4-gram TF-IDF + logistic regression. Train on the train books, pick C on dev (ROM),
score once on test (JHN): full verses, then the first k words of each test verse.
Run: uv run python src/dialect_id.py   (after src/data.py)
Writes to results/dialect_id/.
"""
import json

import matplotlib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import make_pipeline

from data import LANGS, NAMES, ROOT, read_clean, words

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = ROOT / "results" / "dialect_id"
SNIPPET_WORDS = [1, 2, 3, 5, 10]


def long_form(df: pd.DataFrame, k: int | None = None) -> tuple[list[str], list[str]]:
    """One (text, label) per verse per language; k = keep only the first k words."""
    texts, labels = [], []
    for c in LANGS:
        for t in df[c]:
            texts.append(t if k is None else " ".join(words(t)[:k]))
            labels.append(c)
    return texts, labels


def model(C: float):
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 4), sublinear_tf=True, min_df=2),
        LogisticRegression(C=C, max_iter=2000),
    )


def plot_confusion(cm: np.ndarray, path, title: str) -> None:
    pct = 100 * cm / cm.sum(axis=1, keepdims=True)
    names = [NAMES[c] for c in LANGS]
    fig, ax = plt.subplots(figsize=(5, 4.2))
    ax.imshow(pct, cmap="Blues", vmin=0, vmax=100)
    ax.set_xticks(range(4), names, rotation=30, ha="right")
    ax.set_yticks(range(4), names)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{pct[i, j]:.1f}", ha="center", va="center", color="white" if pct[i, j] > 60 else "black")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = read_clean()
    X_tr, y_tr = long_form(df[df.split == "train"])
    X_dev, y_dev = long_form(df[df.split == "dev"], k=3)  # tune on short snippets: full verses are near 100%
    test = df[df.split == "test"]

    dev_acc = {}
    for C in [0.1, 1, 10, 100]:
        dev_acc[C] = accuracy_score(y_dev, model(C).fit(X_tr, y_tr).predict(X_dev))
    best_C = max(dev_acc, key=dev_acc.get)
    clf = model(best_C).fit(X_tr, y_tr)

    rows = []
    for k in [None, *SNIPPET_WORDS]:
        X, y = long_form(test, k)
        pred = clf.predict(X)
        name = "full verse" if k is None else f"first {k} words"
        rows.append({"input": name, "accuracy": round(100 * accuracy_score(y, pred), 2),
                     **{f"acc_{c}": round(100 * accuracy_score(np.array(y)[np.array(y) == c],
                                                              pred[np.array(y) == c]), 2) for c in LANGS}})
        if k in (None, 3):
            cm = confusion_matrix(y, pred, labels=LANGS)
            tag = "full" if k is None else f"{k}w"
            pd.DataFrame(cm, index=LANGS, columns=LANGS).to_csv(OUT / f"confusion_{tag}.csv")
            plot_confusion(cm, OUT / f"confusion_{tag}.png", f"Dialect ID on John ({name}), row %")
            if k is None:
                (OUT / "report_full.txt").write_text(classification_report(y, pred, digits=4), encoding="utf-8")
    acc = pd.DataFrame(rows)
    acc.to_csv(OUT / "accuracy_by_length.csv", index=False)
    (OUT / "settings.json").write_text(json.dumps(
        {"features": "char_wb 1-4 TF-IDF, sublinear, min_df=2", "classifier": "LogisticRegression",
         "dev_acc_3_words": dev_acc, "best_C": best_C,
         "n_train": len(X_tr), "n_test_verses": len(test)}, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(5, 3.5))
    snip = acc.iloc[1:]
    ax.plot(SNIPPET_WORDS, snip.accuracy, marker="o", label="all")
    for c in LANGS:
        ax.plot(SNIPPET_WORDS, snip[f"acc_{c}"], marker=".", lw=1, alpha=0.7, label=NAMES[c])
    ax.axhline(25, ls=":", c="grey")
    ax.set_xlabel("words of input")
    ax.set_ylabel("accuracy %")
    ax.set_xscale("log")
    ax.set_xticks(SNIPPET_WORDS, SNIPPET_WORDS)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "accuracy_by_length.png", dpi=200)
    plt.close(fig)

    print(f"dev acc (3 words) by C: {dev_acc} -> C={best_C}\n")
    print(acc.to_string(index=False))


if __name__ == "__main__":
    toy = pd.DataFrame({c: ["एक दो तीन चार"] for c in LANGS})
    assert long_form(toy, 2)[0] == ["एक दो"] * 4 and long_form(toy)[1] == LANGS
    main()
