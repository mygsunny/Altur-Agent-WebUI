# Altur-Agent fork maintenance

## Brand source and desktop relationship

`branding/brand.json` is canonical for product/short name, publisher, artwork, accessibility label, assistant identity, description, distribution destinations and upstream/runtime pins. The schema follows the desktop brand's schema_version/product/organization/assets/distribution/upstream structure. `branding/assets/source/portrait-icon.svg` is copied byte-for-byte from the desktop recipe's maintained SVG; the original Desktop path was unavailable. The desktop crop is recorded as view_box. The artwork is neither traced nor replaced. The web fork and desktop do not automatically synchronize.

Run `python scripts/generate-branding.py` with requirements-branding.txt installed after editing brand inputs. `branding/literals.json` records approved application-owned source literal templates and their generated values, including all locale bundles and fallback strings. It is a source catalog, not a runtime message filter. If upstream changes a slot, generation fails for review rather than silently missing it. SVG framing, rasterization, PNG sizes (16/32/180/192/512), ICO, manifest and service-worker cache namespace are deterministic. Light/dark use the same transparent portrait; opaque icons use a neutral tile and 20% maskable inset.

The small Python adapter reads the manifest. Normal chat applies identity through the runtime's supported ephemeral_system_prompt; a fresh isolated home also receives SOUL.md. Custom personas and existing SOUL.md are preserved. New identity instructions are not a promise that arbitrary provider output will obey them. No output replacement is installed.

## Architecture and isolation

`server.py` → `api/routes.py` serves static/index.html and standalone login, public share and export pages. The vanilla JS boot/messages/sessions/panels/workspace modules retain their responsibilities. `static/i18n.js` supplies locale dictionaries and English fallback. `api/streaming.py` builds agent kwargs, temporary prompts and SSE messages. The runtime is imported from the selected agent source; it is not a remote desktop backend.

Use scripts/setup-altur.py in a dedicated Python 3.14 environment. It clones/checks out the exact runtime commit from the manifest, refuses dirty runtime source, and applies the runtime's declared uv dependency overrides, matching upstream's Docker installation pattern. The default branch of that runtime repository is not the validation pin. Python 3.14.10 and uv 0.13.6 were used locally. No global runtime, desktop checkout, credentials or installed application is modified.

scripts/start-altur.py binds 127.0.0.1, requires an explicit valid runtime checkout, strips inherited provider credentials and profile overrides, and sets separate agent/base/config/state/workspace locations. ALTUR_WEBUI_ISOLATED additionally prevents discovery/default-home fallback. Existing WebUI APIs, state formats and profile switching remain intact. Default external Claude transcript import is disabled only for a new isolated instance. The service runs in the foreground; no launch agent, updater or public host is installed.

## Intentional compatibility and attribution exceptions

- Python modules/imports, `hermes` executable commands, HERMES_* environment variables and runtime configuration paths remain compatible.
- `X-Hermes-CSRF-Token`, cookies, storage keys, PWA id/scope and API routes/fields remain unchanged. Passkey relying-party id and user id remain stable; human-readable account/presentation labels change.
- Historical generic title recognition accepts both upstream and fork names. User titles/messages, quoted content, custom personas and imported history are never renamed.
- Nous/Nous Portal and model/provider IDs refer to actual third-party services. External runtime documentation links and commands identify that runtime accurately.
- LICENSE, contributors, Git provenance, historical upstream documentation and third-party notices preserve attribution. The upstream skin key `nous` remains; its display label is Artemis.

## Upstream updates

No scheduled synchronization or automatic merging is configured. GitHub Actions is disabled in repository settings, and inherited workflow YAML is retained under `.github/workflows-disabled/`.

1. Commit or back up local work and checkout altur-branding.
2. `git fetch upstream` and review the intended upstream commit and workflows.
3. Merge that explicit commit manually; resolve conflicts without reactivating workflows.
4. Review new customer-facing strings, locale/fallback bundles, icons/vector art, login/SSO/passkey pages, share/export templates, runtime prompt producers and update/distribution actions.
5. Update the upstream baseline only when the merge is accepted. Regenerate branding, run tests and repeat browser acceptance.
6. Runtime upgrades are separate: choose an explicit commit, inspect bootstrap/dependencies, and repeat prompt-boundary/provider tests.

Brand-sensitive files: static/index.html, i18n.js, boot.js, onboarding.js, sw.js, manifest.json, share.html/js, icons and CSS artwork; api/routes.py, config.py, passkeys.py, streaming.py, session_export_html.py, updates.py; startup/path discovery and packaging/install scripts.

Application update checks and application-owned apply actions are disabled. Never point customer update/download actions at an unbranded upstream installer. The upstream bootstrap remains historical compatibility code; this fork's supported setup is the isolated procedure in README.md.

## Cache and PWA behavior

The shell namespace includes a digest of the manifest and original artwork. On install/activation only previous hermes-shell-/altur-shell- caches are removed. Browser storage, conversations and unrelated origin caches are preserved. Assets and navigations retain upstream network-first behavior and subpath rewriting. Both fresh and previously loaded browser tabs were inspected; localStorage theme keys are unchanged.

An installed PWA's OS name/icon refresh is browser-controlled and may lag behind web content. Reopening/updating the installed app may be required; manual reinstall may refresh OS artwork. Do not clear application storage to force an icon change. A real OS-installed PWA upgrade was not certified during this local validation.

## Evidence limits

See VALIDATION.md for actual commands/results and browser evidence. Local fixture responses test transport and rendering, not real provider intelligence. Real provider chat, external SSO, hardware passkey ceremony and outbound messaging integrations require their own configured services. No claims of shared desktop history or accounts are made.
