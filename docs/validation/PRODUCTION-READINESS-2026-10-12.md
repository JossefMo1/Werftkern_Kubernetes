# Production qualification review — 2026-10-12

Status: **BLOCKED; production readiness has not been established.**

This review concerns `JossefMo1/Werftkern_Kubernetes`, the independent Apache-2.0
Go/Python Werftkern project. It is not the complete commercial ClusterPilot
ASP.NET/Next.js repository. Customer Delivery, commercial subscriptions and SaaS
tenancy cannot be qualified from this checkout.

Public source preparation and production qualification are separate decisions.
The repository remains private. No production release, signing, deployment,
certification or successful unexecuted test is asserted by this report.

## Implemented corrections

| Change | Production ownership | Evidence |
| --- | --- | --- |
| Professional README, contribution/security/community and publication guidance | Root documentation and `.github/` templates | [PR #12](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/12), merged after its checks passed |
| Reject malformed provider response objects and server inventories before paid creation | `ops/werftops/cloud.py`, `tests/ops/test_operations.py`, `docs/CLOUD.md` | [PR #13](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/13), merged; regression cases failed against the old adapter |
| Keep rollouts updating until retired allocations acknowledge stopped | `internal/control/scheduler.go`, `scheduler_test.go`, `docs/ARCHITECTURE.md` | [PR #15](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/15), merged; new regression reproduced premature readiness |
| Fixed, secret-safe Ubuntu E2E phase markers | `tests/e2e/ubuntu-vm.sh` | PR #15; additive phase metadata, no command/secret output |
| Pin Go 1.27.2 and govulncheck v1.9.0 before native package construction; isolate manual and push concurrency | `.github/workflows/ci.yml`, `docs/TESTING.md` | [PR #17](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/17), merged after its checks passed |

Provider changes preserve the existing engine, provider credential handling and
durable journal. Invalid create acknowledgments retain `create-ambiguous`; a
subsequently empty inventory cannot trigger a blind repeated create. No new
provisioning engine or hidden compensation was added.

Readiness changes preserve availability, resource reservations and the existing
agent acknowledgment boundary. They do not treat intent as physical stop, force
delete containers, grant fencing authority or add another status model.

## Development-layer findings

| Layer | Actual implementation and boundary | Remaining qualification |
| --- | --- | --- |
| Native API/domain/store | `internal/control`, `internal/model`, `internal/store`: mTLS roles, bounded etcd-CAS state, admission/idempotency, reconciliation | No commercial multi-tenant IAM; no measured production capacity envelope |
| Agent/runtime | `internal/agent`, `internal/engine`: durable desired/report journal and Docker execution | Agent Docker-socket authority, reboot/partition and multi-host qualification; direct containerd remains an unimplemented roadmap requirement |
| CLI/dashboard | `internal/cli`, `internal/dashboard`: typed client, local dashboard host/origin boundary and scoped proxy | Browser transport and independent security qualification; DOM fixture tests are not live cluster tests |
| Provider/operations | `ops/werftops/cloud.py`, `bootstrap.py`, `rollout.py`: durable creation/upgrade intent, explicit approvals and recovery | Real provider creation, uncertain-response adoption, SSH trust and signed upgrades in an approved lab |
| Kubernetes management | `ops/werftops/kube_driver.py`, `kube_lifecycle.py`, `kube_machines.py`, recovery/repair/cloud-scale/add-on modules | k0s install, real cloud replacement/fencing, retained volume/database integrity, real Keycloak/RBAC and ACME |
| Persistence/recovery | etcd state, encrypted native archives, PostgreSQL/Patroni/pgBackRest adapters | Separate-host restore, actual WAL replay, abrupt interruption, HA watchdog/partition and site recovery |
| Packaging/supply chain | Existing `build-deb.sh`, `build-kubernetes-deb.sh`, native verification and `kube_release_evidence.py` | Protected signing, immutable candidate acceptance, complete SBOM/CVE/provenance and independent review |
| CI | Native tests/package, real-etcd processes, Kubernetes contracts/package and publication audit | Optional real VM/PITR execution, protected environments and exact-candidate evidence; contract tests do not qualify real cloud behavior |

Existing production contracts are deliberately retained:

- `release/qualification.json` requires 52 full-masterplan features and 13 gates.
  `scripts/check-release.py` currently rejects qualification and does not itself
  authenticate independent producers or grant production approval.
- `release/kubernetes-readiness.json` lists 14 unmet real-qualification requirements.
  `ops/werftops/kube_release_evidence.py` requires external trust, candidate binding,
  signatures and independent roles. Its own synthetic test bundle never grants
  production readiness or CNCF certification.
- `.github/workflows/auto-alpha-release.yml` is private, source-only and explicitly
  prerelease. It is not a production publication pipeline. Existing alpha tags
  were not overwritten or repointed.

## Executed validation

Linux validation used WSL Ubuntu. Go 1.27.2 was downloaded from the official
distribution and the archive checked against SHA-256
`ecbadb99091a3f46e31f5f934b068b1864eafa7995211b39eaddf76996045fe5`.
Toolchain files remain outside the repository. Failed attempts using an absent or
incompletely extracted toolchain were environment failures, not successful tests.

| Command | Actual outcome | Limit |
| --- | --- | --- |
| `go test -race -count=1 ./internal/control ./internal/agent ./internal/cli ./internal/model` | Passed | Focused scheduler dependency checks |
| `go test -race -count=1 ./...` | Passed | Full local Go suite after scheduler correction; fixtures remain fixtures |
| `go vet ./...` | Passed | Static Go checks |
| `go run golang.org/x/vuln/cmd/govulncheck@v1.9.0 ./...` | Exit 0; no vulnerabilities found | Reachable Go vulnerabilities with Go 1.27.2, not OS/Kubernetes image CVEs |
| `python3 -m unittest discover -s tests/ops -v` | 67 passed | A preceding OpenSSL verification error did not reproduce on diagnostics/repeat; its cause is unresolved, not dismissed by weakening checks |
| `PYTHONPATH=ops python3 -m unittest discover -s tests/kubernetes -v` | 198 passed | Explicit tool/provider/Kubernetes fixtures and signature tests |
| `python3 -m unittest discover -s tests/release -v` | 16 passed in WSL | Windows execution has Linux permission/symlink/fixture-environment differences |
| `python3 tests/browser/test_ui.py` | Could not run: missing `playwright` module in WSL | No current browser result claimed |
| `node --check internal/dashboard/assets/app.js` | Passed during publication preparation | Syntax, not browser/runtime qualification |
| `bash -n tests/e2e/ubuntu-vm.sh` | Passed after phase-marker change | Shell syntax only |
| CI YAML parse and assertions | Passed | Read-only permissions, bounded jobs and event-separated concurrency; not GitHub protection enforcement |
| `git diff --check` | Passed for each submitted change | Patch hygiene |
| `python scripts/check-public-source.py` | Passed; 285 files, zero findings with this report present | Pattern lint only |
| Verified Gitleaks 8.30.1 working-tree scan, `--redact=100` | Exit 0, zero findings after implementation changes | Raw logs/reports retained outside Git; not independent security review |
| `python scripts/check-release.py --commit <actual HEAD>` | Exit 1, `BLOCKED`, `productionReady=false` | Correct rejection: missing commit-bound qualification, 52 unqualified features and 13 unsatisfied gates |

Publication source/history checks, verified Gitleaks execution and their exact
limits are recorded in [the preceding review](PUBLICATION-REVIEW-2026-10-12.md).
Dependabot alerts and automatic security updates were enabled; the inspected alert
list was empty. This is not a vulnerability-free certification.

## Real-execution record

The dispatched [Ubuntu run 38250525787](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/38250525787)
tested main `da06809070abeedf95a69f45d9cf5227e574fc02`. Unit/package and real-etcd jobs
passed. Ubuntu installation, authenticated node registration, demo, service
restart, scaling, rollback and etcd restart proceeded; the VM job failed after
secret rollout readiness. It is a failed qualification, not a partial production pass.

The source-confirmed retiring-allocation defect was fixed in PR #15. The original
log lacks an exact assertion marker, so it does not independently prove that defect
was the sole live failure cause. Phase markers now permit precise diagnosis.

[Run 38252606501](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/38252606501)
on main `9922fe7d6d23a49890e640b149724de83895d069` was canceled when a delayed main push
used the same concurrency group. It has no successful VM qualification. PR #17
separates event groups. Any replacement qualification must be recorded against its
actual source SHA and artifact digest; do not copy a success from another run.

The subsequent [run 38253540392](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/38253540392)
on main **`2df522128514507507aaf6aee1fadcea6b3c1c6d`** completed successfully:
native tests/static/security/package, real-etcd and real-vm jobs passed; real-pitr
was deliberately not requested and was skipped. The downloaded sanitized result
records `stage=complete`, `exitCode=0`, `status=passed`, starting
`2026-10-12T13:10:49Z` and finishing `2026-10-12T13:12:59.833406+00:00`.
The installed CLI reports the same commit and Go 1.27.2.

Actual single-host coverage: Ubuntu package installation, authenticated worker
registration, real constrained Docker demo containers, process restart, scale,
rollback, etcd restart, immutable secret rollout/mount checks, encrypted configuration
backup inspection, pause/resume and complete workload/container deletion. This is
not a data restore, real predecessor-package upgrade, cloud, multi-host HA, Kubernetes,
PITR, signing or production approval result.

Candidate identity, downloaded and checked against its `SHA256SUMS`:

- Package: `werftkern_0.2.0~dev4_amd64.deb`, 4,930,118 bytes.
- SHA-256: `d2b379905d2c96792678fe599904a34bf3a54ff4e0bfc79506690267372dfef1`.
- Build metadata: `sourceDirty=false`, `compiler=go1.27.2`, `signed=false`,
  `qualified=false`. It remains an unsigned development artifact.
- GitHub package/evidence archive digest:
  `35fe626ecd3379190c47973884a9ccb952865d17b72f0bdb7573809663971d5b`.
- GitHub sanitized VM evidence archive digest:
  `6fd70900657b4f7f5f3035da4597dd3057818a36580ef21a0d8cba93ee4efe6c`.

Archive digests are distinct from the Debian package digest. CI artifact retention
is not a durable signed production distribution channel.

## Release and issue disposition

- [Issue #7](https://github.com/JossefMo1/Werftkern_Kubernetes/issues/7): open. Main
  is unprotected; ruleset/protection APIs returned HTTP 403 for the current private
  repository plan. Visibility was not changed to bypass this restriction.
  CODEOWNERS currently names one maintainer; an independent second reviewer is
  not created by that file. No protected environment or self-hosted runner is configured.
- [Issue #8](https://github.com/JossefMo1/Werftkern_Kubernetes/issues/8): open. The
  historical dev.3 baseline is absent from published history. Existing approved-bundle
  support/local fixture evidence is preserved, but real predecessor-package upgrade
  and rollback remain unqualified. Private history was not imported.
- [Issue #14](https://github.com/JossefMo1/Werftkern_Kubernetes/issues/14): source
  correction merged in PR #15 and merged-candidate real VM test passed in run
  38253540392; its correction/qualification acceptance is satisfied.
- [Issue #16](https://github.com/JossefMo1/Werftkern_Kubernetes/issues/16): production
  qualification tracking, including lab, protected supply chain, independent review,
  candidate evidence and product-scope decisions. Open prerequisites are not completed work.

## Security and reliability priorities

| Priority | Evidence and failure scenario | Required action |
| --- | --- | --- |
| BLOCKER | Unprotected main and absent protected signing/test environments permit unreviewed code or evidence to become a candidate | Enforce repository/environment protections and separate approver/signing roles before production publication |
| BLOCKER | Qualification manifests lack real candidate-bound evidence; contract fixtures can succeed without real HA/storage/cloud behavior | Execute the existing independent gates; preserve blocked state until acceptance |
| HIGH, corrected in source | `cloud.py` treated missing inventory as empty and accepted non-object JSON; a bad read could admit a paid create and malformed replies could escape stable errors | PR #13 validates response/list shape; regression covers ambiguous POST retention and one-create-only replay |
| HIGH, corrected in source | `scheduler.go` could report ready while prior containers still had unacknowledged stop intent | PR #15 gates readiness on confirmed retirement; real VM qualification is a separate requirement |
| HIGH qualification boundary | Agent controls the Docker socket; native admin/node/gateway roles are not customer tenant/workspace isolation | Treat hosts/admin credentials as privileged; independently review authorization and host compromise paths; do not expose this as an already isolated public SaaS |
| MEDIUM review item | `ops/werftops/common.py:run` uses `communicate()` with captured stdout/stderr and timeouts but no byte limit; unexpectedly large tool output can consume operator-process memory | Design command-appropriate byte/artifact bounds and interruption tests; no remote exploit is asserted by this source observation |
| MEDIUM qualification gap | Dashboard server tests and JavaScript syntax checks do not prove actual browser transport/login behavior; current browser execution is dependency-blocked | Run the existing DOM fixture and a separately approved live browser/security journey; distinguish the two evidence scopes |

These priorities are concrete release/review obligations, not a claim that a
comprehensive independent penetration test has been performed.

## Required production sequence

1. Preserve and review the completed exact-commit Ubuntu qualification above.
   Requalify any changed candidate. Its single-host success does not prove HA,
   Kubernetes or database recovery.
2. Configure enforceable main/tag/check/review protection and approved lab environments.
   Obtain isolated hosts, trusted SSH, provider account access and explicit cloud
   budget without placing credentials in Git, tickets or evidence.
3. Qualify predecessor upgrade/rollback with reviewed baseline material. Preserve
   explicit version/state-schema boundaries and failed-operation journals.
4. Execute existing real k0s/cloud/HA/PITR/new-host recovery/negative RBAC/ACME/soak
   procedures. Record failures and resource cleanup explicitly, with no synthetic fallback.
5. Agree a supported product scope against the outstanding full masterplan. Implement
   genuinely missing requirements through small tested PRs. Any change to release scope
   needs reviewed compatibility/support criteria, not deletion of failing gates.
6. Build the accepted candidate once in a protected pipeline; generate real SBOM,
   OS/image CVE coverage and provenance; verify signatures against separately controlled
   trust; obtain independent security and maintainer approval.
7. Promote the same accepted immutable bytes, publish accurate release notes and
   rollback/support procedures, and verify a fresh signed installation. Do not turn
   the existing source-only alpha workflow into production authority by relabeling it.

A read-only support reviewer independently verified the scheduler source defect and
its agent/API acknowledgment path. The main agent verified it in code and reproduced
the negative test before implementing the correction. The reviewer edited no files.
