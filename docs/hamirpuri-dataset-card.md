# Hamirpuri elicitation dataset (dataset card, draft)

_Status 2026-10-15: 509 sentences translated and proof-read; 500 more (#510–1009) being translated._

## What it is

Everyday **Hindi sentences translated into Hamirpuri**, the Western Pahari variety of Hamirpur
district, Himachal Pradesh. Hamirpuri has no published NLP resources. The set is designed as a
clean **test/development benchmark** for Hindi → Hamirpuri translation, and as seed training data.

## How the prompts were designed

- **509 Hindi prompts** (English gloss, domain and grammar tag for each), written for everyday
  village and family life rather than formal text.
- **30 domains**: health 38, food 36, general 29, kinship 29, household 28, weather 27, village 26,
  farming 24, work 24, travel 22, social 19, festival 18, … plus dialogues and a short story.
- **Grammar tags** on every prompt (309 distinct tags): tense and aspect (habitual, perfect,
  progressive, past perfect), negation, imperatives (incl. negative and polite), questions,
  ergative and dative-experiencer constructions, causatives, passives, conditionals and
  counterfactuals, relative clauses, reported speech, feminine-speaker forms, and more.
- **Graded length**: batch 1 (#1–200) averages 4.7 Hindi words; batch 2 (#201–509) runs 4 → 10
  words. Overall: Hindi 6.1 words per sentence (max 11), Hamirpuri 5.5 (max 12).
- **Local context**: Hamirpur, Sujanpur Holi fair, Baba Balak Nath, dham, madra, siddu, army
  recruitment, monkeys in fields, step-wells.
- Short **dialogues** (shop, phone call, neighbour visit) and a **story** are kept in order, so
  they can stay together in one data split.

## How it was collected

- **Translator:** one native speaker of Hamirpuri (speaker code `MA`), translating from Hindi.
- **Tool:** a custom Google Apps Script web app shows one Hindi prompt at a time and saves each
  answer to a Google Sheet (append-only, with timestamps). The translator can skip a prompt.
- **Pace:** 509 sentences in 10 days (2026-10-05 → 10-14), up to ~90 per day; median ~48 seconds
  per sentence.

## How it was reviewed

- A second native speaker (the author) proof-read **every** sentence.
- Two routes: small fixes go into a separate `corrected` column (the original is kept); a
  prompt that needs redoing is **flagged** with a note, and the app shows it to the translator
  again (18 sentences were redone this way).
- **88 of 509 sentences (17.3%) were corrected**; on average 19.1% of characters changed in a
  corrected sentence (mostly small spelling and word-form fixes).
- Batch 1 (shorter): 5% corrected. Batch 2 (longer): 25% corrected. Longer sentences need more
  review, so new batches are capped at 10 words.

## Size

| | Sentences | Word tokens | Word types |
|---|---|---|---|
| Hindi prompts | 509 | 3,126 | – |
| Hamirpuri (proof-read) | 509 | 2,817 | 1,383 |

## Examples

| # | Hindi | Hamirpuri | English |
|---|---|---|---|
| 3 | आज बहुत ठंड है। | आज बड़ी ठंड लगादी | It is very cold today. |
| 27 | मेरे पास समय नहीं है। | मिजोगे निया बकत | I don't have time. |
| 88 | मैं अपने भाई के साथ आया हूँ। | मैं अपने पाई सौगी आउदा | I have come with my brother. |
| 230 | बस में बहुत भीड़ थी। | बसा बिच बडी भिड़ थी | The bus was very crowded. |
| 310 | साढ़े चार बजे बस आती है। | बस साडे चार बजे आऊंदी | The bus comes at half past four. |
| 445 | अपने दादा-दादी की सेवा करना हमारा फ़र्ज़ है। | अपणे दादू-दादी दी सेवा करणा असां दा फर्ज ऐ | Looking after our grandparents is our duty. |
| 497 | पुराने ज़माने में लोग मिट्टी के घरों में रहते थे। | पुराने जमाने बिच लोक मिट्टिया देयां करां बिच रैंदे थे | In the old days people lived in mud houses. |

Spelling follows the translator's own Devanagari writing; Hamirpuri has no standard orthography.

## First analysis

A dialect identifier trained on the Bible data (Hindi / Mandyali / Bilaspuri / Kangri) assigns
the Hamirpuri sentences to **Kangri 48%, Bilaspuri 40%, Mandyali 6%, Hindi 6%** (the Hindi prompts
themselves: 96% Hindi). Hamirpuri uses the Kangri genitive `दा/दे/दी`, shares `कने` ("and") and `च`
("in") with both neighbours, and has forms none of the Bible varieties use (`असां` "we",
`तुसां` "you", `बिच` "in"). Details: [results/README.md](../results/README.md#hamirpuri-check-srchamirpuri_checkpy-2026-10-15).

## Plans and limits

- Target ~1,500 human sentences (~500 test, ~200 dev, ~800 train), with dialogues/stories kept in
  one split; test and dev stay 100% human-written.
- **One translator** so far: her spelling and word choices shape the data. More speakers would help.
- Translated from Hindi prompts, so some Hindi influence on word order is possible.
- Consent: the translator agreed to the data being used for research; only speaker codes appear.
