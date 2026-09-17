import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import os
import sys
import numpy as np
import pandas as pd
import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model, PeftModel
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# 17_1-17_3 were all about OBSERVING a model you call over an API (OpenAI via
# LangGraph) - tracing it, metering it. This script is the other half of
# "Fine-Tuning" in this directory's name: actually CHANGING a model's weights,
# using PEFT's LoRA (Low-Rank Adaptation) instead of full fine-tuning.
#
# WHY LoRA, not just fine-tune everything: full fine-tuning of even this small
# a model means updating and storing all ~67M parameters. LoRA freezes the
# entire pretrained model and injects a pair of small trainable matrices
# (rank `r`) alongside a handful of target weight matrices - here, DistilBERT's
# attention query/value projections (`q_lin`/`v_lin` - confirmed by inspecting
# the model's named_modules(), not guessed). Only those small matrices (plus
# the classification head, which is untrained/random for a brand-new task and
# always needs to move - see MODULES_TO_SAVE below) get gradients. The payoff
# this script makes concrete via print_trainable_parameters(): well under 1%
# of the model's weights are ever updated, and the thing you save to disk
# afterward is a few hundred KB adapter, not a new 250MB+ copy of the model.
#
# TASK: sentiment classification (negative/neutral/positive), not text
# generation - a cleaner fit for demonstrating "before vs after" than a
# generative model would be, since accuracy is a single unambiguous number.
#
# DATASET: data/sentiment_data.csv - a custom 900-row sentiment dataset
# (course/learning-experience feedback text), balanced 300/300/300 across
# positive/neutral/negative. Expected columns are "text" and "sentiment"
# (label values "Positive"/"Neutral"/"Negative", case-insensitive - matched
# via .str.lower() below); an "id" column is present but unused. Swap in a
# different CSV with the same two columns and nothing else in this script
# needs to change - more rows just mean a longer training run, not different
# code.
#
# SETUP - everything here is a local HuggingFace model (distilbert-base-uncased),
# not an API call - no .env, no API key, no network needed if the model is
# already cached from a previous HuggingFace download (~270MB the first time).
#
#   pip install peft accelerate
#
# (transformers/torch/datasets are already required elsewhere in this repo -
# see requirements.txt.)
# =====================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "data", "sentiment_data.csv")
ADAPTER_DIR = os.path.join(SCRIPT_DIR, "lora_sentiment_adapter")

MODEL_NAME = "distilbert-base-uncased"
LABELS = ["negative", "neutral", "positive"]
LABEL2ID = {label: i for i, label in enumerate(LABELS)}
ID2LABEL = {i: label for i, label in enumerate(LABELS)}

EXAMPLE_SENTENCES = [
    "The instructor explained every concept clearly and answered all my questions.",
    "I found the assignments confusing and the deadlines unreasonable.",
    "The course consists of eight modules delivered over six weeks.",
]


def banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def load_dataset() -> tuple[Dataset, Dataset]:
    df = pd.read_csv(DATA_PATH)
    df["label"] = df["sentiment"].str.lower().map(LABEL2ID)
    df = df[["text", "label"]]
    train_df, eval_df = train_test_split(
        df, test_size=0.2, random_state=42, stratify=df["label"]
    )
    return Dataset.from_pandas(train_df, preserve_index=False), Dataset.from_pandas(eval_df, preserve_index=False)


def compute_metrics(eval_pred) -> dict:
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1_weighted": f1_score(labels, predictions, average="weighted"),
    }


def show_predictions(model, tokenizer, title: str) -> None:
    model.eval()
    print(f"\n  --- {title} ---")
    with torch.no_grad():
        for sentence in EXAMPLE_SENTENCES:
            inputs = tokenizer(sentence, return_tensors="pt", truncation=True)
            logits = model(**inputs).logits[0]
            probs = torch.softmax(logits, dim=-1)
            predicted = ID2LABEL[int(torch.argmax(probs))]
            confidence = float(torch.max(probs))
            print(f"  [{predicted:>8} {confidence:.2f}] {sentence!r}")


if __name__ == "__main__":
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True)

    train_ds, eval_ds = load_dataset()
    train_ds = train_ds.map(tokenize, batched=True)
    eval_ds = eval_ds.map(tokenize, batched=True)
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    banner("STEP 1 - BASELINE (pretrained DistilBERT, untrained classification head)")
    base_model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABELS), id2label=ID2LABEL, label2id=LABEL2ID
    )
    show_predictions(base_model, tokenizer, "predictions BEFORE any training (head is random)")

    baseline_args = TrainingArguments(
        output_dir=os.path.join(SCRIPT_DIR, "_lora_scratch"),
        per_device_eval_batch_size=8,
        report_to="none",
        save_strategy="no",
    )
    baseline_trainer = Trainer(
        model=base_model,
        args=baseline_args,
        eval_dataset=eval_ds,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )
    baseline_metrics = baseline_trainer.evaluate()
    print(f"\n  Baseline eval accuracy: {baseline_metrics['eval_accuracy']:.2%} "
          f"(expect ~{1 / len(LABELS):.0%}, i.e. chance - the head has never seen a label yet)")

    banner("STEP 2 - WRAP WITH LoRA")
    # SEQ_CLS models need modules_to_save too, not just target_modules: the
    # classification head (pre_classifier/classifier) was randomly initialized
    # above and MUST be fully trainable (not LoRA-decomposed - it's tiny
    # already) or nothing downstream of the LoRA-adapted attention layers
    # could ever learn to map to the right labels.
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=8,
        lora_alpha=16,
        lora_dropout=0.1,
        target_modules=["q_lin", "v_lin"],
        modules_to_save=["pre_classifier", "classifier"],
    )
    lora_model = get_peft_model(base_model, lora_config)
    lora_model.print_trainable_parameters()

    banner("STEP 3 - TRAIN THE ADAPTER")
    training_args = TrainingArguments(
        output_dir=os.path.join(SCRIPT_DIR, "_lora_scratch"),
        num_train_epochs=4,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        learning_rate=1e-3,  # LoRA tolerates a much higher LR than full fine-tuning would
        eval_strategy="epoch",
        logging_strategy="epoch",
        save_strategy="no",
        report_to="none",
    )
    trainer = Trainer(
        model=lora_model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )
    trainer.train()

    banner("STEP 4 - SAVE THE ADAPTER (not the whole model)")
    lora_model.save_pretrained(ADAPTER_DIR)
    tokenizer.save_pretrained(ADAPTER_DIR)
    adapter_size_kb = sum(
        os.path.getsize(os.path.join(ADAPTER_DIR, f)) for f in os.listdir(ADAPTER_DIR)
    ) / 1024
    print(f"  Adapter saved to: {ADAPTER_DIR}")
    print(f"  Adapter size on disk: {adapter_size_kb:.0f} KB "
          f"(a full fine-tuned copy of {MODEL_NAME} would be ~270,000 KB)")

    banner("STEP 5 - RELOAD BASE MODEL + ADAPTER, COMPARE")
    fresh_base = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABELS), id2label=ID2LABEL, label2id=LABEL2ID
    )
    reloaded = PeftModel.from_pretrained(fresh_base, ADAPTER_DIR)
    show_predictions(reloaded, tokenizer, "predictions AFTER LoRA fine-tuning (reloaded from disk)")

    final_metrics = trainer.evaluate()
    print(f"\n  Final eval accuracy: {final_metrics['eval_accuracy']:.2%} "
          f"(vs {baseline_metrics['eval_accuracy']:.2%} before training)")
    print(f"  Final eval F1 (weighted): {final_metrics['eval_f1_weighted']:.2%}")
    if final_metrics["eval_accuracy"] > 0.98:
        print("\n  NOTE: a near-100% score this fast usually means the dataset is templated/repetitive\n"
              "  enough that the eval split overlaps in style (or verbatim) with the train split - great\n"
              "  for proving the LoRA mechanics work, not evidence of real-world generalization. Check\n"
              "  your CSV for duplicate/near-duplicate rows across classes if you see this on your own data.")

    banner("HOW TO USE A DIFFERENT DATASET")
    print(f"""
  Replace {DATA_PATH}
  with any other CSV that has a "text" column and a "sentiment" column
  (values "positive"/"negative"/"neutral", any capitalization):

    id,text,sentiment
    1,"some sentence",Positive
    2,"another sentence",Negative
    3,"a third sentence",Neutral

  Nothing else in this script needs to change - the "id" column is read but
  unused, so it's fine to drop it entirely from your own file too.
""")
