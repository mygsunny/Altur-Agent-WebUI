# One-editor connection workflow: isolated live-test readiness

Status: ready for parent review and synthetic human trials, **not production or
ordinary Office-interoperability acceptance**. No push, merge, production restart,
production config/session change or existing user-document modification occurred.

## Delivered behavior

The current UI automatically freezes native/AI/voice writers when its connection
fails, and automatically reconciles stable local cloud-file arrivals before
resuming. No routine Edit externally / Resume buttons are required. Connected
WebUI writes the same selected-folder filename through native coordination with
expected hashes and recovery copies. A genuine divergent draft requires one
explicit arriving-version choice; normal idle arrivals reload automatically.

The authoritative server state is a short-lived, process-epoch/browser/document
connection grant. Snapshot, publication and intent requests carry that exact grant;
old queued requests cannot borrow a new connection's permission. Model completion
rechecks the grant. The native accessor checks expiry before replacement. Client
connection and document generation changes invalidate late conversion/reload/ack
completions, while committed acknowledgments reconcile separately from native
history reconstruction. See [the full contract](cowork-sync.md).

## Actual verification

- **46 backend/native/runtime/transcription tests passed**, including real native
  same-name replacement, lease expiry/restart, stale queued publication refusal,
  changed offered bytes, inference crossing a reconnect grant, root/state/backup
  security, and the retained noncooperative safety counterexample.
- **64 source-executing editor unit tests passed**, including current automatic
  sync disconnect/switch boundaries at decode/reload/ack, dropped acknowledgment,
  bounded audio/recognition queue, stale microphone/session cleanup and Stop races.
- **21 combined Chromium tests passed**, exercising actual Handler/filesystem operations:
  disconnect freeze, delayed arrival after reconnect, same-file publication,
  preserve-both conflicts (including a last-moment native edit during a status read),
  dropped save/ack responses, native document/spreadsheet commands and history,
  narrow/dark UI and voice lifecycle. This is the final aggregate run, not an
  inferred total from previous workers.
- The production asset build and OSS metadata verification succeeded. Desktop and
  narrow dark screenshots were inspected; narrow disclosure is vertically scrollable.
- **Real final local model/STT browser probe passed**, using a non-looping synthetic
  audio microphone and no model/STT HTTP interceptions. English append was followed
  by spoken native Undo through the current connection-granted module. Actual STT
  and model requests returned 200. Three typed Chinese/mixed checks either applied
  intended text or requested clarification. One actual Chinese model response echoed
  its instruction; the existing client guard refused that edit and asked clarification.
  This is not physical-microphone or general bilingual-accuracy qualification.
- In the exact authorized cloud parent, a fresh UUID synthetic directory exercised
  native same-file publication and exact-byte readback. Foundation then reported
  `ubiquitous=true`, `uploaded=true`, `uploading=false`, no unresolved conflicts and
  no upload error for the final artifact. An earlier status was still uploading with
  a provider error; a bounded later read reported completion. Neither pathname nor
  connection status was treated as proof. Receiving-device delivery is **not tested**.

Core new ownership actions were first observed failing on the old implementation
before being implemented. Initial test-harness and browser timing failures were
repaired and rerun; no synthetic response was substituted for the real-service
checks. Existing pytest-asyncio fixture-scope warnings and Vite directive/large-chunk
warnings remain. Ruff reports one existing B904 at the pre-existing backup refusal
in `api/cowork_sync.py`; it is not a new one-editor implementation diagnostic.

## Safe startup and human trial

Use the **complete existing Agent interpreter**, the existing Agent source checkout,
and independent trial directory with `tests/cowork_trial_server.py`. The ignored
local handoff records the exact executable, command, current loopback URL and test
password-file path without including a password in committed documents. Do not
start a duplicate listener if the handed-off trial is already running. The trial
has its own Agent home, WebUI state, workspace, credentials and cookie namespace;
no production consumers start. Its ordinary browser tests use a local synthetic
shared directory. The real cloud proof is a separate opt-in artifact, not a claim
that the production or local trial root has been bound to the user's document tree.

1. Open a fresh test document and wait for connected status. Type synthetic text;
   verify its watched Office filename updates, not a new export generation.
2. Make the browser offline; native/AI/voice writes must pause. Reconnect without
   editing Office; the stable local version automatically reloads and enables editing.
3. Simulate a separately delayed Office arrival with only a newly created synthetic
   watched file. Idle WebUI automatically imports it and resets native Undo. If new
   WebUI work precedes that arrival, retain both and choose the arriving version or
   export the draft. Inspect native/Office recovery directories before discarding.
4. Never use existing user documents for these tests. Do not use this prototype as
   a two-writer or backup-retention guarantee.

## Remaining limitations and gates

- One cooperating editor at a time. Native coordination cannot prevent every
  noncooperative last-read/rename overwrite; the earlier counterexample still holds.
- Remote offline changes and remote upload completion cannot be inferred from
  browser presence. Local settling is bounded waiting, not global synchronization.
- Whole-package fidelity gates remain narrow. Many ordinary Office-authored files,
  custom formatting/metadata and tables are refused rather than flattened. No Word,
  Excel, LibreOffice, Pages or Numbers application was installed for real-app tests.
  Common Office compatibility was not broadened in this change.
- macOS plus installed Swift/Foundation is required for the current same-file path.
  Provider conflict rejection is implemented, but real multi-device conflict-version
  retention and independent receiving-device delivery remain unqualified.
- Native/Office backups preserve persisted drafts. Every unsaved offline keystroke
  is not crash-durable; keep the tab open or export a draft. No recovery browser,
  pruning, production migration, deployment or full-repository/CI run is claimed.
- Parent review remains required before publishing source or generated assets.
