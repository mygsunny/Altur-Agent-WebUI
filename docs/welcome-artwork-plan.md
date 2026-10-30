# Welcome artwork implementation and verification plan

1. Branch from the maintained Desktop discovery/password policy tip, not the independently modified deployment checkout. Preserve those inherited fixes. Keep all work isolated; no deployment, pushes, merges or live service restarts.
2. RED → GREEN: validate artwork defaults, enum and independent 64–600 height ranges in `tests/test_welcome_artwork.py`. Extend the current schema. Add the supplied intentional PNG, Appearance controls and profile-hydrated renderer. Use one-key FIFO writes, not broad form autosave.
3. RED → GREEN: Chromium tests in `tests/welcome-artwork.browser.cjs` exercise None/Original/photo, width-only desktop/mobile crops, height shrink/restore, alpha masking and profile-generation protection. Late-response and queued-write regressions must fail without their guards. Extend the same schema/one-key path for the separately saved default-on logo glow and independent default-zero desktop/mobile whole-group offsets (-300..300). The full HTTP suite must observe missing halo suppression and equal-child translation failures before implementation, then verify both pseudo-elements, None/no-orphan behavior, all three modes, independence, short-screen positive/negative clamps and tall-screen restoration.
4. RED → GREEN: `tests/login-appearance.browser.cjs` checks Light/Dark/System against both OS schemes on the first frame, with empty storage and palette resolution. Share the blocking prepaint resolver and existing CSS tokens, expose only normalized theme/skin, follow System changes.
5. `tests/welcome-artwork.http.browser.cjs` starts `tests/welcome_http_fixture.py`: the real loopback HTTP handler, no main startup workers, temporary state and generated credentials. Exercise persistence/reload, narrow writes, invalid values, width-only crops/aspect/centering, maximum-height short screens, composer bounds, saved login appearance overriding stale cache, CSRF rejection, optional signed-in password reentry, space-sensitive passwords, disable-auth refusal and logout revocation. Inspect fixture screenshots.
6. Re-run sidebar/rail, password and Desktop discovery tests, syntax and whitespace checks. Commit only the explicit feature-owned source, tests, docs and intentional asset. Parent independently reviews before any publication or deployment.

## Reproducible commands

### Landscape reachability synchronization follow-up

The parent covering run's strict photo-top assertion was reproduced unchanged. Captured frame/write stacks (scratch `welcome-landscape-probe-6/landscape-frames.json`) show composer growth during the 250ms sidebar transition calling `boot.js`'s ResizeObserver → `_repinMessagesAfterComposerResize` → `_setMessageScrollToBottom`. After the harness reset scrollTop to zero, the helper's queued next-frame retry wrote the bottom again: scrollTop 175, photo top -128 versus message viewport top 39. This is not fractional geometry or unreachable negative-position content; it is the harness measuring after a competing pinned-transcript write. The old 100ms sleep does not establish settled geometry.

Repair is test-only: await actual document animations and three animation frames (observer delivery plus queued repin), then reset scroll and verify it stays zero across the next frame. Deterministically queue the same real helper before settling. RED without settling: 175 !== 0 (`welcome-landscape-deterministic-red.log`). Original strict top comparison remains, with rect/scroll/viewport diagnostics saved as `landscape-state.json`; no tolerance, retries, product changes, or animation suppression. Three consecutive covering HTTP runs passed (`welcome-landscape-green-{1,2,3}.log`), each including the full breakpoint matrix/transient and inherited HTTP gates. Artwork/login/rail/sidebar browser suites, artwork/password Python tests, and ten Desktop discovery tests passed. Discovery requires the app venv Python; system Python 3.9 fails importing its pre-existing union annotations. Earlier parent/probe failures remain intact outside Git. No deployment/publication performed.


Requires existing app dependencies and Playwright/Chromium; do not install them in a shared runtime just to run these tests.

```sh
python3 -m unittest discover -s tests -p test_welcome_artwork.py -v
node tests/welcome-artwork.browser.cjs
node tests/login-appearance.browser.cjs
node tests/welcome-artwork.http.browser.cjs
node tests/rail-reorder.browser.cjs
node tests/sidebar-new-chat.browser.cjs
python3 -m unittest discover -s tests -p test_password_reentry_policy.py -v
python3 -m unittest discover -s tests -p test_desktop_session_discovery.py -v
git diff --check
```

Use the application's supported Python version/dependency environment for server/SQLite tests. `PLAYWRIGHT_MODULE` optionally selects an existing module. `FIXTURE_PYTHON` selects Python; `FIXTURE_PYTHON_ARGS` is an optional JSON argument array for a configured isolated interpreter/bootstrap. `EVIDENCE_DIR` optionally saves synthetic fixture screenshots outside the repository. Tests bind only an ephemeral loopback port and stop that exact disposable server on exit.

## Independent-review regression verification

- RED: the previous full HTTP implementation returned photo height 0 at 430 px landscape. GREEN now requires >40 px, a larger positive 530 px landscape photo, width-only short-screen height locking and a bounded composer. Inspect the landscape screenshots; scroll constrained message content to its top to inspect the photo and to its last suggestion to prove reachability.
- RED: executing the complete real `loadSettingsPanel` function with delayed A settings, B generation/hydration, then A completion changed B mode to None. GREEN asserts B mode and its control remain Photo; explicit stale renderer ownership is rejected too. Ordinary boot, queued saves and late save responses remain covered.
- Passed focused artwork, full disposable HTTP/browser, login appearance, rail reorder, sidebar new-chat, artwork schema (1), password policy (5) and Desktop discovery (10) suites, plus JavaScript syntax and whitespace checks. These are selected regressions, not full repository certification.

## Responsive-breakpoint regression

`node tests/welcome-artwork.http.browser.cjs` also runs the shared `tests/welcome-artwork-breakpoints.cjs` full-shell regression. It navigates directly at each width and resizes down/up at fixed heights 1000/800/600/430. Widths are 1000, 901, 900, 850, 840, 831, 830, 829, 820, 800, 769, 768, 767, 740, 641 and 640. Capture image/natural/mask/group geometry, sidebar state, document-overflow baseline, shell fonts/zoom/transforms/padding/gaps/chrome heights, and composer stage classes. `EVIDENCE_DIR` saves `breakpoints.json` and `breakpoint-frames.json` without application/user contents.

Capture animation frames while expanding and shrinking across 630–680 and 880–920; assert no transient main-column undershoot at actual 640→641 and 900→901 boundaries. Closed off-canvas drawers must not interpolate their hidden full widths into the inline flex row; real drawer open sizes and existing closing slides must remain intact. No speculative 830 media rule or global animation suppression. See UI-CHANGES for the measured RED/GREEN mechanism and the separate intended 768 artwork target switch. An approximately reported physical window width is not proof of the CSS viewport width.

## Recorded rulings and limits

- The executor's scope ends at a local commit: publication, independent review and deployment remain with the parent, superseding the original plan's later publish/deploy steps.
- Short screens proportionally shrink artwork from measured chrome/group/composer geometry, retaining visible photos at 430/530 px landscape. Oversized groups remain scrollable without moving the composer. Width-only resizing locks photo height; no saved preference is changed.
- The maintained shell's collapsed right-panel DOM can already extend the document scroll bounds. The full-server test compares artwork against the None baseline rather than claiming this feature fixes that unrelated shell condition.
- Preserve the maintained authentication lifecycle rather than adding all-session revocation to password rotation. Logout revocation is tested separately.
- UI translations fall back to new English keys until translations are supplied.
