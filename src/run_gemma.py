"""Part C baseline: Gemma 3 4B (Ollama), 5-shot Hindi -> Mandyali / Bilaspuri / Kangri, on JHN.

Needs Ollama running locally with `ollama pull gemma3:4b`.
Run: uv run python src/run_gemma.py
Writes results/baselines/gemma_{mjl,kfs,xnr}.jsonl ({"ref": ..., "hyp": ...} per verse, test order).
Resumable: verses already in the file are skipped.
"""
import json
import urllib.request

from data import NAMES, ROOT, read_clean, words

MODEL = "gemma3:4b"
URL = "http://localhost:11434/api/chat"
OUT = ROOT / "results" / "baselines"
N_SHOTS = 5
DESCRIBE = {
    "mjl": "Mandyali (Mandeali), the Western Pahari language of Mandi, Himachal Pradesh",
    "kfs": "Bilaspuri (Kahluri), the Western Pahari language of Bilaspur, Himachal Pradesh",
    "xnr": "Kangri, the Western Pahari language of Kangra, Himachal Pradesh",
}


def shots(train, lang: str, n: int = N_SHOTS) -> list[tuple[str, str]]:
    """Fixed examples: n train verses of 10-20 Hindi words, evenly spread over the train books."""
    pool = train[train.hin.map(lambda t: 10 <= len(words(t)) <= 20)]
    step = len(pool) // n
    return [(r.hin, getattr(r, lang)) for r in pool.iloc[::step].head(n).itertuples()]


def messages(lang: str, examples: list[tuple[str, str]], hindi: str) -> list[dict]:
    system = (f"You translate Hindi into {DESCRIBE[lang]}. Write in Devanagari. "
              f"Reply with only the {NAMES[lang]} translation, nothing else.")
    msgs = [{"role": "system", "content": system}]
    for h, t in examples:
        msgs += [{"role": "user", "content": h}, {"role": "assistant", "content": t}]
    return msgs + [{"role": "user", "content": hindi}]


def clean_reply(s: str) -> str:
    lines = [ln.strip() for ln in s.strip().splitlines() if ln.strip()]
    return lines[0].strip("\"'“”") if lines else ""


def chat(msgs: list[dict]) -> tuple[str, bool]:
    """Returns (reply, aborted). Streams so a reply Ollama aborts (e.g. "token repeat limit
    reached" when the model loops on one character) is kept as the partial output it produced."""
    body = json.dumps({"model": MODEL, "messages": msgs, "stream": True,
                       "options": {"temperature": 0, "seed": 0, "num_ctx": 4096, "num_predict": 300}})
    req = urllib.request.Request(URL, body.encode(), {"Content-Type": "application/json"})
    out = ""
    with urllib.request.urlopen(req, timeout=300) as r:
        for line in r:
            j = json.loads(line)
            if "error" in j:
                print(f"aborted: {j['error']}", flush=True)
                return out, True
            out += j.get("message", {}).get("content", "")
    return out, False


def main() -> None:
    df = read_clean()
    train, test = df[df.split == "train"], df[df.split == "test"]
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in DESCRIBE:
        ex = shots(train, lang)
        path = OUT / f"gemma_{lang}.jsonl"
        done = {json.loads(ln)["ref"] for ln in path.open(encoding="utf-8")} if path.exists() else set()
        with path.open("a", encoding="utf-8") as f:
            for r in test.itertuples():
                if r.ref in done:
                    continue
                reply, aborted = chat(messages(lang, ex, r.hin))
                rec = {"ref": r.ref, "hyp": clean_reply(reply)} | ({"aborted": True} if aborted else {})
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                done.add(r.ref)
                if len(done) % 50 == 0:
                    print(f"{lang}: {len(done)}/{len(test)}", flush=True)
        (OUT / f"gemma_{lang}_shots.json").write_text(json.dumps(ex, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    assert clean_reply('\n "मेरा घर"\nExplanation: ...') == "मेरा घर"
    assert len(messages("kfs", [("a", "b")], "c")) == 4
    main()
