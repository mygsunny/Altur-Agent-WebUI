# Co-work editor integration: proposed design

Status: isolated implementation approved with the updated one-editor connection workflow below. Production deployment, publication and merge remain gated by parent review and authorization.

## Intent and agreed behavior

Embed spreadsheet, document, and PDF work in the existing WebUI, with a human and AI editing the same active document. All editor components must be free/open-source. Preserve authentication, sessions, integrations, and running workers. Track work in GitHub; do not merge or deploy without approval.

The human and AI use one ordered editing command path. The latest applied action wins on overlapping content; AI may overwrite a newer human edit if its action is applied afterward. Apply targeted edits rather than restoring stale whole-document snapshots. Resolve targets against the live document at execution time; missing/deleted or ambiguous targets require clarification rather than guessing. Concurrent action ordering is application order, not speech-start time.

Use one shared undo/redo history per document for human and AI edits. Command+Z and spoken undo invoke the same document undo command. Group a coherent AI instruction into one transaction where feasible. Normal edits after undo invalidate redo according to the editor's native rules. Do not add a separate AI undo stack. Undo must work when voice controls have focus, not only when a cell is focused. Selection-only events and autosave are not edits.

Voice is explicitly enabled by the user, visibly indicated, and immediately pausable. AI infers command versus dictation from speech, selection, and active document; no mode toggle. Users intend clear working speech, not casual conversation. Show partial transcripts but execute only finalized phrases. Clear reversible instructions execute without routine confirmation; ambiguity requests clarification. Spoken stop cancels pending AI work, whereas undo reverses the latest completed edit. Cancellation prevents queued commands from applying and discloses already committed actions; it does not secretly roll them back. Manual input remains usable while inference runs. English and Simplified Chinese/mixed-language input are intended; exact STT support requires testing.

## Approaches

1. Univer for every format: attractive unified APIs, but may depend on proprietary packages for conversion, PDF editing, and collaboration. Not suitable unless every shipped dependency and needed capability is verified open-source.
2. Shared co-working controller with editor adapters: recommended approach discussed with the user. Use open-source Univer for spreadsheet capabilities and appropriate open-source document/PDF adapters when necessary. One command/voice/history contract, without claiming identical file fidelity.
3. Agent rewrites files in the background: rejected because it breaks immediate shared editing and coherent undo.

User has agreed to free/open-source components, shared latest-action priority, shared native undo, inferred voice intent, and an isolated branch. Exact editor package choices remain builder proposals subject to license/capability verification, not approved promises.

## Architecture proposal

- A lazily loaded Co-work editor module inside the existing vanilla-JS shell; isolate any required bundling to that module rather than replacing the WebUI frontend.
- Adapter contract: open/close, read live selection/content, execute targeted transaction, undo/redo, export, and report capabilities. Each active document has one authoritative editor model and command executor. First release targets one interactive browser owner per document plus its AI, not network multiplayer editing. Reject or explicitly mark other writable tabs rather than allowing divergent shared histories.
- Intent service converts finalized utterances or text requests into a constrained operation schema, never arbitrary JavaScript or shell execution. Document text is untrusted data, not permission to run commands. Validate operation type, target document, coordinates, and arguments before execution.
- Bound each request to document identity and listening session. Switching documents cancels or quarantines pending requests; never retarget an in-flight command to the new active document. Use an utterance ID and operation IDs to prevent retries from duplicating edits.
- AI actions read relevant current content at execution. For a semantic command that becomes invalid after manual edits, resolve against current context or clarify. Latest-action priority does not justify unrelated cell/text loss.
- Autosave native working snapshots through authenticated, profile-scoped APIs with atomic replacement and recoverable prior versions. Originals remain untouched until explicit save/export selection. Never expose unrestricted filesystem paths. Recovery snapshots are separate from editor undo, and undo-across-restart is not promised.
- Existing login, CSRF, workspace authorization, and profile boundaries apply to new endpoints. Keep credentials server-side; do not start or resume gateway workers automatically.
- Voice uses the configured speech/model services if compatible; free/open-source editors do not imply free inference. Do not add a paid editor/conversion service or send documents to a new third party without approval. Mobile microphone use needs a secure browser context; current LAN HTTP must not be represented as mobile-mic ready. Choose approved HTTPS/local access during implementation rather than adding a public tunnel.

## Confirmed delivery scope

The user selected spreadsheets and documents for the first complete delivery. PDFs and all other editor types are deferred; PDF capabilities are not a blocker for this release. Spreadsheet-only milestones are intermediate, not completion. Supported file formats and fidelity must be documented from real OSS adapter tests before implementation acceptance.

All human and AI mutations must enter each document's one undo history. Grouping granularity may vary by adapter; undoability is mandatory. An action is applied when its synchronous editor transaction commits through the shared command executor. Serialize target validation and mutation in that same execution boundary. Prefer atomic transactions; if an adapter cannot roll back partial failure, report committed parts explicitly and preserve their undo records.

Before starting the test instance, verify independent configuration, state, workspace, credentials and session cookies, free loopback port, and disabled background consumers. Never rely on a disposable home alone to establish isolation.

## Phases and acceptance gates

1. Capability/license spike after approval: pin exact Univer OSS versions; verify edit APIs, transaction grouping, undo/redo, formulas, CSV/XLSX conversion and file-fidelity limits. Evaluate an OSS document adapter. No product claim based solely on marketing pages. Unsupported imports fail clearly, never silently drop data.
2. Spreadsheet end-to-end: interactive grid; manual plus AI edits; inferred voice commands/dictation; one undo history; pause/stop; autosave/reopen; supported import/export with documented limitations.
3. Documents: equivalent shared editing contract, paragraph/text/table operations and verified import/export scope. Native editing may precede DOCX round-trip fidelity; limitations must be visible.
4. PDFs: explicitly separate viewing/annotations/page operations from editing existing arbitrary text/layout. Begin with verified OSS capabilities; do not label annotation overlays as full PDF text editing. Scope beyond these capabilities requires a reviewed design update.
5. Other formats (slides, boards, etc.) are future extensions, not silently included in first-release acceptance.

Test pointer/keyboard editing, AI/manual interleavings, immediate overwrite ordering, grouped undo/redo, voice undo with controls focused, partial transcript non-execution, duplicate final events, stop races, document switches, invalid targets, disconnect/reload, atomic persistence, profile isolation, unauthorized API rejection, mobile/narrow and light/dark views. Browser simulations do not prove real microphone/STT behavior; record real-device tests and unverified boundaries separately.

## Isolation and tracking

Dedicated branch `feature/univer-cowork`, initially based on the committed Desktop discovery branch at `adfe642f24289d7b1270ca363925b34a121e6379`. This is an explicit provisional baseline, not a claim to include uncommitted live changes. Original maintenance conversation owns cleanup; reconcile its approved commits later, without copying private launchers or live state.

Use an isolated test instance with disposable home/state/workspace, loopback binding, explicit free port, synthetic files, and independent test credentials. Never point it at production session databases or start production consumers. No test instance has been started during design.

Record source changes and tests in the repository change log and a dedicated draft PR. Exclude private paths, credentials, user documents, and deployment records. Review before publication; no merge or live deployment without explicit approval.

## User-selected Office-file sync workflow

Created/uploaded XLSX and DOCX files should live in a user-selected iCloud shared folder, with native working snapshots retained separately for recovery. Users edit downloaded files offline in compatible local Office applications while disconnected from the Mini. After iCloud delivers changed bytes to the Mini, WebUI detects and imports the stable changed file. Reload resets editor undo history; the user explicitly accepts this. This is external Office editing, not an offline WebUI or offline AI requirement.

Before overwriting or reloading, preserve a recoverable copy and compare content hashes against the last imported/exported version. Uncontested external updates can reload automatically; concurrent unsaved WebUI edits require preserving both versions and an explicit choice, not filesystem timestamp-based arbitration. Avoid export/import feedback loops; verify complete readable files before import and do not overwrite unsupported content through lossy conversion. Keep original uploaded bytes. iCloud transport success must be verified separately from local write success, especially across macOS accounts. Exact shared-folder location and account/access permissions remain prerequisites for real-folder connection, not permission to guess or change another user's iCloud configuration. Use synthetic ordinary local directories for sync-adapter tests until the target is chosen. The existing build continues independently; production deployment and merge remain gated.

## Non-goals and unresolved gates

### Approved one-editor clarification (supersedes routine manual handoff)

Office is used only while WebUI is inaccessible. Connection loss or an expired browser-presence grant pauses native/AI writers and autosave; reconnect automatically reconciles stable locally delivered Office bytes before accepting writes. No routine Edit externally / Resume clicks are required. The server checks grant identity across inference; browser document/listening generations quarantine old tasks. A new connection is not proof of remote iCloud upload completion: wait visibly for local stability, continue watching delayed arrivals, automatically reload while idle, and retain native drafts plus incoming Office bytes on conflict. If the user edits WebUI before a delayed remote arrival, preserve both and require a genuine conflict choice. Reconstructing the native adapter resets Undo, as accepted. Crash/restart starts paused and requires fresh automatic reconciliation, never silent stale grant recovery.

Same-file autosave while WebUI owns the connection uses native coordination, expected hashes and recovery copies. This relies on cooperating users editing one place at a time. It does not guarantee preservation of a noncooperative write between final read and replacement, detect an Office application closing, infer unsent offline edits, or establish receiving-device delivery. Only fresh synthetic files in the explicitly selected cloud test folder are authorized. No existing documents or production profiles may be changed. See `docs/cowork-sync.md` for the implemented state machine and fidelity limits.

No full Office compatibility promise, macro execution, arbitrary agent filesystem edits, automatic external sending, proprietary editor dependencies, public exposure, or production migration. Multi-person/multi-device simultaneous editing is deferred; shared human/AI editing in one active editor is the initial target.

Builder must validate OSS licensing, document/PDF choices, native undo feasibility, model tool integration and streaming-STT capability before committing to supported formats. Any requirement that cannot be met is reported with evidence and alternatives rather than replaced with a fabricated working demo.
