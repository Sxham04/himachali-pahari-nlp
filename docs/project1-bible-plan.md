# Project 1: Hindi to Pahari on Bible verses (plan and brief)

_Written 2026-10-11. Status: Parts A, B, C + dataset stats/fertility done (results in `results/README.md`); D–E next._

## 1. In one paragraph

We have the same 7,567 New Testament verses in four languages: Hindi, Mandyali, Bilaspuri and
Kangri. This project uses that table to answer two simple questions. **How close are these
three Pahari languages to Hindi and to each other?** And **can a computer translate Hindi into
them**, first with ready-made tools, then with a small model we train ourselves? The result is a
short report (4–6 pages) plus code.

## 2. Why do this

- Mandyali, Bilaspuri and Kangri have almost no computer tools. Big translation systems (Google,
  NLLB, IndicTrans2) do not support them.
- The Bible table is the largest aligned data we have right now. It is ready to use, while the
  Hamirpuri collection is still growing.
- A finished, measured project shows Dr. Chauhan and NIT faculty that the work is real. It also
  builds the code we will reuse later for Hamirpuri (Project 2) and the final paper.

## 3. Objectives

1. **Measure how similar** Hindi, Mandyali, Bilaspuri and Kangri are, using numbers, not opinion.
2. **Build a dialect identifier**: a program that reads a sentence and says which of the four
   languages it is in.
3. **Test existing translation tools** on Hindi to each Pahari language, to show how big the gap is.
4. **Train our own small translator** (fine-tune an open model) and show how much it improves.
5. **Write it up**: a short report with tables, figures and a few example translations.

## 4. Scope

**In scope**
- Only the Bible data (`bible_verse_trans.xlsx`): Hindi (`hin`), Mandyali (`mjl`), Bilaspuri
  (`kfs`), Kangri (`xnr`).
- Translation direction: Hindi to each Pahari language.
- Everything runs on the laptop GPU (RTX 4060, 8 GB). Kaggle only if something does not fit.

**Out of scope (for now)**
- Hamirpuri sentences from MA. They belong to Project 2.
- Pahari to Hindi direction, speech, and English.
- Dr. Chauhan's unpublished Mandyali data. Not used, not cited.
- Publishing the data. The Bible license is not checked yet, so data and report stay private.

## 5. The data

| Item | Value |
|---|---|
| Verses | 7,567 (7,564 have all four languages; we keep only those) |
| Average length | about 23–26 words per verse |
| Books | all 27 New Testament books |

**How we split it (by book, so test verses are never seen in training):**

| Part | Books | Verses | Used for |
|---|---|---|---|
| Test | John (JHN) | ~876 | final scores only, touched once at the end |
| Dev | Romans (ROM) | ~433 | tuning and choosing settings |
| Train | all other 25 books | ~6,255 | training the model, few-shot examples |

John is the test book because it repeats the other three gospels the least. If we tested on
Luke, the model could just remember similar verses from Matthew and Mark.

## 6. Method

### Part A: How similar are the languages?

1. **Character overlap score (chrF).** For every pair of languages, compare each verse with
   its partner in the other language and count how many short letter sequences they share.
   Result: a 4 × 4 table shown as a colour heatmap. High score = close languages.
2. **Shared words.** What percent of words appear in both languages of a pair.
3. **Typical words.** For each Pahari language, list the words that appear much more often than
   in Hindi (for example, different verb endings or pronouns). These give examples for the report.

### Part B: Dialect identifier

- Turn each verse into counts of short letter chunks (1 to 4 characters, TF-IDF).
- Train a simple classifier (logistic regression) to pick one of the four languages.
- Report accuracy, a confusion table (which languages get mixed up), and how accuracy changes
  with sentence length. This runs on the CPU in minutes.

### Part C: Translation with existing tools (baselines)

Each one translates the John verses from Hindi. All are scored the same way (section 7).

| Baseline | What it is | Why include it |
|---|---|---|
| Copy | Output the Hindi sentence unchanged | Shows how much the languages already share. Any real system must beat this. |
| IndicTrans2 | Strong Indian translation model; we ask for Dogri | Dogri is the closest Pahari language it supports. Shows how a "near" language does. |
| Open LLM | Gemma 3 4B through Ollama, given 5 example pairs from the train books | Shows what a general chatbot-style model can do with a few examples. |

### Part D: Train our own translator

- Start from **NLLB-200-distilled-600M**, an open translation model that already knows Hindi.
- Train **one model for all three Pahari languages**. A language tag on each sentence tells it
  which one to write. NLLB has no tags for these languages, so we borrow three unused existing
  Devanagari tags.
- Use **LoRA**: instead of changing the whole model, we train small add-on layers. This fits in
  8 GB and trains in hours, not days. Precision: bf16. Max length: 256 tokens.
- Stop training when the score on Romans (dev) stops improving. Then score once on John (test).

### Revised plan from Dr. Chauhan's review (2026-10-16)

Dr. Chauhan reviewed the report ("dataset cleaning and initial analysis look good") and set the
experiments for the paper. These replace Parts D and E above.

**Stage 1 (do first):**
1. Fine-tune **NLLB with LoRA** for Hindi → Mandyali, Bilaspuri, Kangri.
2. Train **three separate models** (one per language) **and one joint multilingual model**
   (all three languages together).
3. Score **all models** with **BLEU, chrF++ and TER** (and re-score the Part C baselines the
   same way, so every row of the results table is comparable).

**Stage 2 (after Stage 1): ablation and error analysis**
4. **Data-size ablation:** train with 25%, 50%, 75% and 100% of the training data and compare.
5. **Error analysis:** pick 20–30 incorrect translations per language and explain each mistake.

## 7. How we measure success

- **chrF++** (main score, 0–100): how many letter and word pieces the output shares with the
  real translation. Works well for languages with many word endings, like these.
- **BLEU** (second score): the older standard, reported so others can compare.
- Both computed with the `sacrebleu` library, the standard tool in research papers.

**Success looks like:** the fine-tuned model clearly beats the Copy baseline and the existing
tools on all three languages, and the dialect identifier is well above chance (25%).

## 8. Tools and code layout

- Python via `uv` (no system Python). PyTorch (cu128), Hugging Face `transformers` + `peft`,
  scikit-learn, sacrebleu, pandas, matplotlib. Ollama for the LLM baseline (needs installing).
- Planned folders:
  - `src/` scripts: `data.py` (clean + split), `analysis.py`, `dialect_id.py`, `baselines.py`,
    `finetune.py`, `evaluate.py`
  - `results/` scores, tables, figures, sample outputs
  - Report written in the ACL LaTeX template on Overleaf.

## 9. Timeline (about 2 weeks)

| Days | Work |
|---|---|
| 1 | Set up environment, clean data, make the split |
| 2–3 | Part A similarity + Part B dialect identifier |
| 4–6 | Part C baselines (Copy, IndicTrans2, Gemma) |
| 7–10 | Part D LoRA training + scoring |
| 11–14 | Optional human check, write report, send to Dr. Chauhan |

## 10. Deliverables

1. Private code repo with the scripts above.
2. `results/` with all scores and figures.
3. A 4–6 page report: introduction, data, similarity analysis, dialect ID, translation results,
   example outputs, limits, next steps (Hamirpuri).

## 11. Risks and limits

| Risk | What we do |
|---|---|
| Bible license not checked | Keep report and data private until checked (eBible.org lists each translation's terms) |
| Religious, formal language | Say so clearly in the report; the model may not handle everyday speech. Project 2 fixes this with MA's sentences |
| IndicTrans2 tools may not install on Windows | Run that one baseline on Kaggle |
| Laptop heat slows long training | Keep plugged in, performance mode, good airflow; Kaggle as backup |
| Similar gospel verses inflate scores | Test on John, which overlaps least |

## 12. Open questions for Soham

- Approve this plan as written?
- OK to set up git (private repo) before the code starts?
