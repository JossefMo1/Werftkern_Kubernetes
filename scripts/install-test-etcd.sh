#!/usr/bin/env bash
# Installs a fixed test-only dependency into a NEW user-owned directory. No sudo,
# system service or customer cluster modification. Internet access is required.
set -euo pipefail
cd "$(dirname "$0")/.."
target="${1:?Usage: install-test-etcd.sh NEW_ABSOLUTE_DIRECTORY}"
[[ "$target" = /* && ! -e "$target" ]] || { echo 'New absolute target directory required' >&2; exit 2; }
[[ "$(uname -s)" = Linux && "$(uname -m)" = x86_64 ]] || { echo 'Linux amd64 test host required' >&2; exit 2; }
url="$(python3 -c 'import json;print(json.load(open("tests/runtime/etcd-tool.json"))["url"])')"
hash="$(python3 -c 'import json;print(json.load(open("tests/runtime/etcd-tool.json"))["sha256"])')"
stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
curl --proto '=https' --tlsv1.2 --fail --show-error --location --max-time 120 "$url" -o "$stage/etcd.tar.gz"
printf '%s  %s\n' "$hash" "$stage/etcd.tar.gz" | sha256sum --check --strict
mkdir -m 0700 "$target"
tar --extract --gzip --file "$stage/etcd.tar.gz" --directory "$target" --strip-components=1 --no-same-owner \
  etcd-v3.7.2-linux-amd64/etcd etcd-v3.7.2-linux-amd64/etcdctl etcd-v3.7.2-linux-amd64/etcdutl
"$target/etcd" --version
