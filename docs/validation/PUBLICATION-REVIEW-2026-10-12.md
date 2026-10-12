# Public-source preparation review — 2026-10-12

## Decision and scope

Repository: [JossefMo1/Werftkern_Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes).
Reviewed GitHub main baseline: `45c830694db54d726a3a3eec92907a4545c651f9`.
Preparation branch: `docs/public-launch-readiness`.

**Prepared for maintainer review; PUBLIC visibility is still on hold.**
This review covers public-source presentation, contribution guidance, selected
repository controls, source/history scanning and release claim consistency.
It is not a comprehensive implementation security audit, legal clearance or
production qualification. No SaaS implementation or ClusterPilot rewrite is
part of this change. This checkout is the independent Go/Python Werftkern
project, not the complete private ClusterPilot product.

The initial local worktree was clean and ten commits behind GitHub main.
It was updated by `git merge --ff-only origin/main` before creating the
preparation branch. No history was rewritten and no unrelated changes were
removed. No credentials or matched secret content were printed.

## Source and release evidence

- `go.mod`, imports, linker flags and module identity tests use the actual
  GitHub repository path. Migration commit: `8b20f60`.
- Native CLI: `internal/cli/cli.go`, `0.2.0-dev.4`; native Debian builder:
  `scripts/build-deb.sh`, `0.2.0~dev4`, explicit toolchain policy.
- Kubernetes CLI: `ops/werftops/kube_main.py`, `0.1.0-dev.3`; separate
  package builder: `scripts/build-kubernetes-deb.sh`, `0.1.0~dev3`.
- Runtime, lifecycle and cloud source were inspected to distinguish the
  Go/Docker/etcd path from the Python/k0s management path. README claims do
  not imply tenant RBAC, complete disaster recovery or a managed SaaS.
- Apache-2.0 is present. `NOTICE.md` records ClusterPilot-derived provenance;
  it does not independently establish redistribution rights. No license or
  attribution was removed or replaced.
- Private source prereleases alpha.1 and alpha.2 exist. Alpha.2 points to
  `8b20f60ffd86f28e9776cfa08314ae2ff234c087` and has no uploaded binary assets.
  Tags and release notes were not changed. Visibility conversion will expose
  existing releases and reachable refs as well as current main.
- `release/qualification.json` and `release/kubernetes-readiness.json`
  remain unqualified. No evidence files or readiness flags were manufactured.

## GitHub state inspected and preparation performed

| Control | Observed result |
| --- | --- |
| Visibility | PRIVATE; unchanged |
| Main branch | `protected: false` |
| Rulesets | HTTP 403: private repository requires a different plan or public visibility |
| Default Actions permissions | Read-only; Actions cannot approve PR reviews |
| Allowed Actions policy | All actions allowed; server-side SHA pinning not enforced |
| Source workflow Actions | Explicit commit references; checkout credentials not persisted |
| Dependabot alerts | Initially disabled; enabled during preparation; subsequent API query returned `[]` |
| Dependabot automatic security updates | Enabled and verified: `enabled: true`, `paused: false` |
| Private vulnerability reporting | HTTP 404 on this private repository; enable/verify after PUBLIC |
| Description and topics | Added accurate experimental description and Kubernetes/k0s/Go/Ubuntu topics |

The empty Dependabot alert list does not prove the Python/tool/image ecosystem
has no vulnerabilities. There are no external Go modules in `go.mod`.
Separately supplied tools and operating-system packages require their own
version/license/vulnerability review. No CodeQL workflow is currently configured.
The publication audit is a heuristic scanner, not static security analysis.

## GitHub checks verified for the exact baseline

| Run | Result and scope |
| --- | --- |
| [Native CI, run 38156052434](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/38156052434) | `test` and `real-etcd` successful; `real-vm` and `real-pitr` skipped |
| [Kubernetes CI, run 38156052427](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/38156052427) | `contracts` successful |
| [Publication audit, run 38156052417](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/38156052417) | `publication-audit` successful |

These are baseline results, not results for this preparation branch. Ordinary
native CI records missing dev.3 ancestry as BLOCKED and skips historical binary
compatibility and predecessor package verification. Separately verified local
bundle results are described in `LOCAL-DEV3-DEV4-COMPAT.md`; they must not be
represented as current GitHub compatibility qualification.

## Executed local checks

Windows PowerShell with Python 3.13.7; Linux checks used Ubuntu under WSL.

| Command | Result |
| --- | --- |
| `git status --short --branch` | Initially clean `main`; behind ten commits after fetch |
| `python scripts/check-public-source.py` | PASS at baseline: 281 files, zero known-pattern findings |
| `python scripts/audit-git-history.py --require-noreply` | Exit 1, BLOCKED: 396 blobs, ten non-`users.noreply.github.com` metadata entries; no blob findings |
| `python3 scripts/audit-git-history.py` under WSL | PASS: 396 blobs, zero findings |
| Metadata classification without printing addresses | All ten strict-check entries are GitHub service addresses ending in `@github.com`; zero other entries |
| `gitleaks version` | `8.30.1` |
| `gitleaks git --log-opts=--all --redact=100 --no-banner --report-format json --report-path <private-temp>/history.json .` | Exit 0, zero findings across reachable refs |
| `gitleaks dir --redact=100 --no-banner --report-format json --report-path <private-temp>/source.json .` | Exit 0, zero findings in scanned working directory |
| `python -m unittest discover -s tests/release -v` on Windows | 16 tests, seven errors: unavailable symlink privilege, fixture Git commits and Linux/Bash environment behavior |
| `python3 -m unittest discover -s tests/release -v` under WSL | All 16 tests PASS |
| `python scripts/check-release.py --commit <baseline SHA>` | Exit 1, BLOCKED, `productionReady: false`; includes unmatched historical evidence and unqualified gates |
| `git diff --check` | PASS during documentation preparation |
| Final `python scripts/check-public-source.py` | PASS: 284 files, zero findings |
| Final WSL `python3 -m unittest discover -s tests/release -v` | All 16 tests PASS after documentation changes |
| Local Markdown target check across ten affected documents | 72 links checked, no missing files |
| PyYAML `safe_load` over `.github/**/*.yml` | Eight YAML files parsed successfully; this is syntax checking, not complete GitHub schema validation |
| `node --check internal/dashboard/assets/app.js` | Exit 0 |
| WSL `bash scripts/werft-kube version` | Exit 0; Kubernetes `0.1.0-dev.3`, native `0.2.0-dev.4`, `productionReady: false` |

Gitleaks was downloaded from the official `gitleaks/gitleaks` release. Before
execution, its Windows x64 archive SHA-256 was compared to the GitHub asset
digest: `d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`.
Redacted reports and console output stayed outside the repository in a local
temporary directory. No raw scanner results were committed.

The strict noreply check rejects GitHub service addresses as well as personal
ones. Do not erase bot commits or weaken the scanner to hide this result;
record the reviewed exception. Normal CI does not run this optional email flag.
Scanners cannot establish absence of every secret or sensitive business detail.

## Preparation changes

- Reorganized README around project identity, separate operating paths,
  supported lab target, setup, capabilities, limitations and documentation.
- Added community conduct guidance and issue-template links that steer
  sensitive reports to the security policy.
- Updated contribution guidance for both Go and Python paths, Linux checks,
  explicit evidence, Signed-off-by and optional cryptographic commit signing.
- Corrected stale launch/checklist instructions: the module migration is merged,
  private releases already exist, and existing tags must not be recreated.
- Corrected private vulnerability reporting timing and recorded live settings.

No production code, provisioning behavior, release identity, existing tag,
deployment or production environment was changed.

## Remaining public-launch gates

1. Obtain repository-owner confirmation of redistribution rights for the
   ClusterPilot-derived source/design and review third-party notices and
   confidentiality obligations. Source comments and license files do not
   constitute this approval.
2. Complete manual sensitive-content review of all refs, release notes,
   existing issues/PRs and downloadable artifacts intended to become public.
   The scans above cover source/history patterns, not every GitHub surface.
3. Merge reviewed preparation changes through a PR and verify required CI
   for its exact SHA. Record the chosen launch main commit and unchanged tags.
4. Arrange effective main protection/reviews and release controls under the
   available GitHub plan. If unavailable while PRIVATE, stage the settings and
   apply/verify them immediately at conversion. Do not require signed commits.
5. Establish a real private reporting channel and enable/verify private
   vulnerability reporting, available secret scanning and push protection at
   PUBLIC conversion. Review Actions allowlists and self-hosted runner access.

The private-alpha workflow deliberately rejects public publishing. This is
a preserved boundary; design a separately reviewed public release process
before the next public tag. Do not rename it into a public pipeline or bypass
the ownership/security gate merely to remove a failing run.

Public experimental source does not require pretending production qualification
is complete. Keep production gates blocked until independently evidenced.

## Checks not run

No local Go build/race/vet or vulnerability scan: Go is absent from Windows
and the inspected WSL environment. No local Debian build, Docker/etcd runtime,
browser integration, live Hetzner, VM, Kubernetes, HA/PITR, recovery, load or
production tests were run. This documentation change does not justify cloud
costs or host mutation. Baseline CI evidence is listed separately above;
the new PR's CI must validate the final preparation commit.

An independent read-only reviewer inspected release/publication workflows,
source scanners, provenance and launch documents. It identified stale version
and module instructions, the optional email-check gap and distinct source/GA
gates. The main agent verified those findings against source and GitHub and
integrated the documentation corrections; the reviewer edited no files.
