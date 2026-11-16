# macOS deployment (Hermes host)

Runs the Altru WebUI as a per-user launchd service on a Mac that already runs Hermes.
Production machines only ever run a tagged release. Never edit files in a deployed
checkout: make changes on a branch, merge to `altur-branding`, tag, then update.

## First install

    git clone https://github.com/mygsunny/Altur-Agent-WebUI.git ~/.local/opt/Altur-Agent-WebUI
    ~/.local/opt/Altur-Agent-WebUI/deploy/macos/update.sh            # newest altru-v* tag
    sed -e "s#@HOME@#$HOME#g" -e "s#@HOST@#<this Mac's LAN address>#" \
        ~/.local/opt/Altur-Agent-WebUI/deploy/macos/org.artemisproject.altru-webui.plist.template \
        > ~/Library/LaunchAgents/org.artemisproject.altru-webui.plist
    launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/org.artemisproject.altru-webui.plist

The WebUI refuses to bind a LAN address until a password exists in its state
directory (`persisted-auth-guard.py`). Copy `settings.json` and `.pbkdf2_key` from an
existing install to keep the same settings and password, and create a fresh
`.signing_key` (`head -c 32 /dev/urandom`); keep all three mode 600.

## Update

    ~/.local/opt/Altur-Agent-WebUI/deploy/macos/update.sh            # newest altru-v* tag
    ~/.local/opt/Altur-Agent-WebUI/deploy/macos/update.sh altru-v1.2.0

`update.sh` refuses to run if the checkout has local edits, checks out the tag,
installs requirements into `.venv` and restarts the service.

## Settings (launchd plist environment)

| Variable | Meaning |
|---|---|
| `ALTRU_WEBUI_HOST` | Bind address. Defaults to 127.0.0.1; a LAN address needs persisted auth. |
| `ALTRU_WEBUI_PORT` | Port, default 8787. |
| `ALTRU_HERMES_PROFILE` | Optional named profile (`~/.hermes/profiles/<name>`). Pins the UI to that profile and hides the others (.26 uses `miaaa`); unset, the sidebar "Show N from other profiles" link shows every profile. |
| `ALTRU_WEBUI_DATA` | State directory, default `~/.local/share/hermes-webui-evaluation`. |
| `ALTRU_LAN_HTTPS_PORT`, `ALTRU_LAN_HTTPS_CERT`, `ALTRU_LAN_HTTPS_KEY` | Extra HTTPS listener beside plain HTTP (see below). |

State (settings, auth keys, sessions) lives in the state directory and is never in git.

## HTTPS on the LAN

Over plain HTTP the login password and session cookie cross the network in clear
text. The launcher can serve the same app over HTTPS on a second port while plain
HTTP keeps working, so devices can move over one at a time.

1. On the machine that holds the CA (`~/.local/share/altru-tls/`, created on first
   use), issue a certificate per server: `deploy/macos/make-lan-cert.sh <LAN IP>`.
   It writes `<LAN IP>.pem` and `<LAN IP>.key`; copy only those two files to the
   other server's `~/.local/share/altru-tls/` (mode 600). The CA key stays put.
2. Add to the plist's `EnvironmentVariables` and reload the service
   (`launchctl bootout gui/$(id -u)/org.artemisproject.altru-webui`, wait for the
   old process to exit, then `launchctl bootstrap gui/$(id -u) <plist>`):
   `ALTRU_LAN_HTTPS_PORT` = `8443`, `ALTRU_LAN_HTTPS_CERT` / `ALTRU_LAN_HTTPS_KEY` =
   the two files.
3. Trust `ca.pem` on every device (macOS: Keychain Access, System keychain, Always
   Trust; iPhone/iPad: install it as a profile, then enable it under Settings >
   General > About > Certificate Trust Settings), then open
   `https://<LAN IP>:8443`.
4. When every device uses HTTPS, go HTTPS-only: remove the three
   `ALTRU_LAN_HTTPS_*` settings and set `HERMES_WEBUI_TLS_CERT` and
   `HERMES_WEBUI_TLS_KEY` to the same files instead. The main port (8787) then
   serves HTTPS only, and the 8443 listener is no longer needed.

Do not name these settings `ALTRU_WEBUI_TLS_*`: the Hermes runtime on these Macs
copies every `ALTRU_X` variable to `HERMES_X`, and `HERMES_WEBUI_TLS_*` switches the
main port itself to TLS.
