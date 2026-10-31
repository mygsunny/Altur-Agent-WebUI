# UI change log

This log tracks accepted fork changes. Keep it current with each related feature or fix, link the pull request or commit, and distinguish local verification from CI and deployed behavior. Do not add credentials, machine paths, private network details, user conversations, or deployment-only launchers. The release-maintained root CHANGELOG.md remains unchanged.

## Co-work clarification dismissal resumes FIFO

- Dismiss now releases only the current document/session-bound clarification
  owner, restores waiting entries and immediately pumps FIFO exactly once. It
  skips the dismissed command; it never applies or automatically retries it.
- Unresolved clarification still pauses dependents. Authentication, ownership,
  disconnect and independent document barriers remain closed. Stop/switch and
  stale dismissal cannot resurrect canceled work; explicit failed-entry Retry
  retains its existing new-ID behavior.
- TDD reproduced the stall in actual controller source and Firefox on loopback
  and LAN before the fix. Verification: 89 Node tests and nine Firefox fixture
  tests passed. Intent responses were controlled mocks, not live-model evidence.
  Build succeeded with existing third-party/chunk-size warnings; all 91 manifest
  artifacts matched exact served bytes on both isolated origins, without restart.
- Updates [draft review #4](https://github.com/mygsunny/Altur-Agent-WebUI/pull/4).
  No merge, production restart, relay restart or existing-document edits.

## Co-work command-queue failure isolation

- Ordinary invalid intent responses, inference deadlines and command errors now
  fail only their own entry and advance the shared typed/final-speech FIFO.
  Failed entries offer explicit Retry (with a partial-application warning) and
  Dismiss; no destructive command is retried automatically.
- Authentication, ownership, disconnect and document-clarification barriers
  still stop dependent execution and disclose their reason. Stop and document
  switches keep generation/adapter guards against duplicate or late commits.
- Applied/canceled entries leave the active list immediately. Internal completion
  history retains at most ten ID/status records, without command transcripts.
  Running and Waiting are not hidden behind a truncated success list.
- Regression tests reproduced FIFO stalls and retained completions on the old
  source. Current source: 81 Node tests passed. Firefox fixture tests: seven
  passed, including loopback and plain-HTTP LAN invalid-response/timeout queues
  and authentication/ownership/disconnect barriers. Actual browser/editor/server
  paths were used; intent replies and 100ms deadlines were controlled mocks, not
  configured-model performance measurements. All 91 manifest artifacts matched
  the isolated trial's served bytes on both origins without a server restart.
- Updates [draft review #4](https://github.com/mygsunny/Altur-Agent-WebUI/pull/4).
  No production deployment, merge or existing user-document edits.

## Co-work actual-browser usability and command repair

- Fixed blank documents rendering as an unstyled 17px line: style the actual
  wrapped editor, provide an 850×400px page and a focusable blank-page hint.
- Native spreadsheet keyboard commits attach RGB text colors. Preserve this
  narrow style losslessly in XLSX both directions, instead of freezing subsequent
  input at the strict Office export gate. Other unsupported features still fail
  closed; auth, leases, autosave, conflicts and native Undo remain enabled.
- Unified finalized speech and typed commands in a visible immutable FIFO. New
  draft text cannot replace Running/Waiting entries. One inference/commit runs
  at a time; Stop, switch and connection loss invalidate bound work. Failures,
  clarification and deadlines pause dependent entries; overflow is explicit.
- Added bounded native content clearing rather than asking the model for a huge
  null matrix. Sparse A1-keyed context omits blank formulas while preserving
  zero, false, formulas and known/unknown bounds. Local configured GPT-OSS intent
  calls use low reasoning without changing provider/model or summary behavior.
- Request validation, model JSON and model schema now have separate safe error
  stages. Firefox missing-input errors identify microphone acquisition and an
  input-selection action. Plain HTTP displays a persistent trusted-HTTPS notice;
  no browser-security bypass, microphone change or client trust install.
- Verification: 74 Node tests, 46 focused backend tests, Chromium/Firefox/WebKit
  real-origin visible-page, sustained typing, real-model Apply and persistence
  regressions. Separate Firefox configured-model FIFO/clear/Undo test and real
  recorder test using explicitly synthetic audio passed. No physical-mic claim.
- Important deployment boundary: frontend build is exercised against the active
  isolated trial; backend reasoning/schema changes are verified in a separate
  disposable trial. The active trial was not restarted. Existing backend clear
  instruction timed out at 30s without mutation; reviewed backend cleared both
  near/far synthetic cells in 2.915s (HTTP 2.199s, native commit 87ms). Shared-model
  contention can still exceed the deadline; no guaranteed latency is claimed.
- See [repair evidence and limits](cowork-usability-repair.md). Updates
  [draft review #4](https://github.com/mygsunny/Altur-Agent-WebUI/pull/4), not merged.

## Co-work LAN manual-editor repair

- Fixed startup/New document/New spreadsheet failures on insecure LAN HTTP: use
  CSPRNG UUIDs and a pinned MIT SHA-256 fallback without global API polyfills.
- Missing Web Locks now uses fresh per-open server lease owners, not cloned tab
  session ownership. Existing server auth, CSRF, revision and Office grants remain
  unchanged. Close a prior LAN tab and wait for its lease before reopening.
- Login and ownership errors are actionable in the editor; insecure-origin voice
  refusal survives recorder cleanup and does not claim microphone availability.
- Regression: actual insecure-origin Chromium synthetic document/cell editing,
  persistence, cloned-tab refusal and real HTTP security checks; 65 Node tests.
  Build includes updated dependency notices/manifest. No production restart,
  real-document changes, merge or deployment. Updates the existing
  [draft review #4](https://github.com/mygsunny/Altur-Agent-WebUI/pull/4).

## Experimental selected-folder Office sync

Tracking: [draft pull request #4](https://github.com/mygsunny/Altur-Agent-WebUI/pull/4), branch `feature/univer-cowork-review`, based on `fix/desktop-session-discovery` at `adfe642f`. Draft review only; not merged or deployed. Publication uses a sanitized cumulative snapshot, not the private trial's intermediate commit history. Historical worker statements below describe their local verification scope before publication.

Publication verification: all 155 changed files were included in the privacy review; four UI images show disposable synthetic documents or an empty shell, not user conversations. Machine-specific documentation paths use `$HERMES_HOME`, `$AGENT_PYTHON` and `$AGENT_SOURCE` placeholders; original evidence stays local. The 90 generated-artifact manifest entries verify by byte length and SHA-256. Existing generated third-party string whitespace produces `git diff --check` warnings; compiled bytes were deliberately preserved rather than lint-rewritten. Local publication reruns: 64 Node tests and 38 targeted Python/macOS tests passed. Full repository CI, real Office application interoperability, physical microphone and cross-device delivery acceptance remain pending.

### Approved one-editor connection workflow (current isolated feature)

- Supersedes the older generation/manual-import UI described below: connection
  loss freezes native/AI/voice writers, reconnect waits visibly and automatically
  reloads a stable local cloud arrival before enabling editing. Late idle arrivals
  also reload automatically; divergent native drafts require a conflict choice.
- Connected WebUI autosave writes the same selected-folder filename using native
  coordination and recovery copies. One cooperating editor at a time is required;
  there is no universal Office lock or remote-upload-completion inference.
- Current source-executing voice/session tests and real Handler/filesystem/browser
  checks are recorded in `cowork-sync.md` and the isolated readiness report. The
  real selected cloud proof is synthetic-only. Device delivery, physical microphone
  and real Office application interoperability remain distinct unverified gates.
- No production deployment, push, merge, real-document changes or production
  profile/configuration changes were performed. Historical notes below describe
  the superseded implementation, not the current UI.

- Added an opt-in, profile-scoped operator allowlist for one Office directory;
  clients cannot choose server paths. Disabled without configuration.
- Added hash/stable-read external detection, preserved Office/native recovery
  copies, explicit conflicting-version import, offline/error status, and native
  editor reconstruction with Undo reset. Native and limited download exchange
  remain separate; unsupported sync content is refused.
- Existing Office targets are **never overwritten**. First publication is
  create-if-absent; later edits produce uniquely named output generations. The
  watched stable input is advanced only by the user's explicit Office-file
  handoff; this is no longer advertised as in-place two-way sync.
- Every external import is an explicit choice. Durable native import receipts
  and idempotent acknowledgments reconcile dropped responses without repeating
  editor replacement/Undo reset. Async operations bind immutable generations.
- Whole-package representability checks reject hidden sheets, defined names,
  custom geometry/layout, unsupported metadata/relationships and unknown native
  schema fields. Private descriptor-opened state/backup handling rejects symlinks,
  hardlinks and unrecovered SQLite sidecars.
- Local synthetic filesystem/backend/Chromium tests are documented in
  [cowork-sync.md](cowork-sync.md). No real iCloud or Microsoft Office test,
  production deployment or folder selection is claimed. Exact folder handoff is
  still required; no cloud multi-writer transaction is claimed.

## Navigation and New chat

Tracking: [pull request #1](https://github.com/mygsunny/Altur-Agent-WebUI/pull/1), branch `ui/sidebar-new-chat`. Published as a reviewable feature branch; not merged into `altur-branding`. Local checks passed; GitHub reported no checks for the branch.

### Added
- A theme-aware **New chat** row immediately below conversation search and above date-grouped conversations, with the supplied rounded pencil-in-square icon.
- A matching compose action in the far-left navigation rail. It starts at the top by default, but is movable along with Chat and the ordinary navigation tabs.
- A global compose action that switches to Chat from other pages before invoking the existing new-conversation handler. Existing unsaved-settings guards and empty-chat/draft behavior remain in force.
- Long press for 500 ms to enter reorder mode, then drag an icon onto another icon to move it. Click outside or press Escape to finish.
- Keyboard reorder with Alt+ArrowUp and Alt+ArrowDown.
- Saved ordering through the existing per-profile tab_order setting and prepaint browser cache. Existing saved orders retain their prior placement unless changed.

### Final visual decisions
- New chat and Chat can both move. Settings stays at the bottom; the optional external dashboard retains its existing fixed placement.
- Reorder mode uses a visible nine-degree wiggle with slight horizontal movement. Each cycle lasts 280 ms, slowed from the initial stronger-wiggle implementation at the user's request.
- Respect reduced-motion preferences with a static outline instead of animation.
- The Chat panel header retains its original plus icon. The compose icon is in the far-left rail, not a replacement for the header plus.
- Existing theme colors, rounded controls and sidebar alignment are retained. Mobile sidebar action targets are at least 44 px high.

### Safety and regression fixes
- Persist only tab_order during rail reordering, not unhydrated appearance-form defaults.
- Queue order writes and wait for them before loading Settings, preventing immediate Settings navigation from restoring an older order.
- Retain Chat's always-visible protection independently of its new movable position.
- Suppress activation during a drag or long press, but restore normal clicks after Escape, pointer cancellation, window blur, or hiding the page.
- Version changed assets so refresh retrieves updated CSS and controller code without clearing browser storage.

### Verification
- `node tests/rail-reorder.browser.cjs`: Chromium DOM tests of compose navigation from Chat, Tasks, Settings, Skills, Memory and Kanban; long-press/drag for Chat and New chat; saved order restoration; click suppression and recovery; keyboard reordering; touch pointer cancellation; narrow settings writes; Settings hydration ordering; reduced-motion and light/dark presentation.
- `node tests/sidebar-new-chat.browser.cjs`: desktop and mobile-width alignment, minimum target sizes, and click/Enter/Space delegation in light and dark themes.
- Tests require an available Playwright installation with Chromium. They use normal `require('playwright')`; set PLAYWRIGHT_MODULE to a separately installed module location if needed. They run with disposable DOM state and blocked network requests, not a production account.
- Separately exercised actual settings save/load in a disposable application home, confirming movable Chat is preserved in tab_order while Chat/Settings cannot be hidden.
- Deployed source was read back over HTTP and compared with the tested files; health and login returned 200, unauthenticated protected session access returned 401.
- These are local checks, not a claim of GitHub CI, authenticated production browser automation, real backend chat creation, or physical touchscreen certification.

### Maintenance
- Continue this log for later changes, and publish the source, relevant tests and safe visual evidence together in feature commits and pull requests.
- Local installation migration, reversible backups, guarded launcher and password-management work have separate private deployment records; they are not part of the publishable application source in this change.

## Desktop conversation discovery and signed-in password changes

Tracking: branch `fix/desktop-session-discovery`, stacked on the navigation feature. Deployment is recorded separately; passing isolated checks does not imply the running service has reloaded.

### Fixed
- Recover user-visible Desktop, GUI and local conversations independently of the 20-session recent-agent feed. Busy delegated children no longer evict older standalone Desktop chats from discovery.
- Deduplicate recovery by conversation lineage. Keep profile scoping, project assignment, archived flags and explicit-session lookup narrowing intact.
- Exclude hidden and delegated conversations from this recovery pass after resolving complete compression lineages, so hidden roots/intermediate segments cannot resurface under a tip ID. Keep background-source and ordinary CLI limits unchanged; run GUI recovery after CLI refill/budget accounting, and retain initial results if this optional pass fails.
- Make current-password reentry optional for password changes from an existing authenticated login session, as requested by the owner. Login remains required; any supplied current password is still verified. Disabling authentication or switching to passwordless retains current-password verification. This intentionally changes the fork's prior reentry policy.
- Explain the optional field in Settings, including the stronger requirement for disabling authentication. Blank general settings saves still leave the password unchanged; password spaces remain significant.

### Local verification
- Ten disposable-SQLite discovery tests cover recent-child starvation, hidden/delegated/background exclusions, user forks, archive identity, explicit IDs, malformed metadata, legacy schemas, source filtering, hidden root/intermediate/tip lineages, mixed CLI refill, and optional-query failure.
- Five policy tests exercise the actual settings-route guard and actual Settings save function, including unsigned refusal and the retained disable-authentication guard.
- Existing password-action and dialog tests were exercised with disposable DOM credentials; 25 cases passed. Both navigation browser suites, JavaScript syntax and whitespace checks also passed.
- An isolated loopback full-server test with generated fixture credentials returned 401 for unauthenticated protected access, 200 for a signed-in password rotation without reentry, 403 for disabling authentication without reentry, 401 for the old password and 200 for the new password. Authentication remained enabled.
- The same disposable server returned all four fixture Desktop roots despite 25 newer delegated children, and Chromium rendered all four roots visibly.
- These are local checks, not GitHub CI or a claim that a production password has been rotated.

## Co-work spreadsheet and document trial

Tracking: `feature/univer-cowork`, isolated provisional baseline `adfe642f`. User approved implementation explicitly; no publication, merge or production deployment is authorized by this entry.

### Added
- Lazy Co-work dialog in the existing shell, preserving mounted chat and editor state when hidden.
- Univer OSS spreadsheets and Tiptap/ProseMirror documents with one native human/AI undo history, targeted constrained operations, final-transcript identity/deduplication, immediate pending-work Stop and document-switch cancellation.
- Explicit microphone enable, Finish phrase and discard/pause controls using the existing server transcription endpoint. No new browser-vendor speech service.
- Profile-scoped current/prior snapshots, revision conflicts, server writer leases and browser ownership locks; no filesystem path API.
- Local limited XLSX/DOCX exchange with visible loss acknowledgment and unsupported-content refusals; native snapshot export for working-state preservation.

### Verification and limits
- 21 backend/auth/CSRF tests, 5 Node controller/exchange tests and 12 real Chromium checks pass; editor build, focused Ruff and production dependency audit (zero known vulnerabilities) pass locally.
- Browser evidence includes real manual spreadsheet keyboard input, formula evaluation, targeted edits/shared native undo, document paragraph/table editing, focused-controls undo, reload, competing-tab refusal, real HTTP authorization and genuine Office import/export.
- Synthetic recording reaches the real STT endpoint; a separate test checks real intent failure. Simulated Chinese undo/model schemas are explicitly integration fixtures, not evidence of inference or speech accuracy.
- **Full AI/voice live acceptance remains blocked:** independent Agent runtime is absent (`run_agent` import failure), configured inference returns 503, and the existing speech endpoint returns STT-unavailable 503. No production credentials were copied. Streaming partial STT and automatic phrase segmentation are not implemented; physical microphone/bilingual recognition remains unverified.
- See [co-work trial guide](cowork.md) for scope, reproduction, OSS versions, conversion fidelity, state ownership and remaining gates. Screenshots are synthetic isolated-state evidence, not production observations. Full repository CI and a fresh independent review are not claimed.
