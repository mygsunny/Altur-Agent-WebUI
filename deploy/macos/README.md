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
| `ALTRU_HERMES_PROFILE` | Optional named profile (`~/.hermes/profiles/<name>`). Pins the UI to that profile and hides the others. |
| `ALTRU_WEBUI_DATA` | State directory, default `~/.local/share/hermes-webui-evaluation`. |

State (settings, auth keys, sessions) lives in the state directory and is never in git.
