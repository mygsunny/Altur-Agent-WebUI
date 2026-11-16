# UI change log

This log tracks accepted fork changes. Keep it current with each related feature or fix, link the pull request or commit, and distinguish local verification from CI and deployed behavior. Do not add credentials, machine paths, private network details, user conversations, or deployment-only launchers. The release-maintained root CHANGELOG.md remains unchanged.

## Co-work inline clarification answers

- Each active clarification now has a command-bound reply field and Answer button.
  Answer retries the same logical FIFO head and immutable command ID with the
  original instruction and up to three question/answer turns serialized as bound
  context through the existing tool-free intent endpoint. Reply text is limited
  to 2,000 characters; composed requests above the existing 20,000-character
  endpoint limit are refused visibly without releasing the barrier.
- Reclarification updates the same row. Ordinary answer failures keep the draft
  and dependents paused for explicit retry. Dismiss skips/resumes; Stop, document
  switch and disconnect invalidate replies. Security barriers remain closed.
- Focus the inline reply to direct finalized voice transcription into that draft,
  then click Answer. A visible focus indicator explains this target. Speech
  outside this field remains a separate command; exact spoken Stop still cancels.
- Verification: 99 Node tests and 12 Firefox fixture tests passed. The baseline
  built bundle independently fails the Answer UI test because no reply field
  exists. All 91 manifest artifacts matched exact isolated served bytes.
- Local Firefox uses the built bundle and real editor/recorder with synthetic
  audio and controlled inference/transcription fixtures; it is not real-model or
  microphone-hardware acceptance. No backend change or production restart.
- Updates [draft review #4](https://github.com/mygsunny/Altur-Agent-WebUI/pull/4).

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

## Welcome photo download size (local source only)

- The Photo artwork loaded the 11.5 MB, 5600×1586 `welcome-feast.png` on every cold load. Slow links painted it top-down, so the table looked cut off with an empty slot beneath until the download finished.
- Added resized WebP copies (`welcome-feast-1200.webp` 107 KB, `-2400` 331 KB, `-3600` 589 KB, alpha preserved). The original PNG is kept unchanged as the source asset. `welcome-artwork.js` now sets `srcset` with `sizes` derived from the saved desktop/mobile target height, so the browser fetches one copy matched to pixel density. The `index.html` script URL gains `art=webp` because static JS is served `immutable`.
- `tests/welcome-artwork-first-paint.cjs` now gates `welcome-feast-*.webp` instead of the PNG.
- Verified in Chromium against the live shell with mocked settings: 1440×900@1x fetched only `-2400`; 1512×860@2x, 390×844@3x and 655×874@2x fetched only `-3600`. Layout geometry is identical to the PNG. Also passed `python -I -m unittest tests.test_welcome_artwork` and `git diff --check`.
- Not verified: `node tests/welcome-artwork.http.browser.cjs` could not start its fixture (it timed out preparing an isolated Hermes runtime). `node tests/welcome-artwork.browser.cjs` fails `240 !== 160` at the 430px viewport both with and without this change, so it was already failing.

## New chat startup/refresh follow-up (local source only)

- Fixed first-paint ownership: the HTML's Original logo used to paint before the asynchronous settings GET selected Photo/None. CSS now keeps only the unresolved artwork slot invisible (space retained); welcome text, suggestions and composer are not hidden. Original reappears normally when authoritative settings select it. No localStorage artwork cache or new backend metadata is introduced.
- Photo and its halo remain invisible until `img.decode()` resolves, guarded by the request's profile generation. Failed decoding stays blank rather than showing another mode. Changed static assets have explicit cache-busting URLs.
- Fixed mobile welcome auto-scroll: composer growth reused the transcript bottom-pin helper, whose synchronous and next-frame writes treated welcome artwork as a conversation tail. Welcome now bypasses those writes, including late settle callbacks. Explicit New chat / transition into welcome resets message/document position once and invalidates old settle work. Later hydration does not reset a user's scroll, and genuine transcript following/sticky unpin remain active.
- Added `tests/welcome-artwork-first-paint.cjs`, invoked by the full HTTP suite. Real server settings/auth and generated fixture credentials; separately held settings GET and cold photo transport; frame sampling before hydration and through decoding. Fresh Chromium processes plus refresh cover Original/None/Photo at desktop 1440×1000, touch portrait 430×600 and touch landscape 820×430. Assert no wrong Original frame, no visible undecoded photo, both scroll positions stay at top, composer growth cannot bottom-pin welcome, explicit `newSession()` resets to top, subsequent manual scrolling is retained, and a fixture transcript still follows the bottom / respects unpin / rejects an old queued retry on return to welcome.
- RED evidence: first test failed with `unresolved photo/1440: Original logo painted` at `mode:null`; the added scroll regression failed with composer-resize position `126` instead of `0`. GREEN: `node tests/welcome-artwork.http.browser.cjs` passed startup checks, all **196** width samples, **701–703** transient animation frames around 640/900 breakpoints, saved artwork geometry/settings/auth and six authoritative login cases. `FIRST_PAINT_ONLY=1` selects the tight startup loop. Use existing `PLAYWRIGHT_MODULE`, `FIXTURE_PYTHON` and optional `FIXTURE_PYTHON_ARGS` overrides for local dependencies.
- Also passed `node tests/welcome-artwork.browser.cjs`, `node tests/login-appearance.browser.cjs`, `node tests/rail-reorder.browser.cjs`, `node tests/sidebar-new-chat.browser.cjs`, `python -I tests/test_welcome_artwork.py`, and `git diff --check`. An initial Python invocation through a runpy bootstrap failed because unittest received the script path as a test selector; the portable direct invocation passed. One existing HTTP visibility assertion now waits for decoded-photo readiness rather than only settings hydration. A test-only manual-scroll probe initially changed modes and triggered browser scroll anchoring; it now rehydrates the actual unchanged saved settings before checking the no-reset invariant.
- Static-only implementation: `static/index.html`, `static/style.css`, `static/welcome-artwork.js`, `static/ui.js`, `static/sessions.js`. No backend changes/restart required. No deployment, push, merge, production credentials/state access, or physical-phone acceptance; Chromium touch emulation and fixture transcript scroll-policy checks are not a real iOS keyboard or model-stream certification.

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

## Responsive expansion follow-up (local only)

Tracking: follow-up on `feature/welcome-artwork-login-theme` / PR #3; this follow-up is not deployed or published.

- Reproduced expansion-only shell flicker at the actual **640 → 641** and **900 → 901 CSS px** boundaries. Closed fixed-position drawers retained their full overlay widths, then interpolated those widths inside the desktop flex row. The main column transiently collapsed to 0 px (settled 592) and 420 px (settled 552), respectively. This also briefly selected the composer's burger layout before restoring its settled controls. Reverse-direction changes did not have the same undershoot.
- Closed overlays now finish their existing 250 ms closing slides, then park at zero width. Opening restores the normal drawer width immediately. Sidebar/workspace controls, opacity/transform/right transitions, mobile touch sizing and responsive breakpoints remain enabled; no global animation suppression or observer-error filtering was added.
- No independent 830 px breakpoint or artwork scaling reproduced: direct loads and both resize directions at 850/840/831/830/829/820/800/769 preserve the desktop image height and shell font sizes, zoom, padding, gaps and chrome heights. At tall heights, the image remains approximately 847.41 × 240 px; only the masked crop narrows (701 px at viewport 830). The separate 160 px mobile artwork target is intentionally selected at **768 CSS px**, not 830. Shell phone chrome changes at 640; workspace/default sidebar compact policy changes at 900. Approximate external window dimensions do not establish CSS viewport width.
- The previous verification sampled 1440/900/430/320 and did **not** certify transient expansion or the 830 band. The full HTTP suite now calls `tests/welcome-artwork-breakpoints.cjs`: 196 settled direct-load/descending/ascending samples across 16 widths at fixed heights 1000/800/600/430, plus animation-frame captures in both directions across 630–680 and 880–920. It asserts unchanged intrinsic aspect/height/centering, no artwork-added document overflow, no 830 shell scaling, and no expansion undershoot at either confirmed boundary. Drawer open/full width, width retained during closing animation, and zero-width parking are checked too.
- Observed RED before the CSS fix for the 900 boundary in the real full-server regression and the 640 boundary in recorded-frame assertions; GREEN on the isolated feature source and a physical copy of the independently branded live source with only the narrow CSS patch applied. Generated credentials/temporary state only. Focused artwork/login, rail/sidebar, schema and password-policy regressions also passed. No production restart, deployment or preference change.

## Welcome artwork and theme-matched login

Tracking: [pull request #3](https://github.com/mygsunny/Altur-Agent-WebUI/pull/3), branch `feature/welcome-artwork-login-theme`, stacked on the maintained Desktop discovery/password fixes. Published and locally deployed after parent verification; not merged. GitHub reports no checks.

### Added
- Appearance choices **None**, **Original logo** (unchanged default), and **Uploaded photo**, using the intentional supplied transparent PNG. Welcome text, suggestions and composer remain intact.
- Independent desktop/mobile saved photo targets, default 240/160 CSS px, bounded 64–600. Fixed-height natural aspect rendering, centered left/right cropping and narrow real-alpha edge masks. Width-only resizing does not scale the image; crossing the mobile breakpoint selects the other target.
- Separate saved **Show logo glow** toggle, default on. Off removes the actual circular `::before` halo in original and photo modes, not the artwork. None mode never leaves a halo behind.
- Independent saved desktop/mobile welcome-group positions, default centered at 0 CSS px, bounded -300..300 (negative up, positive down). Move the selected logo/artwork, heading, descriptive text and all three suggestion buttons in one wrapper; do not move composer, sidebar or header. Clamp the effective offset against available message/visual viewport and composer space, and restore it as height returns without changing saved values.
- Measured message/group/composer/visual-viewport geometry proportionally shrinks artwork on short/keyboard-constrained screens, keeping it visible on representative 430/530 CSS px landscape screens and restoring the target as height increases. Width-only resizing does not change the height budget; oversized content remains scrollable.
- Narrow one-key settings writes through the existing FIFO, with hydration that never saves and profile-generation guards for queued writes and late responses. Existing settings-file ownership and unrelated preferences are preserved.
- Shared blocking app/login prepaint appearance resolver and application stylesheet palette. Login receives normalized allowlisted theme/skin only, follows Light/Dark/System, updates on OS changes in System mode, and overrides stale browser appearance cache with saved server values. Authentication routes and security policy are unchanged.
- Public [design](welcome-artwork-design.md) and [verification plan](welcome-artwork-plan.md), including portable commands and explicit evidence boundaries.

### Local verification
- Observed RED then GREEN for missing artwork settings/rendering and login palette, stale-profile responses, queued-profile writes, maximum-height short-screen geometry and malformed artwork enum types.
- The added glow/position requirements also ran RED → GREEN. Real browser controls sent exactly one setting each. Persisted glow false/true removed/restored the selected pseudo-element in both artwork modes. All three modes moved every visible welcome child equally at desktop/mobile widths, while composer, header and sidebar coordinates stayed fixed. Independent offsets round-tripped; both positive/negative extreme offsets clamped at short heights and restored when tall again.
- `python3 -m unittest discover -s tests -p test_welcome_artwork.py -v`: settings schema/default/range contract passed.
- `node tests/welcome-artwork.browser.cjs`: three modes, independent targets, desktop/mobile width-only resizing, vertical shrink/restore, alpha mask, late-response and queued-write ownership guards passed.
- `node tests/login-appearance.browser.cjs`: six first-frame Light/Dark/System × OS cases with palette and live System updates passed.
- `node tests/welcome-artwork.http.browser.cjs`: real disposable loopback HTTP server and Chromium desktop/touch-mobile fixtures passed persisted reloads, independent heights, one-key writes preserving unrelated preferences, malformed/out-of-range rejection, decoded PNG transparency, aspect/centering/crop/mask geometry, maximum-height short viewports, portrait/landscape composer bounds and six authoritative login first-frame cases. Generated-password login, protected API rejection, browser CSRF refusal, signed-in optional reentry, disable-auth refusal, exact password spaces and logout revocation also passed.
- Existing rail and sidebar Chromium suites, five password-policy tests and ten disposable SQLite Desktop discovery tests passed. Changed JavaScript syntax and whitespace checks passed.
- Synthetic screenshots were inspected locally; no user conversations, production account state or credentials are included. These are local tests, not GitHub CI, a production deployment, hardware passkey/external OIDC certification or physical-phone keyboard testing. Existing collapsed-right-panel document overflow and password-rotation session lifetime policy are preserved, not repaired by this feature.
