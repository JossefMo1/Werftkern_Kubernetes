#!/usr/bin/env bash
# Optional, user-run publication. No credentials accepted through arguments.
# Publishes an experimental source project, NEVER a production release.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $# == 2 && "$2" == --public ]] || { echo "Usage: bash scripts/publish-github.sh OWNER/werftkern --public" >&2; exit 64; }
[[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo 'Invalid repository name' >&2; exit 64; }
command -v gh >/dev/null || { echo 'Install the official GitHub CLI and authenticate using gh auth login first.' >&2; exit 69; }
gh auth status
python3 scripts/check-public-source.py
[[ -z "$(git status --porcelain)" ]] || { echo 'Commit the reviewed source changes first.' >&2; exit 65; }
if git remote get-url origin >/dev/null 2>&1; then echo 'An origin exists: refusing to replace or publish an unrelated repository.' >&2; exit 65; fi
[[ -t 0 ]] || { echo 'An interactive publication confirmation is required.' >&2; exit 65; }
printf 'This publishes the complete committed source history as PUBLIC under Apache-2.0.\nIt is EXPERIMENTAL and not production-qualified. Review ownership and secrets first.\nType the repository name %s to continue: ' "$1"
read -r confirmation
[[ "$confirmation" == "$1" ]] || exit 1
gh repo create "$1" --public --source=. --remote=origin --push --description 'Experimental Kubernetes-independent container orchestrator for Ubuntu; not production-qualified'
