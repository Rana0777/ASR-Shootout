"""ASR provider integrations for benchmark runs."""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path

import requests


CONTENT_TYPES = {
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
}


def _result(transcript: str = "", latency_s: float = 0.0, error: str | None = None) -> dict:
    return {"transcript": transcript, "latency_s": round(float(latency_s), 4), "error": error}


def transcribe_deepgram(audio_path: str, api_key: str, language: str = "hi") -> dict:
    started = time.time()
    try:
        params = {"model": "nova-2", "language": language, "smart_format": "true", "punctuate": "true"}
        content_type = CONTENT_TYPES.get(Path(audio_path).suffix.lower(), "application/octet-stream")
        headers = {"Authorization": f"Token {api_key}", "Content-Type": content_type}
        with open(audio_path, "rb") as audio_file:
            response = requests.post(
                "https://api.deepgram.com/v1/listen",
                params=params,
                headers=headers,
                data=audio_file,
                timeout=120,
            )
        response.raise_for_status()
        data = response.json()
        transcript = data["results"]["channels"][0]["alternatives"][0].get("transcript", "")
        return _result(transcript=transcript, latency_s=time.time() - started)
    except Exception as exc:
        return _result(latency_s=time.time() - started, error=str(exc))


def transcribe_whisper(audio_path: str, model_size: str = "base") -> dict:
    started = time.time()
    output_dir = Path(tempfile.gettempdir()) / "whisper_out"
    output_dir.mkdir(parents=True, exist_ok=True)
    audio = Path(audio_path)
    json_path = output_dir / f"{audio.stem}.json"

    try:
        command = [
            "whisper",
            str(audio),
            "--model",
            model_size,
            "--language",
            "hi",
            "--output_format",
            "json",
            "--output_dir",
            str(output_dir),
            "--fp16",
            "False",
        ]
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=1800)
        with json_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return _result(transcript=data.get("text", "").strip(), latency_s=time.time() - started)
    except FileNotFoundError:
        try:
            import whisper

            model = whisper.load_model(model_size)
            data = model.transcribe(str(audio), language="hi", fp16=False)
            return _result(transcript=data.get("text", "").strip(), latency_s=time.time() - started)
        except Exception as exc:
            return _result(latency_s=time.time() - started, error=str(exc))
    except Exception as exc:
        return _result(latency_s=time.time() - started, error=str(exc))


def transcribe_assemblyai(audio_path: str, api_key: str, language: str = "hi") -> dict:
    started = time.time()
    headers = {"authorization": api_key}
    try:
        with open(audio_path, "rb") as audio_file:
            upload_response = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers=headers,
                data=audio_file,
                timeout=120,
            )
        upload_response.raise_for_status()
        upload_url = upload_response.json()["upload_url"]

        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={**headers, "content-type": "application/json"},
            json={"audio_url": upload_url, "language_code": language},
            timeout=60,
        )
        transcript_response.raise_for_status()
        transcript_id = transcript_response.json()["id"]

        while True:
            poll_response = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=headers,
                timeout=60,
            )
            poll_response.raise_for_status()
            data = poll_response.json()
            status = data.get("status")
            if status == "completed":
                return _result(transcript=data.get("text", "") or "", latency_s=time.time() - started)
            if status == "error":
                return _result(latency_s=time.time() - started, error=data.get("error", "AssemblyAI transcription failed"))
            time.sleep(2)
    except Exception as exc:
        return _result(latency_s=time.time() - started, error=str(exc))
