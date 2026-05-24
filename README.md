# ASR Shootout

ASR Shootout is a benchmarking and evaluation project for comparing different Automatic Speech Recognition (ASR) systems on real-world audio data. The project analyzes transcription quality, latency, speaker recognition, and noise robustness across multiple ASR providers and open-source models.

## Features

* Compare multiple ASR models and APIs
* Evaluate transcription accuracy
* Measure response time and latency
* Analyze speaker diarization performance
* Test noise handling capabilities
* Generate structured evaluation reports

## Tech Stack

* Python
* FastAPI
* Whisper / ASR APIs
* Pandas
* Jupyter Notebook
* Docker (optional)

## Use Cases

* Speech-to-text benchmarking
* AI voice assistant evaluation
* Call center transcription analysis
* Research and experimentation in ASR systems

## Project Workflow

1. Upload audio samples
2. Run transcription on multiple ASR systems
3. Compare outputs and metrics
4. Generate evaluation results and reports

## Future Improvements

* Real-time streaming support
* Advanced WER/CER evaluation
* Multi-language benchmarking
* Visualization dashboard

## License

This project is developed for learning, experimentation, and research purposes.
## Quick Start

Step 1 — Install system dependencies

```bash
sudo apt install ffmpeg
brew install ffmpeg
```

Step 2 — Install Python packages

```bash
pip install -r requirements.txt
```

Step 3 - Add your audio files

Put your 20 recorded `.ogg` or `.wav` files in the `audio/` folder. This project is currently configured to use these original WhatsApp filenames:

```text
WhatsApp Ptt 2026-05-24 at 00.59.33.ogg
WhatsApp Ptt 2026-05-24 at 00.59.44.ogg
WhatsApp Ptt 2026-05-24 at 00.59.56.ogg
WhatsApp Ptt 2026-05-24 at 01.00.03.ogg
WhatsApp Ptt 2026-05-24 at 01.00.03 (1).ogg
WhatsApp Ptt 2026-05-24 at 01.00.26.ogg
WhatsApp Ptt 2026-05-24 at 01.00.57.ogg
WhatsApp Ptt 2026-05-24 at 01.01.12.ogg
WhatsApp Ptt 2026-05-24 at 01.06.06.ogg
WhatsApp Ptt 2026-05-24 at 01.01.23.ogg
WhatsApp Ptt 2026-05-24 at 01.02.29.ogg
WhatsApp Ptt 2026-05-24 at 01.02.52.ogg
WhatsApp Ptt 2026-05-24 at 01.03.02.ogg
WhatsApp Ptt 2026-05-24 at 01.03.14.ogg
WhatsApp Ptt 2026-05-24 at 01.04.02.ogg
WhatsApp Ptt 2026-05-24 at 01.04.30.ogg
WhatsApp Ptt 2026-05-24 at 01.05.44.ogg
WhatsApp Ptt 2026-05-24 at 01.05.54.ogg
WhatsApp Ptt 2026-05-24 at 00.59.33 (1).ogg
WhatsApp Ptt 2026-05-24 at 00.59.44 (1).ogg
```

Step 4 — Add API keys

Paste keys into `.env`:

```env
DEEPGRAM_API_KEY=your_deepgram_key
ASSEMBLYAI_API_KEY=your_assemblyai_key
```

Step 5 — Convert audio to WAV

```bash
python convert_audio.py
```

Step 6 — Run benchmark

```bash
python run_benchmark.py --demo
python run_benchmark.py --whisper-only
DEEPGRAM_API_KEY=xxx python run_benchmark.py
DEEPGRAM_API_KEY=xxx ASSEMBLYAI_API_KEY=yyy python run_benchmark.py
```

On Windows PowerShell:

```powershell
$env:DEEPGRAM_API_KEY="xxx"; python run_benchmark.py
$env:DEEPGRAM_API_KEY="xxx"; $env:ASSEMBLYAI_API_KEY="yyy"; python run_benchmark.py
```

## Project Structure

| Path | Purpose |
|---|---|
| `audio/` | Real recorded phone-mic audio files supplied by the user |
| `sentences.py` | Canonical 20-sample locality benchmark inventory |
| `convert_audio.py` | Converts `.ogg`, `.m4a`, `.mp3`, `.wav`, and `.flac` to 16 kHz mono WAV |
| `transcribe.py` | Deepgram, Whisper, and AssemblyAI transcription integrations |
| `evaluate.py` | WER, CER, exact entity hit, fuzzy entity hit, and aggregation |
| `run_benchmark.py` | CLI benchmark runner with demo, Whisper-only, and API modes |
| `requirements.txt` | Python package dependencies |
| `report.md` | Concise benchmark report and recommendation |
| `.env` | Local API-key file |
| `results.json` | Human-readable benchmark output generated after a run |

## Models

| Model | Mode | Best use |
|---|---|---|
| Deepgram Nova-2 | API | Live phone calls and IVR where streaming latency matters |
| Whisper-base | Local | WhatsApp voice notes and privacy-sensitive async processing |
| AssemblyAI | API | Async voice-note baseline and external comparison |

## Metrics

| Metric | Meaning |
|---|---|
| WER | Word error rate against the full sentence |
| CER | Character error rate against the full sentence, ignoring spaces |
| Entity Hit Rate | Exact match for the locality name inside the transcript |
| Fuzzy Hit Rate | RapidFuzz partial-ratio match for near-miss locality names |
| Avg Latency | Mean wall-clock transcription time in seconds |

## Notes

Demo mode works with zero internet, zero API keys, and zero audio files:

```bash
python run_benchmark.py --demo
```

If no Deepgram key is found in CLI args, environment variables, or `.env`, `run_benchmark.py` automatically runs demo mode instead of crashing.
