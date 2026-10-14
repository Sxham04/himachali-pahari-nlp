"""Part C baseline: IndicTrans2-1B, Hindi -> Dogri, on the test book (JHN).

IndicTrans2's remote code needs transformers 4.46.x (5.x: import error; 4.57: past_key_values crash) and its IndicTransToolkit needs a C++ compiler,
so this runs in a separate venv and re-implements IndicProcessor's Devanagari path with
indic-nlp-library (normalise + tokenise before, detokenise after). One-time setup:

    uv venv .venv-it2 --python 3.12
    uv pip install --python .venv-it2 torch --index-url https://download.pytorch.org/whl/cu128
    uv pip install --python .venv-it2 "transformers==4.46.3" pandas sentencepiece numpy indic-nlp-library

Run: .venv-it2/Scripts/python src/run_indictrans2.py
Writes results/baselines/indictrans2_doi.txt (one line per test verse, test order).
"""
import time

import torch
from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
from indicnlp.tokenize import indic_detokenize, indic_tokenize
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from data import ROOT, read_clean

REPO = "ai4bharat/indictrans2-indic-indic-1B"
# pinned: trust_remote_code runs the repo's Python code, so only the revision we ran and checked
REVISION = "24d732922a0a91d0998d5568e3af37b7a21cd705"
SRC, TGT = "hin_Deva", "doi_Deva"
OUT = ROOT / "results" / "baselines" / "indictrans2_doi.txt"
BATCH, BEAMS, MAX_LEN = 8, 5, 256

normalizer = IndicNormalizerFactory().get_normalizer("hi")


def preprocess(s: str) -> str:
    return f"{SRC} {TGT} " + " ".join(indic_tokenize.trivial_tokenize(normalizer.normalize(s), "hi"))


def postprocess(s: str) -> str:
    return indic_detokenize.trivial_detokenize(s.strip(), "hi")


def main() -> None:
    df = read_clean()
    src = df[df.split == "test"].hin.tolist()
    tok = AutoTokenizer.from_pretrained(REPO, revision=REVISION, trust_remote_code=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(REPO, revision=REVISION, trust_remote_code=True, torch_dtype=torch.float16).cuda().eval()
    out, t0 = [], time.time()
    for i in range(0, len(src), BATCH):
        batch = tok([preprocess(s) for s in src[i:i + BATCH]], truncation=True, padding="longest",
                    return_tensors="pt", return_attention_mask=True).to("cuda")
        with torch.no_grad():
            gen = model.generate(**batch, num_beams=BEAMS, max_length=MAX_LEN, min_length=0, use_cache=True)
        with tok.as_target_tokenizer():
            dec = tok.batch_decode(gen, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        out += [postprocess(s) for s in dec]
        print(f"{len(out)}/{len(src)}  {time.time() - t0:.0f}s", flush=True)
    assert len(out) == len(src)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(o.replace("\n", " ") for o in out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    assert preprocess("कहा, ठीक।").startswith("hin_Deva doi_Deva कहा , ठीक ।")
    assert postprocess("कहा , ठीक ।") == "कहा, ठीक।"
    main()
