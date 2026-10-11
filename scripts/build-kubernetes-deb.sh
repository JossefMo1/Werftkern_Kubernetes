#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
version='0.1.0~dev3'
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
stage="$work/package"
mkdir -p "$stage/DEBIAN" "$stage/usr/bin" "$stage/usr/lib/werftkern-kubernetes/ops/werftops" \
 "$stage/usr/share/doc/werftkern-kubernetes" "$stage/usr/share/werftkern-kubernetes/examples" "$stage/lib/systemd/system" "$root/dist"
cp "$root/scripts/werft-kube" "$stage/usr/bin/werft-kube"
# Source only; no interpreter caches, credentials, native binaries or private assets.
cp "$root"/ops/werftops/*.py "$stage/usr/lib/werftkern-kubernetes/ops/werftops/"
cp "$root"/docs/kubernetes/*.md "$stage/usr/share/doc/werftkern-kubernetes/"
cp "$root/LICENSE" "$stage/usr/share/doc/werftkern-kubernetes/copyright"
cp "$root/NOTICE.md" "$stage/usr/share/doc/werftkern-kubernetes/NOTICE.md"
cp "$root"/examples/kubernetes/*.json "$stage/usr/share/werftkern-kubernetes/examples/"
cp "$root"/packaging/kubernetes/*.service "$stage/lib/systemd/system/"
cat > "$stage/DEBIAN/control" <<EOF
Package: werftkern-kubernetes
Version: $version
Section: admin
Priority: optional
Architecture: all
Maintainer: Werftkern Contributors <noreply@localhost>
Depends: python3 (>= 3.10), python3-yaml, openssh-client, openssl, ca-certificates
Description: Experimental Kubernetes management backend for Werftkern
 Uses separately reviewed k0s, k0sctl, kubectl, Helm, age and Sonobuoy assets.
 No production qualification or CNCF certification. No automatic service start.
EOF
find "$stage" -type d -exec chmod 755 {} +
find "$stage" -type f -exec chmod 644 {} +
chmod 755 "$stage/usr/bin/werft-kube"
dpkg-deb --root-owner-group --build "$stage" "$root/dist/werftkern-kubernetes_${version}_all.deb"
