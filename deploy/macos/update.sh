#!/bin/sh
# Deploy a tagged Altru release into this checkout and restart the service.
# Usage: update.sh [tag]   (default: newest altru-v* tag)
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "Refusing to update: $ROOT has local edits. Commit them on a branch first." >&2
  git status --short --untracked-files=no >&2
  exit 1
fi
git fetch --quiet --tags --force origin
TAG="${1:-$(git tag --list 'altru-v*' --sort=-v:refname | head -n 1)}"
[ -n "$TAG" ] || { echo "No altru-v* release tag found." >&2; exit 1; }
git -c advice.detachedHead=false checkout --quiet "refs/tags/$TAG"
if [ ! -x .venv/bin/python ]; then
  PY="$(ls -d "$HOME"/.hermes/tools/python-3.*/bin/python3 2>/dev/null | sort -V | tail -n 1)"
  "${PY:-python3}" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
LABEL=org.artemisproject.altru-webui
if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
  launchctl kickstart -k "gui/$(id -u)/$LABEL"
fi
echo "Altru WebUI now at $TAG ($(git rev-parse --short HEAD))"
