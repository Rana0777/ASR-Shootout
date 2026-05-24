"""Evaluation metrics for ASR locality-name extraction."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from statistics import mean

try:
    from rapidfuzz import fuzz
except ImportError:
    class _FallbackFuzz:
        @staticmethod
        def partial_ratio(needle: str, haystack: str) -> float:
            if not needle or not haystack:
                return 0.0
            if needle in haystack:
                return 100.0
            if len(needle) > len(haystack):
                needle, haystack = haystack, needle
            best = 0.0
            window = len(needle)
            for index in range(0, len(haystack) - window + 1):
                candidate = haystack[index : index + window]
                best = max(best, SequenceMatcher(None, needle, candidate).ratio() * 100.0)
            return best

    fuzz = _FallbackFuzz()


def normalize_text(text: str | None) -> str:
    if text is None:
        return ""
    lowered = str(text).lower()
    cleaned = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
    cleaned = re.sub(r"_", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _levenshtein(seq_a: list[str], seq_b: list[str]) -> int:
    if not seq_a:
        return len(seq_b)
    if not seq_b:
        return len(seq_a)

    previous = list(range(len(seq_b) + 1))
    for i, item_a in enumerate(seq_a, start=1):
        current = [i]
        for j, item_b in enumerate(seq_b, start=1):
            substitution_cost = 0 if item_a == item_b else 1
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + substitution_cost,
                )
            )
        previous = current
    return previous[-1]


def wer(reference: str, hypothesis: str) -> float:
    ref_words = normalize_text(reference).split()
    hyp_words = normalize_text(hypothesis).split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return round(_levenshtein(ref_words, hyp_words) / len(ref_words), 4)


def cer(reference: str, hypothesis: str) -> float:
    ref_chars = list(normalize_text(reference).replace(" ", ""))
    hyp_chars = list(normalize_text(hypothesis).replace(" ", ""))
    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0
    return round(_levenshtein(ref_chars, hyp_chars) / len(ref_chars), 4)


def entity_hit(locality: str, hypothesis: str, threshold: int = 80) -> dict:
    normalized_locality = normalize_text(locality)
    normalized_hypothesis = normalize_text(hypothesis)
    exact_hit = bool(normalized_locality and normalized_locality in normalized_hypothesis)
    fuzzy_score = float(fuzz.partial_ratio(normalized_locality, normalized_hypothesis)) if normalized_hypothesis else 0.0
    return {
        "exact_hit": exact_hit,
        "fuzzy_score": round(fuzzy_score, 2),
        "fuzzy_hit": fuzzy_score >= threshold,
    }


def evaluate_single(reference: str, hypothesis: str, locality: str) -> dict:
    if not hypothesis:
        return {
            "wer": 1.0,
            "cer": 1.0,
            "exact_entity_hit": False,
            "fuzzy_entity_hit": False,
            "fuzzy_score": 0.0,
        }

    entity = entity_hit(locality, hypothesis)
    return {
        "wer": wer(reference, hypothesis),
        "cer": cer(reference, hypothesis),
        "exact_entity_hit": entity["exact_hit"],
        "fuzzy_entity_hit": entity["fuzzy_hit"],
        "fuzzy_score": entity["fuzzy_score"],
    }


def aggregate_metrics(results: list[dict]) -> dict:
    if not results:
        return {
            "mean_wer": 0.0,
            "mean_cer": 0.0,
            "entity_hit_rate": 0.0,
            "fuzzy_hit_rate": 0.0,
            "mean_fuzzy_score": 0.0,
            "mean_latency_s": 0.0,
            "n_samples": 0,
        }

    n = len(results)
    return {
        "mean_wer": round(mean(float(item.get("wer", 0.0)) for item in results), 4),
        "mean_cer": round(mean(float(item.get("cer", 0.0)) for item in results), 4),
        "entity_hit_rate": round(sum(1 for item in results if item.get("exact_entity_hit")) * 100.0 / n, 1),
        "fuzzy_hit_rate": round(sum(1 for item in results if item.get("fuzzy_entity_hit")) * 100.0 / n, 1),
        "mean_fuzzy_score": round(mean(float(item.get("fuzzy_score", 0.0)) for item in results), 2),
        "mean_latency_s": round(mean(float(item.get("latency_s", 0.0)) for item in results), 2),
        "n_samples": n,
    }
