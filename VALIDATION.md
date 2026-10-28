# Altur-Agent validation record

WebUI upstream baseline: `e40f042b6ec80199e06b7edf6e91a31beee2b812`. Runtime pin: `bf0203a794a07aac3ff764972ab9087baa4e4f4e`, with the reviewed private source overlay. Validation used Python 3.14.10 for the runtime, Python 3.12.14 for contributor tests, uv 0.13.6, resvg-py 0.5.0 and Pillow 13.0.0.

## Automated checks

The final relevant suite passed **527 tests, with 3 platform skips**. It covers branding/generation, exact source-slot selection, reversible overlays, source/path guards, runtime locale defaults and priority, isolated startup/permissions, onboarding, authentication sessions/settings, passkeys, PWA/CSP/subpaths, default personalities, approval transport, public shares, export palettes, bootstrap and container packaging. All 18 top-level JavaScript files pass syntax checks; changed Python parses, shell syntax and `git diff --check` pass.

```sh
./scripts/test.sh tests/test_altur_*.py tests/test_auth.py tests/test_auth_sessions.py tests/test_auth_settings_safety.py tests/test_passkey_auth.py tests/test_pwa_manifest_csp.py tests/test_pwa_manifest_sw.py tests/test_subpath_frontend_routes.py tests/test_default_personality.py tests/test_approval_sse.py tests/test_managed_runtime_startup.py tests/test_sidebar_tab_visibility.py tests/test_onboarding_static.py tests/test_session_public_share.py tests/test_session_export_html_palette.py tests/test_onboarding_mvp.py tests/test_onboarding_existing_config.py tests/test_bootstrap_foreground.py tests/test_bootstrap_port_preflight.py tests/test_bootstrap_python_selection.py tests/test_docker_compose_gateway_and_password_forwarding.py tests/test_issue8524_docker_agent_uv_overrides.py -q
```

Run with Node on PATH and isolated HERMES_HOME, HERMES_BASE_HOME and HERMES_WEBUI_STATE_DIR. The runner creates a separate contributor `.venv`; keep it separate from `.runtime/venv`. The legacy bootstrap discovery tests need `ALTUR_WEBUI_ISOLATED=0` with those disposable homes because they exercise mocked discovery fallbacks. The entire inherited suite was not executed.

The 3 skips are Linux-only bind-semantics checks and the native Windows exclusive-bind check. The original focused pre-change baseline had 18 passes and 5 skips. New customer-flow regressions failed on the earlier fork before their fixes; eleven new distribution regressions also failed on pristine upstream before the fixes.

A separate complete run of `test_issue8113_venv_rebuild_keeps_previous.py` gives **3 failed, 13 passed on both pristine upstream and this fork**. macOS `/bin/mv` rejects the inherited GNU `-T` option. The same three tests fail at the same transaction moves. These are pre-existing platform failures, not branding regressions.

Focused tests also execute all 27,915 WebUI locale/fallback results across 15 languages using the real JavaScript producer. The broader name-stem check caught Czech declensions such as Herma, which exact Hermes matching missed. All were fixed. The runtime’s 17-language generated catalog is read through its actual YAML reader; tests preserve English fallback, user overlays, plugin-language priority, interpolation fields and real service names.

## Rendered behavior and runtime boundary

- Supplied portrait, page metadata, empty states, loading/connection copy and default assistant labels identify Altur-Agent before/after hydration. Default layout and themes are preserved.
- Disposable password login succeeds into authenticated navigation and first-run setup. English and Czech system/provider steps were inspected after the final corrections. A cached browser initially retained an old immutable JavaScript URL; a normal server restart and reload computed the new asset revision and displayed corrected Czech copy without clearing storage.
- The real pinned AIAgent imports, assembles its system instructions and 21 enabled tool schemas, calls the local OpenAI-compatible fixture, streams and completes. Captured final instructions include the Altur-Agent identity and neutral Help/Settings guidance. Enabled tool schemas contain no upstream product identity. Necessary parser markers and technical paths remain.
- Fixture responses are labeled `[LOCAL FIXTURE]`. They prove transport/rendering, not real provider intelligence or identity compliance.
- The real Stop control cancels a long fixture stream, returns to idle and renders Altur-Agent cancellation copy. History survives reload. User text naming Hermes, NousResearch and nesquena remains unchanged.
- A fake pending approval was injected through the application’s loopback-only test endpoint, rendered as a real approval card and denied. No command was executed. The actual OAuth callback handler renders Altur-Agent success copy with dummy redirect parameters; this is not an external OAuth ceremony.
- Real API profile creation seeds the supported SOUL identity. A real clone preserves custom SOUL text verbatim. Profile creation also succeeds under managed mode with its required directories. No existing persona/profile files are rewritten.
- Actual managed-update definitions refuse a messaging update before executable resolution/spawn. The launcher uses the runtime’s supported managed-install setting and Relay display-name setting. No external gateway or channel was activated.
- Workspace listing/preview and a disposable text attachment were exercised. Public-share rendering and HTML/JSON export were checked. Browser Markdown/JSON/HTML filename handlers execute in regression tests; the server export API itself supports HTML and JSON.
- Light/dark views, settings, local Help, the ArtemisProject skin label, `/theme nous` compatibility, Spanish/Czech presentation and fallback behavior were inspected. At mobile width 390, document and main widths are both 390; portraits load at 18×18 and 80×80.
- SVG/PNG/ICO/Apple/PWA icons derive from the unchanged source artwork. At 512 pixels the visible portrait’s maximum radius is 199.69 pixels within the 204.8-pixel maskable safe circle. PWA ID/scope, cookies, CSRF headers and storage keys remain compatible. Legacy shell-cache migration preserves unrelated caches and stored data.

The source overlay and generated locale defaults regenerate from the central brand inputs. Unknown source changes, unsupported pins, altered formatting contracts, source/state symlinks and escaped paths fail closed. The managed-mode fresh-home check caught and fixed missing-directory initialization during development; packaging now provisions that skeleton with private permissions before startup.

Screenshots in `docs/images/altur` show the maintained branded flows. The separate local audit deliverables contain detailed source references, reviewed decisions, hashes, browser snapshots and baseline proof logs.

## Limits

Real AI responses need separately configured provider credentials. External SSO, hardware passkey ceremonies, actual outbound/Relay delivery, Docker deployment, native Windows operation and an OS-installed PWA upgrade were not certified. Channel message sources and updater refusal were checked at source/runtime-method boundaries; no external message was sent. The isolated launcher requires POSIX filesystem primitives and was validated on this Mac.

The runtime’s independent external dashboard and third-party extension/plugin identities remain accurate. Actual Nous services, commands/imports/env/header/storage identifiers, legal notices, historical provenance and customer-authored content are intentional exceptions. There is no conversation/output replacement filter.

No desktop checkout, installed application, runtime, profiles or credentials were modified. No public hosting, paid service, scheduled synchronization, automatic release/update or persistent background installation was activated. GitHub Actions remains disabled; inherited workflows remain outside the active workflows directory.
