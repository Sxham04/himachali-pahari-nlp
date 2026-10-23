# Stage 2 report: how much data does the model need?

_Soham Sharma · plain-language report · 2026-10-23 · experiments set by Dr. Shweta Chauhan (2026-10-16)_

---

## In one paragraph

In Stage 1 we taught NLLB, an open translation model, to translate Hindi into Mandyali, Bilaspuri
and Kangri, using about 6,000 Bible verses per language. In Stage 2 we asked **how much of that
data is really needed**: we trained all four models again (three separate, one joint) on **25%,
50% and 75%** of the training verses and compared them with the 100% models. **More data always
helps, but less and less**: going from a quarter of the data to all of it adds 4–8 chrF++ points,
and most of that comes from the first extra quarter. With only **1,511 verses** the models
already reach **about 90% of their full score**, far above any existing tool. The Stage 1 finding
(joint training helps Bilaspuri, slightly hurts Mandyali) holds at every data size. The second
part of Stage 2, the error analysis, is in progress.

---

## 1. Goals

From Dr. Chauhan's plan:

1. **Data-size ablation:** train with 25%, 50%, 75% and 100% of the training data and compare
   performance. **Done** (this report).
2. **Error analysis:** identify 20–30 incorrect translations per language and explain the
   mistakes. **In progress**: 30 wrong translations per language have been selected and are being
   labelled by a native speaker.

---

## 2. What we did

Everything is the same as in Stage 1 (same model, same LoRA settings, same Romans check set, same
John test book, same scores), except the amount of training data.

**Which verses?** We picked training verses at random, with a fixed seed so the result can be
repeated. Three rules keep the comparison fair:

- **Same verses for every language:** the 25% Mandyali model and the 25% Kangri model learn from
  the same 1,511 verses, just in different languages.
- **Same verses for separate and joint models**, so those two can be compared at each size.
- **Each smaller set sits inside the bigger one** (the 25% verses are part of the 50%, which are
  part of the 75%), so a bigger set only ever *adds* data.

| Share of training data | Verses per language | Verse pairs in the joint model |
|---|---|---|
| 25% | 1,511 | 4,533 |
| 50% | 3,022 | 9,066 |
| 75% | 4,534 | 13,602 |
| 100% (Stage 1) | 6,045 | 18,135 |

That is **12 new models** (3 separate + 1 joint, each at 25%, 50% and 75%). Together with the
4 Stage 1 models, 16 models were scored.

**Two technical changes from Stage 1** (they do not change what the model learns):

- **Where it ran.** Windows' new security feature (Smart App Control) now blocks the
  machine-learning library on this laptop, so training ran inside **WSL2**, a Linux system on
  the same laptop and the same GPU.
- **Half-size steps.** At batch size 16 the 8 GB GPU ran out of room under Linux and crashed. So
  the model now looks at 8 verses at a time and updates after every **two** such groups. This
  gives exactly the same "16 verses per update" as Stage 1, and it even ran faster (3.4 updates
  per second instead of 1.9).

| Model | Training time 25% / 50% / 75% |
|---|---|
| Each separate model | about 5 / 9–10 / 11–15 min |
| Joint model | 12 / 22 / 46 min |

All 12 runs took **3.5 hours** together.

---

## 3. Results

### chrF++ (main score, higher = better)

| Language | Model | 25% | 50% | 75% | 100% |
|---|---|---|---|---|---|
| Mandyali | separate | 60.1 | 63.9 | 66.3 | **67.8** |
| Mandyali | joint | 59.1 | 63.3 | 65.8 | 67.0 |
| Bilaspuri | separate | 39.2 | 41.8 | 42.9 | 43.5 |
| Bilaspuri | joint | 40.3 | 42.5 | 43.6 | **44.5** |
| Kangri | separate | 64.4 | 68.6 | 70.2 | 71.1 |
| Kangri | joint | 64.2 | 68.4 | 70.1 | **71.3** |
| *Best existing tool (for comparison)* | | | | | *19–22* |

![Data-size ablation](../results/scores/ablation_chrf.png)

Solid lines are the joint model, dashed lines the separate models.

### BLEU and TER (best model per language)

| | BLEU ↑ 25% → 100% | TER ↓ 25% → 100% |
|---|---|---|
| Mandyali (separate) | 36.4 → 46.7 | 43.7 → 35.4 |
| Bilaspuri (joint) | 14.2 → 17.9 | 68.9 → 64.8 |
| Kangri (separate) | 42.0 → 51.0 | 38.3 → 31.6 |

### Joint vs separate at each size

Difference in chrF++ (joint minus separate) and whether it is real (p below 0.05 = real):

| | 25% | 50% | 75% | 100% |
|---|---|---|---|---|
| Mandyali | −1.0 (real) | −0.6 (real) | −0.5 (real) | −0.9 (real) |
| Bilaspuri | **+1.2** (real) | **+0.7** (real) | **+0.7** (real) | **+1.0** (real) |
| Kangri | −0.2 (no) | −0.2 (no) | −0.1 (no) | +0.2 (no) |

### What more data changes (John 3:16, Mandyali)

| | Text |
|---|---|
| Hindi (input) | क्योंकि परमेश्वर ने जगत से ऐसा प्रेम रखा कि उसने अपना एकलौता पुत्र दे दिया, ताकि जो कोई उस पर विश्वास करे, वह नाश न हो, परन्तु अनन्त जीवन पाए। |
| Mandyali, real | क्यूंकि परमेसरे संसारा किन्हें एहड़ा प्यार कितेया कि तिने आपणा इकलौता म्हठा देई दितेया, ताकि जो कोई तेस पर विस्वास करे से नास नी हो पर अनंत जिंदगी पाए। |
| Model with 25% of the data | क्यूंकि परमेसरे संसारा किन्हें ऐहड़ा प्यार रख्या, कि तिने आपणा इकलौटा पुत्रा देई दितेया, ताकि जो कोई तेस पर विस्वास करे, से नास नी हो, पर अनंत जीउना पाई सके। |
| Model with 100% of the data | क्यूंकि परमेसरे संसारा किन्हें एहड़ा प्यार रख्या, कि तिने आपणा एकुलौता पुत्र देई दितेया, ताकि जो कोई तेस पर विस्वास करे, से नास नी हो, पर अनंत जिंदगी पाए। |

Both models already get the Mandyali grammar right (`परमेसरे`, `किन्हें`, `तिने`, `देई दितेया`,
`नी हो`). The extra data mostly fixes **individual words**: the full model writes `एहड़ा` and
`जिंदगी पाए` like the real translation, where the 25% model wrote `ऐहड़ा`, `इकलौटा` and
`जीउना पाई सके`.

---

## 4. What the results mean

1. **More data always helps, but each extra step helps less.** Going from 25% to 50% adds about
   2–4 chrF++ points; from 75% to 100% only about 1. The curves have not completely flattened, so
   more Bible data would still help a little.

2. **A quarter of the data already does most of the work.** With 1,511 verses the models reach
   **60 (Mandyali), 40 (Bilaspuri) and 64 (Kangri)** chrF++, which is **89–91% of their
   full-data score** and about three times the best existing tool. Why so fast?
   - NLLB already knows Hindi and several related North Indian languages, so it does not learn
     a language from zero; it learns how these languages *differ* from Hindi.
   - Most of that difference is **regular**: small words (`होर`/`कने` for "and", `मन्झ`/`च` for
     "in"), word endings and common words. A model learns those from a few hundred examples.
   - What the extra data adds is the **long tail**: rare words, names, spellings and idioms, which
     each appear only a few times. That is why the gains get smaller.

   **For Hamirpuri this is good news:** about 1,500 sentences, our collection target, should
   already give a useful model.

3. **The joint-vs-separate result is solid.** At every data size, joint training helps
   Bilaspuri, slightly hurts Mandyali and makes no difference for Kangri, and these differences
   are statistically real. So it is a property of the languages (Bilaspuri is close to Kangri;
   Mandyali is the most distinct), not luck from one training run.

4. **Bilaspuri's problem is not the amount of data.** The Kangri model trained on a quarter of the
   data (64.4) beats the Bilaspuri model trained on all of it (44.5), and Bilaspuri also gains the
   least from extra data (about +4 points from 25% to 100%, vs about +7 for the others). This supports the Stage 1 explanation: the Bilaspuri Bible
   translation itself is harder to learn (inconsistent spelling, freer wording).

---

## 5. Limits

- **Fixed training length.** Every model trained for 10 passes over its data, so the smaller sets
  also got fewer training updates (950 instead of 3,780 for a separate model). Every model was
  still improving slightly at the end. The low-data scores are therefore a little pessimistic,
  which makes finding 2 even stronger.
- **Same translation team in training and test** (as in Stage 1): absolute scores are higher than
  they would be on everyday text. The *differences between data sizes* are still meaningful,
  because every model is tested the same way.
- **One random subset per size.** We did not repeat each size with different random verses;
  the smooth curves suggest this would change little.

---

## 6. Next

1. **Error analysis (Stage 2, part 2):** 30 wrong translations per language (from the best
   full-data model) are being labelled by a native speaker into 10 types, for example "Hindi word
   kept", "wrong ending", "word order", "left out", and "acceptable paraphrase, not an error".
2. **Hamirpuri test:** run these models on the native-speaker Hamirpuri sentences, to see how
   they handle everyday language they were never trained on.

All code, scores and model outputs are in the project repository (`src/finetune.py`,
`src/stage2_wsl.sh`, `src/evaluate.py`, `results/scores/ablation.csv`).
