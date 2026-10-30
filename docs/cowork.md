# Co-work editors — isolated trial

Status: **working manual editors and automated integration trial; full AI/voice live acceptance is blocked**. Nothing is deployed or merged. The trial intentionally contains no live credentials, Agent runtime installation, or configured speech provider. The actual intent endpoint returns 503, not fabricated edits. An independent runtime probe failed with `ModuleNotFoundError: run_agent`; the actual transcription endpoint returns 503, `Speech-to-text is unavailable on this server`.

## Run the artifact

The ordinary Python/vanilla-JS shell remains unbundled. Only this optional editor has a build, isolated under `editor/`. Generated `static/cowork/` assets are checked in so the normal app can serve the feature without npm at startup.

```sh
cd editor
npm ci --ignore-scripts
npm run build
cd ..
# Use the checkout's test venv (created by scripts/test.sh).
.venv/bin/python tests/cowork_trial_server.py
```

The harness prints a free **127.0.0.1-only** URL and writes it to ignored `.cowork-local/url`. It generates an independent synthetic password in `.cowork-local/password` (never print or commit it). Use its login page, then the sidebar's **Co-work · sheets & docs** button. Standalone editor path: `/static/cowork/index.html`. A successful open puts the document identity into the URL; refresh reopens that identity. Keep or bookmark that URL to reopen later. Native snapshot export is the full working backup format.

The harness clears inherited environment variables and pins independent OS HOME, Hermes home/base home/config, WebUI state, workspace, password and cookie name. It imports the **real server Handler**, but deliberately does not invoke `server.main()`: no gateway watcher, run resumption, plugin loading, completion drain, delegation poller or channel reaper is started. It does not restart any existing service.

`--agent-source /path/to/independent/agent-source` can add an installed Agent source checkout. This only selects code; it does not copy credentials or configure providers. A human must provision an approved independent test model/STT configuration in the disposable trial home before live inference testing. Do not copy a production `.env`, OAuth token, auth file, sessions, plugins or cron state. No new inference vendor or hosted conversion service is added by this feature.

## Editor and ownership contracts

- Spreadsheet: Univer OSS core preset **1.3.1**, Apache-2.0. Native pointer/keyboard editing, formulas and native undo/redo were exercised in Chromium. One `setValues` operation is one native undo record.
- Document: Tiptap core/starter kit/table **3.32.2**, MIT, using ProseMirror transactions/history. Paragraph/text replacement, append and table insertion commit to the same native history as human typing. Each AI transaction closes its history group before and after; no second AI undo stack exists.
- Human and AI edits are ordered by synchronous native transaction application. No stale full-document AI restoration. A spreadsheet operation binds an exact live sheet ID and explicit cell range; a document replacement must match exactly one text-only paragraph/heading occurrence at execution time. Missing/deleted/ambiguous targets refuse without changing the model.
- Shared Undo/Redo buttons and Cmd/Ctrl+Z outside the editor invoke the adapter's native history, including when voice/request controls have focus. Editor-focused keyboard commands remain native. Autosave, selection and ownership refresh do not add undo records. Undo history does **not** persist across reopening.
- Pending model work is generation/document/utterance-bound and final transcript IDs are deduplicated. Stop, pause, document switch and dialog close cancel pending application. Stop does not roll back committed edits. Aborting HTTP does not promise to interrupt a provider's already-running inference; its result cannot subsequently mutate the switched/stopped editor.
- A browser Web Lock rejects another writable tab in the same browser storage context. A server-side profile/document lease also rejects other browser owners. Lease TTL is 30 seconds; the client renews every 10 seconds and uses a conservative 25-second input/mutation deadline. Expiry/conflict freezes input and requires export/reload; there is no silent takeover or history merging. Closing the dialog hides rather than destroys the active editor; its model/history remain mounted.
- SQLite snapshots are authoritative for persistence only, not for undo. Transactions retain current and one prior snapshot; revision compare-and-swap refuses stale writes. `GET /api/cowork/document?id=ID&previous=1` reads the recoverable prior version. Database connections close on success and error. Snapshots have an 8 MiB limit.
- GET/POST routes retain the existing auth and CSRF boundary. The server derives the profile from request context; writes must match the current profile and have the current server lease. Clients cannot provide filesystem paths. Storage is under WebUI state, scoped by validated profile and document IDs.

## Intent and voice

`POST /api/cowork/intent` calls the existing **configured, profile-scoped tool-free model path** (`_llm_update_summary`), preserving its complete provider/protocol/credential routing. It asks for a strict JSON editing envelope, then validates IDs, operation names, exact fields, coordinate/value shapes and response limits. No regex command simulation, arbitrary code, shell or filesystem execution is provided. Document text is explicitly untrusted model input. One coherent operation per instruction is supported; compound/unsupported instructions require clarification.

Supported operations: spreadsheet set-range values/formulas; document unique-text replacement, paragraph append, table append; shared undo, redo and stop. Spreadsheet model context currently contains A1:T50 plus current selection and sheet identities; semantic targets beyond that context require clarification. Targeted writes are bounded to A1:CV1000. Model-produced text cannot safely infer missing target context by guessing.

Voice uses user-enabled MediaRecorder capture and the existing authenticated `/api/transcribe` multipart **file** endpoint. **Finish phrase** ends a recording and submits it as final; **Pause voice** discards capture and cancels pending work. No browser-vendor SpeechRecognition service is introduced. Streaming STT/partial transcripts and automatic silence-based phrase finalization are **not implemented** because the reused endpoint returns whole-recording final transcripts only. There is no command/dictation mode toggle; inference receives finalized text and the current editor context. Language follows the configured STT backend; real English, Chinese/mixed-language recognition is **unverified**. Localhost is a secure browser context; LAN HTTP is not mobile-microphone ready.

## Office exchange — deliberately limited, not lossless

All conversion runs locally in the browser. Imports create new editable copies and never overwrite originals. Before Office import/export, the UI requires acknowledgment of loss. Use native JSON snapshots for full working-model preservation.

| Exchange | Implemented/tested subset | Exclusions and behavior |
|---|---|---|
| XLSX via ExcelJS 4.4.0 (MIT) | Multiple sheet names/identities on conversion, numeric/string/boolean/null cells, explicit formulas; actual ZIP/XLSX bytes round-tripped through UI and converter tests; formula `SUM(A1:B1)` calculated by Univer | Values/formulas only. Formatting, charts, comments, metadata, merges, macros and page layout are not preserved. Date/rich-text/error/hyperlink/shared-formula cells are refused, not silently coerced. Import bounded to 1000 rows × 100 columns, 8 MiB. XLS/CSV not offered. |
| DOCX via Mammoth 1.13.0 (BSD-2-Clause) and docx 9.15.0 (MIT) | Paragraphs, headings, text, basic bold/italic/strike/underline, simple tables. Real DOCX paragraph + Chinese text + table survived browser import/export and independent raw-text extraction. | No full Word/page fidelity: styles, page layout, comments, tracked changes, images and complex objects are not preserved. Import rejects converter warnings/unsupported HTML nodes. Export rejects unsupported editor nodes/marks (including lists/links/code) and merged table cells; use native snapshots instead. Tested fidelity is semantic paragraph/table text, not rendered pagination or arbitrary Office files. |

No Univer Pro, paid editor, conversion SaaS, PDF editor, macro execution or network multiplayer is included. The 261 installed production dependencies have an allowlisted OSS license inventory and generated notices at `static/cowork/licenses.json` and `THIRD-PARTY-NOTICES.txt`. JSZip's MIT/GPL option is used under MIT. Exact dependencies are locked. `uuid` and `unzipper` overrides remove vulnerable/unclear older transitive dependencies; real exchange tests exercise the replacements. Latest local `npm audit --omit=dev`: **0 vulnerabilities** (not a security guarantee).

## Verification and remaining live gate

```sh
# Backend and neighboring authentication/CSRF checks; disposable HOME is important
# when the harness scratch root lies under the real user's Hermes scratch tree.
HOME="$PWD/.cowork-local/home" \
HERMES_WEBUI_TEST_STATE_ROOT="$TMPDIR/cowork-tests" \
./scripts/test.sh tests/test_cowork.py tests/test_issue1909_csrf_token.py tests/test_issue2572_csrf_diagnostics.py -q
.venv/bin/ruff check api/cowork.py tests/test_cowork.py tests/cowork_trial_server.py

cd editor
npm test
npm run build
# Install browser binaries only into ignored trial state if needed:
PLAYWRIGHT_BROWSERS_PATH="$PWD/../.cowork-local/browsers" npx playwright install chromium
# Requires the trial harness above already running:
TMPDIR="$PWD/../.cowork-local/tmp" \
PLAYWRIGHT_BROWSERS_PATH="$PWD/../.cowork-local/browsers" \
npx playwright test tests/browser.spec.js --workers=1 --timeout=30000
npm audit --omit=dev
```

Local evidence: **21 backend/auth tests**, **5 Node controller/exchange tests**, **12 Chromium tests**, editor build and focused Ruff checks pass. Synthetic screenshots: [shell closed](ui-ux/cowork/shell-closed.png), [shell open](ui-ux/cowork/shell-open.png), [spreadsheet](ui-ux/cowork/spreadsheet.png), [narrow dark](ui-ux/cowork/narrow-dark.png). Closed/open are two states of the implemented feature, not a historical pre-feature baseline. Existing pytest-asyncio configuration emits a deprecation warning; Vite reports ignored upstream `use client` directives and large vendor chunks. These warnings are not represented as pristine output. The full repository test suite and GitHub CI were not run.

Chromium covers actual shell lazy embed, manual typing, targeted native AI-schema operations, formula calculation, shared undo/redo with request controls focused, persistence/reload, competing-tab refusal, live HTTP auth/CSRF/revision/profile guards, partial/final/deduplicated transcript dispatch, narrow/dark controls, genuine Office UI exchange, and synthetic microphone recording/pause reaching the real STT endpoint. **One explicitly named test intercepts model responses to test finalized Chinese undo and Stop races. It is schema/dispatch coverage, not real model inference.** The separate real intent endpoint test observes 503 and proves no canned response is substituted. Synthetic microphone capture observes the actual STT-unavailable 503; it does not prove transcription accuracy or a physical microphone.

Remaining acceptance gate: independently provision an actual Agent runtime plus approved model/STT configuration, then exercise real natural-language editing/dictation, spoken undo/stop and bilingual/mixed speech with a physical device. Prompt-injection resistance, crash/fsync durability under power loss, network disconnect timing, mobile hardware interaction, broad Office fidelity and complete cross-browser lease timing have not been independently certified. This branch must **not** be called fully AI/voice live-test-ready until that gate is passed. Parent/fresh review is still required; no push, PR publication, merge or deployment has occurred.
