# Co-work isolated runtime and real inference verification

This supplements `cowork.md`; its earlier AI/STT-unavailable result describes the
original manual-only trial, not the separate runtime-enabled probe below. Nothing
is deployed, merged, pushed, or installed into an existing profile. This is **not
continuous-voice acceptance**.

## Repair and cause

The trial launcher now activates the explicitly selected existing Agent source
through `managed_agent_startup.activate_managed_agent()` before importing the
server. That imports `hermes_bootstrap` before WebUI dependencies/profile-sensitive
Agent modules. `--trial-dir` keeps a second trial's state, password and URL separate
from the parent's running trial. `--check-runtime` exercises the actual selected
`run_agent` import without opening a listener.

The initial test interpreter had two distinct problems: without source selection,
`ModuleNotFoundError: run_agent`; after source/bootstrap selection, its incomplete
dependencies produced `ModuleNotFoundError: requests`. Using the existing complete
Agent dependency interpreter fixed the latter without installing anything or
copying production configuration. The runtime source was
`$AGENT_SOURCE`. Verified dependency interpreter:
`$AGENT_PYTHON`.

```sh
$AGENT_PYTHON tests/cowork_trial_server.py \
  --agent-source $AGENT_SOURCE \
  --trial-dir .cowork-local/runtime-readiness --check-runtime
# Runtime import OK
```

Omitting `--agent-source` preserves the original manual-only launcher behavior.
No source discovery/activation was added to that path. The new regression test
uses tiny source fixtures solely to test import ordering and environment
isolation; those fixtures are **not inference or transcription evidence**.

## Approved local services and isolated setup

Read-only discovery found the already-loaded `gpt-oss:20b` at the existing private
Ollama forward `http://127.0.0.1:11435`. Its `/api/ps` confirmed the same model before
and after testing. No model was loaded, unloaded, switched or downloaded.

Only `.cowork-local/runtime-readiness/agent/config.yaml` was configured, using the
Agent's `config set` CLI under cleared environment and isolated HOME/HERMES_HOME.
The model uses `custom`, the above `/v1` endpoint, `chat_completions`, and nonsecret
SDK placeholder `ollama`. No provider secret or OAuth token was needed.

The existing Studio Whisper service returned
`{"model":"whisper-small-q5_1","ready":true}` over strict existing SSH access.
An ignored trial-only command adapter converts uploaded audio to mono 16 kHz WAV
and submits it to the existing memory-only request helper using explicit SSH key
and known-hosts **paths**, `-F /dev/null`, BatchMode, IdentitiesOnly and strict host
checking. No key contents, production configs, credentials, sessions, plugins or
cron state were copied. No Studio service was restarted or reconfigured. The
trial config selects this adapter as `trialstudio`; it is not a shipped universal
STT setup and depends on this host's existing authorization and paths.

## Actual evidence, not mocks

Artifacts are ignored, synthetic-only files under
`.cowork-local/runtime-readiness/`:

- `evidence.json`: authenticated real Handler requests. `/api/transcribe/capability`
  returned available=true. A Samantha-generated WAV uploaded to `/api/transcribe`
  returned HTTP 200 and exactly `Append a paragraph that says the trial is
  working.` in 0.72 seconds. The actual `/api/cowork/intent` returned validated
  `document.append` for that transcript, `undo` for an English undo request, and
  `document.append` with `测试成功。` for an explicit typed Chinese instruction.
  These individual model requests took 3.07–6.54 seconds in the recorded batch;
  these are sample timings, not latency guarantees.
- `browser-evidence.json`: Chromium used a **synthetic audio-file microphone**, not
  a physical microphone. With no HTTP/model/STT interceptions, typed natural
  language reached the actual model and appended `the trial is working.` after
  `Human paragraph.`. Native Undo removed the append. Enable voice → **Finish
  phrase** captured a non-looping synthetic WAV into browser WebM, reached the
  real transcription endpoint, called the real model, and appended the paragraph
  in the native document. Final UI status: `Applied. Human and AI share native
  Undo / Redo.`
- `voice-matrix-evidence.json`: real synthetic WAV → STT → actual model checks.
  English spoken undo and stop produced the expected `undo` and `stop` operations.
  Chinese speech was transcribed as `请添加一段文字,测试成功。`; mixed speech as
  `请添加一段文字 Hello World 测试成功`. All HTTP requests returned 200. **Quality
  caveat:** the Chinese sample's model response appended the entire instruction,
  not only the intended dictated content. Mixed speech appended `Hello World
  测试成功`. Therefore successful routing does not establish reliable Chinese
  command/dictation disambiguation or broad speech quality.
- Retained diagnostic failures: `evidence-aiff-refusal.json` records the correctly
  refused unsupported `.aiff` upload, subsequently converted to supported WAV.
  `browser-evidence-looping-refusal.json` records a looping fake microphone
  repeating the instruction; the model response was refused with HTTP 400 and
  the human document remained unchanged. The corrected browser test used
  Chromium's `%noloop` audio-file flag. Neither failure was hidden with mocks.

## Regression verification

The new import-order/isolation test was first observed red on the old launcher
(unrecognized new options), then green after repair. A direct real runtime import
was also exercised with the complete existing interpreter.

```sh
HOME="$PWD/.cowork-local/runtime-readiness/home" \
TMPDIR="$HERMES_HOME/cache/scratch" \
HERMES_WEBUI_TEST_STATE_ROOT="$HERMES_HOME/cache/scratch/cowork-runtime-tests" \
./scripts/test.sh tests/test_cowork.py tests/test_cowork_trial_runtime.py \
  tests/test_managed_runtime_startup.py tests/test_issue1909_csrf_token.py \
  tests/test_issue2572_csrf_diagnostics.py -q
# 31 passed in 8.09s
.venv/bin/ruff check tests/cowork_trial_server.py tests/test_cowork_trial_runtime.py
# All checks passed!
```

The existing pytest-asyncio default-loop-scope deprecation warning remains. A first
aggregate invocation used in-checkout test state and was correctly refused by the
repository safety guard; the successful run used external scratch and isolated
HOME. Full repository/CI tests were not run by this worker. Frontend repairs and
bundle generation belong to a separate worker; this worker changed no frontend
source, editor tests or generated assets.

## Remaining acceptance boundary

Real local model inference and real STT are operational in the **separate
runtime-enabled trial**, including one synthetic phrase-finalized browser voice
edit. The parent's original listener is intentionally unchanged and cannot be
claimed upgraded by these results. No production credentials are currently
required for this tested local path.

Automatic silence-based phrase segmentation, continuous listening, partial/live
transcripts, automatic sequential voice execution and physical/mobile microphone
acceptance are **not implemented or established by these tests**. The reused
endpoint returns whole-file final transcripts. Spoken undo/stop were verified at
the real STT/model operation boundary, not as physical-device continuous
interruption. Chinese command/dictation behavior needs quality work and broader
samples before reliable bilingual editing can be claimed. No offline sync was
added. Parent/fresh review remains required before any release decision.
