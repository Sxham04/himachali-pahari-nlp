# Stage 1 report: teaching a translation model Mandyali, Bilaspuri and Kangri

_Soham Sharma · plain-language report · 2026-10-18 · experiments set by Dr. Shweta Chauhan (2026-10-16)_

---

## In one paragraph

No existing translation tool can translate Hindi into Mandyali, Bilaspuri or Kangri: the best
ones score about the same as simply copying the Hindi. In Stage 1 we took **NLLB**, an open
translation model that already knows Hindi, and taught it the three languages using about 6,000
Bible verses per language and a light-weight training method called **LoRA**. We trained **one
model per language** and **one joint model for all three**, and scored them with **chrF++, BLEU
and TER**. Translation quality jumped from about **21 to 44–71 chrF++**, and the output reads like
the real language. Training the languages together helps the hardest one (Bilaspuri) and slightly
hurts the most distinct one (Mandyali).

---

## 1. What Dr. Chauhan asked for

1. Fine-tune NLLB using LoRA for Hindi → Mandyali, Bilaspuri and Kangri.
2. Train **separate models** for each language and **one joint multilingual model** using all three.
3. Calculate **BLEU, chrF++ and TER** for all models.

All three are done. (Stage 2, the data-size ablation and error analysis, comes next.)

---

## 2. The data

The same New Testament in Hindi, Mandyali, Bilaspuri and Kangri, aligned verse by verse and
cleaned (7,346 verses). We split it **by book**, so no test verse is ever seen in training:

| Part | Book(s) | Verses per language | Used for |
|---|---|---|---|
| Training | 25 books | 6,045 | teaching the models |
| Checking (dev) | Romans | 430 | deciding when to stop training |
| Final test | John | 871 | the final scores, used only once |

John is the test book because it repeats the other gospels the least, so the model cannot
"remember" answers from similar verses.

---

## 3. The model and the method

### Why NLLB?

**NLLB-200** (Meta) is an open translation model for 200 languages. We used the
**600-million-parameter "distilled" version**:

- it already translates **Hindi** well and knows many related North Indian languages, so it
  starts close to our target;
- it is the most widely used open model for **low-resource translation research**, so results
  are comparable with other papers;
- it is small enough to train on an **8 GB laptop GPU** (RTX 4060).

### Why LoRA?

Instead of changing all 600 million numbers in the model, **LoRA** trains small **add-on layers:
8.65 million numbers, 1.4% of the model**. This:

- fits on the laptop and trains in about **35–45 minutes per language**;
- is less likely to over-learn ("memorise") a small dataset of 6,000 verses;
- produces a small file (about **34 MB**) per model that sits on top of the original NLLB.

### Other choices

| Choice | Why |
|---|---|
| **Borrowed language codes**: Mandyali uses Awadhi's code (`awa_Deva`), Bilaspuri Bhojpuri's (`bho_Deva`), Kangri Magahi's (`mag_Deva`) | NLLB needs a code to know which language to write, and has none for ours. Borrowing unused codes is a standard trick; training teaches the model what each code now means. The same codes are used in every model. |
| **`ऴ` written as `ळ`** | NLLB has no symbol for the Bilaspuri letter `ऴ` (928 uses), so it could never write it. We converted it in the training text and in every reference, so all systems are scored the same way. |
| **Early stopping on Romans** | After each pass over the data (an "epoch", up to 10), we check the score on Romans; training stops if it stops improving for 2 epochs, and the best version is kept. |
| **Beam search (5)** | When translating, the model weighs 5 candidate sentences at each step instead of 1, which usually gives better translations. |

Training settings, for completeness: learning rate 0.0002, batch size 16 (verses of similar
length grouped together for speed), LoRA rank 16, bf16 precision.

### The four training runs

| Model | Training verse pairs | Best epoch | Dev loss (lower = better) | Training time |
|---|---|---|---|---|
| Mandyali (separate) | 6,045 | 10 | 0.85 | 38 min |
| Bilaspuri (separate) | 6,045 | 10 | 1.82 | 43 min |
| Kangri (separate) | 6,045 | 9 | 0.65 | 35 min |
| **Joint** (all three) | 18,135 | 10 | 1.12 | 134 min |

The joint model sees all three languages at once and uses the language code to know which one
to write.

---

## 4. How we scored the translations

Every system translated the 871 Hindi verses of John, and each output was compared with the real
Bible translation.

| Score | What it measures | Good is |
|---|---|---|
| **chrF++** (main) | How many letter chunks and words the output shares with the correct translation (0–100). Gives partial credit for nearly-right words, which suits languages with many word endings and no fixed spelling. | higher |
| **BLEU** | How many whole words and word sequences match. The long-standing standard. | higher |
| **spBLEU** | BLEU after splitting words the same way for every language; fairer for Indian scripts. | higher |
| **TER** | How many word edits (insert, delete, replace, move) are needed to fix the output, as a % of the correct translation's length. Can exceed 100 when fixing is harder than rewriting. | **lower** |

We also ran a **significance test** (paired bootstrap, 1,000 samples): it tells whether a
difference between two systems is real or could be luck. A **p-value below 0.05** means the
difference is real.

All scores were computed with **sacrebleu**, the standard tool in translation research.

---

## 5. Results

### chrF++ (main score)

| chrF++ on John ↑ | Mandyali | Bilaspuri | Kangri |
|---|---|---|---|
| Copy the Hindi unchanged | 21.0 | 18.8 | 20.0 |
| IndicTrans2-1B (asked for Dogri) | 16.1 | 17.3 | 20.6 |
| Gemma 3 4B (5 examples) | 21.7 | 18.6 | 21.2 |
| **Our separate models** | **67.8** | 43.5 | 71.1 |
| **Our joint model** | 67.0 | **44.5** | **71.3** |

![chrF++ scores](../results/scores/scores_chrf.png)

### All scores

| Language | System | chrF++ ↑ | BLEU ↑ | spBLEU ↑ | TER ↓ |
|---|---|---|---|---|---|
| Mandyali | best existing tool (Gemma) | 21.75 | 2.64 | 5.53 | 89.76 |
| Mandyali | **separate** | **67.82** | **46.67** | **57.25** | **35.41** |
| Mandyali | joint | 66.96 | 45.67 | 56.59 | 36.08 |
| Bilaspuri | best existing tool (Copy) | 18.77 | 1.21 | 3.13 | 95.06 |
| Bilaspuri | separate | 43.49 | 17.31 | 26.41 | 66.52 |
| Bilaspuri | **joint** | **44.47** | **17.94** | **27.01** | **64.84** |
| Kangri | best existing tool (Gemma) | 21.15 | 2.59 | 6.12 | 88.24 |
| Kangri | separate | 71.08 | 50.98 | 62.63 | 31.55 |
| Kangri | **joint** | **71.31** | **51.43** | **62.84** | **31.41** |

### Is the difference real? (significance tests)

| | Mandyali | Bilaspuri | Kangri |
|---|---|---|---|
| Our models vs the best existing tool | p = 0.001: **real** | p = 0.001: **real** | p = 0.001: **real** |
| Joint vs separate | −0.85, p = 0.001: joint **worse** | +0.98, p = 0.001: joint **better** | +0.23, p = 0.07: **no real difference** |

### What the translations look like (John 1:1)

| | Text |
|---|---|
| Hindi (input) | आदि में वचन था, और वचन परमेश्वर के साथ था, और वचन परमेश्वर था। |
| Mandyali, real | सभी ले पैहले वचन था, होर वचन परमेसरा साउगी था, होर वचन ई परमेसर था। |
| Mandyali, our separate model | आदि मन्झ वचन था, होर वचन परमेसरा साउगी था, होर वचन परमेसर था। |
| Bilaspuri, real | सृष्टिया ते पैहले बचन था, कने बचन परमेशरा सौगी था, कने बचन ई परमेशर था। |
| Bilaspuri, our joint model | शुरू च वचन था, कने वचन परमेशरा सौगी था, कने वचन परमेशर था। |
| Kangri, real | सृष्टिया ते पैहले वचन था, कने वचन परमात्में सौगी था। कने वचन परमात्मां था। |
| Kangri, our joint model | शुरू च वचन था, कने वचन परमात्में सौगी था, कने वचन परमात्मां था। |
| Best existing tool (Gemma, Kangri) | अदी में शब्द ऐह्या, कने शब्द परमेश्वर के साथ ऐह्या, कने परमेश्वर दे शब्द ऐह्या। |

Our models use each language's own small words correctly ("and": `होर` in Mandyali, `कने` in
Bilaspuri and Kangri; "in": `मन्झ` vs `च`) and its own spelling of God (`परमेसर`, `परमेशर`,
`परमात्मां`). The existing tool mostly writes Hindi with a few Pahari words.

---

## 6. What the results mean

1. **Fine-tuning closes the gap.** Every model beats every existing tool by **25–50 chrF++
   points**, and the difference is statistically real. TER drops from about 90 (almost every word
   needs fixing) to **31–65**. The output is the target language, not Hindi.

2. **One joint model or three separate ones? It depends on the language**, and matches what we
   found earlier about how similar the languages are:
   - **Bilaspuri gets better** with the joint model (+1.0). It is the hardest language and the
     closest to Kangri, so it learns from Kangri's data.
   - **Mandyali gets slightly worse** (−0.9). It is the most different of the three, so the other
     two get in its way a little.
   - **Kangri: no real difference.**

   In practice, one joint model is also simpler: one 34 MB file instead of three.

3. **Bilaspuri is still the hardest** (44 vs about 70). This is most likely about *this Bible
   translation*, not the language itself:
   - **most varied wording:** 12,909 different words (vs about 9,000 for the others), half of them
     used only once, which points to inconsistent spelling;
   - **more unseen words:** 5.4% of John's words never appear in training (vs 2.6–3.3%);
   - **freer translation:** it paraphrases more. In John 1:1 it says "सृष्टिया ते पैहले" (before
     creation) where Hindi says "आदि में" (in the beginning); our model wrote "शुरू च", which is
     correct but gets little credit;
   - **noisiest source:** this text had shifted verses that we had to remove during cleaning.

---

## 7. Limits

- **Same translation team in training and test.** Each language's verses come from one Bible
  translation, so the model also learns that team's style and vocabulary. Scores on everyday
  sentences will be lower. The Hamirpuri sentences and the Stage 2 error analysis will show this.
- **Religious, formal language.** The Bible is not everyday speech.
- **Training could go a little further.** The dev loss was still slowly falling at epoch 10 for
  Mandyali, Bilaspuri and the joint model, so a few more epochs might add a little.
- **Licences.** NLLB allows research use, not commercial use. The Hindi and Kangri Bible texts are
  CC BY-SA 4.0; the Mandyali and Bilaspuri licences are still being confirmed.

---

## 8. Next: Stage 2

1. **How much data is needed?** Retrain with 25%, 50%, 75% and 100% of the training verses and
   compare the scores.
2. **What goes wrong?** Collect 20–30 incorrect translations per language and explain each mistake.

All code, scores and model outputs are in the project repository (`src/finetune.py`,
`src/evaluate.py`, `results/scores/`).
