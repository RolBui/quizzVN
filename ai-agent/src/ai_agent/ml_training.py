import argparse
import hashlib
import json
import math
import os
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_agent.config import settings


DATASET_FILES = ("train.jsonl", "validation.jsonl", "test.jsonl")
FORBIDDEN_METADATA_FIELDS = {
    "email",
    "owner_id",
    "phone",
    "teacher_id",
    "user_id",
}


def validate_dataset(options: argparse.Namespace) -> dict[str, Any]:
    dataset_dir = Path(options.dataset_dir)
    _validate_dataset_dir(dataset_dir)
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    failures: list[dict[str, Any]] = []
    seen_hashes: dict[str, str] = {}
    actual_counts: dict[str, int] = {}

    for filename in DATASET_FILES:
        split = filename.removesuffix(".jsonl")
        path = dataset_dir / filename
        expected_checksum = (manifest.get("checksums") or {}).get(filename)
        actual_checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected_checksum != actual_checksum:
            failures.append(
                {
                    "split": split,
                    "reason": "checksum_mismatch",
                }
            )

        rows = _read_jsonl(path, split, failures)
        actual_counts[split] = len(rows)
        expected_count = (manifest.get("counts") or {}).get(split)
        if expected_count != len(rows):
            failures.append(
                {
                    "split": split,
                    "reason": "count_mismatch",
                    "expected": expected_count,
                    "actual": len(rows),
                }
            )

        for index, row in enumerate(rows, start=1):
            reason = _validate_dataset_row(row)
            if reason:
                failures.append({"split": split, "line": index, "reason": reason})
                continue
            content_hash = str(row["metadata"]["content_hash"])
            previous_split = seen_hashes.get(content_hash)
            if previous_split is not None:
                failures.append(
                    {
                        "split": split,
                        "line": index,
                        "reason": "duplicate_content_hash",
                        "first_seen_in": previous_split,
                    }
                )
            else:
                seen_hashes[content_hash] = split

    report = {
        "status": "passed" if not failures else "failed",
        "dataset_dir": str(dataset_dir.resolve()),
        "counts": actual_counts,
        "unique_examples": len(seen_hashes),
        "failures": failures[:100],
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "training_allowed": not failures and actual_counts.get("train", 0) > 0,
    }
    if actual_counts.get("train", 0) == 0:
        report["status"] = "failed"
        report["training_allowed"] = False
        report["failures"].append({"split": "train", "reason": "empty_training_split"})
    if options.output_report:
        output_path = Path(options.output_report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_report(output_path, report)
    return report


def train_adapter(options: argparse.Namespace) -> dict[str, Any]:
    _require_cuda()
    from datasets import load_dataset
    from peft import LoraConfig, prepare_model_for_kbit_training
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    dataset_dir = Path(options.dataset_dir)
    _validate_dataset_dir(dataset_dir)
    output_dir = Path(options.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {"train": str(dataset_dir / "train.jsonl")}
    validation_path = dataset_dir / "validation.jsonl"
    if validation_path.stat().st_size:
        files["validation"] = str(validation_path)
    dataset = load_dataset("json", data_files=files)
    if len(dataset["train"]) == 0:
        raise RuntimeError("Training dataset is empty")

    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    tokenizer = AutoTokenizer.from_pretrained(options.base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        options.base_model,
        quantization_config=quantization_config,
        device_map="auto",
        torch_dtype=compute_dtype,
    )
    model = prepare_model_for_kbit_training(model)
    peft_config = LoraConfig(
        r=options.lora_rank,
        lora_alpha=options.lora_alpha,
        lora_dropout=options.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear",
    )
    training_config = SFTConfig(
        output_dir=str(output_dir),
        num_train_epochs=options.epochs,
        per_device_train_batch_size=options.batch_size,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=options.gradient_accumulation_steps,
        learning_rate=options.learning_rate,
        logging_steps=options.logging_steps,
        save_strategy="epoch",
        eval_strategy="epoch" if "validation" in dataset else "no",
        load_best_model_at_end="validation" in dataset,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        max_length=options.max_length,
        gradient_checkpointing=True,
        bf16=compute_dtype == torch.bfloat16,
        fp16=compute_dtype == torch.float16,
        report_to="none",
        seed=options.seed,
    )
    trainer = SFTTrainer(
        model=model,
        args=training_config,
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("validation"),
        peft_config=peft_config,
        processing_class=tokenizer,
    )
    train_result = trainer.train(resume_from_checkpoint=options.resume_from_checkpoint)
    trainer.save_model(str(output_dir / "adapter"))
    tokenizer.save_pretrained(str(output_dir / "adapter"))
    metrics = _json_safe(dict(train_result.metrics))
    if "validation" in dataset:
        metrics.update(_json_safe(trainer.evaluate()))

    report = {
        "status": "trained",
        "base_model": options.base_model,
        "dataset_dir": str(dataset_dir.resolve()),
        "adapter_dir": str((output_dir / "adapter").resolve()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "activation": "blocked_until_evaluation_passes",
    }
    _write_report(output_dir / "training-report.json", report)
    return report


def evaluate_adapter(options: argparse.Namespace) -> dict[str, Any]:
    _require_cuda()
    from datasets import load_dataset
    from peft import PeftModel
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    test_path = Path(options.dataset_dir) / "test.jsonl"
    if not test_path.exists() or not test_path.stat().st_size:
        raise RuntimeError("Test dataset is empty")
    dataset = load_dataset("json", data_files={"test": str(test_path)})["test"]
    tokenizer = AutoTokenizer.from_pretrained(options.adapter_dir, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    base = AutoModelForCausalLM.from_pretrained(
        options.base_model,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=compute_dtype,
        ),
        device_map="auto",
        torch_dtype=compute_dtype,
    )
    model = PeftModel.from_pretrained(base, options.adapter_dir)
    model.eval()

    evaluated = min(len(dataset), options.max_samples)
    passed = 0
    failures: list[dict[str, Any]] = []
    for index in range(evaluated):
        row = dataset[index]
        messages = list(row["messages"][:-1])
        expected = json.loads(row["messages"][-1]["content"])
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            generated = model.generate(
                **encoded,
                max_new_tokens=options.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        new_tokens = generated[0][encoded["input_ids"].shape[1] :]
        output = tokenizer.decode(new_tokens, skip_special_tokens=True)
        candidate = _parse_json_object(output)
        valid = _structural_match(candidate, expected)
        if valid:
            passed += 1
        elif len(failures) < 20:
            failures.append({"index": index, "output": output[:1000]})

    score = passed / evaluated if evaluated else 0.0
    threshold = options.threshold
    report = {
        "status": "passed" if score >= threshold else "failed",
        "base_model": options.base_model,
        "adapter_dir": str(Path(options.adapter_dir).resolve()),
        "evaluated_samples": evaluated,
        "passed_samples": passed,
        "structural_accuracy": round(score, 6),
        "required_accuracy": threshold,
        "failures": failures,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "activation_allowed": score >= threshold,
    }
    output_path = Path(options.output_report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_report(output_path, report)
    return report


def _structural_match(candidate: dict[str, Any] | None, expected: dict[str, Any]) -> bool:
    if not isinstance(candidate, dict):
        return False
    expected_type = expected.get("type")
    if candidate.get("type") != expected_type:
        return False
    for field in ("content", "explanation", "difficulty", "topic"):
        if not str(candidate.get(field) or "").strip():
            return False
    options = candidate.get("options")
    answer = candidate.get("correct_answer")
    if expected_type == "multiple_choice":
        return isinstance(options, list) and len(options) == 4 and answer in options
    if options not in (None, []):
        return False
    if expected_type == "true_false":
        return isinstance(answer, bool)
    if expected_type in {"short_answer", "essay"}:
        return bool(answer)
    return False


def _read_jsonl(
    path: Path,
    split: str,
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            failures.append({"split": split, "line": index, "reason": "invalid_json"})
            continue
        if not isinstance(row, dict):
            failures.append({"split": split, "line": index, "reason": "row_not_object"})
            continue
        rows.append(row)
    return rows


def _validate_dataset_row(row: dict[str, Any]) -> str:
    messages = row.get("messages")
    metadata = row.get("metadata")
    if not isinstance(messages, list) or len(messages) != 3:
        return "invalid_messages"
    if [message.get("role") for message in messages if isinstance(message, dict)] != [
        "system",
        "user",
        "assistant",
    ]:
        return "invalid_message_roles"
    if not all(
        isinstance(message, dict) and isinstance(message.get("content"), str)
        for message in messages
    ):
        return "invalid_message_content"
    if not isinstance(metadata, dict):
        return "invalid_metadata"
    if FORBIDDEN_METADATA_FIELDS.intersection(metadata):
        return "owner_identifier_present"
    content_hash = str(metadata.get("content_hash") or "")
    if len(content_hash) != 64 or any(char not in "0123456789abcdef" for char in content_hash.lower()):
        return "invalid_content_hash"
    assistant_payload = _parse_json_object(messages[-1]["content"])
    if not _structural_match(assistant_payload, assistant_payload or {}):
        return "invalid_assistant_payload"
    return ""


def _parse_json_object(value: str) -> dict[str, Any] | None:
    cleaned = value.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _require_cuda() -> None:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Install requirements-ml.txt before running ML commands") from exc
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required for QLoRA training and evaluation")


def _validate_dataset_dir(path: Path) -> None:
    for filename in ("manifest.json", "train.jsonl", "validation.jsonl", "test.jsonl"):
        if not (path / filename).exists():
            raise RuntimeError(f"Missing dataset file: {filename}")


def _json_safe(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
    return result


def _write_report(path: Path, report: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline QuizzVN QLoRA training pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train = subparsers.add_parser("train")
    train.add_argument("--dataset-dir", required=True)
    train.add_argument("--output-dir", default=settings.ML_OUTPUT_ROOT)
    train.add_argument("--base-model", default=settings.ML_BASE_MODEL)
    train.add_argument("--epochs", type=float, default=2.0)
    train.add_argument("--batch-size", type=int, default=1)
    train.add_argument("--gradient-accumulation-steps", type=int, default=8)
    train.add_argument("--learning-rate", type=float, default=2e-4)
    train.add_argument("--max-length", type=int, default=2048)
    train.add_argument("--logging-steps", type=int, default=5)
    train.add_argument("--lora-rank", type=int, default=16)
    train.add_argument("--lora-alpha", type=int, default=32)
    train.add_argument("--lora-dropout", type=float, default=0.05)
    train.add_argument("--seed", type=int, default=42)
    train.add_argument("--resume-from-checkpoint", default=None)

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--dataset-dir", required=True)
    evaluate.add_argument("--adapter-dir", required=True)
    evaluate.add_argument("--base-model", default=settings.ML_BASE_MODEL)
    evaluate.add_argument("--threshold", type=float, default=settings.ML_EVALUATION_THRESHOLD)
    evaluate.add_argument("--max-samples", type=int, default=100)
    evaluate.add_argument("--max-new-tokens", type=int, default=768)
    evaluate.add_argument("--output-report", required=True)

    validate = subparsers.add_parser("validate-dataset")
    validate.add_argument("--dataset-dir", required=True)
    validate.add_argument("--output-report", default=None)
    return parser


def main(args: Iterable[str] | None = None) -> int:
    options = _parser().parse_args(args)
    if options.command == "train":
        report = train_adapter(options)
    elif options.command == "evaluate":
        report = evaluate_adapter(options)
    else:
        report = validate_dataset(options)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") != "failed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
