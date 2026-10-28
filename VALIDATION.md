# Validation record — October 27, 2026

Upstream WebUI baseline: `e40f042b6ec80199e06b7edf6e91a31beee2b812`.
Runtime: `bf0203a794a07aac3ff764972ab9087baa4e4f4e` (separate checkout), Python 3.14.10. Tests: Python 3.12.14. Asset tools: resvg-py 0.5.0 / Pillow 13.0.0. The supported isolated setup script completed successfully with the runtime's own dependency overrides.

## Automated results

Before application changes, `./scripts/test.sh tests/test_managed_runtime_startup.py tests/test_sidebar_tab_visibility.py -q`: **18 passed, 5 skipped**. No baseline failures observed in this focused set. This is not a claim that the entire inherited suite is failure-free.

Final focused/compatibility suite: **259 passed, 5 skipped** across branding, isolated startup, sidebar visibility, onboarding, authentication sessions/settings, passkeys, PWA manifests/service worker, subpath routes, default personalities, approval SSE, public shares and HTML export palettes. All 18 top-level JavaScript files pass `node --check`; Python source compilation and `git diff --check` pass. The entire inherited suite (thousands of tests) was not run.

Command (with isolated HERMES_HOME, HERMES_BASE_HOME and HERMES_WEBUI_STATE_DIR):

```sh
./scripts/test.sh tests/test_altur_branding.py tests/test_auth.py tests/test_auth_sessions.py tests/test_auth_settings_safety.py tests/test_passkey_auth.py tests/test_pwa_manifest_csp.py tests/test_pwa_manifest_sw.py tests/test_subpath_frontend_routes.py tests/test_default_personality.py tests/test_approval_sse.py tests/test_managed_runtime_startup.py tests/test_sidebar_tab_visibility.py tests/test_onboarding_static.py tests/test_session_public_share.py tests/test_session_export_html_palette.py tests/test_onboarding_mvp.py tests/test_onboarding_existing_config.py -q
```

Inherited name snapshots for onboarding, share headings and PWA names were updated to the intentional product behavior. During development, the new compatibility test caught a changed CSRF header; it was restored before acceptance. The generator regression caught overlapping source slots during a future-name change; simultaneous replacement now passes both repeatability and rename checks. These were fixed regressions, not baseline failures.

## Rendered browser evidence

- Fresh first paint and empty state show the supplied portrait and Altur-Agent; browser titles and placeholders are branded before hydration.
- Password login with a disposable local test password succeeded, then reached authenticated navigation and onboarding. No real credentials were used.
- Actual AIAgent imported from the pinned isolated runtime, accepted chat, streamed a local fixture response, completed, survived reload and retained session history.
- Captured request inspection confirmed `You are Altur-Agent` in the final assembled system instructions and absence of the upstream default identity line. This is prompt-boundary evidence. Fixture output is transport/rendering evidence, **not real provider identity compliance**.
- A long fixture stream was cancelled with the real Stop control. The resulting cancellation message names Altur-Agent and the application returned to idle.
- A deliberately malformed initial fixture stream exercised displayed provider-error handling. The fixture's missing finish_reason was corrected; clean completion then passed.
- Default → disposable web-qa → default profile switching worked. Profile names remain user-controlled. Workspace listing and disposable attachment upload were exercised.
- Light/dark settings, conversation/empty states, local help, Spanish selection and English fallback were inspected. The skin's internal `nous` key is retained while its displayed label is ArtemisProject.
- Desktop (1280×800) and narrow (390×844) layouts were inspected. Narrow document and main panel widths both measured 390 pixels, with no horizontal overflow; loaded titlebar and empty-state portraits measured 18×18 and 80×80. A titlebar sizing regression found visually was fixed.
- Public share page renders Altur-Agent heading, portrait, home action and footer. HTML export returns a branded filename and product footer; JSON export preserves content. User-authored upstream names remain intact in chat and quoted documents.
- A seeded `hermes-shell-legacy-brand-test` cache was removed on upgrade. An unrelated cache and a localStorage preservation marker remained. Fresh navigation and the previously loaded browser profile received new assets.
- SVG, 16/32/180/192/512 PNGs and ICO were generated; the 512 icon was visually inspected. The 20% inset keeps the portrait within maskable safe framing. No OS-installed PWA was created.

Representative screenshots are maintained under docs/images/altur and delivered separately with the local handoff.

## Remaining external or unverified flows

Real AI provider responses require the user's provider configuration; no existing credentials were read or copied. External OIDC/SSO, hardware passkey ceremonies, configured outbound messaging channels, and an actual OS-installed PWA upgrade were not exercised. Tool approval SSE/auth behavior passed automated checks; a real dangerous-command approval was not triggered in the browser. Docker/native Windows/reverse-proxy deployment and every locale/theme combination were not executed locally; subpath compatibility was checked by the existing suite. No public deployment or persistent background service was installed.

The local validation provider is explicitly labelled `[LOCAL FIXTURE]`. To repeat it, start `python tests/fixtures/altur_provider.py --port 8794`, then configure a custom OpenAI-compatible provider at `http://127.0.0.1:8794/v1` with model `altur-fixture`. An optional `--capture <local-file>` records requests for prompt inspection. Do not use request capture with sensitive real content.
