"""Convert benchmark audio files to 16 kHz mono WAV."""

from __future__ import annotations

import shutil
import wave
from pathlib import Path

from sentences import LOCALITIES


SUPPORTED_EXTENSIONS = (".ogg", ".m4a", ".mp3", ".wav", ".flac")
AUDIO_DIR = Path(__file__).resolve().parent / "audio"


def _wav_is_16k_mono(path: Path) -> tuple[bool, float, int, int]:
    try:
        with wave.open(str(path), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            frames = wav_file.getnframes()
            duration = frames / float(frame_rate) if frame_rate else 0.0
            return frame_rate == 16000 and channels == 1, duration, frame_rate, channels
    except wave.Error:
        return False, 0.0, 0, 0


def _find_source_file(base_name: str) -> Path | None:
    for extension in SUPPORTED_EXTENSIONS:
        candidate = AUDIO_DIR / f"{base_name}{extension}"
        if candidate.exists():
            return candidate
    return None


def _load_audio_segment():
    if shutil.which("ffmpeg") is None:
        raise SystemExit(
            "Missing dependency: ffmpeg. Install ffmpeg and make sure it is available on PATH "
            "before converting audio."
        )

    try:
        from pydub import AudioSegment
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: pydub. Install project dependencies with "
            "`python -m pip install -r requirements.txt` before converting audio."
        ) from exc
    return AudioSegment


def convert_one(base_name: str) -> tuple[str, bool]:
    output_path = AUDIO_DIR / f"{base_name}.wav"
    if output_path.exists():
        is_standard, duration, frame_rate, channels = _wav_is_16k_mono(output_path)
        if is_standard:
            print(f"[OK] {output_path.name} already OK ({duration:.1f}s, {frame_rate // 1000}kHz mono)")
            return "found", False

    source = _find_source_file(base_name)
    if source is None:
        print(f"[MISSING] {base_name} - file not found")
        return "missing", False

    if source.suffix.lower() == ".wav":
        is_standard, duration, frame_rate, channels = _wav_is_16k_mono(source)
        if is_standard:
            print(f"[OK] {source.name} already OK ({duration:.1f}s, {frame_rate // 1000}kHz mono)")
            return "found", False

    AudioSegment = _load_audio_segment()
    audio = AudioSegment.from_file(source)
    converted = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    converted.export(output_path, format="wav")
    duration = len(converted) / 1000.0
    print(f"[OK] {source.name} -> .wav ({duration:.1f}s, 16kHz mono)")
    return "found", True


def main() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    found = 0
    missing = 0
    converted = 0

    for item in LOCALITIES:
        status, did_convert = convert_one(item["filename"])
        if status == "missing":
            missing += 1
        else:
            found += 1
        if did_convert:
            converted += 1

    print()
    print(f"Total found: {found}")
    print(f"Total missing: {missing}")
    print(f"Total converted: {converted}")


if __name__ == "__main__":
    main()
