# Altru changelog

Fork-only changes on `altur-branding`. Upstream changes are in `CHANGELOG.md`.

## altru-v1.0.0 — 2026-11-16

First tagged release; what the LAN machines run.

- Altru branding: name, logo, icons, all 15 WebUI locales, login, share and export
  pages, managed identity and assistant-name fallback (`BRANDING.json`).
- Welcome artwork on new chats and synchronized login-page theming, with resized
  WebP copies of the artwork.
- Global "New chat" button in the rail and sidebar; rearrangeable rail icons.
- Desktop chat history is discoverable in the sidebar; hidden and delegated
  lineages stay hidden.
- Password changes: spaces kept exactly; a signed-in session may change the
  password without re-entering it.
- macOS LAN deployment (`deploy/macos/`) with tag-based `update.sh`, optional
  `ALTRU_HERMES_PROFILE`.
- Merged upstream hermes-webui through v0.52.679 (2026-11-15).
- Export files are named `altru-<session>.*`.
- CI on `altur-branding` (Python 3.12 and 3.14) and a weekly upstream-sync pull request.
