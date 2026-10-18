"""Stage 1: LoRA fine-tuning of NLLB-200-distilled-600M, Hindi -> Mandyali / Bilaspuri / Kangri.

    uv run python src/finetune.py --langs mjl                # separate model (also kfs, xnr)
    uv run python src/finetune.py --langs mjl kfs xnr        # joint multilingual model
    uv run python src/finetune.py --langs mjl kfs xnr --frac 0.25   # Stage 2 data ablation

Train = 25 train books, early stopping on dev (ROM) loss, test once on JHN (beam 5).
NLLB has no codes for these languages, so each borrows an unused Devanagari code (TAGS).
Writes models/<name>/ (LoRA adapter, git-ignored) and results/finetune/<name>/{<lang>.txt, train_log.json}.
"""
import argparse
import json
import time

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq, EarlyStoppingCallback,
                          Seq2SeqTrainer, Seq2SeqTrainingArguments)

from data import ROOT, fold_lla, read_clean

BASE = "facebook/nllb-200-distilled-600M"
SRC = "hin_Deva"
TAGS = {"mjl": "awa_Deva", "kfs": "bho_Deva", "xnr": "mag_Deva"}  # borrowed, same in every model
MAX_LEN = 256
LORA = dict(r=16, lora_alpha=32, lora_dropout=0.05, task_type="SEQ_2_SEQ_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "out_proj", "fc1", "fc2"])


def run_name(langs: list[str], frac: float) -> str:
    base = "joint" if len(langs) > 1 else langs[0]
    return base if frac == 1 else f"{base}_f{round(frac * 100)}"


def pairs(df, langs: list[str], frac: float = 1.0, seed: int = 0) -> list[dict]:
    """(src, tgt, lang) per verse per language; frac keeps the same random verse subset for every language."""
    if frac < 1:
        df = df.sample(frac=frac, random_state=seed)
    return [{"src": s, "tgt": fold_lla(t), "lang": c} for c in langs for s, t in zip(df.hin, df[c])]


def encode(tok, rows: list[dict]) -> Dataset:
    """Tokenise per language so each target starts with its own language tag."""
    feats = []
    for lang in dict.fromkeys(r["lang"] for r in rows):
        group = [r for r in rows if r["lang"] == lang]
        tok.tgt_lang = TAGS[lang]
        enc = tok([r["src"] for r in group], text_target=[r["tgt"] for r in group], max_length=MAX_LEN, truncation=True)
        feats += [{k: enc[k][i] for k in ("input_ids", "attention_mask", "labels")} for i in range(len(group))]
    return Dataset.from_list(feats).shuffle(seed=0)


@torch.no_grad()
def translate(model, tok, srcs: list[str], lang: str, beams: int = 5, bs: int = 16) -> list[str]:
    model.eval()
    bos = tok.convert_tokens_to_ids(TAGS[lang])
    out = []
    for i in range(0, len(srcs), bs):
        batch = tok(srcs[i:i + bs], return_tensors="pt", padding=True, truncation=True, max_length=MAX_LEN).to(model.device)
        gen = model.generate(**batch, forced_bos_token_id=bos, num_beams=beams, max_new_tokens=MAX_LEN)
        out += tok.batch_decode(gen, skip_special_tokens=True)
    return [o.strip() for o in out]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", choices=list(TAGS), required=True)
    ap.add_argument("--frac", type=float, default=1.0, help="share of training verses (Stage 2 ablation)")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()
    name = run_name(args.langs, args.frac)
    model_dir, out_dir = ROOT / "models" / name, ROOT / "results" / "finetune" / name
    out_dir.mkdir(parents=True, exist_ok=True)

    df = read_clean()
    split = {s: df[df.split == s] for s in ("train", "dev", "test")}
    tok = AutoTokenizer.from_pretrained(BASE, src_lang=SRC)
    train = encode(tok, pairs(split["train"], args.langs, args.frac))
    dev = encode(tok, pairs(split["dev"], args.langs))

    model = AutoModelForSeq2SeqLM.from_pretrained(BASE, dtype=torch.bfloat16)
    model = get_peft_model(model, LoraConfig(**LORA))
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)

    trainer = Seq2SeqTrainer(
        model=model,
        args=Seq2SeqTrainingArguments(
            output_dir=str(model_dir / "ckpt"), num_train_epochs=args.epochs, learning_rate=args.lr,
            per_device_train_batch_size=args.batch, per_device_eval_batch_size=8,  # eval logits over the 256k vocab: 32 ran out of 8 GB
            warmup_steps=0.05, lr_scheduler_type="linear", bf16=True, eval_strategy="epoch",
            save_strategy="epoch", save_total_limit=2, load_best_model_at_end=True,
            metric_for_best_model="eval_loss", greater_is_better=False, logging_steps=50,
            report_to=[], seed=0, dataloader_num_workers=0, train_sampling_strategy="group_by_length"),
        train_dataset=train, eval_dataset=dev,
        data_collator=DataCollatorForSeq2Seq(tok, model=model, padding=True),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )
    t0 = time.time()
    trainer.train()
    train_min = (time.time() - t0) / 60
    model.save_pretrained(model_dir)

    test = split["test"]
    for lang in args.langs:
        hyps = translate(model, tok, test.hin.tolist(), lang)
        (out_dir / f"{lang}.txt").write_text("\n".join(h.replace("\n", " ") for h in hyps) + "\n", encoding="utf-8")

    evals = [{"epoch": h["epoch"], "eval_loss": round(h["eval_loss"], 4)} for h in trainer.state.log_history if "eval_loss" in h]
    log = {"run": name, "langs": args.langs, "frac": args.frac, "train_pairs": len(train), "dev_pairs": len(dev),
           "base": BASE, "tags": {c: TAGS[c] for c in args.langs}, "lora": LORA, "lr": args.lr, "batch": args.batch,
           "trainable_params": trainable, "best_checkpoint": trainer.state.best_model_checkpoint,
           "best_eval_loss": trainer.state.best_metric, "evals": evals, "train_minutes": round(train_min, 1)}
    (out_dir / "train_log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(log, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import pandas as pd
    toy = pd.DataFrame({"hin": ["क", "ख", "ग", "घ"], "mjl": ["ऴ1", "2", "3", "4"], "kfs": ["5", "6", "7", "8"]})
    p = pairs(toy, ["mjl", "kfs"], frac=0.5)
    assert len(p) == 4 and [r["src"] for r in p[:2]] == [r["src"] for r in p[2:]]  # same verses per language
    assert pairs(toy, ["mjl"])[0]["tgt"] == "ळ1" and run_name(["mjl", "kfs"], 0.25) == "joint_f25"
    main()
