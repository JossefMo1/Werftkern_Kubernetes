#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for tool in go python3 dpkg-deb; do command -v "$tool" >/dev/null || { echo "Missing build dependency: $tool" >&2; exit 1; }; done
compiler="$(go env GOVERSION)"
# An up-to-date supported compiler is a release requirement. The explicit override
# only creates an unqualified laboratory artifact; it never turns it into a release.
if [[ ! "$compiler" =~ ^go1\.(2[6-9]|[3-9][0-9])\. ]]; then
  if [[ "${WERFT_ALLOW_UNSUPPORTED_TOOLCHAIN:-}" != 1 ]]; then
    echo 'Use a current supported Go toolchain (at least Go 1.26). For an isolated lab build only: WERFT_ALLOW_UNSUPPORTED_TOOLCHAIN=1' >&2
    exit 1
  fi
  echo "WARNING: unqualified laboratory build with $compiler" >&2
fi
mkdir -p build dist
commit="$(git rev-parse HEAD 2>/dev/null || printf uncommitted)"
dirty=false
[[ -z "$(git status --porcelain 2>/dev/null || true)" ]] || dirty=true
time="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w -X github.com/JossefMo1/Werftkern_Kubernetes/internal/cli.BuildCommit=$commit -X github.com/JossefMo1/Werftkern_Kubernetes/internal/cli.BuildTime=$time" -o build/werft ./cmd/werft
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags='-s -w' -o build/demo-server ./cmd/demo
python3 scripts/make-demo-image.py
stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
install -d "$stage/DEBIAN" "$stage/usr/bin" "$stage/usr/lib/systemd/system" "$stage/usr/share/werftkern" "$stage/usr/share/doc/werftkern"
install -m 0755 build/werft "$stage/usr/bin/werft"
install -m 0755 scripts/werft-ops "$stage/usr/bin/werft-ops"
install -d "$stage/usr/lib/werftkern/ops/werftops"
install -m 0644 ops/werftops/*.py "$stage/usr/lib/werftkern/ops/werftops/"
install -m 0644 packaging/systemd/*.service "$stage/usr/lib/systemd/system/"
install -m 0644 build/demo-image.tar build/demo.json "$stage/usr/share/werftkern/"
for name in postinst prerm postrm; do install -m 0755 "packaging/$name" "$stage/DEBIAN/$name"; done
cat > "$stage/DEBIAN/control" <<CONTROL
Package: werftkern
Version: 0.2.0~dev4
Section: admin
Priority: optional
Architecture: amd64
Maintainer: Werftkern Development
Depends: ca-certificates, adduser, systemd, docker.io | docker-ce, etcd-server (>= 3.4), python3
Description: Experimental standalone Werftkern container orchestrator
 Native scheduler, etcd persistence, mTLS, node agent and local dashboard.
 Target: Ubuntu 24.04 LTS amd64. Not production-qualified; no Kubernetes API.
CONTROL
for doc in LICENSE THIRD_PARTY_NOTICES.md third_party/go.LICENSE README.md SECURITY.md NOTICE.md docs/*.md; do
  [[ ! -f "$doc" ]] || install -D -m 0644 "$doc" "$stage/usr/share/doc/werftkern/$doc"
done
COMPILER="$compiler" COMMIT="$commit" DIRTY="$dirty" BUILDTIME="$time" python3 - <<'PY'
import json, os, pathlib
pathlib.Path('build/BUILD-INFO.json').write_text(json.dumps({'version':'0.2.0-dev.4','commit':os.environ['COMMIT'],'sourceDirty':os.environ['DIRTY']=='true','builtAt':os.environ['BUILDTIME'],'compiler':os.environ['COMPILER'],'target':'linux/amd64','qualified':False,'signed':False,'externalGoModules':[],'ubuntuVMEndToEnd':'not-run-in-authoring-environment','runtimeAdapter':'docker-engine-http','controlPlane':'single-or-three-controller-etcd-unqualified','stateSchema':2,'archiveFormat':'WERFTVOL1','upgradeFromDev1':'explicit-offline-schema-migration-required','upgradeFromDev2':'same-schema-coordinated-offline-uniform-version-required','upgradeFromDev3':'bounded-signed-worker-waves-after-all-controllers-target-unqualified','workerBinaryCompatibility':'actual-dev3-and-dev4-agent-processes-with-Docker-etcd-fixtures','databaseHAAdapter':'native-Patroni-profile-not-live-qualified','pitrAdapter':'pgBackRest-no-real-WAL-proof','leafRenewal':'offline-issuer-combined-PEM-live-reload-local-TLS-tested'},indent=2)+'\n')
PY
install -m 0644 build/BUILD-INFO.json "$stage/usr/share/werftkern/"
dpkg-deb --root-owner-group --build "$stage" 'dist/werftkern_0.2.0~dev4_amd64.deb'
cp build/BUILD-INFO.json dist/BUILD-INFO.json
cp build/demo.workload.json dist/demo.workload.json
sha256sum 'dist/werftkern_0.2.0~dev4_amd64.deb' > dist/SHA256SUMS
printf 'Built unsigned experimental package. Clean Ubuntu VM qualification is still required.\n'
