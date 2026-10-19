# Himachali Pahari NLP: Mandyali, Bilaspuri, Kangri and Hamirpuri

Resources and first experiments for low-resource **Western Pahari** languages of Himachal
Pradesh. None of them is supported by today's translation systems.

_Soham Sharma (B.Tech CSE, DIT University; native speaker of Hamirpuri and Bilaspuri) · private preview, October 2026_

**Start here:** [Stage 1 report (LoRA fine-tuning)](docs/stage1-report.md) · [full plain-language report](docs/project1-report.md) · [technical results](results/README.md) · [Hamirpuri dataset card](docs/hamirpuri-dataset-card.md)

---

## Two datasets

| Dataset | Languages | Size | Source |
|---|---|---|---|
| **Bible parallel set** | Hindi, Mandyali (`mjl`), Bilaspuri (`kfs`), Kangri (`xnr`) | 7,346 verse-aligned verses (after cleaning 7,567) | public New Testament translations |
| **Hamirpuri elicitation set** (new) | Hindi → Hamirpuri | 509 sentences translated and proof-read; 500 more in progress | native speaker via a custom collection app |

## Key findings so far

| Question | Answer |
|---|---|
| How close are the languages? | Bilaspuri–Kangri closest (chrF 33.0); all three closer to each other than to Hindi (24.7–26.6) |
| Can a computer tell them apart? | 99.9% accuracy on full verses, 90.9% on just 3 words (char n-gram + logistic regression) |
| Can existing tools translate Hindi into them? | **No.** IndicTrans2 (→ Dogri) and Gemma 3 4B (5-shot) score 16–22 chrF++, no better than copying the Hindi (19–21) |
| Can a fine-tuned model translate them? | **Yes.** LoRA on NLLB-600M: chrF++ **67.8 Mandyali, 44.5 Bilaspuri, 71.3 Kangri** (vs ~21 for existing tools); a joint model helps Bilaspuri (+1.0), slightly hurts Mandyali (−0.9) |
| Where does Hamirpuri fit? | Between Kangri (48%) and Bilaspuri (40%); Kangri-like genitive (`दा/दे/दी`) but its own pronouns (`असां`, `तुसां`) |

<p>
<img src="results/analysis/chrf_heatmap.png" width="32%">
<img src="results/scores/scores_chrf.png" width="38%">
<img src="results/hamirpuri_check/shares.png" width="28%">
</p>

## Next

**Stage 2:** data-size ablation (25/50/75/100% of training data) and error analysis
(20–30 incorrect translations per language). Then extend to Hamirpuri.

## Repository layout

| Path | Contents |
|---|---|
| `docs/stage1-report.md` | Stage 1 (LoRA fine-tuning) report on its own |
| `docs/project1-report.md` | plain-language report of everything so far |
| `docs/project1-bible-plan.md` | project plan and methods |
| `docs/hamirpuri-dataset-card.md` | Hamirpuri dataset: design, collection, review, statistics, examples |
| `results/` | all numbers, figures and model outputs (`results/README.md` explains each) |
| `src/` | scripts: `data.py` (clean + split), `analysis.py` (Part A), `dialect_id.py` (Part B), `stats.py` (statistics, tokenizer fertility), `run_indictrans2.py` / `run_gemma.py` (Part C baselines), `finetune.py` (Stage 1/2 LoRA), `evaluate.py` (all scores), `make_share.py` (image/Excel/PDF for sharing), `hamirpuri_check.py` |
| `data/sample_bible_20.tsv` | 20 aligned verses as a sample |

The full datasets are not included yet: the Mandyali and Bilaspuri Bible licences are being
confirmed (Hindi IRV and Kangri are CC BY-SA 4.0), and the Hamirpuri data is still growing.

## Reproduce

Python via [uv](https://docs.astral.sh/uv/); place `bible_verse_trans.xlsx` in the repo root.

```bash
uv run python src/data.py
uv run python src/analysis.py
uv run python src/dialect_id.py
uv run python src/stats.py
uv run python src/finetune.py --langs mjl   # also kfs, xnr, or all three for the joint model
uv run python src/evaluate.py
```

`run_indictrans2.py` (separate venv, transformers 4.46.3; see its docstring) and `run_gemma.py`
(Ollama, `gemma3:4b`) regenerate the baseline outputs, which are already in `results/baselines/`.

## Notes

- The Mandyali text here is the public Bible translation. It is unrelated to any unpublished
  Mandyali dataset.
- Translators are identified only by speaker codes (e.g. `MA`).
