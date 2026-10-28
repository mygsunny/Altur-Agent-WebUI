# Altur-Agent

Altur-Agent by ArtemisProject is a branded fork of the existing Python and vanilla JavaScript WebUI. It retains chat, streaming, Stop, sessions, profiles, workspaces, attachments, tools, settings, themes, password/passkey authentication and optional SSO. It runs its own agent runtime in-process; it does not connect to the desktop application.

![Altur-Agent portrait](static/favicon-192.png)

## Local setup

Use Python **3.14** for the pinned agent runtime. The WebUI contributor test runner uses a separate Python 3.11–3.13 environment. No global agent installer is needed. The isolated launcher targets macOS/POSIX; native Windows deployment is unverified.

```sh
git clone https://github.com/mygsunny/Altur-Agent-WebUI.git
cd Altur-Agent-WebUI
git switch altur-branding
python3.14 -m venv .runtime/venv
.runtime/venv/bin/python -m pip install --upgrade pip
.runtime/venv/bin/python scripts/setup-altur.py
.runtime/venv/bin/python scripts/start-altur.py --port 8793
```

Open **http://127.0.0.1:8793**. Complete provider setup with your own provider or local OpenAI-compatible server. No real provider credentials are bundled. Stop with Ctrl+C. The launcher stays in the foreground, binds loopback, and uses `.trial/agent-home`, `.trial/state` and `.trial/workspace`. It does not use the desktop profile or import the operator's Claude Code history by default. These checkout-local data directories are ignored by Git; retain them when updating the source.

Setup applies a hash-verified source overlay to the private pinned runtime for hardcoded help/tool/callback copy; the launcher verifies it before starting. The launcher seeds SOUL.md only when missing, using the brand identity. User-edited identity/personas remain authoritative. Settings can enable password protection; passkeys and configured SSO keep upstream authentication behavior. Do not expose this development instance publicly.

## Branding and maintenance

The canonical definition is [`branding/brand.json`](branding/brand.json). The original, unmodified portrait is [`branding/assets/source/portrait-icon.svg`](branding/assets/source/portrait-icon.svg).

```sh
.venv/bin/python -m pip install -r requirements-branding.txt
.venv/bin/python scripts/generate-branding.py
```

This generates SVG/PNG/ICO icons, PWA metadata, catalogued application-owned literals, 17-language runtime defaults, and the reviewed source overlay in an existing private runtime before interpolation. It never filters user messages or model output. Restart the foreground server and reload open tabs after regeneration so versioned browser assets and backend metadata are refreshed. See [`docs/ALTUR.md`](docs/ALTUR.md) for the brand relationship, compatibility exceptions, runtime pin, upstream merge process and validation limits.

## Development checks

```sh
./scripts/test.sh tests/test_altur_*.py tests/test_onboarding_static.py tests/test_session_public_share.py tests/test_pwa_manifest_sw.py
```

The documented test runner creates a separate `.venv` using Python 3.11–3.13. Keep the runtime environment under `.runtime/venv` separate. See [TESTING.md](TESTING.md) and [ARCHITECTURE.md](ARCHITECTURE.md) for the inherited application architecture and detailed feature tests.

GitHub Actions, releases, deployment and application updates are disabled. Updates are manual and must retain this fork's branding. No support email or external documentation website has been configured; in-app help is bundled locally.

## Provenance

Based on [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui), starting at `e40f042b6ec80199e06b7edf6e91a31beee2b812`, with its Git history preserved. The separate runtime is [Hermes Agent](https://github.com/NousResearch/hermes-agent), pinned to `bf0203a794a07aac3ff764972ab9087baa4e4f4e`. Original licensing and contributor credits remain in [LICENSE](LICENSE), [CONTRIBUTORS.md](CONTRIBUTORS.md), and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The historical [upstream README](docs/UPSTREAM-README.md) is reference material, not this fork's installation procedure.
