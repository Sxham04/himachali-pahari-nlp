"""Clean the Bible sheet and split it by book.

Run: uv run python src/data.py
Writes data/bible_clean.tsv (all usable verses, with a `split` column) and results/data_report.txt.
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["hin", "mjl", "kfs", "xnr"]
NAMES = {"hin": "Hindi", "mjl": "Mandyali", "kfs": "Bilaspuri", "xnr": "Kangri"}
SPLIT_BOOKS = {"test": {"JHN"}, "dev": {"ROM"}}  # everything else = train
CLEAN = ROOT / "data" / "bible_clean.tsv"

# a whole other row pasted into a cell, e.g. "...\nJHN.17.21\tकि वे सब..."
PASTED_ROW = re.compile(r"[A-Z0-9]{3}\.\d+\.\d+\s*\t")
# Hindi cross-references, e.g. "(उत्प. 19:26, उत्प. 19:17)"; the dialect texts don't have them
XREF = re.compile(r"\s*\([^()]*\d+:\d+[^()]*\)")


PUNCT = re.compile(r"[।॥,;:?!.\"“”‘’'()\[\]–—\-]")


def words(t: str) -> list[str]:
    # not \w: Python's \w does not match Devanagari vowel signs
    return PUNCT.sub(" ", t).split()


def grams(t: str) -> set[str]:
    t = " ".join(words(t))
    return {t[i:i + 3] for i in range(len(t) - 2)}


def overlap(a: set, b: set) -> float:
    return len(a & b) / (len(a | b) or 1)


def misaligned(df: pd.DataFrame, lang: str, window: int = 10, margin: float = 0.05) -> pd.Series:
    """True where `lang`'s text matches a nearby verse of the other languages better than its own row.

    Score = mean char-trigram overlap with the other three languages. Expects df sorted by
    book/chapter/verse; neighbours are compared only within the same book.
    """
    others = [c for c in LANGS if c != lang]
    g = {c: df[c].map(grams).tolist() for c in LANGS}
    book = df.book.tolist()
    bad = []
    for i in range(len(df)):
        def score(j):
            return sum(overlap(g[lang][i], g[o][j]) for o in others) / len(others)
        own = score(i)
        near = [score(j) for j in range(max(0, i - window), min(len(df), i + window + 1))
                if j != i and book[j] == book[i]]
        bad.append(bool(near) and max(near) > own + margin)
    return pd.Series(bad, index=df.index)


def clean_text(t: str) -> str:
    t = unicodedata.normalize("NFC", t)
    t = XREF.sub("", t)
    t = t.replace("­", "").replace("‌", "").replace("‍", "")
    # mjl ends sentences with Latin "l" (or "ll") instead of the danda; it would leak the label
    t = re.sub(r"(?<![A-Za-z])l{1,2}(?![A-Za-z])", "।", t)
    t = t.replace("|", "।")
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"\s+([।,;?!])", r"\1", t)


def load() -> tuple[pd.DataFrame, list[str]]:
    raw = pd.read_excel(ROOT / "bible_verse_trans.xlsx", sheet_name="bible")[["ref", *LANGS]]
    notes = [f"raw rows: {len(raw)}"]
    empty = raw[raw[LANGS].isna().any(axis=1)]
    notes.append(f"dropped {len(empty)} rows with an empty cell: {', '.join(empty.ref)}")
    df = raw.drop(empty.index).copy()
    pasted = df[df[LANGS].apply(lambda c: c.astype(str).str.contains(PASTED_ROW)).any(axis=1)]
    notes.append(f"dropped {len(pasted)} rows with other verses pasted into a cell: {', '.join(pasted.ref)}")
    df = df.drop(pasted.index)
    for c in LANGS:
        df[c] = df[c].astype(str).map(clean_text)
    parts = df.ref.str.split(".")
    df["book"] = parts.str[0]
    df = df.assign(_c=parts.str[1].astype(int), _v=parts.str[2].astype(int))
    df = df.sort_values(["book", "_c", "_v"]).drop(columns=["_c", "_v"]).reset_index(drop=True)
    short = df[df[LANGS].apply(lambda c: c.str.split().str.len() < 2).any(axis=1)]
    notes.append(f"dropped {len(short)} rows with a cell under 2 words: {', '.join(short.ref)}")
    df = df.drop(short.index).reset_index(drop=True)
    bad = pd.Series(False, index=df.index)
    for c in LANGS:
        m = misaligned(df, c)
        # a shifted block flags most of a chapter but misses a few verses: drop the whole chapter
        chap = df.ref.str.rsplit(".", n=1).str[0]
        m |= chap.isin(m.groupby(chap).mean().loc[lambda s: s >= 0.25].index)
        notes.append(f"misaligned {c}: {m.sum()} ({', '.join(df.ref[m])})")
        bad |= m
    notes.append(f"dropped {bad.sum()} rows with a misaligned cell")
    df = df[~bad]
    df["split"] = "train"
    for split, books in SPLIT_BOOKS.items():
        df.loc[df.book.isin(books), "split"] = split
    notes.append(f"kept {len(df)} verses: " + ", ".join(f"{k} {v}" for k, v in df.split.value_counts().items()))
    return df.reset_index(drop=True), notes


def read_clean() -> pd.DataFrame:
    return pd.read_csv(CLEAN, sep="\t", keep_default_na=False)


def fold_lla(t: str) -> str:
    """ऴ (U+0934, 928x in Bilaspuri) -> ळ: NLLB has no token for ऴ. Applied to MT targets and references alike."""
    return t.replace("ऴ", "ळ")


def check(df: pd.DataFrame) -> None:
    assert clean_text("आस्सा रे l") == "आस्सा रे।"
    assert words("हे भाईयो, हऊँ!") == ["हे", "भाईयो", "हऊँ"]
    assert clean_text("MAT ll ok") == "MAT। ok"  # book codes untouched
    assert df.ref.is_unique
    assert (df[LANGS] != "").all().all()
    assert not df[LANGS].apply(lambda c: c.str.contains(r"\bl\b|\t")).any().any()
    assert set(df[df.split == "test"].book) == {"JHN"} and set(df[df.split == "dev"].book) == {"ROM"}


if __name__ == "__main__":
    df, notes = load()
    check(df)
    CLEAN.parent.mkdir(exist_ok=True)
    df.to_csv(CLEAN, sep="\t", index=False)
    words = {c: df[c].str.split().str.len().mean() for c in LANGS}
    notes.append("avg words/verse: " + ", ".join(f"{c} {w:.1f}" for c, w in words.items()))
    out = ROOT / "results" / "data_report.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(notes) + "\n", encoding="utf-8")
    print("\n".join(notes))
