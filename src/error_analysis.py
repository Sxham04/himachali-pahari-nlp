"""Stage 2 error analysis: sample wrong test translations per language for a native speaker to label.

Run: uv run python src/error_analysis.py [--n 30]
For each language, takes the better 100%-data LoRA model on John (separate or joint, by chrF++), keeps verses whose
sentence chrF++ is below that model's median (clearly flawed, but not only the worst garbage), and draws n of them
at random (seed 0). Writes results/error_analysis/error_analysis.xlsx (git-ignored, like all xlsx): one sheet per
language with empty `category` + `explanation` columns to fill in, and a `categories` sheet with the label set.
Never overwrites an existing file, since it holds the hand-written labels.
"""
import argparse

import pandas as pd
from sacrebleu.metrics import CHRF

from data import NAMES, ROOT, fold_lla, read_clean
from evaluate import FINETUNE, TARGETS, read_lines

OUT = ROOT / "results" / "error_analysis" / "error_analysis.xlsx"
CATEGORIES = {
    "hindi_word": "Hindi word kept where the variety has its own word",
    "wrong_word": "wrong or unrelated word (meaning changed)",
    "morphology": "wrong ending: case/postposition, verb form, gender/number agreement",
    "word_order": "words right, order wrong",
    "omission": "part of the meaning left out",
    "addition": "extra words or repeated/hallucinated content",
    "name_spelling": "proper noun or spelling variant",
    "other_variety": "form from another variety (e.g. Kangri word in Bilaspuri output)",
    "valid_paraphrase": "acceptable translation, just worded differently from the reference (not an error)",
    "reference_issue": "reference itself is wrong, loose or misaligned",
}


def best_run(lang: str, test: pd.DataFrame) -> tuple[str, list[str]]:
    """(run name, hyps) of the better 100%-data LoRA model for lang."""
    refs = [[fold_lla(t) for t in test[lang]]]
    runs = {run: read_lines(FINETUNE / run / f"{lang}.txt", len(test)) for run in (lang, "joint")}
    return max(runs.items(), key=lambda kv: CHRF(word_order=2).corpus_score([fold_lla(h) for h in kv[1]], refs).score)


def sample(test: pd.DataFrame, lang: str, hyps: list[str], n: int) -> pd.DataFrame:
    chrf = CHRF(word_order=2)
    df = pd.DataFrame({"ref": test.ref, "hindi": test.hin, "reference": test[lang], "output": hyps})
    df["chrF++"] = [round(chrf.sentence_score(fold_lla(h), [fold_lla(r)]).score, 1) for h, r in zip(hyps, test[lang])]
    wrong = df[df["chrF++"] < df["chrF++"].median()]
    return wrong.sample(n=min(n, len(wrong)), random_state=0).sort_index().assign(category="", explanation="")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    n = ap.parse_args().n
    if OUT.exists():
        raise SystemExit(f"{OUT} exists (may hold labels); move it away first")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    test = read_clean().query("split == 'test'").reset_index(drop=True)
    with pd.ExcelWriter(OUT) as xl:
        for c in TARGETS:
            run, hyps = best_run(c, test)
            sample(test, c, hyps, n).to_excel(xl, sheet_name=NAMES[c], index=False)
            print(f"{NAMES[c]}: model {run}, {n} verses")
        pd.DataFrame(CATEGORIES.items(), columns=["category", "meaning"]).to_excel(xl, sheet_name="categories", index=False)
    print(OUT)


if __name__ == "__main__":
    toy = pd.DataFrame({"ref": list("abcd"), "hin": list("wxyz"), "kfs": ["एक दो", "तीन", "चार", "पांच"]})
    s = sample(toy, "kfs", ["एक दो", "तीन", "x", "y"], n=5)
    assert list(s.ref) == ["c", "d"] and s["chrF++"].max() < 50  # only the below-median verses
    main()
