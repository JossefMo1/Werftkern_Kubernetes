#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
base=67f5617188a8536d0ce915267a27ed552e55687e
out="${WERFT_COMPAT_EVIDENCE:-$PWD/evidence/agent-compat}"
mkdir -p "$out"; out="$(realpath "$out")"
work="$(mktemp -d)"; trap 'rm -rf -- "$work"' EXIT
git cat-file -e "$base^{commit}"
git archive "$base" | tar -x -C "$work"
(cd "$work" && go build -trimpath -o "$out/werft-dev3" ./cmd/werft)
go build -trimpath -o "$out/werft-dev4" ./cmd/werft
printf '%s\n' "$base" > "$out/baseline-commit.txt"
sha256sum "$out/werft-dev3" "$out/werft-dev4" > "$out/binary-sha256.txt"
WERFT_PREVIOUS_BINARY="$out/werft-dev3" WERFT_CURRENT_BINARY="$out/werft-dev4" \
  go test -race -count=1 -tags compat_agent -run '^TestPreviousAgentBinary' -v ./tests/integration | tee "$out/test.log"
