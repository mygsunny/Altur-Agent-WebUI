# Altur-Agent fork maintenance

## Brand source and desktop relationship

`branding/brand.json` is canonical for product/short name, publisher, artwork, accessibility label, assistant identity, description, distribution destinations and upstream/runtime pins. The schema follows the desktop brand's schema_version/product/organization/assets/distribution/upstream structure. `branding/assets/source/portrait-icon.svg` is copied byte-for-byte from the desktop recipe's maintained SVG; the original Desktop path was unavailable. The desktop crop is recorded as view_box. The artwork is neither traced nor replaced. The web fork and desktop do not automatically synchronize.

Run `python scripts/generate-branding.py` with requirements-branding.txt installed after editing brand inputs. `branding/literals.json` records approved application-owned source literal templates and their generated values, including all locale bundles and fallback strings. It is a source catalog, not a runtime message filter. If upstream changes a slot, generation fails for review rather than silently missing it. SVG framing, rasterization, PNG sizes (16/32/180/192/512), ICO, manifest and service-worker cache namespace are deterministic. Light/dark use the same transparent portrait; opaque icons use a neutral tile and 20% maskable inset.

The small Python adapter reads the manifest. Normal chat applies identity through the runtime's supported ephemeral_system_prompt; a fresh isolated home also receives SOUL.md. Custom personas and existing SOUL.md are preserved. New identity instructions are not a promise that arbitrary provider output will obey them. No output replacement is installed.

The pinned runtime also hardcodes unconditional help guidance, returned diagnostics, tool descriptions, and OAuth success copy. Its supported SOUL/ephemeral settings do not replace those constants. `branding/runtime-literals.json` therefore records reviewed source expressions, original file hashes, and templates for a **private source packaging overlay**. This is a fork-maintained source change, not an upstream configuration flag. `branding/runtime.py` verifies the pin and source hashes, preserves executable structure and formatted expressions, and refuses unknown edits. Only this checkout’s `.runtime` copy (or Docker’s writable `/app/hermes-agent-src` stage) can be changed. Mounted source, installed runtimes, model output, tool output, logs, customer plugins, and history are never post-processed. The original runtime license is retained in `branding/RUNTIME-LICENSE.txt`.

Setup applies the overlay after checking out the pin. Start verifies it before launching. The same `python scripts/generate-branding.py` command regenerates an existing private runtime overlay along with browser assets; an absent runtime is handled by the later setup step. A future display name can change source copy without changing module names, storage paths, headers, cookies, or provider IDs. Source templates reject syntax-changing name characters; review a template change if a future name requires quotes, braces, or backslashes.

## Architecture and isolation

`server.py` → `api/routes.py` serves static/index.html and standalone login, public share and export pages. The vanilla JS boot/messages/sessions/panels/workspace modules retain their responsibilities. `static/i18n.js` supplies locale dictionaries and English fallback. `api/streaming.py` builds agent kwargs, temporary prompts and SSE messages. The runtime is imported from the selected agent source; it is not a remote desktop backend.

Use scripts/setup-altur.py in a dedicated Python 3.14 environment. It clones/checks out the exact runtime commit from the manifest, restores only checksum-known branding edits, refuses other dirty runtime source, applies reviewed branding, and applies the runtime's declared uv dependency overrides, matching upstream's Docker installation pattern. The default branch of that runtime repository is not the validation pin. Python 3.14.10 and uv 0.13.6 were used locally. No global runtime, desktop checkout, credentials or installed application is modified.

scripts/start-altur.py binds 127.0.0.1, requires an explicit valid runtime checkout, strips inherited provider credentials and profile overrides, and sets separate agent/base/config/state/workspace locations. ALTUR_WEBUI_ISOLATED additionally prevents discovery/default-home fallback. Existing WebUI APIs, state formats and profile switching remain intact. Default external Claude transcript import is disabled only for a new isolated instance. The service runs in the foreground; no launch agent, updater or public host is installed.

## Login password

To change the WebUI login password, open Settings → System, enter the current
password and the explicitly labeled New password, then select Change password.
The action uses the existing authenticated settings endpoint and current-password
verification. General Save Settings also applies a populated new-password field;
if only the current-password field is populated, its confirmation explicitly says
the password was unchanged. No password value or hash is returned to the browser.
The new labels use the existing English fallback in locales without a translation.

## Intentional compatibility and attribution exceptions

- Python modules/imports, `hermes` executable commands, HERMES_* environment variables and runtime configuration paths remain compatible.
- `X-Hermes-CSRF-Token`, cookies, storage keys, PWA id/scope and API routes/fields remain unchanged. Passkey relying-party id and user id remain stable; human-readable account/presentation labels change.
- Historical generic title recognition accepts both upstream and fork names. User titles/messages, quoted content, custom personas and imported history are never renamed.
- Nous/Nous Portal and model/provider IDs refer to actual third-party services. Technical runtime commands and factual provider destinations retain their real identities. Application-owned setup and troubleshooting guidance uses bundled Help and this fork’s local procedure.
- LICENSE, contributors, Git provenance, historical upstream documentation and third-party notices preserve attribution. The upstream skin key `nous` remains; its display label is ArtemisProject.

## Upstream updates

No scheduled synchronization or automatic merging is configured. GitHub Actions is disabled in repository settings, and inherited workflow YAML is retained under `.github/workflows-disabled/`.

1. Commit or back up local work and checkout altur-branding.
2. `git fetch upstream` and review the intended upstream commit and workflows.
3. Merge that explicit commit manually; resolve conflicts without reactivating workflows.
4. Review new customer-facing strings, locale/fallback bundles, icons/vector art, login/SSO/passkey pages, share/export templates, runtime prompt producers and update/distribution actions.
5. Update the upstream baseline only when the merge is accepted. Regenerate branding, run tests and repeat browser acceptance.
6. Runtime upgrades are separate: while the old registry/pin are still available, restore only the known overlay with `python scripts/runtime-branding.py restore`. Choose an explicit new commit, review source/dependencies, update the file hashes and expression registry, then rerun setup, generation, runtime safety tests and prompt-boundary/provider checks. An unreviewed pin must fail closed; never bypass the guard or overwrite unknown edits.

Brand-sensitive files: static/index.html, i18n.js, boot.js, onboarding.js, sw.js, manifest.json, share.html/js, icons and CSS artwork; api/routes.py, config.py, passkeys.py, streaming.py, session_export_html.py, updates.py; startup/path discovery and packaging/install scripts.

Application update checks and application-owned apply actions are disabled. Never point customer update/download actions at an unbranded upstream installer. The upstream bootstrap remains historical compatibility code; this fork's supported setup is the isolated procedure in README.md.

## Cache and PWA behavior

The shell namespace includes a digest of the manifest and original artwork. On install/activation only previous hermes-shell-/altur-shell- caches are removed. Browser storage, conversations and unrelated origin caches are preserved. Assets and navigations retain upstream network-first behavior and subpath rewriting. Both fresh and previously loaded browser tabs were inspected; localStorage theme keys are unchanged.

An installed PWA's OS name/icon refresh is browser-controlled and may lag behind web content. Reopening/updating the installed app may be required; manual reinstall may refresh OS artwork. Do not clear application storage to force an icon change. A real OS-installed PWA upgrade was not certified during this local validation.

## Evidence limits

See VALIDATION.md for actual commands/results and browser evidence. Local fixture responses test transport and rendering, not real provider intelligence. Real provider chat, external SSO, hardware passkey ceremony and outbound messaging integrations require their own configured services. No claims of shared desktop history or accounts are made.

## Scheduled jobs

Manual jobs run through the web application. Scheduled execution needs a gateway service configured for the same isolated profile and kept running by the operator. This branding task does not start that service or enable schedules. The local web launcher does not run a scheduler. Configure the gateway only inside this web instance’s private environment; do not reuse a desktop profile or its credentials.

The multi-container recipes now build the WebUI from this fork’s local source instead of pulling an upstream WebUI image. They require the exact reviewed runtime source. The container brands only its writable staged copy and refuses unmatched sources. They remain deployment references requiring their own Docker and gateway acceptance checks before use. No published Altur-Agent container image is claimed. Keep local development bound to loopback.

## Runtime locale defaults and plugin copy

The runtime has its own 17-language catalog, separate from the WebUI’s 15 locale bundles. `branding/runtime-locales.json` contains the pinned parsed core catalogs and reviewed display-leaf templates. Generation writes ignored `branding/generated-locales/*.yaml` files (JSON-form YAML) without needing an installed runtime. The launcher selects them through the runtime’s supported `HERMES_BUNDLED_LOCALES` packaging setting. User profile locale overlays and installed language packs keep their existing higher priority; their words are never renamed. Start verifies generated catalogs against the manifest and registry.

The source overlay also covers reviewed descriptions in bundled plugin manifests and owned default channel messages. YAML/JSON source patches must preserve every unapproved parsed leaf, author, ID and environment setting. Actual third-party plugin titles, authors, external extension-gallery records, selected services and model names retain their identities. The optional external runtime dashboard is labeled as a separate component; this fork does not claim its independent interface is an Altur-Agent-branded dashboard. No gateway, channel, plugin dashboard or sidecar was activated during validation.

## Managed runtime and credential isolation

The local launcher sets the runtime’s supported `HERMES_MANAGED=altur-agent-webui` signal for this process. Messaging-channel `/update` returns the fork’s managed-install guidance before locating or spawning an updater; the WebUI also refuses update execution and does not expose that command. `GATEWAY_RELAY_DISPLAY_NAME` comes from the manifest’s assistant display name. If an operator later enables a separate gateway, it must retain these scoped settings and the generated bundled-locale directory. Such a gateway is not started by this task. Manual source updates use the reviewed procedure above.

The launcher uses private Codex, Claude, and shared-auth roots below `.trial`, strips inherited provider credentials, and preserves HOME, PATH and certificate trust. It does not import live CLI credentials. The packaging layer owns permissions in managed mode: checkout-local trial state is private, new files use umask 077, and paths that escape the checkout are rejected. Existing profile contents and user personas are preserved.

After regenerating source/assets, stop and restart the foreground development server, then reload existing tabs. The upstream server computes its versioned asset URLs at startup; a browser may keep the previous immutable JavaScript URL while that process is still running. Restarting computes the new source revision and requests fresh assets. Do not clear browser storage or conversation history. The generation command rebuilds branding; it does not install or supervise a service.
