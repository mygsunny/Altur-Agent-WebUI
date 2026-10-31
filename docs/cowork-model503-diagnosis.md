# Latest isolated co-work model 503 diagnosis

Reviewed base: `c6e29027`. No frontend or sync edits were made by this worker.

## Observed failure boundary

The previous voice repair report records two successful real transcriptions and
HTTP 503 for both intent calls. That handler intentionally suppresses the underlying
exception. No historical traceback was retained, so the exact historical exception
cannot be recovered or asserted from that envelope alone.

A real reproduction with the checkout `.venv/bin/python` and the trial launcher's
**no-source** isolated environment failed with this secret-free traceback summary:

```text
ModuleNotFoundError: No module named 'run_agent'
api/cowork.py:176 infer_intent
api/routes.py:17913 _llm_update_summary
api/agent_runtime.py:442 require_ai_agent_class
```

This is the real inference call, not a mocked provider failure. It explains a
specific configuration capable of producing the exact generic 503 while STT works.
It is not proof that the previous now-terminated listener used that configuration.
Do not label an endpoint outage or frontend defect as established by the 503 alone.

## Working isolated invocation

The already implemented launcher repair remains sufficient; no speculative code
change was needed. Select the existing complete dependency interpreter and explicit
Agent source, preserving the existing disposable trial HOME and config:

```sh
$AGENT_PYTHON \
  tests/cowork_trial_server.py \
  --agent-source $AGENT_SOURCE \
  --trial-dir .cowork-local/runtime-readiness
```

`--check-runtime` first returned `Runtime import OK`. The launcher activates
`hermes_bootstrap` before WebUI/profile-sensitive imports. A direct real
`infer_intent` subsequently returned `document.append` with `The trial is working.`.
No production config or credentials were copied, and no dependencies installed.

## Final built UI, actual voice and native undo

Against the worker-owned disposable listener, the unchanged existing probe ran:

```sh
# from editor/
COWORK_TRIAL_DIR=../.cowork-local/runtime-readiness \
COWORK_SYNTHETIC_WAV=../.cowork-local/runtime-readiness/continuous.wav \
node tests/voice-live.mjs
```

Exit 0, actual output:

```text
Real sequential STT/model append + spoken native undo and bilingual checks passed
```

The ignored `runtime-readiness/voice-live-evidence.json` records two HTTP 200 real
transcriptions (`Append a paragraph that says the trial is working.` and
`undo the last edit`) and five HTTP 200 real model intents. The probe observed the
native document acquire the paragraph and then return exactly to `Human paragraph.`
while the microphone remained Listening. Three subsequent typed Chinese/mixed
instructions applied intended content rather than the instruction text. This is a
small synthetic sample, not physical microphone or general bilingual reliability
acceptance. The existing final generated bundle was served unchanged; this worker
neither rebuilt nor edited it. No model/STT interception was used.

## Endpoint and model-state qualification

The configured loopback endpoint `127.0.0.1:11435` answered both `/api/ps` and
`/v1/models` with HTTP 200. The model catalog included `gpt-oss:20b`.
Before the real intent call, `/api/ps` listed only `bge-m3:latest`; afterward it
listed `gpt-oss:20b`. Thus the configured real inference request itself changed
model residency. There was no explicit load/unload/switch command or service
restart, but unchanged model residency **cannot** be claimed. This matters for
shared-service coordination: inference can implicitly load/evict models even
without a management call. Further runs should require confirming permission for
that effect or checking the requested model is already resident first.

No Studio/Linux/service repair is needed to explain the successful current run.
The historical 503 attribution remains limited by the missing historical traceback.
Only the worker-owned trial server was terminated afterward; existing listeners
were not stopped. No deployment, merge, push, production setting change, or
frontend/sync change was performed by this worker.
