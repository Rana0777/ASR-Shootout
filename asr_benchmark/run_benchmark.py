"""Run the Bangalore locality ASR benchmark."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

from evaluate import aggregate_metrics, evaluate_single, normalize_text
from sentences import LOCALITIES


PROJECT_DIR = Path(__file__).resolve().parent
AUDIO_DIR = PROJECT_DIR / "audio"
RESULTS_PATH = PROJECT_DIR / "results.json"
MODEL_ORDER = ["Deepgram", "Whisper-base", "AssemblyAI"]
SUPPORTED_AUDIO_EXTENSIONS = (".wav", ".ogg", ".m4a", ".mp3", ".flac")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark ASR systems on Bangalore locality names.")
    parser.add_argument("--demo", action="store_true", help="Run with simulated realistic results and no APIs.")
    parser.add_argument("--whisper-only", action="store_true", help="Run only local Whisper on real WAV files.")
    parser.add_argument("--deepgram-key", default=None, help="Deepgram API key. Defaults to DEEPGRAM_API_KEY.")
    parser.add_argument("--assemblyai-key", default=None, help="AssemblyAI API key. Defaults to ASSEMBLYAI_API_KEY.")
    parser.add_argument("--model-size", default="base", help="Whisper model size. Default: base.")
    return parser.parse_args()


def load_env_file(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path)
        return
    except ImportError:
        pass

    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _replace_locality(sentence: str, locality: str, replacement: str) -> str:
    normalized_sentence = normalize_text(sentence)
    normalized_locality = normalize_text(locality)
    return normalized_sentence.replace(normalized_locality, replacement)


def _latency(base: float, spread: float = 0.12) -> float:
    return round(base + random.uniform(-spread, spread), 2)


def demo_transcript(model: str, item: dict) -> tuple[str, float, str | None]:
    sentence = normalize_text(item["sentence"])
    locality = item["locality"]
    replacements = {
        "Deepgram": {
            "Whitefield": "whitefeel",
            "Bommanahalli": "bommanahali",
            "Yeshwanthpur": "yeshwantpur",
        },
        "AssemblyAI": {
            "Koramangala": "koramangla",
            "Marathahalli": "marathhalli",
            "Yelahanka": "yelanka",
            "Bommanahalli": "bomanahalli",
            "Yeshwanthpur": "yeshwantpur",
        },
        "Whisper-base": {},
    }
    latency_bases = {"Deepgram": 0.82, "Whisper-base": 4.2, "AssemblyAI": 3.6}
    replacement = replacements.get(model, {}).get(locality)
    transcript = _replace_locality(sentence, locality, replacement) if replacement else sentence
    return transcript, _latency(latency_bases[model]), None


def build_result(model: str, item: dict, transcript: str, latency_s: float, error: str | None = None) -> dict:
    metrics = evaluate_single(item["sentence"], transcript, item["locality"])
    return {
        "id": item["id"],
        "filename": item["filename"],
        "locality": item["locality"],
        "condition": item["condition"],
        "reference": normalize_text(item["sentence"]),
        "hypothesis": normalize_text(transcript),
        "latency_s": round(float(latency_s), 2),
        "error": error,
        **metrics,
    }


def run_demo() -> dict:
    random.seed(7)
    all_results = {}
    for model in MODEL_ORDER:
        rows = []
        for item in LOCALITIES:
            transcript, latency_s, error = demo_transcript(model, item)
            rows.append(build_result(model, item, transcript, latency_s, error))
        all_results[model] = rows
    return all_results


def _audio_path(item: dict) -> Path:
    for extension in SUPPORTED_AUDIO_EXTENSIONS:
        candidate = AUDIO_DIR / f"{item['filename']}{extension}"
        if candidate.exists():
            return candidate
    return AUDIO_DIR / f"{item['filename']}.wav"


def run_whisper_only(model_size: str) -> dict:
    from transcribe import transcribe_whisper

    model_name = f"Whisper-{model_size}"
    rows = []
    for index, item in enumerate(LOCALITIES, start=1):
        path = _audio_path(item)
        if not path.exists():
            response = {"transcript": "", "latency_s": 0.0, "error": f"Missing audio file: {path.name}"}
        else:
            response = transcribe_whisper(str(path), model_size=model_size)
        result = build_result(model_name, item, response.get("transcript", ""), response.get("latency_s", 0.0), response.get("error"))
        rows.append(result)
        marker = "✓" if result["exact_entity_hit"] else "✗"
        print(f"[{index:02d}/20] {model_name} | {item['locality']:<15} | {result['latency_s']:.2f}s | {marker}")
    return {model_name: rows}


def run_full(deepgram_key: str | None, assemblyai_key: str | None, model_size: str) -> dict:
    from transcribe import transcribe_assemblyai, transcribe_deepgram, transcribe_whisper

    model_calls = []
    if deepgram_key:
        model_calls.append(("Deepgram", lambda path: transcribe_deepgram(path, deepgram_key)))
    model_calls.append((f"Whisper-{model_size}", lambda path: transcribe_whisper(path, model_size=model_size)))
    if assemblyai_key:
        model_calls.append(("AssemblyAI", lambda path: transcribe_assemblyai(path, assemblyai_key)))

    all_results = {}
    for model_name, transcriber in model_calls:
        rows = []
        for index, item in enumerate(LOCALITIES, start=1):
            path = _audio_path(item)
            if not path.exists():
                response = {"transcript": "", "latency_s": 0.0, "error": f"Missing audio file: {path.name}"}
            else:
                response = transcriber(str(path))
            result = build_result(model_name, item, response.get("transcript", ""), response.get("latency_s", 0.0), response.get("error"))
            rows.append(result)
            marker = "✓" if result["exact_entity_hit"] else "✗"
            print(f"{model_name:<13} [{index:02d}/20] {item['locality']:<15} {result['latency_s']:.2f}s {marker}")
        all_results[model_name] = rows
    return all_results


def _aggregates(all_results: dict) -> dict:
    return {model: aggregate_metrics(rows) for model, rows in all_results.items()}


def _condition_hit_rate(rows: list[dict], condition: str) -> float:
    subset = [row for row in rows if row["condition"] == condition]
    if not subset:
        return 0.0
    return round(sum(1 for row in subset if row["exact_entity_hit"]) * 100.0 / len(subset), 1)


def _display_models(all_results: dict) -> list[str]:
    preferred = [model for model in MODEL_ORDER if model in all_results]
    remaining = [model for model in all_results if model not in preferred]
    return preferred + remaining


def print_results_table(all_results: dict) -> None:
    aggregates = _aggregates(all_results)
    models = _display_models(all_results)

    print()
    print("══════════════════════════════════════════════════════════════")
    print("  ASR BENCHMARK — Bangalore Locality Names (20 samples)")
    print("══════════════════════════════════════════════════════════════")
    print()
    print(f"{'Metric':<28}" + "".join(f"{model:>14}" for model in models))
    print("────────────────────────────────────────────────────────────")
    print(f"{'WER (↓ better)':<28}" + "".join(f"{aggregates[model]['mean_wer']:>14.3f}" for model in models))
    print(f"{'CER (↓ better)':<28}" + "".join(f"{aggregates[model]['mean_cer']:>14.3f}" for model in models))
    print(f"{'Entity Hit Rate % (↑)':<28}" + "".join(f"{aggregates[model]['entity_hit_rate']:>14.1f}" for model in models))
    print(f"{'Fuzzy Hit Rate % (↑)':<28}" + "".join(f"{aggregates[model]['fuzzy_hit_rate']:>14.1f}" for model in models))
    print(f"{'Avg Latency s (↓)':<28}" + "".join(f"{aggregates[model]['mean_latency_s']:>14.2f}" for model in models))
    print()
    print("──────────────── Entity Hit Rate by Condition ───────────────")
    print()
    print(f"{'Condition':<28}" + "".join(f"{model:>14}" for model in models))
    print("────────────────────────────────────────────────────────────")
    for condition in ["quiet", "noisy", "phone", "whispered"]:
        print(f"{condition:<28}" + "".join(f"{_condition_hit_rate(all_results[model], condition):>13.1f}%" for model in models))
    print()
    print("══════════════════════════════════════════════════════════════")
    print()


def print_failure_analysis(all_results: dict) -> None:
    print("Failure Analysis")
    print("────────────────")
    for model in _display_models(all_results):
        misses = [row for row in all_results[model] if not row["exact_entity_hit"]]
        print(f"Model: {model} — {len(misses)} misses")
        for row in misses:
            print(f"  [{row['condition']:<9}] {row['locality']:<16} fuzzy={row['fuzzy_score']:.0f}")
            print(f"    REF: {row['reference']}")
            print(f"    HYP: {row['hypothesis']}")
        print()


def save_results(all_results: dict) -> None:
    with RESULTS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(all_results, handle, indent=2, ensure_ascii=False)
    print(f"Saved results to {RESULTS_PATH}")


def main() -> int:
    load_env_file(PROJECT_DIR / ".env")
    args = parse_args()
    deepgram_key = args.deepgram_key or os.getenv("DEEPGRAM_API_KEY")
    assemblyai_key = args.assemblyai_key or os.getenv("ASSEMBLYAI_API_KEY")

    if args.demo:
        print("Running demo mode because --demo was provided. No audio files or API keys are required.")
        all_results = run_demo()
    elif args.whisper_only:
        print(f"Running Whisper-only mode with local Whisper model '{args.model_size}'.")
        all_results = run_whisper_only(args.model_size)
    elif not deepgram_key:
        print("Running demo mode because no Deepgram key was provided in --deepgram-key, .env, or DEEPGRAM_API_KEY.")
        all_results = run_demo()
    else:
        if assemblyai_key:
            print("Running full mode with Deepgram, Whisper, and AssemblyAI.")
        else:
            print("Running real-audio mode with Deepgram and Whisper. AssemblyAI key not found, so AssemblyAI is skipped.")
        all_results = run_full(deepgram_key, assemblyai_key, args.model_size)

    print_results_table(all_results)
    print_failure_analysis(all_results)
    save_results(all_results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
