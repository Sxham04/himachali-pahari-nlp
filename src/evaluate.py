"""Score every Hindi -> Pahari system on the test book (JHN): Part C baselines and Stage 1/2 LoRA models.

Run: uv run python src/evaluate.py   (missing systems are skipped)
Reads results/baselines/ (Copy, IndicTrans2, Gemma) and results/finetune/<run>/<lang>.txt.
Writes to results/scores/: scores.csv, scores_chrf.png, examples.md, signatures.txt; once Stage 2 data-size
ablation runs exist (<run>_f25 etc.), also ablation.csv + ablation_chrf.png (chrF++ vs share of training data).

Metrics (sacrebleu): chrF++ (main), BLEU (13a), spBLEU (FLORES-200 SentencePiece), TER (lower = better).
"chrF++ vs Hindi" scores the output against the Hindi source: high = the system stayed close to Hindi.
"p vs best baseline" / "p vs separate": paired bootstrap (1,000 samples) on chrF++ against the best baseline / (joint
models only) the separate LoRA models trained on the same share of data, per language.
Outputs and references both go through fold_lla (ऴ -> ळ), since NLLB cannot write ऴ.
"""
import json
import re
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


def data_pct(system: str) -> int:
    """'NLLB-LoRA joint (25% data)' -> 25; every other system -> 100."""
    m = re.search(r"\((\d+)% data\)", system)
    return int(m[1]) if m else 100


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
    for run in sorted(FINETUNE.glob("*/"), key=lambda p: ("_f" in p.name, p.name.startswith("joint"), p.name)):
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
        if models and n_boot:
            vs_best = paired_p(best, models, hyps, refs, n_boot)
            # joint vs separate trained on the same share of data
            vs_sep = {s: paired_p(sep, [s], hyps, refs, n_boot)[s] for s in models
                      if "joint" in s and (sep := s.replace("joint", "separate")) in hyps}
            for r in lang_rows:
                r["p vs best baseline"], r["p vs separate"] = vs_best.get(r["system"]), vs_sep.get(r["system"])
    sigs = [str(m.get_signature()) for m in (chrf, bleu, spbleu, ter)]
    return pd.DataFrame(rows), sigs


def paired_p(ref_sys: str, cands: list[str], hyps: dict, refs: list, n_boot: int) -> dict[str, float]:
    """Paired bootstrap on chrF++: p-value of each candidate against ref_sys."""
    _, res = PairedTest([(s, hyps[s]) for s in [ref_sys, *cands]], metrics={"chrF++": CHRF(word_order=2)},
                        references=refs, test_type="bs", n_samples=n_boot)()
    metric = next(k for k in res if k != "System")  # sacrebleu names it itself ("chrF2++")
    return {s: r.p_value for s, r in zip(res["System"], res[metric]) if s != ref_sys}


def plot(scores: pd.DataFrame) -> None:
    scores = scores[scores.system.map(data_pct) == 100]  # ablation runs get their own chart
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


def ablation(scores: pd.DataFrame) -> pd.DataFrame:
    """chrF++ per (language, model) x share of training data; empty until a Stage 2 run exists."""
    lora = scores[scores.system.str.startswith("NLLB-LoRA")]
    if (lora.system.map(data_pct) == 100).all():
        return pd.DataFrame()
    lora = lora.assign(model=lora.system.str.replace(r" \(\d+% data\)", "", regex=True),
                       data=lora.system.map(data_pct))
    return lora.pivot_table(index=["language", "model"], columns="data", values="chrF++").round(2)


def plot_ablation(table: pd.DataFrame) -> None:
    langs = [NAMES[c] for c in TARGETS]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    for (lang, model), row in table.iterrows():
        ax.plot(row.index, row.values, marker="o", color=f"C{langs.index(lang)}",
                ls="-" if "joint" in model else "--", label=f"{lang}, {model.split()[-1]}")
    ax.set_xticks(table.columns, [f"{d}%" for d in table.columns])
    ax.set_xlabel("share of training data")
    ax.set_ylabel("chrF++ on John (higher = better)")
    ax.legend(fontsize=7)
    ax.set_title("Data-size ablation")
    fig.tight_layout()
    fig.savefig(OUT / "ablation_chrf.png", dpi=200)
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
                      if name not in BASELINE_NAMES[:2] and c in by_lang and data_pct(name) == 100]
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
    if not (table := ablation(scores)).empty:
        table.to_csv(OUT / "ablation.csv")
        plot_ablation(table)
        print(table.to_string())


if __name__ == "__main__":
    t = pd.DataFrame({"ref": ["A.1.1"], "hin": ["एक दो"], **{c: ["एक दो"] for c in TARGETS}})
    s, _ = score({BASELINE_NAMES[0]: {c: ["एक दो"] for c in TARGETS}}, t, n_boot=0)
    assert (s["chrF++"].round(6) == 100).all() and (s["TER"] == 0).all()
    assert finetune_label("joint_f25") == "NLLB-LoRA joint (25% data)" and finetune_label("kfs") == "NLLB-LoRA separate"
    toy = pd.DataFrame({"system": ["NLLB-LoRA joint", "NLLB-LoRA joint (25% data)", BASELINE_NAMES[0]],
                        "language": ["Kangri"] * 3, "chrF++": [70.0, 60.0, 20.0]})
    assert ablation(toy.head(1)).empty and ablation(toy).loc[("Kangri", "NLLB-LoRA joint")].to_dict() == {25: 60.0, 100: 70.0}
    main()
