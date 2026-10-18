"""Score every Hindi -> Pahari system on the test book (JHN): Part C baselines and Stage 1/2 LoRA models.

Run: uv run python src/evaluate.py   (missing systems are skipped)
Reads results/baselines/ (Copy, IndicTrans2, Gemma) and results/finetune/<run>/<lang>.txt.
Writes to results/scores/: scores.csv, scores_chrf.png, examples.md, signatures.txt

Metrics (sacrebleu): chrF++ (main), BLEU (13a), spBLEU (FLORES-200 SentencePiece), TER (lower = better).
"chrF++ vs Hindi" scores the output against the Hindi source: high = the system stayed close to Hindi.
"p vs best baseline" / "p vs separate": paired bootstrap (1,000 samples) on chrF++ against the best baseline / the
separate LoRA models, per language.
Outputs and references both go through fold_lla (ऴ -> ळ), since NLLB cannot write ऴ.
"""
import json
from pathlib import Path

import matplotlib
import pandas as pd
from sacrebleu.metrics import BLEU, CHRF, TER
from sacrebleu.significance import PairedTest

from data import NAMES, ROOT, fold_lla, read_clean, words

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BASELINES, FINETUNE, OUT = (ROOT / "results" / d for d in ("baselines", "finetune", "scores"))
TARGETS = ["mjl", "kfs", "xnr"]
SEPARATE = "NLLB-LoRA separate"
BASELINE_NAMES = ["Copy (Hindi source)", "IndicTrans2-1B (→ Dogri)", "Gemma 3 4B (5-shot)"]


def read_lines(path: Path, n: int) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == n, f"{path}: {len(lines)} lines, expected {n}"
    return lines


def finetune_label(run: str) -> str:
    """joint -> 'NLLB-LoRA joint', mjl -> 'NLLB-LoRA separate', joint_f25 -> 'NLLB-LoRA joint (25% data)'."""
    base, _, frac = run.partition("_f")
    label = "NLLB-LoRA " + ("joint" if base == "joint" else "separate")
    return f"{label} ({frac}% data)" if frac else label


def load_systems(test: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    """{system: {lang: hyps in test order}}; separate per-language runs merge into one system."""
    n = len(test)
    systems = {BASELINE_NAMES[0]: {c: test.hin.tolist() for c in TARGETS}}
    if (it2 := BASELINES / "indictrans2_doi.txt").exists():
        systems[BASELINE_NAMES[1]] = dict.fromkeys(TARGETS, read_lines(it2, n))
    for c in TARGETS:
        if (path := BASELINES / f"gemma_{c}.jsonl").exists():
            got = {d["ref"]: d["hyp"] for d in map(json.loads, path.open(encoding="utf-8"))}
            if set(test.ref) <= set(got):
                systems.setdefault(BASELINE_NAMES[2], {})[c] = [got[r] for r in test.ref]
    for run in sorted(FINETUNE.glob("*/"), key=lambda p: (p.name.startswith("joint"), p.name)):
        for c in TARGETS:
            if (path := run / f"{c}.txt").exists():
                systems.setdefault(finetune_label(run.name), {})[c] = read_lines(path, n)
    return systems


def score(systems: dict, test: pd.DataFrame, n_boot: int = 1000) -> tuple[pd.DataFrame, list[str]]:
    chrf, bleu, spbleu, ter = CHRF(word_order=2), BLEU(), BLEU(tokenize="flores200"), TER()
    hin = [test.hin.tolist()]
    rows = []
    for c in TARGETS:
        refs = [[fold_lla(t) for t in test[c]]]
        hyps = {name: [fold_lla(h) for h in by_lang[c]] for name, by_lang in systems.items() if c in by_lang}
        for name, h in hyps.items():
            rows.append({"system": name, "language": NAMES[c],
                         "chrF++": chrf.corpus_score(h, refs).score, "BLEU": bleu.corpus_score(h, refs).score,
                         "spBLEU": spbleu.corpus_score(h, refs).score, "TER": ter.corpus_score(h, refs).score,
                         "chrF++ vs Hindi": chrf.corpus_score(h, hin).score})
        lang_rows = [r for r in rows if r["language"] == NAMES[c]]
        best = max((r for r in lang_rows if r["system"] in BASELINE_NAMES), key=lambda r: r["chrF++"])["system"]
        models = [s for s in hyps if s not in BASELINE_NAMES]
        for col, ref_sys, cands in [("p vs best baseline", best, models),
                                    ("p vs separate", SEPARATE, [s for s in models if s != SEPARATE])]:
            if cands and ref_sys in hyps and n_boot:
                pvals = paired_p(ref_sys, cands, hyps, refs, n_boot)
                for r in lang_rows:
                    r[col] = pvals.get(r["system"])
    sigs = [str(m.get_signature()) for m in (chrf, bleu, spbleu, ter)]
    return pd.DataFrame(rows), sigs


def paired_p(ref_sys: str, cands: list[str], hyps: dict, refs: list, n_boot: int) -> dict[str, float]:
    """Paired bootstrap on chrF++: p-value of each candidate against ref_sys."""
    _, res = PairedTest([(s, hyps[s]) for s in [ref_sys, *cands]], metrics={"chrF++": CHRF(word_order=2)},
                        references=refs, test_type="bs", n_samples=n_boot)()
    metric = next(k for k in res if k != "System")  # sacrebleu names it itself ("chrF2++")
    return {s: r.p_value for s, r in zip(res["System"], res[metric]) if s != ref_sys}


def plot(scores: pd.DataFrame) -> None:
    piv = scores.pivot(index="language", columns="system", values="chrF++").loc[[NAMES[c] for c in TARGETS]]
    systems = list(dict.fromkeys(scores.system))
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    w = 0.8 / len(systems)
    for k, s in enumerate(systems):
        bars = ax.bar([i + (k - (len(systems) - 1) / 2) * w for i in range(len(piv))], piv[s], w, label=s)
        ax.bar_label(bars, fmt="%.1f", fontsize=6)
    ax.set_xticks(range(len(piv)), piv.index)
    ax.set_ylabel("chrF++ on John (higher = better)")
    ax.set_ylim(0, max(50, piv.values.max() * 1.25))
    ax.legend(fontsize=7, loc="upper left", ncol=2)
    ax.set_title("Hindi → Pahari translation")
    fig.tight_layout()
    fig.savefig(OUT / "scores_chrf.png", dpi=200)
    plt.close(fig)


def examples(systems: dict, test: pd.DataFrame, n: int = 5) -> str:
    pick = test[test.hin.map(lambda t: 8 <= len(words(t)) <= 14)].iloc[:: max(1, len(test) // 40)].head(n)
    lines = ["# Example outputs (John)", ""]
    for r in pick.itertuples():
        i = test.index.get_loc(r.Index)
        lines += [f"## {r.ref}", "", f"- **Hindi source:** {r.hin}"]
        if it2 := systems.get(BASELINE_NAMES[1]):
            lines.append(f"- **IndicTrans2 (Dogri):** {it2['mjl'][i]}")
        for c in TARGETS:
            lines.append(f"- **{NAMES[c]} reference:** {getattr(r, c)}")
            lines += [f"  - {name}: {by_lang[c][i]}" for name, by_lang in systems.items()
                      if name not in BASELINE_NAMES[:2] and c in by_lang]
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    test = read_clean().query("split == 'test'").reset_index(drop=True)
    systems = load_systems(test)
    scores, sigs = score(systems, test)
    # Gemma verses where Ollama aborted a looping reply ("token repeat limit reached")
    aborted = {NAMES[c]: sum("aborted" in ln for ln in p.open(encoding="utf-8"))
               for c in TARGETS if (p := BASELINES / f"gemma_{c}.jsonl").exists()}
    scores["aborted"] = [aborted.get(r.language, 0) if r.system == BASELINE_NAMES[2] else 0 for r in scores.itertuples()]
    scores.round(2).assign(**{c: scores[c].round(4) for c in ["p vs best baseline", "p vs separate"] if c in scores}).to_csv(
        OUT / "scores.csv", index=False)
    (OUT / "signatures.txt").write_text("\n".join(sigs) + "\n", encoding="utf-8")
    (OUT / "examples.md").write_text(examples(systems, test), encoding="utf-8")
    plot(scores)
    print(scores.round(3).to_string(index=False))


if __name__ == "__main__":
    t = pd.DataFrame({"ref": ["A.1.1"], "hin": ["एक दो"], **{c: ["एक दो"] for c in TARGETS}})
    s, _ = score({BASELINE_NAMES[0]: {c: ["एक दो"] for c in TARGETS}}, t, n_boot=0)
    assert (s["chrF++"].round(6) == 100).all() and (s["TER"] == 0).all()
    assert finetune_label("joint_f25") == "NLLB-LoRA joint (25% data)" and finetune_label("kfs") == "NLLB-LoRA separate"
    main()
