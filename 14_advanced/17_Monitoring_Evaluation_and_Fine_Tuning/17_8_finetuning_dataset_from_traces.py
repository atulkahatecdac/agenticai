import json
import os
import random
import re
import sys

from dotenv import load_dotenv

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# From production traces to a fine-tuning dataset.
#
# Every traced run (Module 09) is a real question and the app's real
# answer. The ones users rated well are exactly the examples you want a
# smaller, cheaper model to copy. The work is in the cleaning:
#
#   1. keep  : runs with good feedback and no error
#   2. scrub : remove PII - it must never be trained into a model
#   3. dedupe: the same Q&A twice teaches nothing and skews the mix
#   4. split : hold back a test set the model never trains on (17_4)
#   5. write : the chat JSONL format OpenAI fine-tuning and most open
#              trainers (Hugging Face TRL, Unsloth, Axolotl) accept
#
#   python 17_8_finetuning_dataset_from_traces.py                  (bundled sample traces)
#   python 17_8_finetuning_dataset_from_traces.py --langsmith <project>
#     (your project's root runs, with "thumbs" feedback from 09_x)
# =====================================================================

SYSTEM = "You are the support assistant for an online store. Answer briefly and politely."
SAMPLE = os.path.join(BASE_DIR, "data", "sample_support_traces.jsonl")


def load_sample() -> list[dict]:
    with open(SAMPLE, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_langsmith(project: str) -> list[dict]:
    from langsmith import Client
    runs = []
    for run in Client().list_runs(project_name=project, is_root=True, limit=500):
        stats = run.feedback_stats or {}
        runs.append({
            "id": str(run.id),
            "inputs": run.inputs or {},
            "outputs": run.outputs or {},
            "feedback": {k: v.get("avg") for k, v in stats.items()},
            "error": run.error,
            "latency_s": (run.end_time - run.start_time).total_seconds() if run.end_time else None,
        })
    return runs


PII = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<EMAIL>"),
    (re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), "<PHONE>"),
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "<CARD>"),
]


def scrub(text: str) -> str:
    for pattern, tag in PII:
        text = pattern.sub(tag, text)
    return text


if __name__ == "__main__":
    if "--langsmith" in sys.argv:
        project = sys.argv[sys.argv.index("--langsmith") + 1]
        runs, source = load_langsmith(project), f"LangSmith project '{project}'"
    else:
        runs, source = load_sample(), os.path.basename(SAMPLE)
    print(f"Loaded {len(runs)} runs from {source}\n")

    kept, seen, reasons = [], set(), {"error": 0, "no thumbs-up": 0, "missing text": 0, "duplicate": 0}
    scrubbed = 0
    for run in runs:
        q = (run["inputs"] or {}).get("question")
        a = (run["outputs"] or {}).get("answer")
        if run["error"]:
            reasons["error"] += 1; continue                       # 1. keep only clean runs...
        if (run["feedback"] or {}).get("thumbs") != 1:
            reasons["no thumbs-up"] += 1; continue                # ...that users liked
        if not q or not a:
            reasons["missing text"] += 1; continue
        clean_q, clean_a = scrub(q), scrub(a)                     # 2. scrub PII
        scrubbed += (clean_q != q) + (clean_a != a)
        key = (clean_q.lower().strip(), clean_a.lower().strip())
        if key in seen:
            reasons["duplicate"] += 1; continue                   # 3. dedupe
        seen.add(key)
        kept.append({"messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": clean_q},
            {"role": "assistant", "content": clean_a},
        ]})

    random.Random(42).shuffle(kept)                               # 4. split
    cut = max(1, int(len(kept) * 0.8))
    splits = {"train": kept[:cut], "test": kept[cut:]}
    for name, rows in splits.items():                             # 5. write JSONL
        path = os.path.join(BASE_DIR, "data", f"finetune_{name}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        print(f"wrote {len(rows):3} examples -> data/finetune_{name}.jsonl")

    print(f"\nDropped: " + ", ".join(f"{n} {r}" for r, n in reasons.items()))
    print(f"PII scrubbed in {scrubbed} field(s)")
    print("\nOne training example:")
    print(json.dumps(splits["train"][0], indent=2, ensure_ascii=False))
    pii_example = next((r for r in kept if "<PHONE>" in json.dumps(r) or "<EMAIL>" in json.dumps(r)), None)
    if pii_example:
        print("\nAfter scrubbing:\n  user:", pii_example["messages"][1]["content"])
    print("\nNext: 17_4 trains a LoRA adapter on data like this; evaluate it on finetune_test.jsonl against the")
    print(f"base model before switching traffic. Rule of thumb: start with a few hundred good examples, not {len(kept)}.")
