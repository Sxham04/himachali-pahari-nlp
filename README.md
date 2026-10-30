# Himachali Pahari NLP

Resources and first experiments for low-resource **Western Pahari** languages of Himachal: Mandyali, Bilaspuri, Kangri and Hamirpuri.
None of them is supported by today's translation systems.

_Soham Sharma (B.Tech CSE, DIT University; native speaker of Hamirpuri and Bilaspuri) · October 2026_

**Start here:** [Stage 1 report (LoRA fine-tuning)](docs/stage1-report.md) · [Stage 2 report (how much data is needed)](docs/stage2-report.md) · [full report](docs/project1-report.md) · [technical results](results/README.md) · [Hamirpuri dataset card](docs/hamirpuri-dataset-card.md)

## Two datasets

| Dataset | Languages | Size | Source |
|---|---|---|---|
| **Bible parallel set** | Hindi, Mandyali (`mjl`), Bilaspuri (`kfs`), Kangri (`xnr`) | 7,346 aligned verses (from 7,567) | public New Testament translations |
| **Hamirpuri sentence set** (new) | Hindi → Hamirpuri | 1,009 sentence pairs; 500 more in progress | native speaker + LLM drafts post-edited by a native speaker |

## Key findings so far

| Question | Answer |
|---|---|
| How close are the languages? | Bilaspuri–Kangri closest (chrF 33.0); all three closer to each other than to Hindi (24.7–26.6) |
| Can a computer tell them apart? | 99.9% accuracy on full verses, 90.9% on just 3 words (char n-gram + logistic regression) |
| Can existing tools translate Hindi into them? | **No.** IndicTrans2 (→ Dogri) and Gemma 3 4B (5-shot) score 16–22 chrF++, no better than copying the Hindi (19–21) |
| Can a fine-tuned model translate them? | **Yes.** LoRA on NLLB-600M: chrF++ **67.8 Mandyali, 44.5 Bilaspuri, 71.3 Kangri**; a joint model helps Bilaspuri (+1.0), slightly hurts Mandyali (−0.9) |
| How much data is needed? | A quarter of the training verses (1,511) already gives 89–91% of the full score |
| Where does Hamirpuri fit? | Between Kangri (48%) and Bilaspuri (40%); Kangri-like genitive (`दा/दे/दी`) but its own pronouns (`असां`, `तुसां`) |

<p>
<img src="results/analysis/chrf_heatmap.png" width="32%">
<img src="results/scores/scores_chrf.png" width="38%">
<img src="results/hamirpuri_check/shares.png" width="28%">
</p>

## Next

Error analysis of the fine-tuned models (in progress), then Hindi → Hamirpuri baselines.

## Layout

| Path | Contents |
|---|---|
| `docs/` | Stage 1 and Stage 2 reports, full report, Hamirpuri dataset card |
| `results/` | all numbers, figures and model outputs (`results/README.md` explains each) |
| `src/` | all scripts (data cleaning, analysis, dialect ID, baselines, fine-tuning, evaluation) |
| `data/sample_bible_20.tsv` | 20 aligned verses as a sample |

The full datasets are not included yet: the Mandyali and Bilaspuri Bible licences are being
confirmed (Hindi IRV and Kangri are CC BY-SA 4.0), and the Hamirpuri set is still growing.

## Reproduce

Python via [uv](https://docs.astral.sh/uv/); place `bible_verse_trans.xlsx` in the repo root.

```bash
uv run python src/data.py
uv run python src/analysis.py
uv run python src/dialect_id.py
uv run python src/stats.py
uv run python src/finetune.py --langs mjl   # also kfs, xnr, or all three for the joint model
uv run python src/finetune.py --langs mjl kfs xnr --frac 0.25   # 25/50/75% of the data
uv run python src/evaluate.py
```

Baseline outputs are already in `results/baselines/` (`run_indictrans2.py`, `run_gemma.py` regenerate them).
