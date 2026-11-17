# Selected-folder same-file sync (experimental, one cooperating editor)

This isolated feature now uses **automatic connection reconciliation**, not routine
Edit externally / Resume clicks. The user clarified that Office is used only while
WebUI is inaccessible. This is a cooperating-user workflow, not a universal lock
against simultaneous Office/WebUI edits. No production deployment is authorized.

## Operator prerequisite

An explicitly selected existing directory is mapped to exact profiles in
`HERMES_WEBUI_STATE_DIR/cowork-office-roots.json`:

```json
{"default":"/absolute/path/to/disposable/shared"}
```

Missing entries disable Office sync. Clients cannot supply filesystem paths. Use
independent trial state, credentials, cookie namespace and loopback listener. No
recursive discovery, default iCloud binding, placeholder download, real-document
migration or background consumers are enabled. Same-file publication currently
requires macOS Foundation/CryptoKit and the installed `/usr/bin/swift` toolchain.
Other systems fail closed rather than substituting an uncoordinated replacement.

## Connection and state ownership

- The browser polls every two seconds. A server connection grant lasts twelve
  monotonic seconds and is bound to process epoch, document and browser owner.
  Status heartbeats renew an existing grant; a normal snapshot save, inference
  request or old acknowledgment cannot revive an expired grant.
- The client immediately freezes native/AI writers and voice on its offline event.
  An eight-second response watchdog handles a stalled connection; ordinary API
  requests have an eight-second deadline. An undetectable connection break has a
  bounded detection interval, not an instantaneous server-side disconnect signal.
- Reconnect, browser reopen and server restart begin with writers paused. The
  browser automatically yields any old grant, waits a five-second local settling
  window, and reconciles the readable local Office file. Two observed matching
  hashes, complete ZIP checks and native provider/conflict checks precede import.
- This waiting window is **not remote-upload completion**. If iCloud delivers bytes
  later while WebUI is idle, polling detects and automatically imports them. A new
  browser edit before that arrival makes the versions conflicting: retain both,
  pause writers and show **Use arriving Office version (draft preserved)**. The
  user may export the native draft instead. There is no timestamp arbitration.
- A local snapshot, Office baseline and Office publication are separate state
  layers. Native drafts and prior canonical snapshots are backed up before an
  external native replacement. An import reconstructs the native adapter and
  resets Undo. Its unique offer token, Office hash and normalized native hash are
  committed with the snapshot. A dropped save response is read back; dropped
  acknowledgments retry only acknowledgment, never a second native reconstruction.
- Inference is tool-free. The backend checks the connection grant before and
  after model inference; a changed grant rejects old intent results. The browser
  stops its controller/listening session on loss and quarantines late completions
  across document generations. No disconnected server AI writer is introduced.

## Same-file publication and the noncooperative boundary

First publication creates `<document-id>.xlsx` / `.docx` only if absent. Subsequent
WebUI-owned updates save **that same name**, through a real `NSFileCoordinator`
accessor. The helper checks provider downloading/conflict status and the expected
content hash before descriptor-relative replacement of an fsynced staged file.
Recoverable incoming and outgoing Office copies are written first. A detected
external change pauses publication and preserves both, rather than overwriting it.
Unresolved provider conflict versions and missing/unavailable files remain paused.

Native coordination is not an atomic compare-and-swap against a writer that
bypasses it. The prior [native counterexample](cowork-samefile-qualification.md)
remains valid: an uncoordinated rename after the last read can be overwritten, and
ordinary backups do not guarantee preservation of that intervening version.
Use Office only while WebUI is inaccessible. We cannot detect an Office application
closing, an offline device's unsent changes, or remote upload completion from a
browser heartbeat. No simultaneous-edit guarantee is offered or implied.

The older generation-publication implementation remains available for historical
regression tests, but the current UI calls the connection-granted same-file path.
A bound connection-managed file cannot use legacy `publish` to bypass ownership.

## Fidelity: preserve or refuse

The existing whole-package round-trip gate remains deliberately strict:

- XLSX: scalar values and ordinary formulas, default visible sheets and geometry,
  up to 1000 rows by 100 columns. No styles, hidden sheets, custom dimensions,
  unknown metadata/parts, charts or cached-formula compatibility promise.
- DOCX: plain paragraphs/text/line breaks with the pinned writer's default package.
  Tables, marks, tracked changes, custom styles/layout and foreign package metadata
  are refused for sync. Native editing and explicitly lossy manual download have
  wider capabilities; those are not same-file fidelity guarantees.

All package parts/XML fields are compared. Unknown native fields also pause
publication. Original uploads retain exact bytes. There is no silent stripping of
unsupported features. Many ordinary Word/Excel-authored files, including some
semantically equivalent encodings, still fail this gate. No installed Word, Excel,
LibreOffice, Pages or Numbers application was available for real-app qualification.
Do not advertise ordinary Office interoperability from generated fixtures alone.

## Recovery and confinement

Office copies: `cowork/<profile>/office-backups/<document-id>/`.
Native recovery envelopes: `cowork/<profile>/native-backups/<document-id>/`.
SQLite retains current/previous canonical snapshots. Recover native envelopes
through native import; copy an Office recovery version separately before choosing
it as the watched file. No pruning or recovery browser is implemented. A draft not
successfully persisted while offline still depends on retaining the browser tab or
exporting it; arbitrary browser crashes cannot preserve every unsaved keystroke.

Roots, configuration, private databases/locks and backup paths retain no-follow,
descriptor-opened safeguards. Private directories are 0700, state/backup files 0600.
Symlink/hardlink and SQLite sidecar refusal remain. Database images are serialized
under process/interprocess locks, a prototype tradeoff, not a production scalability
qualification. No older writer may run against the same state concurrently.

## Verification and safe testing

```sh
./scripts/test.sh tests/test_cowork_connection.py tests/test_cowork_oneowner.py \
  tests/test_cowork_sync.py tests/test_cowork_sync_security.py \
  tests/test_cowork_sync_paths.py tests/test_cowork.py -q
cd editor
npm test
npm run build
COWORK_TRIAL_DIR=/absolute/isolated-trial \
  npx playwright test tests/auto-sync.spec.js tests/browser.spec.js --workers=1
```

Use `tests/cowork_trial_server.py --agent-source <existing-agent-source>
--trial-dir <independent-trial>` with a complete existing Agent interpreter, not an
incomplete test interpreter, for actual inference/STT. Do not copy production
profiles or credentials. Browser tests create only synthetic document IDs in the
trial root. `tests/cowork_cloud_proof.py` is opt-in: it creates a fresh UUID child
beneath an explicitly supplied test parent and never opens an existing document.
`tests/cowork_cloud_status.swift` reads provider metadata for the exact proof file.
Local same-file readback, provider-reported upload, and receiving-device delivery
are distinct claims. Independent device delivery and provider conflict retention
remain unverified. Review is required before publication, merge or deployment.
