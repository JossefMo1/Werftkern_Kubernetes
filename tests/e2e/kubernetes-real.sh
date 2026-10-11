#!/usr/bin/env bash
# REAL tool/SSH/Kubernetes path; missing prerequisites fail, never become a pass.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ "${WERFT_DISPOSABLE_CLUSTER:-}" != 1 || -z "${WERFT_KUBE_ASSETS:-}" || -z "${WERFT_KUBE_PLAN:-}" || -z "${WERFT_KUBE_ROOT:-}" ]]; then
    echo '{"status":"BLOCKED","reason":"Explicit disposable cluster, reviewed assets, host plan and management root are required; no Kubernetes/SSH fixtures are used.","productionReady":false}'
    exit 3
fi
cli="$root/scripts/werft-kube"
digest="$($cli plan "$WERFT_KUBE_PLAN" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sha256"])')"
"$cli" --root "$WERFT_KUBE_ROOT" --assets "$WERFT_KUBE_ASSETS" apply --plan "$WERFT_KUBE_PLAN" --confirm "$digest"
uid="$($cli --root "$WERFT_KUBE_ROOT" --assets "$WERFT_KUBE_ASSETS" status | python3 -c 'import json,sys; print(json.load(sys.stdin)["clusterUID"])')"
"$cli" --root "$WERFT_KUBE_ROOT" --assets "$WERFT_KUBE_ASSETS" acceptance run --confirm "DISPOSABLE:$uid"
"$cli" --root "$WERFT_KUBE_ROOT" --assets "$WERFT_KUBE_ASSETS" backup
# A separate intentional conformance command controls disruption and run identity.
# No VM deletion or cloud creation is hidden in this script. Clean up owned lab
# resources explicitly; failures preserve evidence and locks for investigation.
echo '{"status":"passed","scope":"Kubernetes create/apply, direct controller/worker observations, 3-worker DNS/traffic smoke and backup command; NOT conformance, SSO, node failure or production qualification.","productionReady":false}'
