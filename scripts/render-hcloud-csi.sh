#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 <helm-v3.22.1-binary> <hcloud-csi-2.24.2.tgz> <output.yaml>" >&2
  exit 2
fi

helm_bin="$1"
chart="$2"
output="$3"
values="examples/kubernetes/hcloud-csi-values.example.yaml"
node_service_account="examples/kubernetes/hcloud-csi-node-serviceaccount.yaml"
expected_helm_sha="46aeab5e043f62d01f7c168823b392cabc1cea3807b67906296290483791be43"
expected_chart_sha="1f4ebe7d2a8b06e95559a5315ecf125e158ccdadc8a6aae885c7ecd33a7fb4f6"
expected_values_sha="beb09c6f3fd5569de4dae7dbb81064f5893c5451fcef5a4be2ecc43453541088"
expected_node_service_account_sha="494c760af35dd6a4307f17a7d5fd840b1c70e6de3a39bdde8568374421c66b7b"

for file in "$helm_bin" "$chart" "$values" "$node_service_account"; do
  if [ ! -f "$file" ] || [ -L "$file" ]; then
    echo "required regular non-symlink file missing: $file" >&2
    exit 1
  fi
done
if [ ! -x "$helm_bin" ]; then
  echo "Helm binary is not executable: $helm_bin" >&2
  exit 1
fi

check_sha() {
  expected="$1"
  file="$2"
  actual="$(sha256sum -- "$file" | awk '{print $1}')"
  if [ "$actual" != "$expected" ]; then
    echo "SHA-256 mismatch for $file: expected $expected, got $actual" >&2
    exit 1
  fi
}

check_sha "$expected_helm_sha" "$helm_bin"
check_sha "$expected_chart_sha" "$chart"
check_sha "$expected_values_sha" "$values"
check_sha "$expected_node_service_account_sha" "$node_service_account"

helm_version="$("$helm_bin" version --short)"
case "$helm_version" in
  v3.22.1+*) ;;
  *) echo "unexpected Helm version: $helm_version" >&2; exit 1 ;;
esac

tmpdir="$(mktemp -d)"
trap 'rm -rf -- "$tmpdir"' EXIT
export HELM_CACHE_HOME="$tmpdir/cache"
export HELM_CONFIG_HOME="$tmpdir/config"
export HELM_DATA_HOME="$tmpdir/data"
export LC_ALL=C
export TZ=UTC

"$helm_bin" lint "$chart" --values "$values" --strict
"$helm_bin" template werftkern-hcloud-csi "$chart" \
  --namespace kube-system \
  --kube-version 1.37.2 \
  --values "$values" \
  --include-crds > "$tmpdir/chart.yaml"

# The upstream chart can select an existing node ServiceAccount but does not
# create it. Bind the reviewed token-free account into the exact render.
cat -- "$node_service_account" "$tmpdir/chart.yaml" > "$tmpdir/render.yaml"

python3 scripts/check-hcloud-csi-image-lock.py --rendered "$tmpdir/render.yaml"
install -m 0644 -- "$tmpdir/render.yaml" "$output"
sha256sum -- "$output"
