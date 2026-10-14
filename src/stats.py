"""Dataset statistics + tokenizer fertility.

Run: uv run python src/stats.py   (after src/data.py)
Writes to results/stats/: dataset_stats.csv, fertility.csv, fertility.png

Fertility = subword tokens per word (punctuation removed). Higher = the model's vocabulary fits the
language worse. IndicTrans2 is gated on Hugging Face (needs `hf auth login` + accepted terms); its
remote tokenizer code breaks on transformers 5, so its target-side SentencePiece model is used directly.
"""
import json

import matplotlib
import pandas as pd
import sentencepiece as spm
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer

from data import LANGS, NAMES, ROOT, read_clean, words

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = ROOT / "results" / "stats"
IT2_REPO = "ai4bharat/indictrans2-en-indic-dist-200M"


class IndicTrans2Target:
    """IndicTrans2 Indic-side tokenizer: raw SentencePiece + the model's dict (pieces not in it = <unk>)."""
    unk_token = "<unk>"

    def __init__(self, repo: str = IT2_REPO):
        self.sp = spm.SentencePieceProcessor(model_file=hf_hub_download(repo, "model.TGT"))
        self.vocab = set(json.load(open(hf_hub_download(repo, "dict.TGT.json"), encoding="utf-8")))

    def tokenize(self, w: str) -> list[str]:
        return [p if p in self.vocab else self.unk_token for p in self.sp.encode(w, out_type=str)]


TOKENIZERS = {
    "NLLB-200": lambda: AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M"),
    "IndicTrans2": IndicTrans2Target,
}


def dataset_stats(df: pd.DataFrame) -> pd.DataFrame:
    train, test = df[df.split == "train"], df[df.split == "test"]
    rows = {}
    for c in LANGS:
        toks = [w for t in df[c] for w in words(t)]
        per_verse = df[c].map(lambda t: len(words(t)))
        train_vocab = {w for t in train[c] for w in words(t)}
        test_toks = [w for t in test[c] for w in words(t)]
        counts = pd.Series(toks).value_counts()
        rows[NAMES[c]] = {
            "verses": len(df),
            "tokens": len(toks),
            "types": len(counts),
            "TTR %": 100 * len(counts) / len(toks),
            "hapax % of types": 100 * (counts == 1).mean(),
            "words/verse mean": per_verse.mean(),
            "words/verse median": per_verse.median(),
            "chars/word": sum(map(len, toks)) / len(toks),
            "test OOV % tokens": 100 * sum(w not in train_vocab for w in test_toks) / len(test_toks),
            "test OOV % types": 100 * len(set(test_toks) - train_vocab) / len(set(test_toks)),
        }
    return pd.DataFrame(rows).T


def fertility(df: pd.DataFrame, tok) -> dict[str, float]:
    out = {}
    for c in LANGS:
        ws = [w for t in df[c] for w in words(t)]
        pieces = [len(tok.tokenize(w)) for w in ws]
        out[NAMES[c]] = {
            "tokens/word": sum(pieces) / len(ws),
            "% words kept whole": 100 * sum(p == 1 for p in pieces) / len(ws),
            "% words in 3+ pieces": 100 * sum(p >= 3 for p in pieces) / len(ws),
            "% unk": 100 * sum(tok.unk_token in tok.tokenize(w) for w in ws) / len(ws),
        }
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = read_clean()
    stats = dataset_stats(df)
    stats.round(2).to_csv(OUT / "dataset_stats.csv")
    print(stats.round(2).T.to_string(), "\n")

    rows = []
    for name, load in TOKENIZERS.items():
        for lang, m in fertility(df, load()).items():
            rows.append({"tokenizer": name, "language": lang, **m})
    fert = pd.DataFrame(rows)
    fert.round(2).to_csv(OUT / "fertility.csv", index=False)
    print(fert.round(2).to_string(index=False))

    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    piv = fert.pivot(index="language", columns="tokenizer", values="tokens/word").loc[[NAMES[c] for c in LANGS]]
    x, w = range(len(piv)), 0.38
    for k, (name, color) in enumerate(zip(TOKENIZERS, ["#3b6ea8", "#d08a2c"])):
        bars = ax.bar([i + (k - 0.5) * w for i in x], piv[name], w, color=color, label=name)
        ax.bar_label(bars, fmt="%.2f", fontsize=8)
    ax.set_xticks(list(x), piv.index)
    ax.set_ylabel("subword tokens per word")
    ax.set_title("Tokenizer fertility (lower = better fit)")
    ax.set_ylim(0, piv.values.max() * 1.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fertility.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    toy = pd.DataFrame({c: ["एक दो।", "तीन"] for c in LANGS} | {"split": ["train", "test"]})
    s = dataset_stats(toy)
    assert s.loc["Hindi", "tokens"] == 3 and s.loc["Hindi", "test OOV % tokens"] == 100
    main()
