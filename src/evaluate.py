"""Score Part C baselines (and later Part D) on the test book (JHN).

Run: uv run python src/evaluate.py   (after the run_*.py scripts; missing systems are skipped)
Writes to results/baselines/: scores.csv, scores_chrf.png, examples.md, signatures.txt

Metrics (sacrebleu): chrF++ (main) and spBLEU (BLEU with the FLORES-200 SentencePiece tokenizer,
the usual BLEU for Indian languages). "chrF++ vs Hindi" scores the output against the Hindi
source instead of the reference: high = the system mostly copied or stayed in Hindi.
"""
import json

import matplotlib
import pandas as pd
from sacrebleu.metrics import BLEU, CHRF

from data import NAMES, ROOT, read_clean, words

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = ROOT / "results" / "baselines"
TARGETS = ["mjl", "kfs", "xnr"]


def load_systems(test: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    """{system: {lang: hyps in test order}}."""
    systems = {"Copy (Hindi source)": {c: test.hin.tolist() for c in TARGETS}}
    it2 = OUT / "indictrans2_doi.txt"
    if it2.exists():
        hyps = it2.read_text(encoding="utf-8").splitlines()
        assert len(hyps) == len(test), f"{it2}: {len(hyps)} lines, expected {len(test)}"
        systems["IndicTrans2-1B (→ Dogri)"] = {c: hyps for c in TARGETS}
    gemma = {}
    for c in TARGETS:
        path = OUT / f"gemma_{c}.jsonl"
        if path.exists():
            got = {d["ref"]: d["hyp"] for d in map(json.loads, path.open(encoding="utf-8"))}
            if set(test.ref) <= set(got):
                gemma[c] = [got[r] for r in test.ref]
    if gemma:
        systems["Gemma 3 4B (5-shot)"] = gemma
    return systems


def score(systems, test) -> tuple[pd.DataFrame, list[str]]:
    chrf, bleu = CHRF(word_order=2), BLEU(tokenize="flores200")
    rows = []
    for name, by_lang in systems.items():
        for c, hyps in by_lang.items():
            rows.append({
                "system": name, "language": NAMES[c],
                "chrF++": chrf.corpus_score(hyps, [test[c].tolist()]).score,
                "spBLEU": bleu.corpus_score(hyps, [test[c].tolist()]).score,
                "chrF++ vs Hindi": chrf.corpus_score(hyps, [test.hin.tolist()]).score,
            })
    return pd.DataFrame(rows), [str(chrf.get_signature()), str(bleu.get_signature())]


def plot(scores: pd.DataFrame) -> None:
    piv = scores.pivot(index="language", columns="system", values="chrF++").loc[[NAMES[c] for c in TARGETS]]
    systems = list(dict.fromkeys(scores.system))
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    w = 0.8 / len(systems)
    for k, s in enumerate(systems):
        bars = ax.bar([i + (k - (len(systems) - 1) / 2) * w for i in range(len(piv))], piv[s], w, label=s)
        ax.bar_label(bars, fmt="%.1f", fontsize=7)
    ax.set_xticks(range(len(piv)), piv.index)
    ax.set_ylabel("chrF++ on John (higher = better)")
    ax.set_ylim(0, max(50, piv.values.max() * 1.2))
    ax.legend(fontsize=7, loc="upper left")
    ax.set_title("Hindi → Pahari baselines")
    fig.tight_layout()
    fig.savefig(OUT / "scores_chrf.png", dpi=200)
    plt.close(fig)


def examples(systems, test, n: int = 5) -> str:
    pick = test[test.hin.map(lambda t: 8 <= len(words(t)) <= 14)].iloc[:: max(1, len(test) // 40)].head(n)
    lines = ["# Example outputs (John)", ""]
    for r in pick.itertuples():
        i = test.index.get_loc(r.Index)
        lines += [f"## {r.ref}", "", f"- **Hindi source:** {r.hin}"]
        it2 = systems.get("IndicTrans2-1B (→ Dogri)")
        if it2:
            lines.append(f"- **IndicTrans2 (Dogri):** {it2['mjl'][i]}")
        for c in TARGETS:
            lines.append(f"- **{NAMES[c]} reference:** {getattr(r, c)}")
            g = systems.get("Gemma 3 4B (5-shot)", {}).get(c)
            if g:
                lines.append(f"  - Gemma: {g[i]}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = read_clean()
    test = df[df.split == "test"].reset_index(drop=True)
    systems = load_systems(test)
    scores, sigs = score(systems, test)
    # Gemma verses where Ollama aborted a looping reply ("token repeat limit reached")
    aborted = {NAMES[c]: sum("aborted" in ln for ln in (OUT / f"gemma_{c}.jsonl").open(encoding="utf-8"))
               for c in TARGETS if (OUT / f"gemma_{c}.jsonl").exists()}
    scores["aborted"] = [aborted.get(r.language, 0) if r.system.startswith("Gemma") else 0
                         for r in scores.itertuples()]
    scores.round(2).to_csv(OUT / "scores.csv", index=False)
    (OUT / "signatures.txt").write_text("\n".join(sigs) + "\n", encoding="utf-8")
    (OUT / "examples.md").write_text(examples(systems, test), encoding="utf-8")
    plot(scores)
    print(scores.round(2).to_string(index=False))


if __name__ == "__main__":
    t = pd.DataFrame({"ref": ["A.1.1"], "hin": ["एक दो"], **{c: ["एक दो"] for c in TARGETS}})
    s, _ = score({"Copy": {c: ["एक दो"] for c in TARGETS}}, t)
    assert (s["chrF++"].round(6) == 100).all()
    main()
