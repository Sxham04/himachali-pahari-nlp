# Project 1 report: Hindi and three Pahari languages, studied with Bible data

_Soham Sharma · plain-language report · status as of 2026-10-18 (Steps 0–7 done; Stage 2 next)_

Technical details, every number and all figures: [`results/README.md`](../results/README.md).
The plan this follows: [`project1-bible-plan.md`](project1-bible-plan.md).

---

## The idea in one paragraph

Mandyali, Bilaspuri and Kangri are spoken by lakhs of people in Himachal Pradesh, but computers
know almost nothing about them. No translation app supports them. We found the same New
Testament translated into **Hindi, Mandyali, Bilaspuri and Kangri**, verse by verse, which
gives us about 7,500 sentences that mean the same thing in all four languages. With this
table we asked three questions:

1. **How close are these languages to Hindi, and to each other?**
2. **Can a computer tell them apart?**
3. **Can today's translation tools translate Hindi into them?**

---

## Step 0: Cleaning the data

Before measuring anything, we checked the data carefully, and found real problems:

- **13 cells had other verses pasted inside them** (copy-paste accidents), and 4 rows were
  empty or almost empty. These were removed.
- **Bilaspuri was shifted out of place in 1 Corinthians (chapters 3–6 and 15–16).** The text
  sat next to the wrong verse numbers, so the "same verse" in Bilaspuri was actually a
  different verse. A small program found these by checking which verse each text matches
  best. In total 204 verses were removed for this reason.
- **Mandyali used the English letter "l" instead of the full stop `।`.** We fixed it. Left
  alone, a computer could recognise Mandyali just from that one letter, which would be cheating.
- **Hindi verses carried Bible cross-references** like `(उत्प. 19:26)` that the other
  languages don't have. We removed them.

**Result:** 7,346 clean verses out of 7,567 (97%). We split them by book:

| Part | Book(s) | Verses | Used for |
|---|---|---|---|
| Training | 25 books | 6,045 | teaching models |
| Checking | Romans | 430 | tuning settings |
| Final test | John | 871 | the final score, used only once |

John is the test book because it repeats the other gospels the least, so a model can't
"remember" the answer from a similar verse it saw in training.

---

## Step 1: How big and how varied is each language? (dataset statistics)

| | Hindi | Mandyali | Bilaspuri | Kangri |
|---|---|---|---|---|
| Total words | 169,305 | 180,688 | 186,210 | 173,439 |
| Different words | 6,292 | 8,768 | 12,909 | 9,167 |
| Words in John never seen in training | 1.3% | 3.3% | **5.4%** | 2.6% |

**What this means:**
- For the same verses, the Pahari texts use **40–105% more different words** than Hindi.
  Two reasons: these languages change word endings more, and their spelling is not
  standardised (one word can be written several ways).
- **Bilaspuri has the most variety** and the most unseen words, so we expected it to be the
  hardest to translate. (Step 4 confirmed this.)

---

## Step 2: How close are the languages? (Part A)

We compared each verse with the same verse in another language and measured how many small
letter chunks they share (a score called **chrF**, 0–100; higher = more similar).

| | Hindi | Mandyali | Bilaspuri | Kangri |
|---|---|---|---|---|
| **Hindi** | – | 26.6 | 24.7 | 25.4 |
| **Mandyali** | 26.6 | – | 29.2 | 27.5 |
| **Bilaspuri** | 24.7 | 29.2 | – | **33.0** |
| **Kangri** | 25.4 | 27.5 | **33.0** | – |

![How similar the languages are](../results/analysis/chrf_heatmap.png)

**What this means:**
1. **Bilaspuri and Kangri are the closest pair.** Mandyali sits a little apart.
2. **The three Pahari languages are closer to each other than to Hindi**, though only by a
   few points.
3. **Hindi is about equally far from all three.**
4. The small, everyday words are what differ most. For example:

   | Meaning | Hindi | Mandyali | Bilaspuri | Kangri |
   |---|---|---|---|---|
   | "and" | और | होर | कने | कने |
   | "in" | में | मन्झ | च | च |
   | "of" | का / के | रा / रे | रा / रे | दा / दे |

**One caution:** each Bible was translated freely by a different team, so these scores mix
real language differences with each team's writing style. They are good for comparing pairs,
not as exact distances.

---

## Step 3: Can a computer tell the languages apart? (Part B)

We built a simple program that looks at short letter patterns and guesses the language of a
sentence. We trained it on the training books and tested it on John.

| What the program sees | Correct guesses |
|---|---|
| A full verse | **99.9%** |
| First 10 words | 99.2% |
| First 5 words | 96.7% |
| First 3 words | 90.9% |
| First 2 words | 81.4% |
| First 1 word | 72.4% |
| _(random guessing)_ | _25%_ |

![Accuracy by number of words](../results/dialect_id/accuracy_by_length.png)

**What this means:**
1. The four languages are **clearly different**: a simple program separates them almost
   perfectly, and needs only about 5 words to be right 97% of the time.
2. Its most common mistake is **mixing up Kangri and Bilaspuri**, the same pair Step 2 found
   to be closest. Two different methods agree, which makes the finding stronger.
3. **One caution:** each language here comes from one translation team, so the program may
   partly be learning that team's spelling habits (e.g. यीसू vs यीशु). The real test will be
   text from other speakers, such as the Hamirpuri sentences (Project 2).

---

## Step 4: How do translation models "see" these languages? (word splitting)

Translation models don't read whole words. They cut words into smaller pieces from a fixed
list. If a language is new to the model, its words get cut into more, smaller pieces, which
usually means the model understands it worse.

| Pieces per word | Hindi | Mandyali | Bilaspuri | Kangri |
|---|---|---|---|---|
| NLLB (the model we will train) | 1.20 | 1.74 | 1.70 | 1.81 |
| IndicTrans2 | 1.10 | 1.45 | 1.42 | 1.42 |

![Pieces per word](../results/stats/fertility.png)

**What this means:**
1. Both models keep most Hindi words whole, but **break up about a third to a half of all
   Pahari words**. To these models, Pahari looks like "broken Hindi".
2. **NLLB cannot write one Bilaspuri letter at all:** `ऴ` (a retroflex "ḷ" sound) is missing
   from its list. It appears 928 times in the Bilaspuri text. We must handle this before
   training (Part D).

---

## Step 5: Can today's tools translate Hindi into these languages? (Part C)

We asked three "translators" to translate the 871 Hindi verses of John:

1. **Copy:** just hand back the Hindi unchanged. This is the "do nothing" option, and the
   minimum any real tool should beat.
2. **IndicTrans2:** the best Indian translation model (AI4Bharat). It doesn't know our three
   languages, so we asked for **Dogri**, the closest Pahari language it supports.
3. **Gemma:** a small AI chatbot from Google, running on the laptop. We showed it 5 example
   translations and asked it to continue.

Each output was compared with the real Bible translation using **chrF++** (0–100: how many
letters and words it shares with the correct translation; 100 = identical).

| | Mandyali | Bilaspuri | Kangri |
|---|---|---|---|
| Copy (Hindi unchanged) | 21.0 | 18.8 | 20.0 |
| IndicTrans2 → Dogri | 16.1 | 17.3 | 20.6 |
| Gemma (5 examples) | 21.7 | 18.6 | 21.2 |

**What this means:**
1. **No existing tool can translate into these languages.** The best one (Gemma) scores
   almost exactly the same as just returning the Hindi unchanged: at most about 1 point
   better. In practice, none of them adds anything.
2. **Using a "nearby" language doesn't work.** IndicTrans2 writes good Dogri, but Dogri is
   different enough that for Mandyali and Bilaspuri it scores *worse* than plain Hindi. It only
   roughly ties for Kangri, the language closest to Dogri.
3. **The AI chatbot fakes it.** Gemma writes mostly Hindi and sprinkles in a few Pahari words
   it saw in the examples (`होर`, `कने`). Sometimes it uses a word from the wrong language
   (Mandyali `होर` in Bilaspuri), and in 14 out of 2,613 answers it got stuck repeating one
   letter.
4. **Bilaspuri is the hardest** for every system, just as Step 1 predicted.
5. **Why all scores are low (about 20):** the reference Bibles are free translations, not
   word-for-word. Even a correct translation loses points if it chooses different words. So we
   compare systems against each other, not against scores from other datasets.

A real example (John 1:1):

| | Text |
|---|---|
| Hindi | आदि में वचन था, और वचन परमेश्वर के साथ था, और वचन परमेश्वर था। |
| Real Bilaspuri | सृष्टिया ते पैहले बचन था, कने बचन परमेशरा सौगी था, कने बचन ई परमेशर था। |
| IndicTrans2 (Dogri) | शुरू च वचन हा, ते वचन भगवान दे कन्नै हा, ते वचन भगवान हा। |
| Gemma | अदी में शब्द था, कने सै रे शब्द परमेशर के साथ था, कने परमेशर री शब्द था। |

---

## Step 6: Where does Hamirpuri fit? (the Hamirpuri check)

Alongside the Bible data, a native speaker from my family (speaker code `MA`) has translated **509
everyday Hindi sentences into Hamirpuri**, and I proof-read all of them (88 needed corrections,
17%). We gave these 509 sentences to the language identifier from Step 3. It only knows Hindi,
Mandyali, Bilaspuri and Kangri, so for each Hamirpuri sentence it picks the closest of the four.
As a check, we also gave it the 509 Hindi originals.

| | Hindi | Mandyali | Bilaspuri | Kangri |
|---|---|---|---|---|
| Hamirpuri sentences | 6% | 6% | 40% | **48%** |
| Hindi originals (check) | **96%** | 2% | 1% | 1% |

![Hamirpuri check](../results/hamirpuri_check/shares.png)

**What this means:**
1. The check works: Hindi sentences are recognised as Hindi 96% of the time.
2. **Hamirpuri is closest to Kangri, then Bilaspuri**, and far from Mandyali and Hindi. This
   matches the map: Hamirpur lies between Kangra and Bilaspur.
3. The small words show why. Hamirpuri says "of" like Kangri (`दा / दे / दी`), never like
   Mandyali or Bilaspuri (`रा / रे / री`), and shares `कने` ("and") and `च` ("in") with both
   neighbours.
4. But Hamirpuri also has **its own words** that none of the three Bible languages uses:
   `असां` ("we"), `तुसां` ("you") and `बिच` ("in"). So Hamirpuri is not just Kangri: it needs
   its own dataset, which is exactly what we are building.

(Only totals are reported; the sentences themselves stay private.)

---

## Step 7: Teaching a model the three languages (Stage 1)

Following Dr. Shweta Chauhan's review, we fine-tuned **NLLB**, an open translation model that
already knows Hindi, on the 6,045 training verses. We used **LoRA**, which trains small add-on
layers (1.4% of the model) instead of the whole model, so it runs on a laptop GPU. We trained:

- **three separate models**, one per language, and
- **one joint model** that learns all three languages at once.

Each was tested once on the 871 verses of John, which it had never seen. We report three scores:
**chrF++** and **BLEU** (higher = better) and **TER** (how many edits are needed to fix the
output; lower = better).

| chrF++ on John | Mandyali | Bilaspuri | Kangri |
|---|---|---|---|
| Best existing tool (Step 5) | 21.7 | 18.8 | 21.2 |
| **Our separate models** | **67.8** | 43.5 | 71.1 |
| **Our joint model** | 67.0 | **44.5** | **71.3** |

| BLEU / TER on John | Mandyali | Bilaspuri | Kangri |
|---|---|---|---|
| Best existing tool | 2.6 / 89.8 | 1.2 / 95.1 | 2.6 / 88.2 |
| Our separate models | 46.7 / 35.4 | 17.3 / 66.5 | 51.0 / 31.6 |
| Our joint model | 45.7 / 36.1 | 17.9 / 64.8 | 51.4 / 31.4 |

![Translation scores](../results/scores/scores_chrf.png)

**What this means:**
1. **It works, by a wide margin.** Scores jump from about 21 to **68 (Mandyali), 44
   (Bilaspuri) and 71 (Kangri)**. A statistical test confirms every model beats every existing
   tool. The output reads like the real language, not Hindi:

   | | John 1:1 |
   |---|---|
   | Hindi | आदि में वचन था, और वचन परमेश्वर के साथ था, और वचन परमेश्वर था। |
   | Real Mandyali | सभी ले पैहले वचन था, होर वचन परमेसरा साउगी था, होर वचन ई परमेसर था। |
   | Our Mandyali model | आदि मन्झ वचन था, होर वचन परमेसरा साउगी था, होर वचन परमेसर था। |

2. **One joint model or three separate ones? It depends on the language**, and the answer
   matches Step 2:
   - **Bilaspuri gets better** with the joint model (+1.0, statistically significant). It is the
     hardest language and close to Kangri, so it learns from Kangri's data.
   - **Mandyali gets slightly worse** (−0.9, significant). It is the most different of the
     three, so the others get in its way a little.
   - **Kangri: no real difference.**
3. **Bilaspuri is still the hardest** (44 vs about 70). This is most likely about *this Bible
   translation*, not the language itself:
   - **Most varied wording:** 12,909 different words (vs about 9,000 for the others), half of
     them used only once, which points to inconsistent spelling. A word seen once is hard to learn.
   - **More unseen words in the test:** 5.4% of John's words never appear in training (vs 2.6–3.3%).
   - **Freer translation:** it paraphrases more. In John 1:1 it says "सृष्टिया ते पैहले" (before
     creation) where Hindi says "आदि में" (in the beginning); our model wrote "आदि च", which is
     correct but gets no credit.
   - **Noisiest source:** this text had the shifted verses in 1 Corinthians; small misalignments
     may remain.
4. **One caution:** each language's training and test verses come from the same translation
   team, so the model also learns that team's style. On everyday sentences, scores will be lower.

---

## What we have shown so far

1. **The data is usable**, after careful cleaning that found and fixed real errors.
2. **The three languages are real, distinct languages**, not just "Hindi with an accent".
   They are closer to each other than to Hindi, and a computer can tell them apart easily.
3. **There is a clear gap:** no existing translation tool handles them, not even the best
   Indian model or a modern AI chatbot.
4. **Hamirpuri sits between Kangri and Bilaspuri**, with words of its own, so it deserves
   its own dataset.
5. **The gap can be closed:** a small fine-tuned model lifts translation quality from about 21
   to 44–71 chrF++, and training the languages together helps the hardest one (Bilaspuri).

These results are the core of the paper.

---

## What comes next

**Stage 2 (set by Dr. Chauhan):**
1. **How much data is needed?** Retrain with 25%, 50%, 75% and 100% of the training verses and
   compare the scores.
2. **What goes wrong?** Collect 20–30 incorrect translations per language and explain each
   mistake.

---

## How we did it, and why

A short guide to every method and model, and the reason we chose it.

### Preparing the data

| What | Why |
|---|---|
| **Cleaning before anything else** (removing pasted, empty and misaligned verses; fixing the Mandyali full stop) | Every later number depends on the verses really matching. One shifted block would teach the model wrong translations and make test scores meaningless. |
| **Splitting by book** (train 25 books, check on Romans, test on John) | If verses from the same book were in both training and test, the model could "remember" answers. Whole books keep the test honest. John repeats the other gospels least, so it is the fairest test. |
| **Test set used only once, at the very end** | Choosing settings by looking at the test scores would quietly inflate them. Romans is used for all decisions instead. |

### Measuring similarity and telling languages apart

| Method | What it does | Why we chose it |
|---|---|---|
| **chrF between aligned verses** (Step 2) | Counts shared letter chunks between the same verse in two languages | Works at the letter level, so it gives credit for related words with different endings or spellings (`परमेसर` / `परमेशर`). Word-level measures would miss this. |
| **Weighted log-odds** (typical words) | Finds words much more common in one language than another, adjusted for chance | A standard, well-tested way to pick out characteristic words without being fooled by rare ones. |
| **Letter-pattern classifier** (TF-IDF on 1–4 letter chunks + logistic regression, Step 3) | Learns which letter patterns belong to which language | Simple, fast (runs on a normal CPU in minutes) and very strong for telling closely related languages apart. Letter chunks capture word endings and spellings, which is exactly where these languages differ. A big neural model would add cost without much gain. |
| **Word-splitting count** (tokenizer fertility, Step 4) | Counts how many pieces a model cuts each word into | A quick, model-free way to see whether a translation model "knows" a language before training anything. |

### The translation systems

| System | What it is | Why we included it |
|---|---|---|
| **Copy** | Returns the Hindi unchanged | The floor: since these languages share many words with Hindi, copying already scores something. Any useful system must beat it. |
| **IndicTrans2-1B** (AI4Bharat) | The strongest open translation model for Indian languages | It represents the best existing Indian MT. It doesn't support our languages, so we asked for **Dogri**, the closest Pahari language it knows. |
| **Gemma 3 4B** (Google), 5 examples | A small open AI chatbot model, run locally with Ollama | Represents the "just ask an AI" approach. 4B is the largest that runs comfortably on an 8 GB laptop GPU. Open and local, so anyone can repeat the test (closed tools like ChatGPT or Google Translate can change any day and don't support these languages). |
| **NLLB-200-distilled-600M + LoRA** (our models) | Meta's open translation model for 200 languages, adapted to ours | See below. |

**Why NLLB?**
- It already translates **Hindi** well and knows many related North Indian languages, so it starts
  close to our target.
- It is the most widely used open model for **low-resource translation research**, so our results
  are easy to compare with other papers.
- The **600M "distilled"** version is small and fast enough to fine-tune on an 8 GB laptop GPU.
- Note for later: NLLB's licence allows research use but not commercial use.

**Why LoRA?**
- Instead of changing all 600 million numbers in the model, LoRA trains small **add-on layers
  (1.4% of the model)**. This fits on the laptop, trains in about 35–45 minutes per language,
  and is less likely to over-fit with only 6,000 training verses.
- The result is a small file (about 35 MB) per language that sits on top of the original model,
  easy to share and swap.

**Other choices inside the training:**

| Choice | Why |
|---|---|
| **Borrowed language codes** (Mandyali uses Awadhi's code, Bilaspuri Bhojpuri's, Kangri Magahi's) | NLLB needs a code to know which language to write, and has none for ours. Borrowing unused codes is a standard trick; training then teaches the model what each code now means. |
| **`ऴ` written as `ळ`** | NLLB has no symbol for `ऴ`, so it could never write it. We converted it in the training text and in every reference, so all systems are scored the same way. |
| **Early stopping on Romans** | Training stops when the check score stops improving, and the best version is kept, which avoids over-training. |
| **Beam search (5)** when translating | The model compares 5 candidate translations at each step instead of 1, which usually gives better sentences. |
| **Separate vs joint models** (Dr. Chauhan's design) | Tests whether the three languages help each other when learned together. |

### Scoring and checking the results

| Method | What it measures | Why |
|---|---|---|
| **chrF++** (main score) | Shared letter chunks and words with the correct translation (0–100) | Gives partial credit for near-correct words, which suits languages with many word endings and no fixed spelling. Recommended for Indian languages. |
| **BLEU** and **spBLEU** | Shared whole words / word pieces | The long-standing standard; reported so other papers can compare. spBLEU splits words the same way for every language, which is fairer for Indian scripts. |
| **TER** | How many edits are needed to turn the output into the correct translation (lower = better) | Easy to interpret, and added at Dr. Chauhan's request. |
| **sacrebleu** | The software that computes all of the above | The standard tool in MT papers; it records its exact settings, so anyone gets identical numbers. |
| **Paired bootstrap test** | Re-scores 1,000 random re-samplings of the test verses | Tells whether a difference between two systems is real or could be luck. Expected in any MT paper. |

### The Hamirpuri check

| What | Why |
|---|---|
| Run the language identifier (Step 3) on the Hamirpuri sentences | A cheap way to place a new language among known ones without any Hamirpuri training data. |
| Also run it on the Hindi originals | A control: if those didn't come out as Hindi, the method wouldn't be trustworthy. |
| Report only totals | The sentences are family data and stay private. |

---

## Limits to keep in mind

- **Religious, formal language.** The Bible is not everyday speech, so results may not carry
  over to daily conversation. Project 2 (Hamirpuri sentences from native speakers) addresses this.
- **One translation per language.** Each language comes from a single team, so their style
  affects all results.
- **Licences.** The Hindi and Kangri texts are openly licensed (CC BY-SA 4.0); the Mandyali
  and Bilaspuri licences are still being confirmed, so the data stays private for now.
