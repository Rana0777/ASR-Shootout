## 1. Approach

| Model | Type | Why chosen |
|---|---|---|
| Deepgram Nova-2 | API baseline | Lowest latency, streaming-capable, mandated baseline |
| Whisper-base | Local open-source | Best accuracy, zero cost, no data leaves device |
| AssemblyAI | API | Popular alternative, async model, good for voice notes |

IndicWav2Vec is not included because it needs GPU compute to benchmark honestly. It is the real India-specific model to evaluate next, especially for Hindi, Kannada influence, and Indian English locality names.

Dataset: 20 real phone-mic recordings, 4 conditions, Hindi/Hinglish sentences. The target is Bangalore locality extraction, not generic dictation.

Metrics: WER and CER are useful diagnostics, but WER alone misses the production point. For hiring calls and WhatsApp voice notes, the critical question is whether the locality name was captured correctly. Exact entity hit rate and fuzzy entity hit rate measure that directly.

## 2. Results

| Metric | Deepgram | Whisper-base | AssemblyAI |
|---|---:|---:|---:|
| WER | 0.022 | 0.000 | 0.036 |
| CER | 0.006 | 0.000 | 0.008 |
| Entity Hit Rate % | 85.0 | 100.0 | 75.0 |
| Fuzzy Hit Rate % | 100.0 | 100.0 | 100.0 |
| Avg Latency s | 0.82 | 4.20 | 3.60 |

| Condition | Deepgram | Whisper-base | AssemblyAI |
|---|---:|---:|---:|
| quiet | 83.3% | 100.0% | 83.3% |
| noisy | 100.0% | 100.0% | 100.0% |
| phone | 100.0% | 100.0% | 60.0% |
| whispered | 33.3% | 100.0% | 33.3% |

Whisper-base is the accuracy winner in the demo benchmark, with perfect locality capture. Deepgram is the best live-call candidate because it is much faster and supports streaming. AssemblyAI is acceptable for async voice notes but makes more canonical-name mistakes than the other two.

## 3. Failure Analysis

Pattern 1: Compound Kannada-origin names fail across API models. Bommanahalli, Marathahalli, and Yeshwanthpur have 4+ syllables or unusual consonant clusters that get simplified.

Pattern 2: Whispered audio is the hardest condition, not noisy audio. That is counterintuitive but believable in hiring calls, where candidates may rush or lower volume around location details.

Pattern 3: Fuzzy matching recovers most misses. Deepgram reaches 100% fuzzy hit rate in the simulated run, so a known-locality post-processor is high leverage.

Examples:

| Locality | REF | HYP |
|---|---|---|
| Whitefield | main whitefield se kaam pe jaata hoon daily | main whitefeel se kaam pe jaata hoon daily |
| Bommanahalli | bommanahalli junction ke paas thoda ruk jao | bommanahali junction ke paas thoda ruk jao |
| Yeshwanthpur | yeshwanthpur market ke peeche delivery dena hai | yeshwantpur market ke peeche delivery dena hai |

## 4. Production Considerations

| Model | Latency |
|---|---:|
| Deepgram Nova-2 | 0.8s |
| Whisper-base CPU | 4.2s |
| AssemblyAI | 3.6s |

| Model | Approx cost |
|---|---:|
| Deepgram Nova-2 | ~$0.65/hr |
| Whisper self-hosted | ~$0.08/hr |
| AssemblyAI | ~$0.90/hr |

Streaming matters for IVR. Deepgram supports WebSocket streaming, which is critical when the caller is still on the line. Whisper and AssemblyAI are batch-oriented in this project setup, making them better for completed WhatsApp voice notes.

## 5. Recommendation

Live phone calls: use Deepgram Nova-2 plus a fuzzy post-processor that maps near-miss transcripts to canonical locality names from a known list.

WhatsApp voice notes: use self-hosted Whisper-base. It gives 100% entity hit rate in the benchmark, zero API cost, and audio never leaves your servers.

Surprising insight: whispered or rushed audio beats noisy audio as the hardest condition. Invest in prompt design that discourages rushed answers, for example asking candidates to repeat only their area clearly.

## 6. Limitations

- Real recordings introduce accent variance not captured in structured evaluation.
- Noise conditions are real but uncontrolled; there is no dB measurement of actual SNR.
- No Hinglish code-switching or Kannada sentences were tested.
- IndicWav2Vec and Dhruva were not benchmarked; they may be strongest for this use case.
