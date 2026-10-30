# Welcome artwork implementation and verification plan

1. Branch from the maintained Desktop discovery/password policy tip, not the independently modified deployment checkout. Preserve those inherited fixes. Keep all work isolated; no deployment, pushes, merges or live service restarts.
2. RED → GREEN: validate artwork defaults, enum and independent 64–600 height ranges in `tests/test_welcome_artwork.py`. Extend the current schema. Add the supplied intentional PNG, Appearance controls and profile-hydrated renderer. Use one-key FIFO writes, not broad form autosave.
3. RED → GREEN: Chromium tests in `tests/welcome-artwork.browser.cjs` exercise None/Original/photo, width-only desktop/mobile crops, height shrink/restore, alpha masking and profile-generation protection. Late-response and queued-write regressions must fail without their guards. Extend the same schema/one-key path for the separately saved default-on logo glow and independent default-zero desktop/mobile whole-group offsets (-300..300). The full HTTP suite must observe missing halo suppression and equal-child translation failures before implementation, then verify both pseudo-elements, None/no-orphan behavior, all three modes, independence, short-screen positive/negative clamps and tall-screen restoration.
4. RED → GREEN: `tests/login-appearance.browser.cjs` checks Light/Dark/System against both OS schemes on the first frame, with empty storage and palette resolution. Share the blocking prepaint resolver and existing CSS tokens, expose only normalized theme/skin, follow System changes.
5. `tests/welcome-artwork.http.browser.cjs` starts `tests/welcome_http_fixture.py`: the real loopback HTTP handler, no main startup workers, temporary state and generated credentials. Exercise persistence/reload, narrow writes, invalid values, width-only crops/aspect/centering, maximum-height short screens, composer bounds, saved login appearance overriding stale cache, CSRF rejection, optional signed-in password reentry, space-sensitive passwords, disable-auth refusal and logout revocation. Inspect fixture screenshots.
6. Re-run sidebar/rail, password and Desktop discovery tests, syntax and whitespace checks. Commit only the explicit feature-owned source, tests, docs and intentional asset. Parent independently reviews before any publication or deployment.

## Reproducible commands

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

## Recorded rulings and limits

- The executor's scope ends at a local commit: publication, independent review and deployment remain with the parent, superseding the original plan's later publish/deploy steps.
- Very short screens may reduce the artwork to zero to prioritize chat usability. No saved preference is changed.
- The maintained shell's collapsed right-panel DOM can already extend the document scroll bounds. The full-server test compares artwork against the None baseline rather than claiming this feature fixes that unrelated shell condition.
- Preserve the maintained authentication lifecycle rather than adding all-session revocation to password rotation. Logout revocation is tested separately.
- UI translations fall back to new English keys until translations are supplied.
