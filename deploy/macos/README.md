# macOS deployment (Hermes host)

Used for the Altru WebUI on 192.168.1.8 and 192.168.1.26.

Install / update on a Mac that already runs Hermes:

    git clone -b altur-branding https://github.com/mygsunny/Altur-Agent-WebUI.git ~/.local/opt/Altur-Agent-WebUI
    cd ~/.local/opt/Altur-Agent-WebUI
    ~/.hermes/tools/python-3.*/bin/python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

Update later:

    cd ~/.local/opt/Altur-Agent-WebUI && git pull && launchctl kickstart -k gui/$(id -u)/org.artemisproject.altru-webui

State (settings.json, auth keys, sessions) lives in ~/.local/share/hermes-webui-evaluation
and is never in git. The launchd plist sets ALTRU_WEBUI_HOST to the machine's LAN IP,
ALTRU_HERMES_PROFILE pins the UI to one profile and hides the others (.26 uses miaaa;
unset, the sidebar "Show N from other profiles" link shows every profile).
