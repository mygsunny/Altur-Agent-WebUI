# Continuous voice trial evidence

Implemented local Web Audio energy/silence phrase finalization (800 ms silence,
minimum 180 ms voiced span, maximum 20 seconds speech), continuous microphone
capture between phrases, ordered final STT/model execution and cancellation on
Pause/Stop/document switch. UI reports listening/speech activity, **not partial
transcripts**: existing STT is whole-file only. All edits still use native editor
transactions and shared Undo.

## Exercised, not simulated inference

Separate isolated runtime launched with the existing dependency interpreter and
`tests/cowork_trial_server.py --agent-source $AGENT_SOURCE
--trial-dir .cowork-local/runtime-readiness`; this worker's listener was 62519.
Parent listener 54851 was not changed. No production config, service restart,
merge, push or offline sync implementation.

Chromium synthetic file microphone: existing generated English append WAV plus
3 seconds silence plus generated undo WAV plus 3 seconds silence, concatenated
with ffmpeg at mono 48 kHz. One Enable click, no Finish/Stop between phrases.
Actual STT returned `Append a paragraph that says the trial is working.` then
`undo the last edit`; actual model returned document.append then undo. The
native document became `Human paragraph.\n\nThe trial is working.` then
`Human paragraph.` while UI still reported listening. Pause subsequently cleaned
microphone tracks. No physical microphone was accessed.

Ignored artifacts: `.cowork-local/runtime-readiness/continuous-evidence.json`,
`voice-live-evidence.json`, `bilingual-current-evidence.json`, `continuous.wav`,
`continuous-build.log`. Reproducible opt-in test:

```sh
cd editor
COWORK_TRIAL_DIR=/absolute/isolated-trial \
COWORK_SYNTHETIC_WAV=/absolute/synthetic-append-silence-undo.wav \
node tests/voice-live.mjs
```

The audio path is canonicalized: an initial `/../` Chromium fake-audio path
produced no transcription and timed out; the canonical-path rerun passed.

Bilingual real-model checks produced `测试成功。` for both unquoted and quoted
Chinese instructions, and `Hello World 测试成功` for mixed speech-style text.
This differs from the earlier observed instruction-echo failure and demonstrates
model variation, **not established general bilingual reliability**. New frontend
regressions refuse normalized verbatim text echoes with an English/Chinese
clarification request rather than inserting an ambiguous instruction. Conservative
tradeoff: bare dictation whose desired content equals the complete request also
asks clarification; use an explicit instruction with quoted content. This guard
is not a complete semantic validator and cannot catch every partial echo.

Verification: 20 Node tests passed; 14 Playwright browser regressions passed;
Vite build and OSS notices generated successfully (existing third-party directive
and large-chunk warnings). Real-service opt-in sequential voice + bilingual
assertions passed. The first aggregate browser run exposed an old expectation of
model unavailability; it now checks final dispatch/deduplication without requiring
a broken model.

Remaining limitations: fixed energy threshold needs noisy/quiet device tuning;
long idle silence retains recording data until the next phrase; capture restart
at each file boundary has a small recorder-event gap; no physical/mobile device
acceptance or partial transcript support. Spoken stop must reach ordered STT/model
processing; toolbar Pause/Stop is immediate and cancels queued work. Do not claim
release-ready bilingual or physical-device continuous voice. This worker makes no
persistent listener handoff claim; its isolated child listener must be terminated
or relaunched under verified parent ownership.
