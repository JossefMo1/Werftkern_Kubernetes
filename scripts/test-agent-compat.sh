#!/usr/bin/env bash
# Validate actual dev.3 -> dev.4 binaries. Historical source must be authentic.
# An externally provided legacy bundle is OPTIONAL and never added to this repo.
set -euo pipefail
cd "$(dirname "$0")/.."

base=67f5617188a8536d0ce915267a27ed552e55687e
expected_bundle_sha256=ae14dd172a8286876b0f6d8f1b2806d4d1da5012ca633b48cf1eecad5a9b7fd8
out="${WERFT_COMPAT_EVIDENCE:-$PWD/evidence/agent-compat}"
mkdir -p "$out"; out="$(realpath "$out")"
work="$(mktemp -d)"; trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/previous"

source_kind=git-ancestor
if git cat-file -e "$base^{commit}" 2>/dev/null; then
  git archive "$base" | tar -x -C "$work/previous"
else
  source_kind=sha256-pinned-external-bundle
  if [[ -z "${WERFT_PREVIOUS_BUNDLE:-}" ]]; then
    echo "BLOCKED: historical dev.3 commit absent; set WERFT_PREVIOUS_BUNDLE to the exact verified private .bundle (no mock fallback)." >&2
    exit 3
  fi
  bundle="$(realpath -e -- "$WERFT_PREVIOUS_BUNDLE")"
  [[ -f "$bundle" && ! -L "$bundle" ]] || { echo 'BLOCKED: bundle must be a regular non-symlink file.' >&2; exit 3; }
  actual="$(sha256sum -- "$bundle" | awk '{print $1}')"
  if [[ "$actual" != "$expected_bundle_sha256" ]]; then
    echo 'BLOCKED: historical dev.3 bundle SHA256 does not match the approved delivery manifest.' >&2
    exit 3
  fi
  git clone --quiet --no-checkout -- "$bundle" "$work/git-history"
  git -C "$work/git-history" cat-file -e "$base^{commit}" || { echo 'BLOCKED: bundle does not contain dev.3 source commit.' >&2; exit 3; }
  git -C "$work/git-history" archive "$base" | tar -x -C "$work/previous"
fi

(cd "$work/previous" && go build -trimpath -o "$out/werft-dev3" ./cmd/werft)
go build -trimpath -o "$out/werft-dev4" ./cmd/werft
printf '%s\n' "$base" > "$out/baseline-commit.txt"
printf '%s\n' "$source_kind" > "$out/source-kind.txt"
sha256sum "$out/werft-dev3" "$out/werft-dev4" > "$out/binary-sha256.txt"
WERFT_PREVIOUS_BINARY="$out/werft-dev3" WERFT_CURRENT_BINARY="$out/werft-dev4" \
  go test -race -count=1 -timeout 3m -tags compat_agent -run '^TestPreviousAgentBinary' -v ./tests/integration | tee "$out/test.log"
